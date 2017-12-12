# COPYRIGHT LINE: FIXME

"""
dbsign.shell

shell routines for debugsign
"""

from __future__ import print_function

import os
from subprocess import PIPE, Popen

import dbsign.logger


log = dbsign.logger.get_logger(__name__)


class ShellCommand(object):
    """
    Represents the result of a shell command
    """
    def __init__(self, args, code, stdout, stderr):
        # type: (list[str], int, str, str) -> ()
        self.data = {
            'args': args,
            'code': code,
            'stdout': stdout,
            'stderr': stderr,
        }

    def __eq__(self, rhs):  # type: (ShellCommand) -> bool
        return self.data == rhs.data

    def __getattr__(self, attr):  # type: (str) -> T
        if attr in self.data:
            return self.data[attr]
        raise AttributeError(attr)

    def __nonzero__(self):  # type: () -> bool
        return self.code == 0

    def __repr__(self):  # type: () -> str
        repr_fmt = "{0}(args={1.args!r}, code={1.code!r},"
        repr_fmt += " stdout={1.stdout!r}, stderr={1.stderr!r})"
        return repr_fmt.format(self.__class__.__name__, self)


def __run(args, stdin=None):  # type: (list[str], str) -> ShellCommand
    """internal function to run shell commands"""
    try:
        p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(input=stdin)
    except OSError as os_err:
        log.debug('Unable to execute command: %s: %s', args, os_err)
        raise

    cmd = ShellCommand(args, code=p.returncode, stdout=stdout, stderr=stderr)
    log.debug(cmd)
    return cmd


def run(args, stdin=None):  # type: (list[str]) -> ShellCommand
    """Run a regular (non-sudo) command"""
    log.debug("run(args=%s)", repr(args))

    if os.path.basename(args[0]).startswith('su'):
        log.info('run() called with illegal command `%s`', args)
        raise RuntimeError('Unauthorized use of run; use sudo_run')

    return __run(args, stdin)


def sudo_run(args, stdin=None):  # type: (list[str]) -> ShellCommand
    """Run a command with root privileges using sudo"""
    log.debug("sudo_run(args=%s)", repr(args))

    args.insert(0, 'sudo')

    return __run(args, stdin)
