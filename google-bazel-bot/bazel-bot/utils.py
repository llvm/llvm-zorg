import abc
import dataclasses
import enum
import logging
import os
import re
import subprocess
import time
from collections.abc import Mapping, Sequence
from typing import Any

import git
import github
import requests

logger = logging.getLogger(__name__)


def parse_targets(error_log: str | None) -> Sequence[str]:
    if not error_log:
        return []
    return re.findall(r"\(from target (.*?)\)", error_log)


@dataclasses.dataclass
class BazelBuildResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    time_taken: float = 0.0


class CredentialManager:
    def __init__(self):
        self.gh_fork_user = os.getenv("GITHUB_FORK_USER")
        self.gh_pr_user = os.getenv("GITHUB_PR_USER")
        self.bk_token = os.getenv("BUILDKITE_API_TOKEN")
        self.gh_app_id = os.getenv("GITHUB_APP_ID")
        self.gh_app_private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        self.gh_pr_app_id = os.getenv("GITHUB_PR_APP_ID")
        self.gh_pr_app_private_key = os.getenv("GITHUB_PR_APP_PRIVATE_KEY")

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
            git.Repo.clone_from(
                f"https://github.com/{self.creds.gh_fork_repo_name}.git",
                self.repo_path,
            )
        self.repo = git.Repo(repo_path)
        self.fork_github_integration = github.GithubIntegration(
            auth=github.Auth.AppAuth(creds.gh_app_id, creds.gh_app_private_key)
        )
        self.gh_fork_installation = self.fork_github_integration.get_repo_installation(
            self.creds.gh_fork_user, "llvm-project"
        )
        self.gh_fork_repo = (
            self.gh_fork_installation.get_github_for_installation().get_repo(
                self.creds.gh_fork_repo_name
            )
        )
        self.pr_github_integration = github.GithubIntegration(
            auth=github.Auth.AppAuth(creds.gh_pr_app_id, creds.gh_pr_app_private_key)
        )
        self.gh_pr_installation = self.pr_github_integration.get_repo_installation(
            self.creds.gh_pr_user, "llvm-project"
        )
        self.gh_pr_repo = (
            self.gh_pr_installation.get_github_for_installation().get_repo(
                self.creds.gh_pr_repo_name
            )
        )
        self.bazel_utils_path = os.path.join(self.repo_path, "utils", "bazel")
        self.main_branch = "main"
        self.remote_name = "origin"
        self.author_name = os.getenv("GIT_AUTHOR_NAME", "Google Bazel Bot")
        self.author_email = os.getenv("GIT_AUTHOR_EMAIL", "google-bazel-bot@google.com")
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
        actor = git.Actor(self.author_name, self.author_email)
        self.repo.index.commit(message, author=actor, committer=actor)

    def is_repo_dirty(self, untracked_files=False) -> bool:
        return self.repo.is_dirty(untracked_files=untracked_files)

    def push_fix(self, commit_hash: str, create_pr: bool) -> bool:
        """Pushes the branch and creates a GitHub PR against it."""
        branch_name = self.get_branch_name(commit_hash)
        try:
            logger.info(f"Pushing branch {branch_name} to remote...")
            self.repo.delete_remote(self.remote_name)
            access_token = self.fork_github_integration.get_access_token(
                self.gh_fork_installation.id
            ).token
            self.repo.create_remote(
                self.remote_name,
                f"https://x-access-token:{access_token}@github.com/{self.creds.gh_fork_repo_name}.git",
            )
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

            # This requires the Github app installation used for authentication
            # to have pull-request:write access.
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


class BuildState(enum.Enum):
    UNKNOWN = "unknown"
    PASSED = "passed"
    FAILED = "failed"
    RUNNING = "running"
    SCHEDULED = "scheduled"


@dataclasses.dataclass
class BuildInfo:
    commit: str
    state: BuildState = BuildState.UNKNOWN
    failed_targets: Sequence[str] = dataclasses.field(default_factory=list)
    build_number: int | None = None


class BuildProcessor(abc.ABC):
    @abc.abstractmethod
    def get_latest_build_status(self) -> BuildInfo | None:
        """Get the latest build status."""
        pass

    @abc.abstractmethod
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
