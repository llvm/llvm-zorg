import traceback

from buildbot.plugins import reporters
from buildbot.process.results import CANCELLED
from buildbot.process.results import EXCEPTION
from buildbot.process.results import FAILURE
from buildbot.process.results import RETRY
from buildbot.process.results import SKIPPED
from buildbot.process.results import SUCCESS
from buildbot.process.results import WARNINGS
from buildbot.process.results import statusToString

def get_log_details(build):
    text = ""
    try:
        for step in build['steps']:
            results = step['results']
            if results == SUCCESS or results == SKIPPED:
                continue

            text += "Step {} ({}) {}: {}\n".format(step['number'], step['name'], statusToString(results), step['state_string'])

            logs = step['logs']
            if logs:
                log_index = -1
                log_type = 0
                for i, _log in enumerate(logs):
                    if _log['name'].startswith("FAIL: "): # Use only first logchunk FAIL:
                        log_type = 3
                        log_index = i
                    elif log_type < 2 and _log['name'].startswith("warnings "):
                        log_type = 2
                        log_index = i
                    elif log_type < 1 and _log['type'] == "s": # stdio
                        log_type = 1
                        log_index = i

                if log_index < 0:
                    continue

                log_text = logs[log_index]['content']['content']
                if log_type == 1:
                    # Parse stdio
                    lines = log_text.splitlines()
                    for line in lines[:]:
                        if line.startswith("h"):
                            lines.remove(line)
                    for j, line in enumerate(lines):
                        if line.startswith("o") or line.startswith("e"):
                            lines[j] = line[1:]
                    for j, line in enumerate(lines):
                        if line.find("FAIL:") != -1 or line.find("FAILED") != -1:
                            if j > 10:
                                del lines[:j-10] # Start 10 lines before FAIL
                                lines = ["..."] + lines
                            del lines[50:] # Keep up to 50 lines around FAIL
                            break
                    if len(lines) > 50:
                        del lines[:len(lines)-50] # Otherwise keep last 50 lines
                        lines = ["..."] + lines

                    log_text = "\n".join(lines)

                elif logs[log_index]['num_lines'] > 50:
                    # Keep first 50 lines
                    lines = log_text.splitlines()
                    del lines[50:]
                    log_text = "\n".join(lines + ["..."])

                text += log_text + "\n"

    except Exception as err:
        print("Exception in LLVMMessageFormatter.get_log_details(): {}\n{}".format(err, traceback.format_exc()))
        # TODO: We should send something useful in this case.

    return dict(details=text)

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

class LLVMMessageFormatter(reporters.MessageFormatter):
    def buildAdditionalContext(self, master, ctx):
        ctx.update(self.ctx)
        ctx.update(get_log_details(ctx["build"]))

LLVMInformativeMailNotifier = LLVMMessageFormatter(
    template=MAIL_TEMPLATE,
    template_type="plain",
    wantLogs=True,
    wantProperties=True,
    wantSteps=True,
)
