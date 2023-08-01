import re

from twisted.internet import defer
from twisted.python import log as logging

from buildbot.plugins import steps, util


class NinjaCommand(steps.WarningCountingShellCommand):
    DEFAULT_NINJA = "ninja"

    name = "build"
    haltOnFailure = True
    description = ["building"]
    descriptionDone = ["build"]
    renderables = [
        'options',
        'targets',
        'ninja',
        'jobs',
        'loadaverage'
    ]

    def __init__(self, options=None, targets=None, ninja=DEFAULT_NINJA, logObserver=None,
                 jobs=None, loadaverage=None, **kwargs):
        self.ninja = ninja
        self.targets = targets
        
        # The options must be iterable or None.
        self.options = options

        if logObserver:
            self.logObserver = logObserver
            self.addLogObserver('stdio', self.logObserver)

        self.jobs = jobs
        self.loadaverage = loadaverage

        # Update the environment variables with the ninja status format settings.
        env = kwargs.get("env") or {}

        # Note: At this point env could be a dictionary or a Property object.
        if isinstance(env, dict):
            if "NINJA_STATUS" not in env:
                env = env.copy()
                env["NINJA_STATUS"] = "%e [%u/%r/%f] "
        #else:
            # FIXME: Properly handle Property('vs_env')
            #logging.msg(f'NinjaCommand: Be sure {env} contains NINJA_STATUS="%e [%u/%r/%f] "')
        kwargs["env"] = env

        # And upcall to let the base class do its work
        super().__init__(**kwargs)

    @defer.inlineCallbacks
    def run(self):
        # Prepare the full build command to run.
        ninja_command = [self.ninja]

        if self.jobs is None and self.build.hasProperty("jobs"):
            self.jobs = self.build.getProperty("jobs")
        if self.loadaverage is None and self.build.hasProperty("loadaverage"):
            self.loadaverage = self.build.getProperty("loadaverage")

        if self.jobs:
            ninja_command.extend(["-j", f"{self.jobs}"])
        if self.loadaverage:
            ninja_command.extend(["-l", f"{self.loadaverage}"])

        if self.options:
            ninja_command.extend(self.options)
        if self.targets:
            ninja_command.extend(self.targets)

        self.command = ninja_command

        result = yield super().run()

        return result
