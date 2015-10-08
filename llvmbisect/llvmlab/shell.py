"""
shell like utilities
"""

import os


def execute(args):
    import subprocess
    """execute(command) - Run the given command (or argv list) in a shell and
    return the exit code."""
    return subprocess.Popen(args).wait()


def capture(args, include_stderr=False):
    import subprocess
    """capture(command) - Run the given command (or argv list) in a shell and
    return the standard output."""
    stderr = subprocess.PIPE
    if include_stderr:
        stderr = subprocess.STDOUT
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=stderr)
    out, _ = p.communicate()
    return p.wait(), out


def mkdir_p(path):
    """mkdir_p(path) - Make the "path" directory, if it does not exist; this
    will also make directories for any missing parent directories."""
    import errno

    if not path or os.path.exists(path):
        return

    parent = os.path.dirname(path)
    if parent != path:
        mkdir_p(parent)

    try:
        os.mkdir(path)
    except OSError as e:
        # Ignore EEXIST, which may occur during a race condition.
        if e.errno != errno.EEXIST:
            raise
