'''
Task runner.
'''

import os
import sys

sys.path.append(os.path.dirname(__file__))

import argparse
import json
import os
import re
import sys
import tempfile
import utils
import repos


_userdir = os.path.abspath('.')
_hooksdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hooks'))
_artifact_input_regex = \
    re.compile(r'\s*#?\s*build\s+get\s+([a-zA-Z_\-0-9]+)')
_artifact_input_regex_ex = \
    re.compile(r'\s*#?\s*build\s+get\s+([a-zA-Z_\-0-9]+)\s+--from=([a-zA-Z_\-0-9]+)')
_artifact_param_regex = \
    re.compile(r'build\s+arg\s+([a-zA-Z_\-0-9]+)\s*')
_artifact_optional_param_regex = \
    re.compile(r'build\s+arg\s+--optional\s+([a-zA-Z_\-0-9]+)\s*')


def _determine_task_inputs(taskfile):
    artifacts = dict()
    parameters = set()
    for line in taskfile:
        m = _artifact_input_regex_ex.search(line)
        if m:
            name = m.group(1)
            repo = m.group(2)
            artifacts[name] = repo
            continue
        m = _artifact_input_regex.search(line)
        if m:
            name = m.group(1)
            artifacts[name] = name
            continue
        m = _artifact_optional_param_regex.search(line)
        if m:
            name = m.group(1)
            optional = True
            parameter = (name, optional)
            parameters.add(parameter)
            continue
        m = _artifact_param_regex.search(line)
        if m:
            name = m.group(1)
            optional = False
            parameter = (name, optional)
            parameters.add(parameter)
            continue

    if 'config' in artifacts:
        sys.stderr.write("%s: Artifact name 'config' is reserved\n" % taskfile)
        sys.exit(1)

    return (artifacts, list(parameters))


def _get_configfilename(taskfilename):
    configname = taskfilename
    if configname.endswith('.sh'):
        configname = configname[:-3]
    configname += '.json'
    return configname


def _find_repo_config(taskdir, reponame, extra_searchpath=[]):
    repo_searchpath = extra_searchpath + ['repos']

    for path in repo_searchpath:
        full_path = os.path.join(taskdir, path, reponame+'.json')
        if os.path.exists(full_path):
            return full_path
    sys.stderr.write("There is no configuration for repository '%s'\n" %
                     reponame)
    sys.stderr.write("Note: Searchpath: %s\n" % ", ".join(repo_searchpath))
    sys.exit(1)


def _read_repo_config(taskdir, reponame, extra_searchpath):
    configfile = _find_repo_config(taskdir, reponame, extra_searchpath)
    with open(configfile) as file:
        try:
            repoconfig = json.load(file)
        except ValueError as e:
            sys.stderr.write("%s: error: %s\n" % (configfile, e))
            sys.exit(1)

    copyfrom = repoconfig.get('copyfrom')
    if copyfrom is not None:
        merged_config = repoconfig
        del merged_config['copyfrom']
        copyfrom_config = _read_repo_config(taskdir, copyfrom, extra_searchpath)
        for key, val in copyfrom_config.items():
            merged_config[key] = val
        repoconfig = merged_config

    # Check repoconfig for errors.
    type = repoconfig.get('type')
    if type is None:
        sys.stderr.write("No type specified in repo config '%s'\n" %
                         configfile)
        sys.exit(1)
    repohandler = repos.modules.get(type)
    if repohandler is None:
        sys.stderr.write("Unknown type '%s' in repo config '%s'\n" %
                         (type, configfile))
        sys.exit(1)
    try:
        repohandler.verify(repoconfig)
    except Exception as e:
        sys.stderr.write("Invalid repo config '%s': %s\n" %
                         (configfile, e))
        sys.exit(1)
    return repoconfig


def _make_task_argparser(command_name, debughelper_mode=False,
                         hostname_arg=False):
    p = argparse.ArgumentParser(prog=('task %s' % command_name))
    p.set_defaults(name=None)
    p.set_defaults(local=False)
    p.set_defaults(existing=False)
    p.set_defaults(rewrite_local=False)
    if hostname_arg:
        p.add_argument('hostname')
    p.add_argument('task')
    p.add_argument('-a', '--artifact', action='append', default=[],
                   dest='artifacts')
    p.add_argument('-r', '--ref', action='append', default=[], dest='refs')
    p.add_argument('-D', '--define', action='append', default=[], dest='defs')
    p.add_argument('-v', '--verbose', action='store_true', default=False)
    if debughelper_mode:
        p.add_argument('-l', '--local', action='store_true')
        p.add_argument('-e', '--existing', action='store_true')
        p.add_argument('-L', '--rewrite-local', action='store_true')
    else:
        p.add_argument('-n', '--name')
    return p


def _rewrite_local_git_urls(buildconfig):
    '''
    Prefix all git repository urls in buildconfig that start with a slash
    (they reference local files) with a prefix of the local machine/user.
    '''
    hostname = utils.check_output(['hostname', '-f'], encoding='utf8').strip()
    user = utils.check_output(['whoami'], encoding='utf8').strip()
    for name, config in buildconfig.items():
        if not isinstance(config, dict):
            continue
        url = config.get('url')
        if url is not None and url.startswith('/'):
            config['url'] = '%s@%s:%s' % (user, hostname, url)


class BuildConfig(object):
    def __init__(self, taskfilename, taskname, config):
        self.taskfilename = taskfilename
        self.taskname = taskname
        self.config = config


def _make_buildconfig(argconfig):
    if argconfig.verbose:
        utils.verbose = True
    taskfilename = os.path.abspath(argconfig.task)
    taskname = argconfig.name
    if taskname is None:
        taskname = os.path.basename(taskfilename).partition('.')[0]

    try:
        with open(taskfilename) as taskfile:
            artifact_parameters, parameters = _determine_task_inputs(taskfile)
    except IOError as e:
        sys.stderr.write("%s\n" % (e,))
        sys.exit(1)

    # Resolve arguments
    buildconfig = dict()
    mandatory_parameters = set()
    optional_parameters = set()
    for parameter, optional in parameters:
        if optional:
            optional_parameters.add(parameter)
        else:
            mandatory_parameters.add(parameter)
    for d in argconfig.defs:
        name, eq, val = d.partition('=')
        if eq != '=':
            sys.stderr.write("Expected 'key=value' for -D argument\n")
            sys.exit(1)
        if name not in mandatory_parameters and \
           name not in optional_parameters:
            sys.stderr.write("Warning: task does not have parameter '%s'\n" %
                             name)
        buildconfig[name] = val
        mandatory_parameters.discard(name)
    if len(mandatory_parameters) > 0:
        for param in mandatory_parameters:
            sys.stderr.write("Error: No value for mandatory parameter '%s'\n" %
                             param)
        sys.stderr.write("Note: Use the `-D parameter=value` option\n")
        sys.exit(1)

    # Resolve artifact inputs
    extra_searchpath = ["repos.try"] if argconfig.local else []
    taskdir = os.path.dirname(taskfilename)
    repo_overrides = {}
    for i in argconfig.artifacts:
        name, eq, val = i.partition('=')
        if eq != '=':
            sys.stderr.write("Expected 'name=url' for -i argument\n")
            sys.exit(1)
        if name not in artifact_parameters:
            sys.stderr.write("Warning: task does not have input '%s'\n" % name)
            artifact_parameters[name] = name
        if '://' in val:
            repo_overrides[name] = {'type': 'url', 'url': val}
        else:
            # If it's not an https URL, assume it's an S3 path within the bucket
            repo_overrides[name] = {'type': 'artifact_server', 'url': val}
    for i in argconfig.refs:
        name, eq, val = i.partition('=')
        if eq != '=':
            sys.stderr.write("Expected 'repo=ref' for -r argument\n")
            sys.exit(1)
        if name not in artifact_parameters:
            sys.stderr.write("Warning: task does not have input '%s'\n" % name)
            continue
        reponame = artifact_parameters[name]
        repoconfig = _read_repo_config(taskdir, reponame, extra_searchpath)
        type = repoconfig['type']
        if type == 'git':
            repoconfig['rev'] = val
        else:
            sys.stderr.write("Cannot override revision of repo '%s'\n" % name)
        repo_overrides[name] = repoconfig

    for name, reponame in artifact_parameters.items():
        repoconfig = repo_overrides.get(name)
        if repoconfig is None:
            if argconfig.existing:
                buildconfig[name] = {'type': 'existing'}
                continue
            repoconfig = _read_repo_config(taskdir, reponame, extra_searchpath)
        type = repoconfig['type']
        repohandler = repos.modules.get(type)
        try:
            repohandler.resolve_latest(repoconfig)
        except Exception as e:
            sys.stderr.write("While resolving %s:\n" % reponame)
            sys.stderr.write("%s\n" % e)
            sys.exit(1)
        buildconfig[name] = repoconfig

    if argconfig.rewrite_local:
        _rewrite_local_git_urls(buildconfig)

    return BuildConfig(taskfilename, taskname, buildconfig)


def _extract_buildid(build):
    '''
    Extract buildid from buildscript. By convention the first line of a
    complete buildscript has to start with `buildid='`
    '''
    firstline = build.splitlines()[0]
    if not firstline.startswith("buildid='") or not firstline.endswith("'"):
        sys.stderr.write(
                "error: build malformed (must start with buildid='...')\n")
        sys.exit(1)
    return firstline[9:-1]


def _make_buildscript(hook, buildconfig, keep_buildconfig=False):
    if not keep_buildconfig:
        buildconfig_file = tempfile.NamedTemporaryFile(prefix='buildconfig_',
                                                       delete=False)
        buildconfig_filename = buildconfig_file.name
    else:
        buildconfig_filename = 'buildconfig.json'
        buildconfig_file = open(buildconfig_filename, 'w')

    with buildconfig_file:
        buildconfig_file.write(json.dumps(buildconfig.config, indent=2))
        buildconfig_file.write('\n')
        buildconfig_file.close()
        build = utils.check_output([hook, _userdir, buildconfig.taskfilename,
                                    buildconfig_filename,
                                    buildconfig.taskname], cwd=_hooksdir, encoding='utf8')
        if not keep_buildconfig:
            os.unlink(buildconfig_filename)

    # Extract buildid and create buildname
    buildid = _extract_buildid(build)
    buildname = buildconfig.taskname + "_" + buildid

    return build, buildname


def _mk_submit_results(buildname):
    return utils.check_output(['./mk-submit-results', _userdir, buildname],
                              cwd=_hooksdir, encoding='utf8')


def _command_try(args):
    '''Execute task locally.'''
    p = _make_task_argparser('try')
    argconfig = p.parse_args(args)
    argconfig.local = True
    buildconfig = _make_buildconfig(argconfig)
    build, buildname = _make_buildscript('./mk-try-build', buildconfig)

    with tempfile.NamedTemporaryFile(delete=False) as tempf:
        tempf.write(build)
        tempf.close()
        utils.check_call(['./exec-try-build', _userdir, tempf.name, buildname],
                         cwd=_hooksdir, encoding='utf8')
        os.unlink(tempf.name)


def _command_submit(args):
    '''Submit task to jenkins OneOff job.'''
    p = _make_task_argparser('submit')
    argconfig = p.parse_args(args)
    buildconfig = _make_buildconfig(argconfig)
    build, buildname = _make_buildscript('./mk-submit-build', buildconfig)

    build += _mk_submit_results(buildname)

    with tempfile.NamedTemporaryFile(delete=False) as tempf:
        tempf.write(build)
        tempf.close()
        utils.check_call(['./submit', _userdir, tempf.name, buildname],
                         cwd=_hooksdir, encoding='utf8')
        os.unlink(tempf.name)


def _command_jenkinsrun(args):
    '''Run task as part of a jenkins job.'''
    p = _make_task_argparser('jenkinsrun')
    p.add_argument('-s', '--submit', action='store_true', default=False,
                   help='Submit results to artifact storage at end of task')
    argconfig = p.parse_args(args)
    argconfig.existing = True
    buildconfig = _make_buildconfig(argconfig)
    build, buildname = _make_buildscript('./mk-jenkinsrun-build', buildconfig,
                                         keep_buildconfig=True)

    if argconfig.submit:
        build += _mk_submit_results(buildname)

    with open("run.sh", "w") as runfile:
        runfile.write(build)

    retcode = utils.call(['/bin/sh', 'run.sh'])
    if retcode != 0:
        sys.stdout.write("*Build failed!* (return code %s)\n" % retcode)
        sys.stdout.flush()
        taskdir = os.path.dirname(buildconfig.taskfilename)
        repro_script = os.path.join(taskdir, 'repro_message.sh')
        if os.access(repro_script, os.X_OK):
            utils.check_call([repro_script, _userdir,
                              buildconfig.taskfilename], encoding='utf8')
    sys.exit(retcode)


def _command_sshrun(args):
    '''Run task by logging into a remote machine with ssh.'''
    p = _make_task_argparser('sshrun', hostname_arg=True)
    argconfig = p.parse_args(args)
    argconfig.local = True
    argconfig.rewrite_local = True
    buildconfig = _make_buildconfig(argconfig)
    build, buildname = _make_buildscript('./mk-sshrun-build', buildconfig)

    run_file = tempfile.NamedTemporaryFile(prefix=buildname, delete=False)
    with run_file:
        run_file.write(build)
        run_file.close()
        try:
            utils.check_call(['./sshrun', argconfig.hostname, run_file.name],
                             cwd=_hooksdir, encoding='utf8')
        finally:
            os.unlink(run_file.name)


def _command_resolve(args):
    '''Print artifact resolution results. (debug helper)'''
    p = _make_task_argparser('resolve', debughelper_mode=True)
    argconfig = p.parse_args(args)
    buildconfig = _make_buildconfig(argconfig)

    for name, config in sorted(buildconfig.config.items()):
        if isinstance(config, dict):
            url = config.get('url', '')
            line = "%-15s\t%-30s" % (name, url)
            rev = config.get('rev')
            if rev is not None:
                line += " " + rev
            sys.stdout.write("%s\n" % line)
        else:
            sys.stdout.write("%-15s\t%s\n" % (name, config))


def _command_buildconfig(args):
    '''Produce buildconfig. (debug helper)'''
    p = _make_task_argparser('buildconfig', debughelper_mode=True)
    argconfig = p.parse_args(args)
    buildconfig = _make_buildconfig(argconfig)

    json.dump(buildconfig.config, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')


def main():
    argv = sys.argv
    # Allow overriding _hooksdir for testing.
    if len(argv) > 1 and argv[1].startswith("--hooks-dir="):
        global _hooksdir
        _hooksdir = argv[1].split('=', 1)[1]
        del argv[1]

    commands = {
        'buildconfig': _command_buildconfig,
        'jenkinsrun': _command_jenkinsrun,
        'resolve': _command_resolve,
        'sshrun': _command_sshrun,
        'submit': _command_submit,
        'try': _command_try,
    }
    utils.run_subcommand(commands, argv, docstring=__doc__)


if __name__ == '__main__':
    main()
