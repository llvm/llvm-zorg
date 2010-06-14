import os
from lnt.testing.util import commands

def get_source_version(path):
    """get_source_version(path) -> str or None

    Given the path to a revision controlled source tree, return a revision
    number, hash, etc. which identifies the source version.
    """

    if os.path.exists(os.path.join(path, ".svn")):
        return commands.capture(['/bin/sh', '-c',
                                 'cd "%s" && svnversion' % path]).strip()
    elif os.path.exists(os.path.join(path, ".git", "svn")):
        res = commands.capture(['/bin/sh', '-c',
                                    'cd "%s" && git svn info' % path]).strip()
        for ln in res.split("\n"):
            if ln.startswith("Revision:"):
                return ln.split(':',1)[1].strip()
    elif os.path.exists(os.path.join(path, ".git")):
        return commands.capture(['/bin/sh', '-c',
                                 ('cd "%s" && '
                                  'git log -1 --pretty=format:%%H') % path]
                                ).strip()
