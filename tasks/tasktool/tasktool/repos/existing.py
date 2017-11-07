import sys
import os.path
import tasktool.utils as utils


def verify(config):
    pass


def resolve_latest(config):
    pass


def get_artifact(config, dest_dir):
    if not os.path.isdir(dest_dir):
        sys.stderr.write("Error: Expected directory '%s' is missing\n" %
                         (dest_dir, ))
        sys.exit(1)


def repro_arg(config, dest_dir):
    if os.path.exists('%s/.git' % dest_dir):
        rev = utils.check_output(['git', '--git-dir=%s/.git' % dest_dir,
                                  'rev-parse', 'HEAD'])
        rev = rev.strip()
        return '-r %s=%s' % (dest_dir, rev)
    else:
        return "!Unknown repository type in '%s'" % dest_dir
