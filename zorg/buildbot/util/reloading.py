"""
Helper module for defining a utility which will reload all of the
modules used in the system.

This is important when using buildbot's reload command.
"""

import os
import sys

time_cache = {}

def path_starts_with_one_of(path, paths):
    for p in paths:
        if path.startswith(p):
            return True

def reload_all(only_paths = [], log = False):
    # Reload all modules in sys.modules which have changed.
    for module in sys.modules.values():
        if not hasattr(module, '__file__'):
            continue
        path = getattr(module, '__file__')
        if not path:
            continue
        if os.path.splitext(path)[1] in ['.pyc', '.pyo', '.pyd']:
            path = path[:-1]

        # Never reload ourselves, we don't want to kill the cache.
        if path == __file__:
            continue

        # If we were given a limited path list, only reload modules
        # with paths under that.
        if only_paths and not path_starts_with_one_of(path, only_paths):
            continue

        if os.path.isfile(path):
            mtime = os.stat(path).st_mtime
            if path not in time_cache or mtime != time_cache[path]:
                if log:
                    print >>sys.stderr, "note: reloading %r" % path
                time_cache[path] = mtime
                reload(module)
