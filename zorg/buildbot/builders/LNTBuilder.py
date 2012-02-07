"""
Builders for using LNT to test LLVM/Clang.
"""

# The URL of our local package cache.
g_package_url = "http://lab.llvm.org/packages"

def getLNTFactory(triple, nt_flags, xfails=[], clean=True, test=False,
                  **kwargs):
    # Build compiler to test.  
    f = ClangBuilder.getClangBuildFactory(
        triple, outOfDir=True, clean=clean, test=test,
        always_install=True, **kwargs)

    # Add an LNT test runner.
    AddLNTTestsToFactory(f, nt_flags,
                         cc_path="llvm.install/bin/clang",
                         cxx_path="llvm.install/bin/clang++")

    return f

def AddLNTTestsToFactory(f, nt_flags, cc_path, cxx_path,
                         parallel = False, jobs = '%(jobs)s'):
    """
    Add the buildbot steps necessary to run an LNT driven test of a compiler.

    This assumes at a minimum that the factory has already been set up to
    contain a builddir proeprty which points at the full path to the build
    directory.
    """

    # Create variables to refer to the compiler-under-test.
    #
    # We assume any relative paths are relative to the build directory (which
    # prior steps will have presumably populated with a compiler).
    cc_path = WithProperties(os.path.join('%(builddir)s', cc_path))
    cxx_path = WithProperties(os.path.join'%(builddir)s', cxx_path))

    # Add --liblto-path if necessary. We assume it will be in a lib directory
    # adjacent to cc_path.
    #
    # FIXME: This is currently only going to work on Darwin.
    if '-flto' in nt_flags:
        base_directory = os.path.dirname(os.path.dirname(cc_path))
        lnt_flags.extend(['--liblto-path', WithProperties(
                os.path.join('%(builddir)s',
                             os.path.join(base_directory, 'lib',
                                          'libLTO.dylib'))

    # Get the Zorg sources, for LNT.
    f.addStep(SVN(name='pull.zorg', mode='incremental', method='fresh',
                  baseURL='http://llvm.org/svn/llvm-project/zorg/',
                  defaultBranch='trunk', workdir='zorg', alwaysUseLatest=True))

    # Get the LLVM test-suite sources.
    f.addStep(SVN(name='pull.test-suite', mode='incremental', method='fresh',
                  baseURL='http://llvm.org/svn/llvm-project/test-suite/',
                  defaultBranch='trunk', workdir='test-suite',
                  alwaysUseLatest=False))

    # Create the LNT virtual env.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.clean', command=['rm', '-rf', 'lnt.venv'],
            haltOnFailure=True, description=['clean', 'LNT', 'venv'],
            workdir='%(builddir)s'))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.create', command=['virtualenv', 'lnt.venv'],
            haltOnFailure=True, description=['create', 'LNT', 'venv'],
            workdir=WithProperties('%(builddir)s'), 
            env={'PATH' : '${PATH}:/usr/local/bin'}))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lnt.install', haltOnFailure=True,
            command=[WithProperties('%(builddir)s/lnt.venv/bin/pip'), 'install',
                     '--no-index',
                     '--find-links', g_package_url,
                     '-e', '.'],
            description=['install', 'LNT'], workdir='zorg/lnt',
            env={'ARCHFLAGS' : '-arch i386 -arch x86_64'}))

    # Clean up the sandbox dir.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='lnt.nightly-test.clean', command=['rm', '-rf', 'nt'],
            haltOnFailure=True, description=['clean', 'LNT', 'sandbox'],
            workdir='tests'))

    # Run the nightly test.
    args = [WithProperties('%(builddir)s/lnt.venv/bin/python'),
            WithProperties('%(builddir)s/lnt.venv/bin/lnt'),
            'runtest', '--verbose',
            '--submit', 'http://llvm.org/perf/submitRun',
            'nt', '--sandbox', 'nt',
            '--cc', cc_path, '--cxx', cxx_path,
            '--without-llvm',
            '--test-suite', WithProperties('%(builddir)s/test-suite'), 
            '--no-machdep-info', WithProperties('%(slavename)s')]
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
