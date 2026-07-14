import os
import unittest
from unittest import mock

import bazel_agent
import bazelbot_server
import git
import github
import utils


class TestBazelBotServer(unittest.TestCase):
    def test_parse_targets(self):
        log = "ERROR: /path/to/BUILD:10:11: (from target //foo:bar)"
        self.assertEqual(utils.parse_targets(log), ["//foo:bar"])

        log = "some other error\n(from target //a:b)\n(from target //c:d)"
        self.assertEqual(utils.parse_targets(log), ["//a:b", "//c:d"])

        self.assertEqual(utils.parse_targets(None), [])

    @mock.patch.dict(
        os.environ,
        {
            "GITHUB_FORK_USER": "fork_user",
            "GITHUB_PR_USER": "pr_user",
            "BUILDKITE_API_TOKEN": "bk_token",
            "GITHUB_APP_ID": "app_id",
            "GITHUB_APP_PRIVATE_KEY": "private_key",
            "GITHUB_PR_APP_ID": "pr_app_id",
            "GITHUB_PR_APP_PRIVATE_KEY": "pr_private_key",
        },
    )
    def test_credential_manager(self):
        creds = utils.CredentialManager(use_github_app=True)
        self.assertEqual(creds.gh_fork_user, "fork_user")
        self.assertEqual(creds.gh_pr_user, "pr_user")
        self.assertEqual(creds.bk_token, "bk_token")
        self.assertEqual(creds.gh_fork_repo_name, "fork_user/llvm-project")
        self.assertEqual(creds.gh_pr_repo_name, "pr_user/llvm-project")
        self.assertEqual(creds.gh_pr_app_id, "pr_app_id")
        self.assertEqual(creds.gh_pr_app_private_key, "pr_private_key")

    @mock.patch("utils.git.Repo")
    @mock.patch("utils.github.GithubIntegration")
    @mock.patch("utils.github.Auth")
    @mock.patch("os.path.exists")
    def test_local_git_repo(self, mock_exists, github_mock, auth_mock, mock_repo):
        mock_exists.return_value = False
        creds = mock.MagicMock()
        creds.gh_fork_repo_name = "fork/repo"
        creds.gh_pr_repo_name = "pr/repo"
        creds.gh_app_id = "app_id"
        creds.gh_app_private_key = "app_private_key"

        repo = utils.LocalGitRepo("/path/to/repo", creds, can_create_pr=True)
        mock_repo.clone_from.assert_called_once()

        # Test get_branch_name
        self.assertEqual(repo.get_branch_name("abcdef"), "bazel-abcdef")

        # Test refresh_main_branch
        repo_instance = mock_repo.return_value
        repo_instance.head.commit.hexsha = "new_sha"
        sha = repo.refresh_main_branch()
        self.assertEqual(sha, "new_sha")
        repo.gh_fork_repo.merge_upstream.assert_called()
        repo.repo.git.checkout.assert_called_with("-f", repo.main_branch)
        repo.repo.remotes.origin.fetch.assert_called()
        repo.repo.git.reset.assert_called_with(
            "--hard", f"{repo.remote_name}/{repo.main_branch}"
        )

        # Setup mocks for getting open PRs.
        class MockPullRequest:
            def __init__(self):
                setattr(self, "state", "open")

            def edit(self, state: str) -> None:
                setattr(self, "state", state)

            @property
            def url(self) -> str:
                return "PullRequestMockObjectURL"

        mock_prs = [MockPullRequest(), MockPullRequest()]
        repo.gh_pr_repo.get_issues = mock.MagicMock()
        repo.gh_pr_repo.get_issues.return_value = mock_prs

        # Test push_fix
        repo_instance.git.push.return_value = True
        repo.push_fix(utils.BuildInfo("commit_hash"), True)
        repo_instance.git.push.assert_called()
        repo.gh_pr_repo.create_pull.assert_called()
        self.assertEqual(mock_prs[0].state, "closed")
        self.assertEqual(mock_prs[1].state, "closed")

    @mock.patch("utils.github.GithubIntegration")
    @mock.patch("utils.github.Auth")
    @mock.patch("utils.call_with_retry")
    @mock.patch("utils.git.Repo")
    @mock.patch("os.path.exists")
    def test_push_fix_uses_retry(
        self, mock_exists, mock_repo, mock_call_with_retry, mock_auth, mock_github_integration
    ):
        mock_exists.return_value = False
        creds = mock.MagicMock()
        creds.gh_fork_repo_name = "fork/repo"
        creds.gh_pr_repo_name = "pr/repo"
        creds.gh_app_id = "app_id"
        creds.gh_app_private_key = "app_private_key"
        repo = utils.LocalGitRepo("/path/to/repo", creds, can_create_pr=True)
        repo_instance = mock_repo.return_value
        branch_name = repo.get_branch_name("commit_hash")

        mock_call_with_retry.side_effect = lambda exceptions, f, *args, **kwargs: f(*args, **kwargs)

        repo.fork_github_integration.get_access_token.return_value.token = "token"
        repo.gh_pr_repo.get_issues.return_value = []
        repo.gh_pr_repo.create_pull.return_value = mock.MagicMock(html_url="http://pr")

        result = repo.push_fix(utils.BuildInfo("commit_hash"), True)

        self.assertTrue(result)
        self.assertEqual(mock_call_with_retry.call_count, 4)

        # 1. get_access_token
        call1 = mock_call_with_retry.call_args_list[0]
        self.assertEqual(call1[0][0], (github.GithubException,))
        self.assertEqual(call1[0][1], repo.fork_github_integration.get_access_token)
        self.assertEqual(call1[0][2], repo.gh_fork_installation.id)

        # 2. git push
        call2 = mock_call_with_retry.call_args_list[1]
        self.assertEqual(call2[0][0], (git.GitCommandError,))
        self.assertEqual(call2[0][1], repo_instance.git.push)
        self.assertEqual(
            call2[0][2:],
            ("--set-upstream", repo.remote_name, f"HEAD:{branch_name}", "-f"),
        )

        # 3. close_existing_prs
        call3 = mock_call_with_retry.call_args_list[2]
        self.assertEqual(call3[0][0], (github.GithubException,))
        self.assertEqual(call3[0][1], repo.close_existing_prs)

        # 4. create_pull
        call4 = mock_call_with_retry.call_args_list[3]
        self.assertEqual(call4[0][0], (github.GithubException,))
        self.assertEqual(call4[0][1], repo.gh_pr_repo.create_pull)
        self.assertEqual(call4[1]["base"], "main")
        self.assertEqual(call4[1]["maintainer_can_modify"], False)


    @mock.patch("utils.call_with_retry")
    @mock.patch("utils.git.Repo")
    @mock.patch("utils.github.GithubIntegration")
    @mock.patch("utils.github.Auth")
    @mock.patch("os.path.exists")
    def test_refresh_main_branch_uses_retry(
        self, mock_exists, github_mock, auth_mock, mock_repo, mock_call_with_retry
    ):
        mock_exists.return_value = False
        creds = mock.MagicMock()
        creds.gh_fork_repo_name = "fork/repo"
        creds.gh_pr_repo_name = "pr/repo"
        creds.gh_app_id = "app_id"
        creds.gh_app_private_key = "app_private_key"
        repo = utils.LocalGitRepo("/path/to/repo", creds, can_create_pr=True)

        repo_instance = mock_repo.return_value
        repo_instance.head.commit.hexsha = "new_sha"

        repo.gh_fork_repo.merge_upstream.side_effect = [
            utils.github.GithubException(504, "Gateway Timeout", {}),
            None,
        ]
        repo_instance.remotes.origin.fetch.return_value = None

        repo.refresh_main_branch()

        self.assertEqual(mock_call_with_retry.call_count, 2)
        
        call1 = mock_call_with_retry.call_args_list[0]
        self.assertEqual(call1[0][0], (github.GithubException,))
        self.assertEqual(call1[0][1], repo.gh_fork_repo.merge_upstream)
        self.assertEqual(call1[0][2], "main")
        
        call2 = mock_call_with_retry.call_args_list[1]
        self.assertEqual(call2[0][0], (git.GitCommandError,))
        self.assertEqual(call2[0][1], repo.repo.remotes.origin.fetch)
        

    def test_local_build_processor(self):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()

        lbp = utils.LocalBuildProcessor(cmd_processor, git_repo)

        # Test get_latest_build_status
        git_repo.refresh_main_branch.return_value = "sha1"
        cmd_processor.run_bazel_build.return_value = mock.MagicMock(
            success=True, stderr=""
        )

        info = lbp.get_latest_build_status()
        self.assertEqual(info.commit, "sha1")
        self.assertEqual(info.state, utils.BuildState.PASSED)

        # Test get_builds_to_process
        git_repo.repo.is_ancestor.return_value = True
        sha_new = mock.MagicMock()
        sha_new.hexsha = "sha_new"
        sha_old = mock.MagicMock()
        sha_old.hexsha = "sha_old"
        git_repo.repo.iter_commits.return_value = [sha_new, sha_old]

        builds = lbp.get_builds_to_process("sha1")
        self.assertEqual(len(builds), 2)
        self.assertEqual(builds[0].commit, "sha_old")
        self.assertEqual(builds[1].commit, "sha_new")

    @mock.patch("bazelbot_server.asyncio.run")
    def test_process_failure_with_ai(self, mock_asyncio_run):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()
        git_repo.can_create_pr = True
        creds = mock.MagicMock()
        build_processor = mock.MagicMock()

        bot = bazelbot_server.BazelRepairBot(
            cmd_processor, git_repo, creds, build_processor, 10
        )
        build_info = utils.BuildInfo("sha1", utils.BuildState.FAILED, [], 1)

        # Mock agent result success
        agent_result = mock.MagicMock()
        agent_result.status = bazel_agent.AgentErrors.SUCCESS
        agent_result.summary = "Fixed"
        mock_asyncio_run.return_value = agent_result

        # Mock build success after fix
        cmd_processor.run_bazel_build.return_value = mock.MagicMock(success=True)
        git_repo.push_fix.return_value = True

        result = bot.process_failure_with_ai(build_info)

        self.assertTrue(result)
        git_repo.create_branch_for_fix.assert_called_with("sha1")
        git_repo.commit.assert_called()
        git_repo.push_fix.assert_called_with(build_info, True)

    @mock.patch("bazelbot_server.bazel_agent.query_agent")
    @mock.patch("bazelbot_server.asyncio.run")
    def test_process_failure_with_ai_past_fixes(
        self, mock_asyncio_run, mock_query_agent
    ):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()
        creds = mock.MagicMock()
        build_processor = mock.MagicMock()

        bot = bazelbot_server.BazelRepairBot(
            cmd_processor, git_repo, creds, build_processor, 10
        )
        build_info = utils.BuildInfo("sha1", utils.BuildState.FAILED, [], 1)

        # Iteration 1: Agent fails, repo is dirty -> adds to past_fixes
        result_fail = mock.MagicMock()
        result_fail.status = bazel_agent.AgentErrors.FAILURE
        result_fail.summary = ["Failed attempt"]

        # Iteration 2: Agent succeeds
        result_success = mock.MagicMock()
        result_success.status = bazel_agent.AgentErrors.SUCCESS
        result_success.summary = ["Fixed"]

        mock_asyncio_run.side_effect = [result_fail, result_success]

        # Mock repo state
        git_repo.is_dirty.return_value = True
        git_repo.diff.return_value = "diff_content"

        # Mock final verification build
        cmd_processor.run_bazel_build.return_value = mock.MagicMock(success=True)
        git_repo.push_fix.return_value = True

        result = bot.process_failure_with_ai(build_info)

        self.assertTrue(result)
        self.assertEqual(mock_query_agent.call_count, 2)
        self.assertEqual(mock_query_agent.call_args_list[0][1]["past_fixes"], [])
        self.assertEqual(
            mock_query_agent.call_args_list[1][1]["past_fixes"], ["diff_content"]
        )

    def test_process_failure_with_bant(self):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()
        creds = mock.MagicMock()
        build_processor = mock.MagicMock()

        bot = bazelbot_server.BazelRepairBot(
            cmd_processor, git_repo, creds, build_processor, 10
        )
        build_info = utils.BuildInfo(
            "sha1", utils.BuildState.FAILED, ["//target:foo"], 1
        )

        # Mock bant success
        cmd_processor.run_bant.return_value = True
        # Mock validation success
        bot.validate_before_publishing = mock.MagicMock(return_value=True)
        git_repo.push_fix.return_value = True

        result = bot.process_failure_with_bant(build_info)

        self.assertTrue(result)
        git_repo.create_branch_for_fix.assert_called_with("sha1")
        cmd_processor.run_bant.assert_called_with(targets=["//target:foo"])
        git_repo.commit.assert_called()
        git_repo.push_fix.assert_called()

    def test_validate_before_publishing(self):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()
        creds = mock.MagicMock()
        build_processor = mock.MagicMock()

        bot = bazelbot_server.BazelRepairBot(
            cmd_processor, git_repo, creds, build_processor, 10
        )

        # Case 1: Repo not dirty -> False
        git_repo.is_repo_dirty.return_value = False
        self.assertFalse(bot.validate_before_publishing())

        # Case 2: Repo dirty, build fails -> False
        git_repo.is_repo_dirty.return_value = True
        cmd_processor.run_bazel_build.return_value = mock.MagicMock(
            success=False, stderr="err"
        )
        self.assertFalse(bot.validate_before_publishing())

        # Case 3: Repo dirty, build passes, buildifier fails -> False
        cmd_processor.run_bazel_build.return_value = mock.MagicMock(success=True)
        git_repo.repo.git.diff.return_value = "file1.py"
        git_repo.repo.untracked_files = []
        cmd_processor.run_buildifier.return_value = False
        self.assertFalse(bot.validate_before_publishing())

        # Case 4: All pass
        cmd_processor.run_buildifier.return_value = True
        cmd_processor.run_bazel_build.return_value = mock.MagicMock(success=True)
        self.assertTrue(bot.validate_before_publishing())

    def test_repair_build_logic(self):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()
        creds = mock.MagicMock()
        build_processor = mock.MagicMock()
        bot = bazelbot_server.BazelRepairBot(
            cmd_processor, git_repo, creds, build_processor, 10
        )

        build_info = utils.BuildInfo("sha1", utils.BuildState.FAILED, [], 1)

        # Mock methods
        bot.process_failure_with_bant = mock.MagicMock()
        bot.process_failure_with_ai = mock.MagicMock()

        # 1. Bant succeeds
        bot.process_failure_with_bant.return_value = True
        self.assertTrue(bot.repair_build(build_info))
        bot.process_failure_with_ai.assert_not_called()

        # 2. Bant fails, AI succeeds
        bot.process_failure_with_bant.return_value = False
        bot.process_failure_with_ai.return_value = True
        self.assertTrue(bot.repair_build(build_info))
        bot.process_failure_with_ai.assert_called_once()

        # 3. Both fail
        bot.process_failure_with_ai.return_value = False
        self.assertFalse(bot.repair_build(build_info))

    def test_run_logic(self):
        cmd_processor = mock.MagicMock()
        git_repo = mock.MagicMock()
        creds = mock.MagicMock()
        build_processor = mock.MagicMock()

        # Initialize bot with known state
        bot = bazelbot_server.BazelRepairBot(
            cmd_processor, git_repo, creds, build_processor, 10
        )
        bot.last_processed_sha = "init_sha"
        bot.last_processed_state = utils.BuildState.PASSED

        # Define the sequence of builds
        builds = [
            utils.BuildInfo(commit="sha1", state=utils.BuildState.PASSED),
            utils.BuildInfo(commit="sha2", state=utils.BuildState.FAILED),
            utils.BuildInfo(commit="sha3", state=utils.BuildState.FAILED),
            utils.BuildInfo(commit="sha4", state=utils.BuildState.PASSED),
        ]

        build_processor.get_builds_to_process.return_value = builds

        # Mock repair_build to verify calls
        bot.repair_build = mock.MagicMock(return_value=True)

        # Mock wait to break the loop
        bot.wait = mock.MagicMock(side_effect=StopIteration)

        # Run the bot
        try:
            bot.run()
        except StopIteration:
            pass

        # Verifications

        # 1. repair_build should be called only for sha2 (PASSED -> FAILED transition)
        self.assertEqual(bot.repair_build.call_count, 1)
        bot.repair_build.assert_called_with(builds[1])  # sha2

        # 2. Verify state updates
        self.assertEqual(bot.last_processed_sha, "sha4")
        self.assertEqual(bot.last_processed_state, utils.BuildState.PASSED)

        # Verify get_builds_to_process was called with initial sha
        build_processor.get_builds_to_process.assert_called_with("init_sha")

    def test_buildkite_url(self):
        info_with_num = utils.BuildInfo("sha1", build_number=123)
        self.assertEqual(
            info_with_num.buildkite_url,
            "https://buildkite.com/llvm-project/upstream-bazel/builds/123",
        )
        info_without_num = utils.BuildInfo("sha2")
        self.assertEqual(
            info_without_num.buildkite_url,
            "https://buildkite.com/llvm-project/upstream-bazel/builds?commit=sha2",
        )

    def test_call_with_retry_success(self):
        mock_func = mock.MagicMock(return_value="success")
        res = utils.call_with_retry((utils.github.GithubException,), mock_func)
        self.assertEqual(res, "success")
        mock_func.assert_called_once()

    @mock.patch("utils.time.sleep")
    def test_call_with_retry_fail_then_success(self, mock_sleep):
        mock_func = mock.MagicMock(
            side_effect=[
                utils.github.GithubException(504, "Gateway Timeout", {}),
                "success",
            ]
        )
        res = utils.call_with_retry((utils.github.GithubException,), mock_func)
        self.assertEqual(res, "success")
        self.assertEqual(mock_func.call_count, 2)
        mock_sleep.assert_called_once_with(3)

    @mock.patch("utils.time.sleep")
    def test_call_with_retry_always_fail(self, mock_sleep):
        mock_func = mock.MagicMock(
            side_effect=utils.github.GithubException(504, "Gateway Timeout", {})
        )
        with self.assertRaises(utils.github.GithubException):
            utils.call_with_retry((utils.github.GithubException,), mock_func)
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_has_calls([mock.call(3), mock.call(6)])

    @mock.patch("utils.time.sleep")
    def test_call_with_retry_no_retry_on_unspecified_exception(self, mock_sleep):
        mock_func = mock.MagicMock(
            side_effect=ValueError("Some value error")
        )
        with self.assertRaises(ValueError):
            utils.call_with_retry((utils.github.GithubException,), mock_func)
        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()

    def test_call_with_retry_empty_exceptions(self):
        mock_func = mock.MagicMock()
        with self.assertRaises(ValueError):
            utils.call_with_retry((), mock_func)
        mock_func.assert_not_called()



if __name__ == "__main__":
    unittest.main()
