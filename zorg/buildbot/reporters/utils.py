import re
import traceback

from twisted.internet import defer
from twisted.python import log

from buildbot.reporters.generators.build import BuildStatusGenerator
from buildbot.reporters.github import GitHubCommentPush
from buildbot.reporters.message import MessageFormatter
from buildbot.reporters.utils import getDetailsForBuild

from buildbot.process.results import CANCELLED
from buildbot.process.results import EXCEPTION
from buildbot.process.results import FAILURE
from buildbot.process.results import RETRY
from buildbot.process.results import SKIPPED
from buildbot.process.results import SUCCESS
from buildbot.process.results import WARNINGS
from buildbot.process.results import statusToString

from zorg.buildbot.commands.LitTestCommand import LitLogObserver

def get_log_details(build):
    failed_step = None
    text = ""
    try:
        for step in build['steps']:
            results = step['results']
            if results != FAILURE:
                continue

            text += f"Step {step['number']} ({step['name']}) {statusToString(results)}: {step['state_string']}\n"

            if failed_step is None:
                failed_step = f"{step['number']} \"{step['name']}\""

            logs = step['logs']
            if logs:
                log_index = -1
                log_priority = 0
                for i, _log in enumerate(logs):
                    # Use only first logchunk "FAIL: "
                    if log_priority < 4 and _log['name'].startswith("FAIL: "):
                        log_priority = 4
                        log_index = i
                    # Use lower priority for 'preamble'. Note the type is stdio too.
                    elif log_priority < 2 and _log['name'] == "preamble":
                        log_priority = 2
                        log_index = i
                    elif log_priority < 3 and _log['type'] == "s":  # stdio
                        log_priority = 3
                        log_index = i
                    elif log_priority < 1 and _log['name'].startswith("warnings "):
                        log_priority = 1
                        log_index = i

                if log_index < 0:
                    continue

                log_text = logs[log_index]['content']['content']
                if logs[log_index]['type'] == "s":
                    # Parse stdio
                    raw_lines = log_text.splitlines()
                    lines = []
                    fail_index = -1
                    for line in raw_lines:
                        if line.startswith("h"): # header
                            line = line[1:]
                            if fail_index == -1:
                                # Check for "command timed out:"
                                if LitLogObserver.kTestLineKill.match(line):
                                    fail_index = len(lines)
                                else:
                                    # Drop this header line
                                    continue
                        elif line.startswith("o") or line.startswith("e"):
                            # Adjust stdout or stderr line
                            line = line[1:]
                        lines.append(line)
                    for j, line in enumerate(lines):
                        if fail_index != -1 and fail_index < j:
                            break
                        if line.startswith("FAIL:") or line.find("FAILED") != -1:
                            fail_index = j
                            break
                    if fail_index >= 0:
                        if fail_index > 10:
                            del lines[:fail_index-10] # Start 10 lines before FAIL
                            lines = ["..."] + lines
                        del lines[50:] # Keep up to 50 lines around FAIL
                    elif len(lines) > 50:
                        # Otherwise keep last 50 lines
                        del lines[:len(lines)-50]
                        lines = ["..."] + lines

                    log_text = "\n".join(lines)

                elif logs[log_index]['num_lines'] > 50:
                    # Keep first 50 lines
                    lines = log_text.splitlines()
                    del lines[50:]
                    log_text = "\n".join(lines + ["..."])

                text += log_text + "\n"

    except Exception as err:
        log.msg(
            f"Exception in LLVMMessageFormatter.get_log_details(): {err}\n{traceback.format_exc()}"
        )

    return {"failed_step": failed_step if failed_step else "?", "details": text}


# TODO: Add build reason if we have that valid and available
#Build Reason: {{ build['properties'].get('reason', ["<unknown>"])[0] }}

MAIL_TEMPLATE = """\
The Buildbot has detected a {{ status_detected }} on builder {{ buildername }} while building {{ projects }}.

Full details are available at:
    {{ build_url }}

Worker for this Build: {{ workername }}
Blamelist:
    {{ ",\n    ".join(blamelist) }}

{{ summary }}

{{ details }}
Sincerely,
LLVM Buildbot
"""

COMMENT_TEMPLATE = """\
LLVM Buildbot has detected a new failure on builder `{{ buildername }}` running on `{{ workername }}` while building `{{ projects }}` at step {{ failed_step }}.

Full details are available at: {{ build_url }}

<details>
<summary>Here is the relevant piece of the build log for the reference</summary>

```
{{ details }}
```

</details>
"""


class LLVMMessageFormatter(MessageFormatter):
    def buildAdditionalContext(self, master, ctx):
        ctx.update(self.context)
        ctx.update(get_log_details(ctx["build"]))

LLVMInformativeMailNotifier = LLVMMessageFormatter(
    template=MAIL_TEMPLATE,
    template_type="plain",
    want_logs=True,
    want_logs_content=True,
    want_properties=True,
    want_steps=True,
)

LLVMInformativeComment = LLVMMessageFormatter(
    template=COMMENT_TEMPLATE,
    template_type="plain",
    want_logs=True,
    want_logs_content=True,
    want_properties=True,
    want_steps=True,
)


class LLVMInformativeMailGenerator(BuildStatusGenerator):
    def __init__(self, mode=("problem",),
                 message_formatter = LLVMInformativeMailNotifier, **kwargs):
        super().__init__(mode=mode, message_formatter=message_formatter, **kwargs)

class LLVMDefaultBuildStatusGenerator(BuildStatusGenerator):
    def __init__(self, mode=("failing",),
                 subject="Build Failure: {{ buildername }}", **kwargs):
        super().__init__(mode=mode,
                         message_formatter=MessageFormatter(subject=subject),
                         **kwargs)


class LLVMFailBuildGenerator(BuildStatusGenerator):
    def __init__(
        self,
        tags=None,
        builders=None,
        schedulers=None,
        branches=None,
        add_logs=True,
        add_patch=False,
        message_formatter=LLVMInformativeComment,
    ):
        super().__init__(
            mode=("problem",),
            tags=tags,
            builders=builders,
            schedulers=schedulers,
            branches=branches,
            subject=None,
            add_logs=add_logs,
            add_patch=add_patch,
        )
        self.formatter = message_formatter

    def is_message_needed_by_results(
        self, build
    ):  # override, the code may be moved to generate()
        results = build["results"]
        # Check for mode == "problem" only.
        if results == FAILURE:
            prev_build = build["prev_build"]
            if (
                prev_build and prev_build["results"] == SUCCESS
            ):  # Note != FAILURE in base
                return True
        return False

    @defer.inlineCallbacks
    def generate(self, master, reporter, key, build):  # override
        yield getDetailsForBuild(
            master,
            build,
            want_properties=True,
            want_steps=self.formatter.want_steps,
            want_previous_build=True,
            want_logs=self.formatter.want_logs,
            want_logs_content=self.formatter.want_logs_content,
        )
        buildid = build["buildid"]

        if not self.is_message_needed_by_props(build):
            # log.msg(f"LLVMFailBuildGenerator.generate(buildid={buildid}): INFO: Not is_message_needed_by_props. Ignore.")
            return None
        if not self.is_message_needed_by_results(build):
            # log.msg(f"LLVMFailBuildGenerator.generate: INFO(buildid={buildid}): INFO: Not is_message_needed_by_results. Ignore.")
            return None

        changes = yield master.data.get(("builds", buildid, "changes"))
        log.msg(
            f"LLVMFailBuildGenerator.generate(buildid={buildid}): INFO: changes={changes}"
        )

        len_changes = len(changes)
        if len_changes < 1:
            log.msg(
                f"LLVMFailBuildGenerator.generate(buildid={buildid}): WARNING: No changes (unknown). Ignore."
            )
            return None
        elif len_changes > 1:
            log.msg(
                f"LLVMFailBuildGenerator.generate(buildid={buildid}): WARNING: Number of changes ({len_changes}) must be 1. Ignore."
            )
            return None

        change = changes[0]
        # Get the first line of the commit description.
        title = change["comments"].split("\n")[0]

        # Search for PR# in the first line of the commit description, which looks like 'Some text (#123)'.
        m = re.search(r"^.* \(#(\d+)\)$", title)
        if not m:
            log.msg(
                f"LLVMFailBuildGenerator.generate(buildid={buildid}): WARNING: Cannot extract PR# from the title '{title}'."
            )
            return None

        issue = m.group(1)

        # To play it safe for further processing we want a snapshot:
        # a local shallow copy of build information,
        # along with a copy of build properties.
        build_info = build.copy()
        build_info["properties"] = build["properties"].copy()

        build_info["properties"]["issue"] = (
            issue,
            None,
        )

        #log.msg(f"LLVMFailBuildGenerator.generate(buildid={buildid}): INFO: calling  yield self.build_message build_info={build_info}")
        report = yield self.build_message(self.formatter, master, reporter, build_info)
        # log.msg(f"LLVMFailBuildGenerator.generate(buildid={buildid}): INFO: report={report}")
        return report


class LLVMFailGitHubReporter(GitHubCommentPush):
    name = "LLVMFailGitHubReporter"

    def _extract_issue(self, props):  # override
        log.msg(f"LLVMFailGitHubReporter._extract_issue: INFO: props={props}")
        issue = props.getProperty("issue")
        log.msg(f"LLVMFailGitHubReporter._extract_issue: INFO: issue={issue}")
        return issue

    # This function is for logging purposes only.
    # Could be removed completely if log verbosity would be reduced.
    @defer.inlineCallbacks
    def createStatus(
        self,
        repo_user,
        repo_name,
        sha,
        state,
        target_url=None,
        context=None,
        issue=None,
        description=None,
    ):  # override
        payload = {"body": description}
        log.msg(f"LLVMFailGitHubReporter.createStatus: INFO:\n{description}")

        if issue is None:
            log.msg(
                f"LLVMFailGitHubReporter.createStatus: WARNING: Skipped adding the comment for repo {repo_name} sha {sha} as issue is not specified."
            )
            return None

        # Users could reference wrong PRs in commit messages.
        # So, to make sure we are commenting the correct one we need to check
        # if the given commit is actually corresponding to the PR we parsed
        # from the commit message.

        wrong_issue = True
        page = 1
        while wrong_issue:
            events_response = yield self._http.get(
                "/".join(["/repos", repo_user, repo_name, "issues", issue, "events"]) +
                f"?per_page=100&page={page}")
            if events_response.code not in (200,):
                log.msg(
                    f"LLVMFailGitHubReporter.createStatus: WARNING: Cannot get events for PR#{issue}. Do not comment this PR."
                )
                return None

            events = yield events_response.json()

            # Empty events array signals that there is no more.
            if not events:
                log.msg(
                    f"LLVMFailGitHubReporter.createStatus: WARNING: Got empty events list for PR#{issue}."
                )
                break

            log.msg(
                f"LLVMFailGitHubReporter.createStatus: WARNING: Got events list for PR#{issue} (page {page}): {events}."
            )

            for event in events:
                if event["event"] == "merged":
                    if event["commit_id"] == sha:
                        wrong_issue = False
                        break
                    else:
                        log.msg(
                            f"LLVMFailGitHubReporter.createStatus: WARNING: Event 'merged' in PR#{issue} contains commit_id {event['commit_id']}, but revision is {sha}."
                        )
            page += 1

        if wrong_issue:
            log.msg(
                f"LLVMFailGitHubReporter.createStatus: WARNING: Given commit {sha} is not related to PR#{issue}. Do not comment this PR."
            )
            return None

        # This is the right issue to comment.

        url = "/".join(["/repos", repo_user, repo_name, "issues", issue, "comments"])
        log.msg(f"LLVMFailGitHubReporter.createStatus: INFO: http.post({url})")

        # Comment out this line and uncomment following lines
        # to disable submitting to github for debug purpose.
        ret = yield self._http.post(url, json=payload)
        # yield
        # ret = None
        return ret
