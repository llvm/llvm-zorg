from buildbot.process.buildstep import LoggedRemoteCommand
from buildbot.interfaces import BuildSlaveTooOldError
import stat

from twisted.python import log

class FileExists(object):
    """I check a file existence on the buildslave. I return True if the file
    with the given name exists, False if the file does not exist or that is
    a directory.

    Use me with doStepIf to make a build step conditional to existence of some
    file. For example

    doStepIf=FileExists('build/configure')
    """

    def __init__(self, filename):
        self.filename = filename

    def __call__(self, step):
        slavever = step.slaveVersion('stat')
        if not slavever:
            raise BuildSlaveTooOldError("slave is too old, does not know "
                                        "about stat")

        def commandComplete(cmd):
            if cmd.rc != 0:
                return False

            s = cmd.updates["stat"][-1]
            filemode = s[stat.ST_MODE]
            if stat.S_ISREG(filemode) or stat.S_ISLNK(filemode):
                # True only if this is a file or a link and not any other file
                # system object.
                return True
            else:
                return False

        cmd = LoggedRemoteCommand('stat', {'file': self.filename})
        d = step.runCommand(cmd)
        d.addCallback(lambda res: commandComplete(cmd))
        return d

class FileDoesNotExist(object):
    """I check a file existence on the buildslave. I return False if
    the file with the given name exists or that is a directory, True if the
    file does not exist.

    Use me with doStepIf to make a build step conditional to nonexistence
    of some file. For example

    doStepIf=FileDoesNotExist('build/configure')
    """

    def __init__(self, filename):
        self.filename = filename

    def __call__(self, step):
        slavever = step.slaveVersion('stat')
        if not slavever:
            raise BuildSlaveTooOldError("slave is too old, does not know "
                                        "about stat")

        def commandComplete(cmd):
            # False if any filesystem object with the given name exists.
            return (cmd.rc != 0)

        cmd = LoggedRemoteCommand('stat', {'file': self.filename})
        d = step.runCommand(cmd)
        d.addCallback(lambda res: commandComplete(cmd))
        return d