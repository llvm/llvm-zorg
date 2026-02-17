from collections.abc import MutableSequence, Sequence
from enum import Enum
import time
import os
import logging
import sys
import asyncio

from attr import dataclass
from dotenv import load_dotenv
import argparse
from bazel_agent import AgentErrors
from utils import (
    CredentialManager,
    LocalGitRepo,
    BuildState,
    BuildInfo,
    BuildProcessor,
    LocalBuildProcessor,
    CommandProcessor,
    parse_targets,
)

import bazel_agent
import utils

parser = argparse.ArgumentParser(description="Bazelbot")
parser.add_argument(
    "--llvm_git_repo", type=str, help="Absolute path to LLVM repo", required=True
)
parser.add_argument(
    "--bot_state_file", type=str, help="Bot state file", default="bot_state.log"
)
parser.add_argument("--poll_interval", type=int, help="Polling interval", default=120)
parser.add_argument("--create_prs", action="store_true", help="Whether to create PRs.")
parser.add_argument(
    "--log_level", default="INFO", help="Set the logging level -- WARNING, INFO, DEBUG"
)
parser.add_argument(
    "--test_commits", type=str, help="File path containing commits to test."
)

logger = logging.getLogger(__name__)

load_dotenv()

# This is the max iteration on the bot side. We will run agent MAX_ITERATIONS times to see if it can give us a fix
# Note that agent has its own max iterations. The difference being that agent iterations iterates on an already made fix
# while we start fresh everytime.
MAX_AGENT_ITERATIONS = 3

# When agent returns resource exhausted, number of times we retry before giving up.
MAX_AGENT_RESOURCE_EXHAUSTED_TRIES = 3


class FixTool(Enum):
    BANT = "bant"
    AI = "ai"
    NOT_FIXED = "not fixed"


@dataclass
class RepairSummaryRecord:
    # Commit that was repaired
    commit: str
    # What fixed it: 'bant', 'ai', 'not fixed'
    fixed_by: FixTool
    # timestmap
    timestamp: float


class BazelRepairBot:
    def __init__(
        self,
        command_processor: CommandProcessor,
        git_repo: LocalGitRepo,
        creds: CredentialManager,
        build_processor: BuildProcessor,
        state_file,
        poll_interval,
    ):
        # Injectables
        self.command_processor = command_processor
        self.creds = creds
        self.git_repo = git_repo
        self.build_processor = build_processor

        # Simple variables
        self.last_processed_build = 0
        self.last_processed_state: BuildState = BuildState.UNKNOWN
        self.last_processed_sha: str = ""
        self.state_file = state_file
        self.poll_interval = poll_interval

    def load_state(self):
        """Loads the last commit sha from file and find the status of that build."""
        if not os.path.exists(self.state_file):
            logger.info("No state file found. Will initialize state on first run.")
            return

        try:
            with open(self.state_file, "r") as f:
                self.last_processed_sha = f.read().strip()

            # Local build to find the last processed build state
            logging.info(
                f"Finding build state for {self.last_processed_sha} by running build locally..."
            )
            self.git_repo.checkout_commit(self.last_processed_sha)
            build_result = self.command_processor.run_bazel_build()
            self.last_processed_state = (
                BuildState.PASSED if build_result.success else BuildState.FAILED
            )
            logger.info(
                f"Loaded state: last processed sha {self.last_processed_sha} with state {self.last_processed_state}."
            )
        except Exception as e:
            logger.error(f"Failed to load state file: {e}.")
            self.last_processed_sha = ""

    def save_state(self):
        """Saves current commit sha into a file."""
        try:
            with open(self.state_file, "w") as f:
                f.write(self.last_processed_sha)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def wait(self, seconds):
        """Sleeps for a given number of seconds"""
        time.sleep(seconds)

    def process_failure_with_bant(self, build_data: BuildInfo) -> bool:
        self.git_repo.create_branch_for_fix(build_data.commit)
        if not self.command_processor.run_bant(targets=build_data.failed_targets):
            logger.warning("Running bant failed.")
            return False

        if not self.validate_before_publishing():
            logger.info("Validation before publishing failed.")
            return False

        self.git_repo.commit(f"[Bazel] Fix build for {build_data.commit[:7]}")
        if not self.git_repo.push_fix(build_data.commit):
            logger.warning("Failed to publish bant fix.")
            return False

        return True

    def repair_build(self, build: BuildInfo) -> bool:
        if build.state != BuildState.FAILED:
            logger.info(f"Build for {build.commit} is not failed. Nothing to repair.")
            return False

        record = RepairSummaryRecord(build.commit, "", time.time())
        if self.process_failure_with_bant(build):
            logger.info(f"Successfully repaired build for {build.commit}) using bant.")
            record.fixed_by = FixTool.BANT
        elif self.process_failure_with_ai(build):
            logger.info(
                f"Successfully repaired build for {build.commit} using AI agent."
            )
            record.fixed_by = FixTool.AI
        else:
            record.fixed_by = FixTool.NOT_FIXED

        with open("summary." + self.state_file, "a") as summary_file:
            summary_file.write(
                f"{record.timestamp},{record.commit},{record.fixed_by}\n"
            )

        return record.fixed_by != FixTool.NOT_FIXED

    def run_buildifier_on_changed_files(self) -> bool:
        repo = self.git_repo.repo
        changed_files = repo.git.diff(name_only=True).splitlines()
        changed_files.extend(repo.untracked_files)
        return self.command_processor.run_buildifier(files=changed_files)

    def validate_before_publishing(self) -> bool:
        if not self.git_repo.is_repo_dirty(untracked_files=True):
            logger.info("validate: no changes detected.")
            return False

        bazel_build = self.command_processor.run_bazel_build()
        if not bazel_build.success:
            logger.info("validate: build fails.")
            logger.info(bazel_build.stderr)
            return False

        if not self.run_buildifier_on_changed_files():
            logger.info("validate: buildifier failed.")
            return False

        # Check bazel build again after running buildifier
        bazel_build = self.command_processor.run_bazel_build()
        if not bazel_build.success:
            logger.info("validate: build fails after buildifier.")
            logger.info(bazel_build.stderr)
            return False

        return True

    def process_failure_with_ai(self, build_data):
        logger.info("Invoking AI Agent...")
        attempt_num = 0
        agent_exhausted_tries = 0
        past_fixes = []

        # Push an empty branch to indicate that AI fix is in progress
        self.git_repo.create_branch_for_fix(build_data.commit)
        self.git_repo.commit(
            f"AI is working on fixing build for {build_data.commit[:7]}. Check back later!"
        )
        self.git_repo.push_fix(build_data.commit, False)

        while True:
            if attempt_num == MAX_AGENT_ITERATIONS:
                logger.info(
                    f"Reached max AI agent attempts ({MAX_AGENT_ITERATIONS}) for commit {build_data.commit}. Giving up."
                )
                break

            self.git_repo.create_branch_for_fix(build_data.commit)
            # We pass the local path so the agent can read files, and the commit to analyze
            agent_result = asyncio.run(
                bazel_agent.query_agent(
                    commit_sha=build_data.commit,
                    cmd_processor=self.command_processor,
                    past_fixes=past_fixes[:],
                )
            )

            logger.info("------------------")
            logger.info(f"AI Agent attempt #{attempt_num} summary")
            logger.info(agent_result.summary)
            logger.info("------------------")

            if agent_result.status == AgentErrors.AGENT_RESOURCE_EXHAUSTED:
                self.wait(self.poll_interval * 5)
                agent_exhausted_tries += 1
                if agent_exhausted_tries > MAX_AGENT_RESOURCE_EXHAUSTED_TRIES:
                    logger.warning(
                        f"Giving up commit {build_data.commit} after too many resource exhausted errors"
                    )
                    break

                continue
            elif (
                agent_result.status != AgentErrors.SUCCESS
                and self.git_repo.is_repo_dirty(untracked_files=True)
            ):
                # Get dirty status of the repo in storage
                past_fixes.append(self.git_repo.diff())
            elif agent_result.status == AgentErrors.SUCCESS:
                break

            attempt_num += 1

        bazel_build = self.command_processor.run_bazel_build()
        commit_msg = f"Fix Bazel build for {build_data.commit[:7]}"
        if not bazel_build.success:
            logger.info("Local verification FAILED after running AI agent.")
            logger.info(bazel_build.stderr)
            commit_msg = f"[DO NOT MERGE] Attempted AI fix for {build_data.commit[:7]}"

        self.git_repo.commit(commit_msg)
        should_create_pr = bazel_build.success and self.git_repo.can_create_pr
        if not self.git_repo.push_fix(build_data.commit, should_create_pr):
            logger.warning(
                f"Failed to publish AI changes for commit: {build_data.commit}"
            )
            return False

        return bazel_build.success

    def set_state_from_latest_build(self) -> bool:
        logger.info("Initializing state with the latest build.")
        latest_build = self.build_processor.get_latest_build_status()
        if latest_build:
            self.last_processed_sha = latest_build.commit
            self.last_processed_state = latest_build.state
            self.save_state()
            return True

        logger.error("Could not init state from latest build.")
        return False

    def get_build_info_for_commit(self, commit_sha: str) -> BuildInfo | None:
        logger.info(f"Finding build state for commit {commit_sha} locally ...")
        current_build = BuildInfo(commit=commit_sha)
        self.git_repo.checkout_commit(commit_sha)
        build_result = self.command_processor.run_bazel_build()
        current_build.state = (
            BuildState.PASSED if build_result.success else BuildState.FAILED
        )
        if not build_result.success:
            current_build.failed_targets = parse_targets(build_result.stderr)
        return current_build

    def run(self) -> None:
        while True:
            # On first run (or state reset), initialize with the latest build number.
            if not self.last_processed_sha:
                if not self.set_state_from_latest_build():
                    continue

            builds_to_process: Sequence[
                BuildInfo
            ] = self.build_processor.get_builds_to_process(self.last_processed_sha)
            if not builds_to_process:
                logger.debug("No new builds to process. Sleeping ...")
                self.wait(self.poll_interval)
                continue

            logger.info(f"Found {len(builds_to_process)} new builds to process.")
            for build in builds_to_process:
                if not build:
                    continue

                current_build = (
                    self.get_build_info_for_commit(build.commit)
                    if build.state == BuildState.UNKNOWN
                    else build
                )
                logger.info(
                    f"Processing build {current_build.commit} with state '{current_build.state}'."
                )

                if (
                    current_build.state == BuildState.RUNNING
                    or current_build.state == BuildState.SCHEDULED
                ):
                    logger.debug(
                        f"Build for {current_build.commit} is still running. Waiting for completion."
                    )
                    # Stop processing current list of builds for now.
                    break
                elif current_build.state == BuildState.PASSED:
                    logger.info(
                        f"Build for {current_build.commit} passed. Nothing to do."
                    )
                elif current_build.state == BuildState.FAILED:
                    if self.last_processed_state == BuildState.PASSED:
                        logger.info(
                            f"Detected 'passed' -> '{current_build.state}' transition for {current_build.commit}). Repairing ..."
                        )
                        if not self.repair_build(current_build):
                            logger.warning(
                                f"Failed to repair build #{current_build.commit} (commit: {current_build.commit}). Giving up and waiting for user to fix it manually."
                            )
                    else:
                        logger.info(
                            f"{self.last_processed_sha} also not passing. Waiting for transition from passed->failed state."
                        )
                else:
                    # Unknown states. Skip this.
                    logger.warning(
                        f"Build for {current_build.commit} is in unknown state ❌: ('{current_build.state}'). Skipping this."
                    )

                # Update state for the next iteration.
                self.last_processed_state = current_build.state
                self.last_processed_sha = current_build.commit
                self.save_state()

            self.wait(self.poll_interval)


def test_commits(bot, test_commits_file):
    print("Testing commits")
    with open("results." + test_commits_file, "w") as result_file:
        with open(test_commits_file, "r") as f:
            commits = f.read().splitlines()
            for commit in commits:
                print(f"Testing commit: {commit}")
                result = bot.repair_build(bot.get_build_info_for_commit(commit))
                if result:
                    result_file.write(f"{commit}: success\n")
                else:
                    result_file.write(f"{commit}: failed\n")
                result_file.flush()
                print("\n")


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
    )
    creds_manager = CredentialManager()
    cmd_processor = utils.CommandProcessor(args.llvm_git_repo)
    git_repo = LocalGitRepo(args.llvm_git_repo, creds_manager, args.create_prs)
    build_processor = LocalBuildProcessor(cmd_processor, git_repo)
    bot = BazelRepairBot(
        cmd_processor,
        git_repo,
        creds_manager,
        build_processor,
        args.bot_state_file,
        args.poll_interval,
    )
    if args.test_commits:
        test_commits(bot, args.test_commits)
        exit(0)

    logger.info("Bazel Bot entering main loop...")
    bot.load_state()
    bot.run()
    print("Exiting Bazel Bot Server...")
    exit(1)
