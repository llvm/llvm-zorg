import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, SetProperty
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.steps.slave import RemoveDirectory
from buildbot.process.properties import WithProperties, Property
import zorg.buildbot.commands.BatchFileDownload as batch_file_download
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.builders.Util import getVisualStudioEnvironment
from zorg.buildbot.builders.Util import extractSlaveEnvironment
import json

# We *must* checkout at least Clang, LLVM, and LLDB.  Once we add a step to run
# tests (e.g. ninja check-lldb), we will also need to add a step for LLD, since
# MSVC LD.EXE cannot link executables with DWARF debug info.
def getLLDBSource(f,llvmTopDir='llvm'):
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvmTopDir))
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='%s/tools/clang' % llvmTopDir))
    f.addStep(SVN(name='svn-lldb',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/lldb/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lldb' % llvmTopDir))
    return f

# Clean SVN source tree
# SVN doesn't provide build-in commands to remove all untracked files
# List all untracked files, and remove one by one
def cleanSVNSourceTree(f, srcdir='llvm'):
    f.addStep(ShellCommand(name='clean svn source %s' % srcdir,
                           command="svn status --no-ignore | grep '^[I?]' | cut -c 9- | while IFS= read -r f; do echo \"$f\"; rm -rf \"$f\"; done",
                           description="clean SVN source tree",
                           workdir='%s' % srcdir))
    return f

# CMake Windows builds
def getLLDBWindowsCMakeBuildFactory(
            clean=False,
            cmake='cmake',
            jobs="%(jobs)s",

            # Source directory containing a built python
            python_source_dir=r'C:/src/python',

            # Default values for VS devenv and build configuration
            vs=r"""%VS120COMNTOOLS%""",
            config='Release',
            target_arch='x86',

            extra_cmake_args=[],
            test=False,
            install=False):

    ############# PREPARING
    f = buildbot.process.factory.BuildFactory()

    # Determine Slave Environment and Set MSVC environment.
    f.addStep(SetProperty(
        command=getVisualStudioEnvironment(vs, target_arch),
        extract_fn=extractSlaveEnvironment))

    f = getLLDBSource(f,'llvm')

    build_cmd=['ninja']
    install_cmd = ['ninja','install']
    test_cmd = ['ninja','check-lldb']

    if jobs:
        build_cmd.append(WithProperties("-j%s" % jobs))
        install_cmd.append(WithProperties("-j%s" % jobs))
        test_cmd.append(WithProperties("-j%s" % jobs))

    # Global configurations
    build_dir='build'

    ############# CLEANING
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean '+build_dir,
                dir=build_dir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    if config.lower() == 'release':
        python_lib = 'python27.lib'
        python_exe = 'python.exe'
    elif config.lower() == 'debug':
        python_lib = 'python27_d.lib'
        python_exe = 'python_d.exe'

    python_lib = os.path.join(python_source_dir, 'PCbuild', python_lib)
    python_exe = os.path.join(python_source_dir, 'PCbuild', python_exe)
    python_include = os.path.join(python_source_dir, 'Include')

    # Use batch files instead of ShellCommand directly, Windows quoting is
    # borked. FIXME: See buildbot ticket #595 and buildbot ticket #377.
    f.addStep(batch_file_download.BatchFileDownload(name='cmakegen',
                                command=[cmake, "-G", "Ninja", "../llvm",
                                         "-DCMAKE_BUILD_TYPE="+config,
                                         # Need to use our custom built version of python
                                         '-DPYTHON_LIBRARY=' + python_lib,
                                         '-DPYTHON_INCLUDE_DIR=' + python_include,
                                         '-DPYTHON_EXECUTABLE=' + python_exe,
                                         "-DCMAKE_INSTALL_PREFIX=../install"]
                                         + extra_cmake_args,
                                workdir=build_dir))

    f.addStep(ShellCommand(name='cmake',
                           command=['cmakegen.bat'],
                           haltOnFailure=True,
                           description='cmake gen',
                           workdir=build_dir,
                           env=Property('slave_env')))

    f.addStep(WarningCountingShellCommand(name='build',
                          command=build_cmd,
                          haltOnFailure=True,
                          description='ninja build',
                          workdir=build_dir,
                          env=Property('slave_env')))

    ignoreInstallFail = bool(install != 'ignoreFail')
    f.addStep(ShellCommand(name='install',
                          command=install_cmd,
                          flunkOnFailure=ignoreInstallFail,
                          description='ninja install',
                          workdir=build_dir,
                          doStepIf=bool(install),
                          env=Property('slave_env')))

    ignoreTestFail = bool(test != 'ignoreFail')
    f.addStep(ShellCommand(name='test',
                          command=test_cmd,
                          flunkOnFailure=ignoreTestFail,
                          description='ninja test',
                          workdir=build_dir,
                          doStepIf=bool(test),
                          env=Property('slave_env')))

    return f

def getLLDBBuildFactory(
            triple,
            useTwoStage=False,
            make='make',
            jobs='%(jobs)s',
            extra_configure_args=[],
            env={},
            *args,
            **kwargs):

    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(SetProperty(name="get_builddir",
              command=["pwd"],
              property="builddir",
              description="set build dir",
              workdir="."))

    # Find out what version of llvm and clang are needed to build this version
    # of lldb. Right now we will assume they use the same version.
    # XXX - could this be done directly on the master instead of the slave?
    f.addStep(SetProperty(command='svn cat http://llvm.org/svn/llvm-project/lldb/trunk/scripts/build-llvm.pl | grep ^our.*llvm_revision | cut -d \\" -f 2',
                          property='llvmrev'))

    # The SVN build step provides no mechanism to check out a specific revision
    # based on a property, so just run the commands directly here.

    svn_co = ['svn', 'checkout', '--force']
    svn_co += ['--revision', WithProperties('%(llvmrev)s')]

    # build llvm svn checkout command
    svn_co_llvm = svn_co + \
     [WithProperties('http://llvm.org/svn/llvm-project/llvm/trunk@%(llvmrev)s'),
                     llvm_srcdir]
    # build clang svn checkout command
    svn_co_clang = svn_co + \
     [WithProperties('http://llvm.org/svn/llvm-project/cfe/trunk@%(llvmrev)s'),
                     '%s/tools/clang' % llvm_srcdir]

    f.addStep(ShellCommand(name='svn-llvm',
                           command=svn_co_llvm,
                           haltOnFailure=True,
                           workdir='.'))
    f.addStep(ShellCommand(name='svn-clang',
                           command=svn_co_clang,
                           haltOnFailure=True,
                           workdir='.'))

    f.addStep(SVN(name='svn-lldb',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/lldb/',
                  defaultBranch='trunk',
                  always_purge=True,
                  workdir='%s/tools/lldb' % llvm_srcdir))

    # Run configure
    config_args = [WithProperties("%%(builddir)s/%s/configure" % llvm_srcdir),
                   "--disable-bindings",
                   "--without-llvmgcc",
                   "--without-llvmgxx",
                  ]
    if triple:
        config_args += ['--build=%s' % triple]
    config_args += extra_configure_args

    f.addStep(Configure(name='configure',
        command=config_args,
        env=env,
        workdir=llvm_objdir))

    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          env=env,
                                          haltOnFailure=True,
                                          workdir=llvm_objdir))

    # Test.
    f.addStep(LitTestCommand(name="test lldb",
                             command=['nice', '-n', '10',
                                      make],
                             description="test lldb",
                             env=env,
                             workdir='%s/tools/lldb/test' % llvm_objdir))

    return f
# Add test steps from list of compilers and archs
def getLLDBTestSteps(f,
                     isRemoteTest,
                     bindir,
                     test_archs,
                     test_compilers,
                     remote_host=None,
                     remote_port=None,
                     remote_dir=None,
                     env=None):
    # Skip test steps if no test compiler or arch is specified
    if None in (test_archs, test_compilers):
        return f
    llvm_srcdir = "llvm"
    llvm_builddir = "build"
    for compiler in test_compilers:
        # find full path for top of tree clang
        if compiler=='totclang':
            compilerPath=bindir+'/clang'
        else:
            compilerPath = compiler
        for arch in test_archs:
            DOTEST_OPTS=''.join(['--executable ' + bindir + '/lldb ',
                                 '-A %s ' % arch,
                                 '-C %s ' % compilerPath,
                                 '-s lldb-test-traces-%s-%s ' % (compiler, arch),
                                 '-u CXXFLAGS ',
                                 '-u CFLAGS'])
            testname = "local"
            if(isRemoteTest):
                DOTEST_OPTS+=''.join([' --platform-name remote-linux ',
                                      '--platform-url connect://%(remote_host)s:%(remote_port)s ',
                                      '--platform-working-dir %(remote_dir)s'])
                testname = "remote"
            f.addStep(LitTestCommand(name="test lldb %s (%s-%s)" % (testname, compiler, arch),
                                     command=['../%s/tools/lldb/test/dosep.py' % llvm_srcdir,
                                              '--options',
                                              WithProperties(DOTEST_OPTS)],
                                     description="test lldb",
                                     parseSummaryOnly=True,
                                     workdir='%s' % llvm_builddir))
            f=cleanSVNSourceTree(f, '%s/tools/lldb' % llvm_srcdir)
    return f

# Add steps to run lldb test on remote target
def getLLDBRemoteTestSteps(f,
                           bindir,
                           remote_test_archs,
                           remote_test_compilers,
                           env):

    if None in (remote_test_archs, remote_test_compilers):
        return f
    llvm_srcdir = "llvm"
    llvm_builddir = "build"
    # get hostname
    slave_hostname=None
    f.addStep(SetProperty(name="get hostname",
                          command=["hostname"],
                          property="slave_hostname",
                          description="set slave hostname",
                          workdir="."))
    # get configuration of remote target
    # config file should be placed under builddir on builder machine
    # file name: remote_cfg.json
    # content: json format with keys "remote_host", "remote_port", and "remote_dir"
    # example: {"remote_host":"remotehostname","remote_port":"1234","remote_dir":"/path/to/dir"}
    def getRemoteCfg(rc, stdout, stderr):
       return json.loads(stdout)
    f.addStep(SetProperty(name="get remote target",
                          command="cat remote_cfg.json",
                          extract_fn=getRemoteCfg,
                          description="get remote target",
                          workdir="."))
    # rsync
    f.addStep(ShellCommand(name="rsync lldb-server",
                           command=WithProperties("rsync -hav bin/lldb-server* %(remote_host)s:%(remote_dir)s"),
                           description="rsync lldb-server",
                           haltOnFailure=True,
                           env=env,
                           workdir='%s' % llvm_builddir))
    f.addStep(ShellCommand(name="rsync python2.7",
                           command=WithProperties("rsync -havL lib/python2.7 %(remote_host)s:%(remote_dir)s"),
                           description="rsync python2.7",
                           haltOnFailure=True,
                           env=env,
                           workdir='%s' % llvm_builddir))
    # launch lldb-server
    f.addStep(ShellCommand(name="launch lldb-server",
                           command=WithProperties("ssh %(remote_host)s screen -d -m %(remote_dir)s/lldb-server platform --listen %(slave_hostname)s:%(remote_port)s --server"),
                           description="launch lldb-server on remote host",
                           env=env,
                           haltOnFailure=True,
                           workdir='%s' % llvm_builddir))
    # test steps
    f = getLLDBTestSteps(f,
                         True,
                         bindir,
                         remote_test_archs,
                         remote_test_compilers,
                         '%(remote_host)s',
                         '%(remote_port)s',
                         '%(remote_dir)s',
                         env)
    # terminate lldb-server on remote host
    f.addStep(ShellCommand(name="terminate lldb-server remote",
                           command=WithProperties("ssh %(remote_host)s pkill lldb-server"),
                           description="terminate lldb-server",
                           env=env,
                           workdir='%s' % llvm_builddir))
    return f

# Cmake bulid on Ubuntu
# Build command sequence - cmake, ninja, ./dosep
# Note: If test_archs or test_compilers is not specified, lldb-test will not be added to build factory
def getLLDBUbuntuCMakeBuildFactory(build_compiler,
                                   build_type,
                                   test_archs=None,
                                   test_compilers=None,
                                   remote_test_archs=None,
                                   remote_test_compilers=None,
                                   jobs='%(jobs)s',
                                   env=None,
                                   *args,
                                   **kwargs):

    if env is None:
        env={}

    llvm_srcdir = "llvm"
    llvm_builddir = "build"
    bindir='%(builddir)s/' + llvm_builddir + '/bin'

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(SetProperty(name="get_builddir",
                          command=["pwd"],
                          property="builddir",
                          description="set build dir",
                          workdir="."))
    # Get source code
    f = getLLDBSource(f,llvm_srcdir)

    # Construct cmake
    cmake_args = ["cmake", "-GNinja"]
    if build_compiler == "clang":
        cmake_args.append("-DCMAKE_C_COMPILER=clang")
        cmake_args.append("-DCMAKE_CXX_COMPILER=clang++")
    elif build_compiler == "gcc":
        cmake_args.append("-DCMAKE_C_COMPILER=gcc")
        cmake_args.append("-DCMAKE_CXX_COMPILER=g++")

    cmake_args.append(WithProperties("-DCMAKE_BUILD_TYPE=%s" % build_type))
    cmake_args.append(WithProperties("../%s" % llvm_srcdir))

    # Clean Build Folder
    f.addStep(ShellCommand(name="clean",
                           command="rm -rf *",
                           description="clear build folder",
                           env=env,
                           workdir='%s' % llvm_builddir))
    # Configure
    f.addStep(Configure(name='configure/cmake',
                        command=cmake_args,
                        env=env,
                        workdir=llvm_builddir))
    # Compile
    f.addStep(WarningCountingShellCommand(name="compile/ninja",
                                          command=['nice', '-n', '10',
                                                   'ninja', WithProperties("-j%s" % jobs)],
                                          env=env,
                                          haltOnFailure=True,
                                          workdir=llvm_builddir))

    # TODO: it will be good to check that architectures listed in test_archs are compatible with host architecture
    # For now, the caller of this function should make sure that each target architecture is supported by builder machine

    # Add local test steps
    f = getLLDBTestSteps(f,
                         False,
                         bindir,
                         test_archs,
                         test_compilers)
    # Remote test
    f = getLLDBRemoteTestSteps(f,
                               bindir,
                               remote_test_archs,
                               remote_test_compilers,
                               env)
    return f

def getLLDBxcodebuildFactory(use_cc=None):
    f = buildbot.process.factory.BuildFactory()
    f.addStep(SetProperty(name='get_builddir',
                          command=['pwd'],
                          property='builddir',
                          description='set build dir',
                          workdir='.'))
    lldb_srcdir = 'lldb.src'
    OBJROOT='%(builddir)s/' + lldb_srcdir + '/build'
    f.addStep(SetProperty(name='get_bindir',
                          command=['echo',
                                   WithProperties('%(builddir)s/' + lldb_srcdir + '/build/Debug')],
                          property='lldb_bindir',
                          description='set bin dir',
                          workdir='.'))
    # cleaning out the build directory is vital for codesigning.
    f.addStep(ShellCommand(name='clean.lldb-buid',
                           command=['rm', '-rf', WithProperties(OBJROOT)],
                           haltOnFailure=True,
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(ShellCommand(name='clean.llvm-buid',
                           command=['rm', '-rf', '%s/llvm-build' % lldb_srcdir ],
                           haltOnFailure=True,
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(ShellCommand(name='clean.test trace',
                           command=['rm', '-rf', '%s/DerivedData/lldb-test-results' % lldb_srcdir ],
                           haltOnFailure=True,
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(SVN(name='svn-lldb',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/lldb/',
                  defaultBranch='trunk',
                  workdir=lldb_srcdir))
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir='%s/llvm' % lldb_srcdir))
    f.addStep(SVN(name='svn-clang',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='%s/llvm/tools/clang' % lldb_srcdir))
# setup keychain for codesign
# In order for the codesigning to work inside of buildbot, security must be
# called to unlock the keychain, which requires a password.
# I've set up a special keychain for this purpose, so as to not compromise
# the login password of the buildslave.
# This means I have to set the special keychain as the default and unlock it
# prior to building the sources.

    f.addStep(ShellCommand(name='check.keychain',
                           command=['security', 'default-keychain'],
                           haltOnFailure=True,
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(ShellCommand(name='find.certificate',
                           command=['security', 'find-certificate', '-c',
                                    'lldb_codesign'],
                           haltOnFailure=True,
                           workdir=WithProperties('%(builddir)s')))
# Building the sources
#
    f.addStep(ShellCommand(name='lldb-build',
                           command=['xcrun', 'xcodebuild', '-workspace',
                                    'lldb.xcworkspace', '-scheme', 'lldb-tool',
                                    '-configuration', 'Debug',
                                    WithProperties('SYMROOT=' + OBJROOT),
                                    WithProperties('OBJROOT=' + OBJROOT)],
                           haltOnFailure=False,
                           workdir=lldb_srcdir))

# Currently the first build always fail, so ignore the first result and add retry as workaround

    f.addStep(ShellCommand(name='lldb-build-Retry',
                           command=['xcrun', 'xcodebuild', '-workspace',
                                    'lldb.xcworkspace', '-scheme', 'lldb-tool',
                                    '-configuration', 'Debug',
                                    WithProperties('SYMROOT=' + OBJROOT),
                                    WithProperties('OBJROOT=' + OBJROOT)],
                           haltOnFailure=True,
                           workdir=lldb_srcdir))
# Testing
#
    if not use_cc:
        use_cc = '/Applications/Xcode.app/Contents/Developer/Toolchains/'
        use_cc += 'XcodeDefault.xctoolchain/usr/bin/clang'
        f.addStep(SetProperty(name='set.cc',
                  command=['xcrun', '-find', 'clang'],
                  property='use_cc',
                  description='set cc',
                  workdir=lldb_srcdir))
    else:
        f.addStep(SetProperty(name='set.cc',
                  command=['echo', use_cc],
                  property='use_cc',
                  description='set cc',
                  workdir=lldb_srcdir))

    f.addStep(LitTestCommand(name='lldb-test',
                             command=['./dosep.py',
                                      '--options',
                                      WithProperties('-m --executable %(lldb_bindir)s/lldb --framework %(lldb_bindir)s/LLDB.framework -A x86_64 -C clang -s ../DerivedData/lldb-test-results')],
                             haltOnFailure=True,
                             workdir='%s/test' % lldb_srcdir,
                             env={'DYLD_FRAMEWORK_PATH' : WithProperties('%(lldb_bindir)s')}))

# Results go in a directory coded named according to the date and time of the test run, e.g.:
#
# 2012-10-16-11_26_48/Failure-x86_64-_Applications_Xcode.app_Contents_Developer_Toolchains_XcodeDefault.xctoolchain_usr_bin_clang-TestLogging.LogTestCase.test_with_dsym.log
#
# Possible results are ExpectedFailure, Failure, SkippedTest, UnexpectedSuccess, and Error.    return f
    return f
