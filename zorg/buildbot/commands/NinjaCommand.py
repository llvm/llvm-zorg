# TODO: Use Interpolate instead of WithProperties.
import re

from buildbot.process.properties import WithProperties
from buildbot.steps.shell import WarningCountingShellCommand

class NinjaCommand(WarningCountingShellCommand):
    DEFAULT_NINJA = 'ninja'

    @staticmethod
    def sanitize_kwargs(kwargs):
        # kwargs we could get and must not pass through
        # to the buildstep.RemoteShellCommand constructor.
        # Note: This is a workaround of the buildbot design issue,
        # thus should be removed once the original issue gets fixed.
        consume_kwargs = [
                             "jobs",
                             "loadaverage",
                         ]

        sanitized_kwargs = kwargs.copy()
        for k in consume_kwargs:
            if k in sanitized_kwargs.keys():
                del sanitized_kwargs[k]

        return sanitized_kwargs

    name = "build"
    haltOnFailure = True
    description = ["building"]
    descriptionDone = ["build"]
    renderables = (
        'options',
        'targets',
        'ninja',
    )

    def __init__(self, options=None, targets=None, ninja=DEFAULT_NINJA, logObserver=None, **kwargs):
        self.ninja = ninja
        self.targets = targets

        if options is None:
            self.options = list()
        else:
            self.options = list(options)

        if logObserver:
            self.logObserver = logObserver
            self.addLogObserver('stdio', self.logObserver)

        j_opt = re.compile(r'^-j$|^-j\d+$')
        l_opt = re.compile(r'^-l$|^-l\d+(\.(\d+)?)?$')

        command = list()
        command += [self.ninja]

        # We can get jobs in the options. If so, we would use that.
        if not any(j_opt.search(opt) for opt in self.options if isinstance(opt, str)):
            # Otherwise let's see if we got it in the kwargs.
            if kwargs.get('jobs', None):
                self.options += ["-j", kwargs['jobs']]
            else:
                # Use the property if option was not explicitly
                # specified.
                command += [
                    WithProperties("%(jobs:+-j)s"),
                    WithProperties("%(jobs:-)s"),
                    ]

        # The same logic is for handling the loadaverage option.
        if not any(l_opt.search(opt) for opt in self.options if isinstance(opt, str)):
            if kwargs.get('loadaverage', None):
                self.options += ["-l", kwargs['loadaverage']]
            else:
                command += [
                    WithProperties("%(loadaverage:+-l)s"),
                    WithProperties("%(loadaverage:-)s"),
                    ]

        if self.options:
            command += self.options

        if self.targets:
            command += self.targets

        # Remove here all the kwargs any of our LLVM buildbot command could consume.
        # Note: We will remove all the empty items from the command at start, as we
        # still didn't get yet WithProperties rendered.
        sanitized_kwargs = self.sanitize_kwargs(kwargs)

        sanitized_kwargs["command"] = command

        # And upcall to let the base class do its work
        super().__init__(**sanitized_kwargs)

    def setupEnvironment(self, cmd):
        # First upcall to get everything prepared.
        super().setupEnvironment(cmd)

        # Set default status format string.
        if cmd.args['env'] is None:
            cmd.args['env'] = {}
        cmd.args['env']['NINJA_STATUS'] = cmd.args['env'].get('NINJA_STATUS', "%e [%u/%r/%f] ")

    def buildCommandKwargs(self, warnings):
        kwargs = super().buildCommandKwargs(warnings)
        # Remove all the empty items from the command list,
        # which we could get if Interpolate rendered to empty strings.
        kwargs['command'] = [cmd for cmd in kwargs['command'] if cmd]
        return kwargs
