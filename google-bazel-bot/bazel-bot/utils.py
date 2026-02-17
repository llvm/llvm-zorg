from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import List
import time
import subprocess
import logging
import os
from github import Github
from git import Repo, Actor
import requests
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Any

logger = logging.getLogger(__name__)


def parse_targets(error_log: Optional[str]) -> Sequence[str]:
    if not error_log:
        return []
    return re.findall(r"\(from target (.*?)\)", error_log)


@dataclass
class BazelBuildResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    time_taken: float = 0.0


class CredentialManager:
    DefaultGHUser = "pranavk"

    def __init__(self):
        self.gh_fork_user = os.getenv("GITHUB_FORK_USER", self.DefaultGHUser)
        self.gh_fork_token = os.getenv("GITHUB_FORK_API_TOKEN")
        self.gh_pr_user = os.getenv("GITHUB_PR_USER", self.DefaultGHUser)
        self.gh_pr_token = os.getenv("GITHUB_PR_API_TOKEN")
        self.bk_token = os.getenv("BUILDKITE_API_TOKEN")

    @property
    def gh_fork_repo_name(self):
        return f"{self.gh_fork_user}/llvm-project"

    @property
    def gh_pr_repo_name(self):
        return f"{self.gh_pr_user}/llvm-project"


class CommandProcessor:
    BazelPath = "utils/bazel"

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.bazel_path = os.path.join(repo_path, self.BazelPath)

    def bazel_build_in_kubernetes(self) -> bool:
        return os.getenv("POD_NAME") is not None

    def run_bazel_build(self) -> BazelBuildResult:
        """
        Runs the bazel build command in the given repository path for specific targets.

        Returns:
            BazelBuildResult containing status, stdout, stderr, and time taken.
        """
        try:
            bazel_build_file = (
                "bazel-build-ci" if self.bazel_build_in_kubernetes() else "bazel-build"
            )
            base_path = os.path.dirname(os.path.abspath(__file__))
            bazel_build_path = os.path.join(base_path, bazel_build_file)

            logger.info("Running bazel build...")
            start_time = time.time()
            result = subprocess.run(
                [bazel_build_path],
                cwd=os.path.join(self.repo_path, self.BazelPath),
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes
            )
            end_time = time.time()
            time_taken = end_time - start_time
            logger.info(f"Bazel build took {time_taken} seconds.")
            return BazelBuildResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                time_taken=time_taken,
            )

        except subprocess.TimeoutExpired:
            return BazelBuildResult(success=False, stderr="Timeout", time_taken=1800)
        except FileNotFoundError:
            return BazelBuildResult(
                success=False,
                stderr="Error: 'bazel' command not found. Please ensure Bazel is installed.",
            )
        except Exception as e:
            return BazelBuildResult(
                success=False, stderr=f"Error running bazel build: {str(e)}"
            )

    def run_buildifier(self, files: Sequence[str]) -> bool:
        """
        Runs buildifier on the given files.

        Args:
            repo_path: The absolute path to the root of the local git repository.
            files: List of files to run buildifier on.
        """
        if not files:
            return False

        cmd = ["buildifier"] + list(files)
        logger.info(f"Running buildifier: {' '.join(cmd)}...")
        result = subprocess.run(
            cmd,
            cwd=os.path.join(self.repo_path, self.BazelPath),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"Buildifier failed: {result.stderr}")
            return False

        return True

    def run_bant(self, targets: Sequence[str]) -> bool:
        """
        Runs bant on the given files.

        Args:
            repo_path: The absolute path to the root of the local git repository.
            files: List of files to run bant on.
        """
        try:
            if not targets:
                return False

            # Target will be @@+_repo_rules+llvm-project//mlir:AMDGPUDialect
            # We want @llvm-project//mlir:AMDGPUDialect
            processed_targets = [
                t.replace("@@+_repo_rules+llvm-project//", "@llvm-project//")
                for t in targets
            ]
            cmd = ["bant", "dwyu"] + processed_targets
            logger.info(f"Running bant: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=os.path.join(self.repo_path, self.BazelPath),
                capture_output=True,
                text=True,
                timeout=30,
            )

            for buildozer_cmd in result.stdout.splitlines():
                logger.info(f"Executing: {buildozer_cmd}")
                buildozer_cmd = buildozer_cmd.replace(
                    "@llvm-project//", "//llvm-project-overlay//"
                )
                buildozer_result = subprocess.run(
                    buildozer_cmd, shell=True, cwd=self.repo_path
                )
                if buildozer_result.returncode != 0:
                    logger.error(f"Buildozer command failed: {buildozer_cmd}")

            return True

        except Exception as e:
            logger.error(f"Error running bant: {str(e)}")
            return False


class LocalGitRepo:
    def __init__(self, repo_path: str, creds: CredentialManager, can_create_pr):
        self.can_create_pr = can_create_pr
        self.repo_path = repo_path
        self.creds = creds
        if not os.path.exists(self.repo_path):
            logger.info(
                f"Cloning {self.creds.gh_fork_repo_name} to {self.repo_path}..."
            )
            Repo.clone_from(
                f"https://{self.creds.gh_fork_token}@github.com/{self.creds.gh_fork_repo_name}.git",
                self.repo_path,
            )
        self.repo = Repo(repo_path)
        self.gh_fork_repo = Github(self.creds.gh_fork_token).get_repo(
            self.creds.gh_fork_repo_name
        )
        self.gh_pr_repo = Github(self.creds.gh_pr_token).get_repo(
            self.creds.gh_pr_repo_name
        )
        self.bazel_utils_path = os.path.join(self.repo_path, "utils", "bazel")

        self.main_branch = "main"
        self.remote_name = "origin"
        self.author_name = os.getenv("GIT_AUTHOR_NAME", "Pranav Kant")
        self.author_email = os.getenv("GIT_AUTHOR_EMAIL", "prka@google.com")
        self.branch_prefix = "bazel-"

    def get_branch_name(self, commit_hash: str) -> str:
        return f"{self.branch_prefix}{commit_hash}"

    def refresh_main_branch(self) -> str:
        """Pulls the repository locally."""
        self.gh_fork_repo.merge_upstream(self.main_branch)
        self.repo.git.checkout("-f", self.main_branch)
        # Force pull by fetching and resetting to overwrite local changes.
        self.repo.remotes.origin.fetch()
        self.repo.git.reset("--hard", f"{self.remote_name}/{self.main_branch}")

        return self.repo.head.commit.hexsha

    def diff(self) -> str:
        return self.repo.git.diff(None)

    def create_branch_for_fix(self, commit_hash: str) -> None:
        """Prepares the local git repository for applying fixes."""
        self.checkout_commit(commit_hash)
        self.repo.create_head(self.get_branch_name(commit_hash), force=True).checkout()

    def checkout_commit(self, commit_hash: str):
        """Prepares the local git repository for applying fixes."""
        self.refresh_main_branch()
        self.repo.git.checkout("-f", commit_hash)

    def commit(self, message: str) -> None:
        self.repo.git.add(".")
        actor = Actor(self.author_name, self.author_email)
        self.repo.index.commit(message, author=actor, committer=actor)

    def is_repo_dirty(self, untracked_files=False) -> bool:
        return self.repo.is_dirty(untracked_files=untracked_files)

    def push_fix(self, commit_hash: str, create_pr: bool) -> bool:
        """Pushes the branch and creates a GitHub PR against it."""
        branch_name = self.get_branch_name(commit_hash)
        try:
            logger.info(f"Pushing branch {branch_name} to remote...")
            if not self.repo.git.push(
                "--set-upstream", self.remote_name, f"HEAD:{branch_name}", "-f"
            ):
                logger.error("Failed to push branch.")
                return False

            if not create_pr:
                logger.info("PR creation disabled. Skipping PR creation.")
                logger.info(
                    f"Pull request can be created at: https://github.com/llvm/llvm-project/compare/main...{self.creds.gh_fork_user}:llvm-project:{branch_name}?expand=1"
                )
                return True

            # This requires GITHUB_PR_API_TOKEN to have pull-request:write access.
            logger.info(
                f"Creating Pull Request for branch {branch_name} from {self.creds.gh_fork_repo_name} to {self.creds.gh_pr_repo_name}..."
            )
            pr_body = f"This fixes {commit_hash}.\n\n"

            pr = self.gh_pr_repo.create_pull(
                title=f"[Bazel] Fixes {commit_hash[:7]}",
                body=pr_body,
                head=f"{self.creds.gh_pr_user}:{branch_name}",
                base=self.main_branch,
            )
            logger.info(f"Pull Request Created: {pr.html_url}")
        except Exception as e:
            logger.error(f"Failed to push or create PR: {e}")
            return False

        return True


class BuildState(Enum):
    UNKNOWN = "unknown"
    PASSED = "passed"
    FAILED = "failed"
    RUNNING = "running"
    SCHEDULED = "scheduled"


@dataclass
class BuildInfo:
    commit: str
    state: BuildState = BuildState.UNKNOWN
    failed_targets: Sequence[str] = field(default_factory=list)
    build_number: Optional[int] = None


class BuildProcessor(ABC):
    @abstractmethod
    def get_latest_build_status(self) -> BuildInfo | None:
        """Get the latest build status."""
        pass

    @abstractmethod
    def get_builds_to_process(self, last_processed_sha: str) -> Sequence[BuildInfo]:
        """Get builds to process since last processed build."""
        pass


class LocalBuildProcessor(BuildProcessor):
    def __init__(self, cmd_processor: CommandProcessor, git_repo: LocalGitRepo):
        self.cmd_processor = cmd_processor
        self.git_repo = git_repo

    def get_latest_build_status(self) -> BuildInfo:
        """Get the latest build status by running bazel build locally."""
        latest_sha = self.git_repo.refresh_main_branch()
        result = self.cmd_processor.run_bazel_build()

        return BuildInfo(
            commit=latest_sha,
            state=BuildState.PASSED if result.success else BuildState.FAILED,
            failed_targets=parse_targets(result.stderr),
        )

    def get_builds_to_process(self, last_processed_sha: str) -> Sequence[BuildInfo]:
        """Get builds to process since last processed build by checking commits since then."""
        self.git_repo.refresh_main_branch()
        repo = self.git_repo.repo

        # First ensure that last_processed_sha is in the main branch
        try:
            if not repo.is_ancestor(
                repo.commit(last_processed_sha), repo.commit(self.git_repo.main_branch)
            ):
                logger.error(
                    f"Commit {last_processed_sha} is not in branch {self.git_repo.main_branch}"
                )
                return []
        except Exception as e:
            logger.error(
                f"Commit {last_processed_sha} not found or error checking ancestry: {e}"
            )
            return []

        commits = list(
            repo.iter_commits(f"{last_processed_sha}..{self.git_repo.main_branch}")
        )
        builds = []
        for commit in commits:
            builds.append(BuildInfo(commit.hexsha, BuildState.UNKNOWN, []))

        builds.reverse()  # Oldest first
        return builds


class BuildkiteBuildProcessor(BuildProcessor):
    ORG = "llvm-project"
    PIPELINE = "upstream-bazel"

    def __init__(self, creds: CredentialManager):
        self.buildkite_token = creds.bk_token
        self.buildkite_api_url = f"https://api.buildkite.com/v2/organizations/{self.ORG}/pipelines/{self.PIPELINE}/builds"

    def get_latest_build_status(self) -> BuildInfo | None:
        """Fetch the latest build status from Buildkite."""
        headers = {"Authorization": f"Bearer {self.buildkite_token}"}
        try:
            response = requests.get(
                self.buildkite_api_url, headers=headers, params={"per_page": 1}
            )
            response.raise_for_status()
            builds = response.json()
            if not builds:
                return None
            return BuildInfo(
                commit=builds[0].get("commit", ""),
                build_number=builds[0].get("number"),
                state=BuildState(builds[0].get("state", "unknown")),
                failed_targets=parse_targets(self.get_error_log(builds[0])),
            )
        except Exception as e:
            logger.error(f"Error fetching Buildkite status: {e}")
            return None

    def get_error_log(self, build: Mapping[str, Any]) -> Optional[str]:
        """Fetches the error log for a failed build from Buildkite."""
        headers = {"Authorization": f"Bearer {self.buildkite_token}"}
        for job in build.get("jobs", []):
            if job.get("state") == "failed":
                log_url = job.get("log_url")
                if log_url:
                    try:
                        response = requests.get(log_url, headers=headers)
                        response.raise_for_status()
                        return response.json().get("content")
                    except Exception as e:
                        logger.error(
                            f"Failed to fetch log for job {job.get('id')}: {e}"
                        )
        return None

    def get_builds_to_process(self, last_processed_sha: str) -> Sequence[BuildInfo]:
        """Fetches new builds from Buildkite since the last processed one from the loaded state."""
        headers = {"Authorization": f"Bearer {self.buildkite_token}"}
        new_builds = []
        page = 1
        fetched_builds = set()
        found_old_build = False
        # Buildkite returns builds in descending order of creation.
        # We go through pages until we find a build we've already processed.
        while True:
            try:
                params = {"per_page": 100, "page": page}
                logging.debug(f"Fetching Buildkite builds, page {page}...")
                response = requests.get(
                    self.buildkite_api_url, headers=headers, params=params
                )
                response.raise_for_status()
                builds = response.json()

                if not builds:
                    break  # No more builds

                found_old_build = False
                logging.debug(
                    f"Processing builds from {builds[0].get('number')} to {builds[-1].get('number')}"
                )
                for build in builds:
                    build_number = build.get("number")
                    build_commit = build.get("commit")
                    if build_number is None or build_number in fetched_builds:
                        # By the time, we start fetching builds for next page, some builds already processed
                        # in previous page may have made their way into the next page. We need to skip those.
                        continue

                    if build_commit == last_processed_sha:
                        logging.debug(
                            f"Found last processed sha {last_processed_sha} in build #{build_number}. Stopping fetch."
                        )
                        found_old_build = True
                        break

                    if build.get("state") in ["failed", "broken"]:
                        build["targets"] = parse_targets(self.get_error_log(build))

                    build_object = BuildInfo(
                        commit=build.get("commit", ""),
                        state=BuildState(build.get("state", "unknown")),
                        failed_targets=build.get("targets", []),
                        build_number=build_number,
                    )
                    fetched_builds.add(build_number)
                    new_builds.append(build_object)

                if found_old_build:
                    break

                page += 1
                if page > 10:  # Safety break to avoid fetching too much history
                    logger.warning(
                        "Stopped fetching builds after 10 pages to avoid excessive requests."
                    )
                    break
            except Exception as e:
                logger.error(f"Error fetching Buildkite builds: {e}")
                return []  # Return empty list on error

        if len(new_builds) > 0:
            logger.info(
                f"Fetched {len(new_builds)} new builds: (from #{new_builds[-1].build_number} to #{new_builds[0].build_number}). Last processed: #{last_processed_sha}."
            )
            if not found_old_build:
                logger.warning(
                    "Last processed build is too old. Skipping intermediate builds."
                )

        return new_builds[::-1]
