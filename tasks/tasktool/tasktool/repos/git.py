import sys
import tasktool.utils as utils


def _git_ls_remote(url, ref):
    refs = utils.check_output(['git', 'ls-remote', url, ref])
    revs = {}
    for line in refs.split("\n"):
        line = line.strip()
        if line == "":
            continue
        rev, _, name = line.partition('\t')
        revs[name] = rev

    return revs


def verify(config):
    if config.get('url') is None:
        raise Exception("No 'url' specified")


def resolve_latest(config):
    assert(config['type'] == 'git')
    rev = config.get('rev')
    default_rev = config.pop('default_rev', None)
    if default_rev is None:
        default_rev = "refs/heads/master"
    if rev is not None:
        return
    url = config['url']
    revs = _git_ls_remote(url, default_rev)
    # Look for an exact match
    if default_rev is not None:
        rev = revs.get(default_rev, None)
    # Otherwise hope that we only have a single match.
    if rev is None:
        if len(revs) == 0:
            raise Exception("No refs matching '%s' found for "
                            "repository '%s'\n" % (default_rev, url))
        if len(revs) > 1:
            raise Exception("Found multiple refs matching '%s' for "
                            "repository '%s': %s\n" %
                            (default_rev, url, ", ".join(revs.keys())))
        rev = revs.values()[0]
    config['rev'] = rev


def get_artifact(config, dest_dir):
    url = config['url']
    rev = config['rev']
    # Note: -s is slightly dangerous for long running builds on the local
    # machine where the user changes the reference repo. But it's also a good
    # bit faster.
    utils.check_call(['git', 'clone', '-q', '-n', '-s', url, dest_dir])
    utils.check_call(['git', '--git-dir=%s/.git' % dest_dir,
                     '--work-tree=%s' % dest_dir, 'checkout', '-q', rev])


def repro_arg(config, dest_dir):
    return '-r %s=%s' % (dest_dir, config['rev'])
