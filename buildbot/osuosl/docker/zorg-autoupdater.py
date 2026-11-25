#!/usr/bin/env python3
"""Validate an updated LLVM Zorg checkout before applying it to Buildbot.

    Add the following sections to your local.cfg file to support the slack notifications:

    [slack]
    webhook = https://hooks.slack.com/services/XXX/XXX/XXX

    Also the script will use a list of recipient emails specified in the local.cfg file within the [Admins] section for these notifications.

    The crontab entry for running this script can be added as follows:

    */5 * * * * mkdir -p /opt/docker/stagebot/logs && docker exec -t llvm-buildbot "/usr/bin/buildbotctl updateconfig" 2>&1 >> /opt/docker/stagebot/logs/zorg-autoupdater.log

    Co-authored by: Copilot
"""

import argparse
import configparser
import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request


LOG = logging.getLogger("zorg-autoupdater")
DEFAULT_REPO = "https://github.com/llvm/llvm-zorg.git"
DEFAULT_BRANCH = "main"
DEFAULT_CONFIG_FILE = Path("buildbot/osuosl/master/config/local.cfg")
DEFAULT_CONFIG_PATH = Path("buildbot/osuosl/master")
CONFIG_PATH_PREFIX = "buildbot/osuosl/master/config/"
ZORG_PATH_PREFIX = "zorg/buildbot/"


class CommandError(RuntimeError):
    def __init__(self, command, result):
        self.command = command
        self.result = result
        output = (result.stdout or "") + (result.stderr or "")
        super().__init__("{} failed (exit {}):\n{}".format(
            " ".join(map(str, command)), result.returncode, output.strip()))


def run(command, cwd=None, check=True, env=None):
    #LOG.info("Running command: {}".format(" ".join(map(str, command))))
    #LOG.info("  environment: {}".format("\n".join(map(str, env or os.environ.items()))))
    result = subprocess.run(
        [str(part) for part in command], cwd=str(cwd) if cwd else None,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env,
    )
    if check and result.returncode:
        raise CommandError(command, result)
    return result


def git(root, *args):
    LOG.info("Running git command in {}: {}".format(root, " ".join(map(str, args))))
    return run(["git", "-C", root, *args])


def configure_logging():
    class Formatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            return datetime.datetime.fromtimestamp(record.created).astimezone().strftime(
                "%Y-%m-%dT%H:%M:%S%z")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(Formatter("%(asctime)s [zorg-autoupdater] %(message)s"))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-w", "--working-root", default=os.environ.get("BUILDBOT_ZORG"))
    parser.add_argument("-s", "--staging-root", default=os.environ.get("BUILDBOT_STAGED_ZORG"))
    parser.add_argument("-c", "--config", help="INI config file (defaults to local.cfg in working-root)")
    parser.add_argument("--zorg-repo-url", default=DEFAULT_REPO)
    parser.add_argument("--zorg-branch-name", default=DEFAULT_BRANCH)
    args = parser.parse_args()
    if not args.working_root:
        parser.error("--working-root or BUILDBOT_ZORG is required")
    if not args.staging_root:
        parser.error("--staging-root or BUILDBOT_STAGED_ZORG is required")
    return args


def ensure_checkout(root, repo_url, branch):
    root = Path(root).expanduser().resolve()
    if root.exists():
        if not root.is_dir():
            raise RuntimeError("checkout path is not a directory: {}".format(root))
        if (root / ".git").exists():
            staging_baseline = git(root, "rev-parse", "HEAD").stdout.strip()
            LOG.info("Staging baseline revision: %s", staging_baseline)
            return staging_baseline
        if any(root.iterdir()):
            raise RuntimeError("staging path is not an empty directory or Git checkout: {}".format(root))

    LOG.info("Initial clone checkout at {} (repo: {}, branch: {})".format(root, repo_url, branch))
    root.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--branch", branch, "--single-branch", repo_url, root])
    staging_baseline = git(root, "rev-parse", "HEAD").stdout.strip()
    LOG.info("Staging baseline revision after checkout: %s", staging_baseline)
    return staging_baseline


def update_staging(root, branch, baseline):
    git(root, "fetch", "origin", branch)
    git(root, "checkout", "-B", branch, "origin/" + branch)
    git(root, "reset", "--hard", "origin/" + branch)
    revision = git(root, "rev-parse", "HEAD").stdout.strip()
    changed = git(root, "diff", "--name-only", baseline, revision).stdout.splitlines()
    return root, revision, changed

def update_working(root, revision):
    LOG.info("Updating working directory to revision {}".format(revision))
    git(root, "fetch", "origin", revision)
    git(root, "reset", "--hard", revision)


def link_working_config(staging, working_config):
    link = staging / DEFAULT_CONFIG_FILE
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        if link.resolve() != working_config.resolve():
            LOG.info("Updating symlink for local.cfg from {} to {}".format(link.resolve(), working_config.resolve()))
            link.unlink()
            link.symlink_to(working_config)
    elif link.exists():
        raise RuntimeError("staging local.cfg exists but is not a symlink: {}".format(link))
    else:
        LOG.info("Creating symlink for local.cfg from {} to {}".format(link, working_config.resolve()))
        link.symlink_to(working_config)


def changed_paths(changed):
    config = [path for path in changed if path.startswith(CONFIG_PATH_PREFIX)]
    zorg = [path for path in changed if path.startswith(ZORG_PATH_PREFIX)]
    return config, zorg


def commit_details(root, revision):
    values = git(root, "show", "-s", "--format=%H%n%s%n%an", revision).stdout.splitlines()
    details = {"hash": values[0], "subject": values[1] if len(values) > 1 else "",
            "author": values[2] if len(values) > 2 else ""}
    LOG.info("Commit details: %s", details)
    return details

def notification_settings(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    webhook = config.get("slack", "webhookurl", fallback="").strip()
    blamelist = [value.strip() for _, value in config.items("Admins")] if config.has_section("Admins") else []
    instance_title = config.get("Buildbot", "title", fallback="").strip()
    return {
        "webhook": webhook,
        "blamelist": [email for email in blamelist if email],
        "instance_title": instance_title
    }


def notify(to, status, details, failure_log=""):
    webhook = to.get("webhook", "")
    blamelist = to.get("blamelist", [])
    instance_title = to.get("instance_title", "Local Develop")

    if not webhook:
        LOG.info("Slack webhook is not configured; notification skipped")
        return
    lines = [f"{instance_title} - Buildbot Zorg/Configuration update {status}"]
    if details:
        # Add commit details to the notification message
        lines.extend([
            "Commit: {}".format(details.get("hash", "<unspecified>")),
            "Subject: {}".format(details.get("subject", "<unspecified>")),
            "Author: {}".format(details.get("author", "<unspecified>"))
        ])
    if blamelist:
        lines.append("Blamelist: " + ", ".join(blamelist))
    if failure_log:
        lines.extend(["Checkconfig failure log:", "```", failure_log[-12000:], "```"])
    request = urllib.request.Request(
        webhook, data=json.dumps({"text": "\n".join(lines)}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except (OSError, urllib.error.URLError) as exc:
        LOG.error("Could not send Slack notification: %s", exc)


def check_config(root, config_root, env=None):
    LOG.info("Checking configuration at: %s", config_root)
    return run(["buildbot", "checkconfig", config_root], cwd=root, env=env)


def error_log(exc):
    if isinstance(exc, CommandError):
        return (exc.result.stdout or "") + (exc.result.stderr or "")
    return str(exc)


def main():
    configure_logging()
    args = parse_args()
    working = Path(args.working_root).expanduser().resolve()
    if not working.is_dir():
        LOG.error("Working checkout does not exist: %s", working)
        return 2
    if not (working / ".git").exists():
        LOG.error("Working root is not a Git checkout: %s", working)
        return 2

    working_config = Path(args.config).expanduser() if args.config else DEFAULT_CONFIG_FILE
    if not working_config.is_absolute():
        working_config = working / working_config
    working_config = working_config.resolve()
    if not working_config.is_file():
        LOG.error("Configuration file does not exist: %s", working_config)
        return 2

    LOG.info("Working root: %s", working)
    LOG.info("Using working configuration file: %s", working_config)

    staging_arg = Path(args.staging_root).expanduser().resolve()
    LOG.info("Staging root: %s", staging_arg)
    
    working_baseline = git(working, "rev-parse", "HEAD").stdout.strip()
    LOG.info("Working baseline revision: %s", working_baseline)

    to = notification_settings(working_config)

    details = None

    try:
        staging_baseline = ensure_checkout(staging_arg, args.zorg_repo_url, args.zorg_branch_name)

        staging, revision, changed = update_staging(
            staging_arg, args.zorg_branch_name, working_baseline)
        link_working_config(staging, working_config)
        if working_baseline == staging_baseline and not changed:
            LOG.info("No new commits to validate")
            return 0
        config_changes, zorg_changes = changed_paths(changed)
        LOG.info("Changed files: %s", ", ".join(changed))
        # Get the details of the commit that triggered the changes.
        details = commit_details(staging, revision)

        if not config_changes and not zorg_changes:
            LOG.info("Changes are outside monitored paths; just sync the repository and exiting")
            update_working(working, revision)
            notify(to, "SUCCEEDED", details)
            return 0

        try:
            check_config(staging, str(staging / DEFAULT_CONFIG_PATH), env=os.environ.copy().update({"BUILDBOT_TEST" : "1"}))
        except (CommandError, OSError) as exc:
            LOG.error("Staging checkconfig failed: %s", exc)
            notify(to, "FAILED", details, error_log(exc))
            return 1

        # Apply the exact revision that passed staging validation.
        update_working(working, revision)
        try:
            check_config(working, str(working / DEFAULT_CONFIG_PATH))
        except (CommandError, OSError) as exc:
            LOG.error("Working checkconfig failed: %s", exc)
            notify(to, "FAILED", details, error_log(exc))
            return 1

        if config_changes and not zorg_changes:
            LOG.info("Reconfiguring working Buildbot")
            notify(to, "SUCCEEDED (reconfig)", details)
            run(["buildbot", "reconfig", working], cwd=working)
        elif zorg_changes:
            notify(to, "SUCCEEDED (restart)", details)
            if Path("/.dockerenv").exists():
                LOG.info("Restarting container by terminating PID 1")
                run(["kill", "1"])
            else:
                LOG.info("Restarting working Buildbot")
                run(["buildbot", "restart", working], cwd=working)
        return 0
    except (CommandError, OSError, RuntimeError) as exc:
        LOG.error("Update failed: %s", exc)
        notify(to, "FAILED", details, error_log(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
