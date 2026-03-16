import argparse
import logging
import sys

import bazelbot_server
import utils

parser = argparse.ArgumentParser(description="Bazelbot")
parser.add_argument(
    "--llvm_git_repo", type=str, help="Absolute path to LLVM repo", required=True
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
    creds_manager = utils.CredentialManager()
    cmd_processor = utils.CommandProcessor(args.llvm_git_repo)
    git_repo = utils.LocalGitRepo(args.llvm_git_repo, creds_manager, args.create_prs)
    build_processor = utils.LocalBuildProcessor(cmd_processor, git_repo)
    bot = bazelbot_server.BazelRepairBot(
        cmd_processor,
        git_repo,
        creds_manager,
        build_processor,
        args.poll_interval,
    )
    if args.test_commits:
        test_commits(bot, args.test_commits)
        exit(0)

    logger.info("Bazel Bot entering main loop...")
    bot.run()
