import re
import os
from lnt.testing.util import commands

_git_svn_id_re = re.compile("^    git-svn-id: [^@]*@([0-9]+) .*$")
def get_source_version(path):
    """get_source_version(path) -> str or None

    Given the path to a revision controlled source tree, return a revision
    number, hash, etc. which identifies the source version.
    """

    if os.path.exists(os.path.join(path, ".svn")):
        return commands.capture(['/bin/sh', '-c',
                                 'cd "%s" && svnversion' % path]).strip()
    elif os.path.exists(os.path.join(path, ".git", "svn")):
        # git-svn is pitifully slow, extract the revision manually.
        res = commands.capture(['/bin/sh', '-c',
                                ('cd "%s" && '
                                 'git log -1') % path]
                               ).strip()
        last_line = res.split("\n")[-1]
        m = _git_svn_id_re.match(last_line)
        if not m:
            commands.warning("unable to understand git svn log: %r" % res)
            return
        return m.group(1)
    elif os.path.exists(os.path.join(path, ".git")):
        return commands.capture(['/bin/sh', '-c',
                                 ('cd "%s" && '
                                  'git log -1 --pretty=format:%%H') % path]
                                ).strip()
