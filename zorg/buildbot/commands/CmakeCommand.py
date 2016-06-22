from buildbot.process.properties import WithProperties
from buildbot.steps.shell import WarningCountingShellCommand

class CmakeCommand(WarningCountingShellCommand):

    def __init__(self, prefixCommand=None, options=None, path=None, **kwargs):
        self.prefixCommand = prefixCommand
        self.path = [path]

        if options is None:
            self.options = list()
        else:
            self.options = list(options)

        command = []
        if prefixCommand:
            command += prefixCommand

        command += ["cmake"]

        # Set some default options.

        if not any(a.startswith('-DCMAKE_BUILD_TYPE=')   for a in self.options):
            self.options.append('-DCMAKE_BUILD_TYPE=Release')
        if not any(a.startswith('-DLLVM_ENABLE_WERROR=') for a in self.options):
            self.options.append('-DLLVM_ENABLE_WERROR=ON')
        if self.options:
            command += self.options

        if self.path:
            command += self.path

        # Note: We will remove all the empty items from the command at start.
        kwargs['command'] = command

        # And upcall to let the base class do its work
        WarningCountingShellCommand.__init__(self, **kwargs)

        self.addFactoryArguments(prefixCommand=prefixCommand,
                                 options=self.options,
                                 path=path)

    def start(self):
        # Don't forget to remove all the empty items from the command,
        # which we could get because of WithProperties rendered as empty strings.
        self.command = filter(bool, self.command)
        # Then upcall.
