from __future__ import print_function

import errno
import os
import re
import shutil
import subprocess
import sys


def clean_dir(path):
    """
    Remove directory path if it exists and create a new, empty directory
    in its place.
    """
    try:
        shutil.rmtree(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
    mkdirp(path)


def cmake_pjoin(*args):
    """
    Join paths like safe_pjoin, but replace backslashes with forward
    slashes on platforms where they are path separators. This prevents
    CMake from choking when trying to decode what it thinks are escape
    sequences in filenames.
    """
    result = safe_pjoin(*args)
    if os.sep == '\\':
        return result.replace('\\', '/')
    else:
        return result


def report(msg):
    sys.stderr.write(msg + '\n')
    sys.stderr.flush()


def report_run_cmd(cmd, shell=False, *args, **kwargs):
    """
    Print a command, then executes it using subprocess.check_call.
    """
    report('Running: %s' % ((cmd if shell else shquote_cmd(cmd)),))
    sys.stderr.flush()
    subprocess.check_call(cmd, shell=shell, *args, **kwargs)


def mkdirp(path):
    """Create directory path if it does not already exist."""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def safe_pjoin(dirname, *args):
    """
    Join path components with os.path.join, skipping the first component
    if it is None.
    """
    if dirname is None:
        return os.path.join(*args)
    else:
        return os.path.join(dirname, *args)


def _shquote_impl(txt, escaped_chars, quoted_chars):
    quoted = re.sub(escaped_chars, r'\\\1', txt)
    if len(quoted) == len(txt) and not quoted_chars.search(txt):
        return txt
    else:
        return '"' + quoted + '"'


_SHQUOTE_POSIX_ESCAPEDCHARS = re.compile(r'(["`$\\])')
_SHQUOTE_POSIX_QUOTEDCHARS = re.compile('[|&;<>()\' \t\n]')


def shquote_posix(txt):
    """Return txt, appropriately quoted for POSIX shells."""
    return _shquote_impl(
        txt, _SHQUOTE_POSIX_ESCAPEDCHARS, _SHQUOTE_POSIX_QUOTEDCHARS)


_SHQUOTE_WINDOWS_ESCAPEDCHARS = re.compile(r'(["\\])')
_SHQUOTE_WINDOWS_QUOTEDCHARS = re.compile('[ \t\n]')


def shquote_windows(txt):
    """Return txt, appropriately quoted for Windows's cmd.exe."""
    return _shquote_impl(
        txt.replace('%', '%%'),
        _SHQUOTE_WINDOWS_ESCAPEDCHARS, _SHQUOTE_WINDOWS_QUOTEDCHARS)


def shquote(txt):
    """Return txt, appropriately quoted for use in a shell command."""
    if os.name in set(('nt', 'os2', 'ce')):
        return shquote_windows(txt)
    else:
        return shquote_posix(txt)


def shquote_cmd(cmd):
    """Convert a list of shell arguments to an appropriately quoted string."""
    return ' '.join(map(shquote, cmd))
