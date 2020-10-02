# TODO: Add support for clang crash dumps.
# TODO: Better handle unit/regression tests failures

# TODO: For debug purposes. Remove this later.
from twisted.python import log

from buildbot.plugins import reporters

def _get_logs_and_tracebacks_from_build(build):
    # TODO: Implement interesting parts of the logs and tracebacks extraction.
    return dict()

MAIL_TEMPLATE = """\
The Buildbot has detected a {{ status_detected }} on builder {{ buildername }} while building {{ projects }}.
Full details are available at:
    {{ build_url }}
Buildbot URL: {{ buildbot_url }}
Worker for this Build: {{ workername }}
Build Reason: {{ build['properties'].get('reason', ["<unknown>"])[0] }}
Blamelist: {{ ", ".join(blamelist) }}
{{ summary }}
Sincerely,
LLVM Buildbot
"""

class LLVMMessageFormatter(reporters.MessageFormatter):
    def buildAdditionalContext(self, master, ctx):
        #log.msg(">>> LLVMMessageFormatter.buildAdditionalContext got ctx={}".format(ctx))
        ctx.update(self.ctx)

        build = ctx["build"]
        build_interesting_data = _get_logs_and_tracebacks_from_build(build)
        #log.msg(">>> LLVMMessageFormatter.buildAdditionalContext build_interesting_data={}",format(build_interesting_data))
        ctx["build"].update(build_interesting_data)


LLVMInformativeMailNotifier = LLVMMessageFormatter(
    template=MAIL_TEMPLATE,
    template_type="plain",
    wantLogs=True,
    wantProperties=True,
    wantSteps=True,
)
