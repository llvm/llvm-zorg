from buildbot.process.remotecommand import RemoteCommand
from buildbot.interfaces import WorkerTooOldError
import stat


class FileExists(object):
    """I check a file existence on the worker. I return True if the file
    with the given name exists, False if the file does not exist or that is
    a directory.

    Use me with doStepIf to make a build step conditional to existence of some
    file. For example

    doStepIf=FileExists('build/configure')
    """

    def __init__(self, filename):
        self.filename = filename

    def __call__(self, step):
        step.checkWorkerHasCommand('stat')
        cmd = RemoteCommand('stat', {'file': self.filename})
        d = step.runCommand(cmd)
        d.addCallback(lambda res: self.commandComplete(cmd))
        return d

    def commandComplete(self, cmd):
        if cmd.didFail():
            return False

        s = cmd.updates["stat"][-1]
        filemode = s[stat.ST_MODE]
        if stat.S_ISREG(filemode) or stat.S_ISLNK(filemode):
            # True only if this is a file or a link and not any other file
            # system object.
            return True
        else:
            return False


class FileDoesNotExist(object):
    """I check a file existence on the worker. I return False if
    the file with the given name exists or that is a directory, True if the
    file does not exist.

    Use me with doStepIf to make a build step conditional to nonexistence
    of some file. For example

    doStepIf=FileDoesNotExist('build/configure')
    """

    def __init__(self, filename):
        self.filename = filename

    def __call__(self, step):
        step.checkWorkerHasCommand('stat')
        cmd = RemoteCommand('stat', {'file': self.filename})
        d = step.runCommand(cmd)
        d.addCallback(lambda res: self.commandComplete(cmd))
        return d

    def commandComplete(self, cmd):
        # False if any filesystem object with the given name exists.
        return cmd.didFail()
