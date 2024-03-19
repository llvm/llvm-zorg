import os
import sys

sys.path.append(os.path.dirname(__file__))

from pipes import quote
import json
import os
import shutil
import sys
import utils
import tasktool.repos as repos


def _read_config():
    try:
        configfilename = 'buildconfig.json'
        with open(configfilename) as configfile:
            config = json.load(configfile)
    except Exception as e:
        sys.stderr.write("Could not read buildconfig.json: %s" % e)
        sys.exit(1)
    return config


def _get_artifact_from_url(config, dest_dir):
    url = config.get('url')
    if url is None:
        sys.stderr.write("Missing URL for '%s'\n" % name)
        sys.exit(1)
    tar_cmd = "cd %s ; curl -s %s | tar -x" % (quote(dest_dir), quote(url))
    utils.check_call(['mkdir', '-p', dest_dir])
    utils.check_call(tar_cmd, shell=True)


def _command_get(args):
    if len(args) < 1:
        sys.stderr.write("Expected remote name\n")
        sys.exit(1)
    name = args[0]

    config = _read_config().get(name)
    if config is None:
        sys.stderr.write("No config for '%s'\n" % name)
        sys.exit(1)

    type = config['type']
    repohandler = repos.modules[type]
    repohandler.get_artifact(config, name)


def _command_arg(args):
    if len(args) == 0:
        sys.stderr.write("Expected argument name\n")
        sys.exit(1)
    argname = args[0]
    optional = False
    if args[0] == '--optional':
        optional = True
        argname = args[1]

    config = _read_config().get(argname)
    if config is None:
        if not optional:
            sys.stderr.write("No config entry for '%s'\n" % name)
            sys.exit(1)
        config = ''

    sys.stdout.write("%s\n" % config)


def _command_clean(args):
    '''This removes all directories not mentioned in the buildconfig.
    (It's main usage is as part of 'jenkinsrun' command where we assume that
     all artifacts are already supplied. And everything else is leftovers from
     previous build)'''
    config = _read_config()
    keep = set(['config', 'buildconfig.json', 'run.sh'])
    for name, kconfig in config.items():
        if isinstance(kconfig, dict) and kconfig.get('type') == 'existing':
            keep.add(name)
    remove_files = set()
    for filename in os.listdir('.'):
        if filename not in keep:
            remove_files.add(filename)
    for filename in remove_files:
        sys.stderr.write("...removing '%s'\n" % filename)
        try:
            if os.path.isdir(filename):
                shutil.rmtree(filename)
            else:
                os.unlink(filename)
        except Exception as e:
            sys.stderr.write("Error: Could not remove '%s': %s\n" %
                             (filename, e))
            sys.exit(1)


def _command_repro_args(args):
    '''Produces a message on how to reproduce a particular build locally.'''
    config = _read_config()
    for name, kconfig in config.items():
        sys.stdout.write(' \\\n')
        if isinstance(kconfig, dict):
            type = kconfig['type']
            repohandler = repos.modules[type]
            repro_arg = repohandler.repro_arg(kconfig, name)
            sys.stdout.write('    %s' % repro_arg)
        else:
            sys.stdout.write('    -D %s=%s' % (name, quote(kconfig)))
    sys.stdout.write('\n')


def main():
    commands = {
        'arg': _command_arg,
        'clean': _command_clean,
        'get': _command_get,
        'repro_args': _command_repro_args,
    }
    utils.run_subcommand(commands, sys.argv)


if __name__ == '__main__':
    main()
