"""
Builders for using LNT to test LLVM/Clang.
"""

import os

import buildbot
from buildbot.steps.source.svn import SVN
from buildbot.process.properties import WithProperties

import zorg
from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.util.phasedbuilderutils import getBuildDir, setProperty
from zorg.buildbot.util.artifacts import GetCompilerRoot, package_url

def _get_cc(status, stdin, stdout):
    lines = filter(bool, stdin.split('\n'))
    for line in lines:
        if 'bin/clang' in line:
            cc_path = line
            return { 'cc_path' : cc_path }
    return {}

def _get_cxx(status, stdin, stdout):
    lines = filter(bool, stdin.split('\n'))
    for line in lines:
        if 'bin/clang++' in line:
            cxx_path = line
            return { 'cxx_path' : cxx_path }
    return {}

def _get_liblto(status, stdin, stdout):
    lines = filter(bool, stdin.split('\n'))
    for line in lines:
        if 'lib/libLTO.dylib' in line:
            lto_path = line
            return { 'lto_path' : lto_path }
    return {}

def getLNTFactory(triple, nt_flags, xfails=[], clean=True, test=False,
                  reportBuildslave = True, **kwargs):
    lnt_args = {}
    lnt_arg_names = ['submitURL', 'package_cache', 'testerName',
                     'reportBuildslave']

    for argname in lnt_arg_names:
        if argname in kwargs:
            lnt_args[argname] = kwargs.pop(argname)

    # Build compiler to test.  
    f = ClangBuilder.getClangBuildFactory(
        triple, outOfDir=True, clean=clean, test=test,
        stage1_config='Release+Asserts', **kwargs)

    # Add an LNT test runner.
    AddLNTTestsToFactory(f, nt_flags,
                         cc_path="llvm.install.1/bin/clang",
                         cxx_path="llvm.install.1/bin/clang++",
                         **lnt_args);

    return f

def AddLNTTestsToFactory(f, nt_flags, cc_path, cxx_path, **kwargs):
    """
    Add the buildbot steps necessary to run an LNT driven test of a compiler.

    This assumes at a minimum that the factory has already been set up to
    contain a builddir property which points at the full path to the build
    directory.
    """

    parallel = kwargs.pop('parallel', False)
    jobs = kwargs.pop('jobs', '$(jobs)s')
    submitURL = kwargs.pop('submitURL', None)
    package_cache = kwargs.pop('package_cache', 'http://lab.llvm.org/packages')
    testerName = kwargs.pop('testerName', None)
    reportBuildslave = kwargs.pop('reportBuildslave', True)
    env = kwargs.pop('env', {})

    # Create variables to refer to the compiler-under-test.
    #
    # We assume any relative paths are relative to the build directory (which
    # prior steps will have presumably populated with a compiler).
    cc_path = WithProperties(os.path.join('%(builddir)s', cc_path))
    cxx_path = WithProperties(os.path.join('%(builddir)s', cxx_path))

    # Add --liblto-path if necessary. We assume it will be in a lib directory
    # adjacent to cc_path.
    #
    # FIXME: This is currently only going to work on Darwin.
    if '-flto' in nt_flags:
        base_directory = os.path.dirname(os.path.dirname(cc_path))
        nt_flags.extend(['--liblto-path', WithProperties(
                         os.path.join('%(builddir)s', base_directory, 'lib',
                                      'libLTO.dylib'))])

    # Get the LNT sources.
    f.addStep(SVN(name='pull.lnt', mode='incremental', method='fresh',
                  baseURL='http://llvm.org/svn/llvm-project/lnt/',
                  defaultBranch='trunk', workdir='lnt', alwaysUseLatest=True))

    # Get the LLVM test-suite sources.
    f.addStep(SVN(name='pull.test-suite', mode='incremental', method='fresh',
                  baseURL='http://llvm.org/svn/llvm-project/test-suite/',
                  defaultBranch='trunk', workdir='test-suite',
                  alwaysUseLatest=False))

    # Create the LNT virtual env.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.clean', command=['rm', '-rf', 'lnt.venv'],
            haltOnFailure=True, description=['clean', 'LNT', 'venv'],
            workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.create', command=['virtualenv', 'lnt.venv'],
            haltOnFailure=True, description=['create', 'LNT', 'venv'],
            workdir=WithProperties('%(builddir)s'), 
            env={'PATH' : '${PATH}:/usr/local/bin'}))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.install', haltOnFailure=True,
            command=[WithProperties('%(builddir)s/lnt.venv/bin/pip'), 'install',
                     '--no-index',
                     '--find-links', package_cache,
                     '-e', '.'],
            description=['install', 'LNT'], workdir='lnt',
            env={'ARCHFLAGS' : '-arch i386 -arch x86_64'}))

    # Clean up the sandbox dir.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='lnt.nightly-test.clean', command=['rm', '-rf', 'nt'],
            haltOnFailure=True, description=['clean', 'LNT', 'sandbox'],
            workdir='tests'))

    if reportBuildslave:
        reportName = '%(slavename)s'

        if testerName:
            reportName += '__' + testerName
        reportName = WithProperties(reportName)
    else:
        reportName = testerName

    # Run the nightly test.
    args = [WithProperties('%(builddir)s/lnt.venv/bin/python'),
            WithProperties('%(builddir)s/lnt.venv/bin/lnt'),
            'runtest', '--verbose']

    # Only submit if a URL has been specified
    if submitURL is not None:
      args.extend(['--submit', submitURL])

    args.extend(['--commit=1',
             'nt', '--sandbox', 'nt',
             '--no-timestamp',
             '--cc', cc_path, '--cxx', cxx_path,
             '--without-llvm',
             '--test-suite', WithProperties('%(builddir)s/test-suite'), 
             '--no-machdep-info', reportName])
    if parallel:
        args.extend(['-j', WithProperties(jobs)])
    args.extend(nt_flags)
    f.addStep(zorg.buildbot.commands.LitTestCommand.LitTestCommand(
            name='lnt.nightly-test', command=args, haltOnFailure=True,
            description=['nightly test'], workdir='tests',
            logfiles={'configure.log' : 'nt/build/configure.log',
                      'build-tools.log' : 'nt/build/build-tools.log',
                      'test.log' : 'nt/build/test.log',
                      'report.json' : 'nt/build/report.json'},
            env=env))
    return f

def CreateLNTNightlyFactory(nt_flags, cc_path=None, cxx_path=None,
                            parallel = False, jobs = '%(jobs)s',
                            db_url=None, external_URL=None):
    # Paramaters used by this method:
    # nt_flags  : a list of flags passed to the lnt process
    # cc_path   : explicit path to c compiler
    # cxx_path  : explicit path to c++ compiler
    # parallel  : set to True if using multiple cores for faster turnaround
    #             set to False if measuring performance
    # db_url    : set to the submission URL for an LNT database when measuring 
    #             performance
    # external_URL : Used to pull additional tests from a separate svn 
    #                repository
    # Properties set externally but used by this method:
    # builddir  : This property is set below
    # jobs      : This property is set by the slave, it indicates the number of
    #             cores availble to use.
    # revision  : This property should be set by an upstream builder.
    # slavename : This property is set by the slave
    # buildername : This property is set by the master

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f = getBuildDir(f)
    f = GetCompilerRoot(f)
    if cc_path:
       cc_command = ['echo', cc_path]
    else:
       cc_command = ['find', 'host-compiler', '-name', 'clang']
    f.addStep(buildbot.steps.shell.SetProperty(
              name='find.cc',
              command=cc_command,
              extract_fn=_get_cc,
              workdir=WithProperties('%(builddir)s')))
    if cxx_path:
       cc_command = ['echo', cxx_path]
    else:
       cc_command = ['find', 'host-compiler', '-name', 'clang++']
    f.addStep(buildbot.steps.shell.SetProperty(
              name='find.cxx',
              command=cc_command,
              extract_fn=_get_cxx,
              workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='sanity.test', haltOnFailure=True,
            command=[WithProperties('%(builddir)s/%(cc_path)s'), '-v'],
            description=['sanity test']))
    args = [WithProperties('%(builddir)s/lnt.venv/bin/python'),
            WithProperties('%(builddir)s/lnt.venv/bin/lnt'),
            'runtest', '--verbose']
    if db_url:
        f.addStep(buildbot.steps.shell.SetProperty(
                  name='db_url',
                  command=['echo', db_url, ':', WithProperties('%(buildername)s')],
                  extract_fn=_get_db_url,
                  workdir=WithProperties('%(builddir)s')))
        args.extend(['--submit', WithProperties('%(db_url)s')])
    # Add --liblto-path if necessary.
    if '-flto' in nt_flags:
        f.addStep(buildbot.steps.shell.SetProperty(
                  name='find.liblto',
                  command=['find', 'host-compiler', '-name', 'libLTO.dylib'],
                  extract_fn=_get_liblto,
                  workdir=WithProperties('%(builddir)s')))
        nt_flags.extend(['--liblto-path', WithProperties('%(builddir)s/%(lto_path)s')])
    # Get the LNT sources.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name = 'svn.clean.lnt',
            command = ['svn', 'cleanup'],
            haltOnFailure=False, flunkOnFailure=False,
            description = ['svn clean lnt'],
            workdir='lnt'))
    f.addStep(SVN(name='pull.lnt', mode='full', method='fresh',
                  repourl='http://llvm.org/svn/llvm-project/lnt/trunk',
                  haltOnFailure=False, flunkOnFailure=False,
                  workdir='lnt', alwaysUseLatest=True, retry = (60, 5),
                  description='pull.lnt'))
    # Get the LLVM test-suite sources.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name = 'svn.clean.tests',
            command = ['svn', 'cleanup'],
            haltOnFailure=False, flunkOnFailure=False,
            description = ['svn clean test-suite'],
            workdir='test-suite'))
    f.addStep(SVN(name='pull.test-suite', mode='full', method='fresh',
                  repourl='http://llvm.org/svn/llvm-project/test-suite/trunk',
                  haltOnFailure=False, flunkOnFailure=False,
                  workdir='test-suite', retry = (60, 5),
                  description='pull.test-suite'))
    if external_URL:
        external_dir = WithProperties('%(builddir)s/test-suite-externals')
        f.addStep(buildbot.steps.shell.ShellCommand(
                name = 'svn.clean.externals',
                command = ['svn', 'cleanup'],
                haltOnFailure=False, flunkOnFailure=False,
                description = ['svn clean externals'],
                workdir='test-suite-externals'))
        f.addStep(SVN(name='pull.test-suite-externals', mode='full',
                      repourl=external_URL, retry = (60, 5), method='fresh',
                      workdir='test-suite-externals', alwaysUseLatest=True,
                      haltOnFailure=False, flunkOnFailure=False,
                      description='pull.test-suite-externals',
                      timeout=300))
        # Buildbot uses got_revision instead of revision to identify builds.
        # The previous step will set it incorrectly
        # We set it to the correct value in th following step
        setProperty(f, 'got_revision', WithProperties('%(revision)s'))
    # Create the LNT virtual env.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.clean', command=['rm', '-rfv', 'lnt.venv'],
            haltOnFailure=True, description=['clean', 'LNT', 'venv'],
            workdir=WithProperties('%(builddir)s')))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.create', command=['virtualenv', 'lnt.venv'],
            haltOnFailure=True, description=['create', 'LNT', 'venv'],
            workdir=WithProperties('%(builddir)s'),
            env={'PATH' : '${PATH}:/usr/local/bin'}))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.install', haltOnFailure=True,
            command=[WithProperties('%(builddir)s/lnt.venv/bin/pip'), 'install',
                     '--index-url', package_url,
                     '-e', '.'],
            description=['install', 'LNT'], workdir='lnt'))
    # Clean up the sandbox dir.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='lnt.nightly-test.clean', command=['rm', '-rfv', 'nt'],
            haltOnFailure=True, description=['clean', 'LNT', 'sandbox'],
            workdir='tests'))
    # Run the nightly test.
    nick = '%(slavename)s-%(buildername)s'
    args.extend(['nt', '--sandbox', 'nt', '--cc',
            WithProperties('%(builddir)s/%(cc_path)s'), '--cxx',
            WithProperties('%(builddir)s/%(cxx_path)s'), '--without-llvm',
            '--test-suite', WithProperties('%(builddir)s/test-suite'),
            '--no-timestamp', '--no-machdep-info', '--no-auto-name',
            '--no-configure'])
    if external_URL:
        args.extend(['--test-externals', external_dir])
    if parallel:
        args.extend(['-j', WithProperties(jobs)])
    args.extend(nt_flags)
    f.addStep(zorg.buildbot.commands.LitTestCommand.LitTestCommand(
            name='lnt.nightly-test', command=args, haltOnFailure=True,
            description=['nightly test'], workdir='tests',
            logfiles={'configure.log' : 'nt/build/configure.log',
                      'build-tools.log' : 'nt/build/build-tools.log',
                      'test.log' : 'nt/build/test.log',
                      'report.json' : 'nt/build/report.json'}))

    return f
