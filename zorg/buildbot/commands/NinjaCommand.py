from buildbot.process.properties import WithProperties
from buildbot.steps.shell import WarningCountingShellCommand

class NinjaCommand(WarningCountingShellCommand):

    def __init__(self, prefixCommand=None, targets=None, **kwargs):
        self.prefixCommand = prefixCommand
        self.targets = targets

        command = []
        if prefixCommand:
            command += prefixCommand

        command += ["ninja",
                     WithProperties("%(jobs:+-j)s"),        WithProperties("%(jobs:-)s"),
                     WithProperties("%(loadaverage:+-l)s"), WithProperties("%(loadaverage:-)s")]

        if targets:
            command += targets

        # Don't forget to remove all the empty items from the command,
        # which we could get because of WithProperties rendered as empty strings.
        kwargs['command'] = command

        # And upcall to let the base class do its work
        WarningCountingShellCommand.__init__(self, **kwargs)

        self.addFactoryArguments(prefixCommand=prefixCommand,
                                 targets=targets)

    def setupEnvironment(self, cmd):
        # First upcall to get everything prepared.
        WarningCountingShellCommand.setupEnvironment(self, cmd)

        # Set default status format string.
        if cmd.args['env'] is None:
            cmd.args['env'] = {}
        cmd.args['env']['NINJA_STATUS'] = cmd.args['env'].get('NINJA_STATUS', "%e [%u/%r/%f] ")

    def start(self):
        # Don't forget to remove all the empty items from the command,
        # which we could get because of WithProperties rendered as empty strings.
        self.command = filter(bool, self.command)
        # Then upcall.
        WarningCountingShellCommand.start(self)
