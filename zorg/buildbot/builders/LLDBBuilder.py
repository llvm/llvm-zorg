import os
import json
import collections
import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, SetProperty
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.steps.slave import RemoveDirectory
from buildbot.process.properties import WithProperties, Property
from buildbot.steps import trigger
import zorg.buildbot.commands.BatchFileDownload as batch_file_download
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.builders.Util import getVisualStudioEnvironment
from zorg.buildbot.builders.Util import extractSlaveEnvironment
from zorg.buildbot.process.factory import LLVMBuildFactory

# We *must* checkout at least Clang, LLVM, and LLDB.  Also check out LLD since
# it is needed to run the LLDB test suite.
def getLLDBSource(f,llvmTopDir='llvm'):
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvmTopDir))
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='%s/tools/clang' % llvmTopDir))
    f.addStep(SVN(name='svn-lld',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/lld/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lld' % llvmTopDir))
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

# CMake builds
def getLLDBCMakeBuildFactory(
            clean=False,
            cmake='cmake',
            jobs="%(jobs)s",

            # Source directory containing a built python
            python_source_dir=None,

            # Default values for VS devenv and build configuration
            vs=None,
            config='Release',
            target_arch='x86',

            extra_cmake_args=None,
            test=False,
            testTimeout=2400,
            install=False):

    ############# PREPARING
    f = buildbot.process.factory.BuildFactory()

    # Determine Slave Environment and Set MSVC environment.
    if vs:
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

    # get full path to build directory
    f.addStep(SetProperty(name="get_builddir",
                          command=["pwd"],
                          property="builddir",
                          description="set build dir",
                          workdir=build_dir))

    ############# CLEANING
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean '+build_dir,
                dir=build_dir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    cmake_cmd = [
        "cmake", "-G", "Ninja", "../llvm",
        "-DCMAKE_BUILD_TYPE=" + config,
        "-DCMAKE_INSTALL_PREFIX=../install"
        ]
    if python_source_dir:
        cmake_cmd.append("-DPYTHON_HOME=" + python_source_dir)
    if extra_cmake_args:
        cmake_cmd += extra_cmake_args
    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="cmake-configure",
                           description=["cmake configure"],
                           command=WithProperties(" ".join(cmake_cmd)),
                           haltOnFailure=True,
                           warnOnWarnings=True,
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
                          timeout=testTimeout,
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
                     bindir,
                     test_archs,
                     test_compilers,
                     remote_platform=None,
                     remote_host=None,
                     remote_port=None,
                     remote_dir=None,
                     env=None):
    # Skip test steps if no test compiler or arch is specified
    if None in (test_archs, test_compilers):
        return f
    llvm_srcdir = "llvm"
    llvm_builddir = "build"
    if env is None:
        env = {}
    flunkTestFailure = True
    extraTestFlag = ''
    # TODO: for now, run tests with 8 threads and without mi tests on android
    # come back when those issues are addressed
    testenv=dict(env)
    for compiler in test_compilers:
        # find full path for top of tree clang
        if compiler=='totclang':
            compilerPath=bindir + '/clang'
        elif remote_platform is 'android':
            compilerPath = os.path.join('%(toolchain_test)s', 'bin', compiler)
        else:
            compilerPath = compiler
        for arch in test_archs:
            DOTEST_OPTS=''.join(['--executable ' + bindir + '/lldb ',
                                 '--filecheck ' + bindir + '/FileCheck ',
                                 '-A %s ' % arch,
                                 '-C %s ' % compilerPath,
                                 '-s lldb-test-traces-%s-%s ' % (compiler, arch),
                                 '-u CXXFLAGS ',
                                 '-u CFLAGS ',
                                 '--channel ',
                                 '"gdb-remote packets" ',
                                 '--channel ',
                                 '"lldb all"'])
            testname = "local"
            if remote_platform is not None:
                urlStr='connect://%(remote_host)s:%(remote_port)s'
                if remote_platform is 'android':
                    #i386/x86_64 are the only android archs that are expected to pass at this time
                    flunkTestFailure = arch in ('i386', 'x86_64')
                    testenv['LLDB_TEST_THREADS'] = '8'
                    extraTestFlag = ' -m'
                    urlStr = 'adb://%(deviceid)s:%(remote_port)s'
                    # for Android, remove all forwarded ports before running test
                    # it is noticed that forwarded socket connections were not cleaned for certain crashed tests
                    # clean it here to avoid too many "LISTEN" ports left on slave
                    f.addStep(ShellCommand(name="remove port forwarding %s" % arch,
                                           command=['adb',
                                                    'forward',
                                                    '--remove-all'],
                                           description="Remove port forwarding",
                                           env=env,
                                           haltOnFailure=False,
                                           workdir='%s' % llvm_builddir))
                DOTEST_OPTS += ''.join([' --platform-name remote-' + remote_platform,
                                        ' --platform-url ' + urlStr,
                                        ' --platform-working-dir %(remote_dir)s',
                                        ' --env OS=' + remote_platform.title()])
                testname = "remote-" + remote_platform
            DOTEST_OPTS += extraTestFlag
            f.addStep(LitTestCommand(name="test lldb %s (%s-%s)" % (testname, compiler, arch),
                                     command=['../%s/tools/lldb/test/dosep.py' % llvm_srcdir,
                                              '--options',
                                              WithProperties(DOTEST_OPTS)],
                                     description="test lldb",
                                     parseSummaryOnly=True,
                                     flunkOnFailure=flunkTestFailure,
                                     warnOnFailure=flunkTestFailure,
                                     workdir='%s' % llvm_builddir,
                                     timeout=1800,
                                     env=testenv))
            f=cleanSVNSourceTree(f, '%s/tools/lldb/test' % llvm_srcdir)
    return f

# Define a structure to describe remote target
# For example, RemoteConfig('linux','x86_64',['gcc4.8.2','clang'],['i386'])
RemoteConfig = collections.namedtuple("RemoteConfig", ["platform", "host_arch", "test_compilers", "test_archs"])

# Add steps to run lldb test on remote target
def getLLDBRemoteTestSteps(f,
                           bindir,
                           build_type,
                           remote_config,
                           env):
    if None in (remote_config.test_archs, remote_config.test_compilers):
        return f
    # only supports linux and android as remote target at this time
    if remote_config.platform not in ('linux', 'android'):
        return f
    llvm_srcdir = "llvm"
    llvm_builddir = "build"
    stepDesc = remote_config.platform + "-" + remote_config.host_arch
    # get hostname
    slave_hostname = None
    f.addStep(SetProperty(name="get hostname",
                          command=["hostname"],
                          property="slave_hostname",
                          description="set slave hostname",
                          workdir="."))
    # get configuration of remote target
    # config file should be placed under builddir on builder machine
    # file name: remote_cfg.json
    # content: json format with keys [remote_platform]-[remote_arch]
    # the value for each key defines "remote_host", "remote_port", "remote_dir", "toolchain", "deviceId"
    # example: {"android-i386": {"remote_host":"localhost",
    #                            "remote_port":"5430",
    #                            "remote_dir":"/data/local/tmp/lldb",
    #                            "toolchain_build":"/home/lldb_build/Toolchains/i386-android-toolchain-21",
    #                            "toolchain_test":"/home/lldb_build/Toolchains/i386-android-toolchain-16",
    #                            "deviceid":"XXXXXXX"},

    def getRemoteCfg(rc, stdout, stderr):
        return json.loads(stdout)[stepDesc]
    f.addStep(SetProperty(name="get remote target " + stepDesc,
                          command="cat remote_cfg.json",
                          extract_fn=getRemoteCfg,
                          description="get remote target",
                          workdir="."))
    # rsync
    if remote_config.platform is 'linux':
        shellcmd = ['ssh',
                    WithProperties('%(remote_host)s')]
        hostname = '%(slave_hostname)s'
        launchcmd = shellcmd + ['screen', '-d', '-m']
        terminatecmd = shellcmd + ['pkill', 'lldb-server']
        cleandircmd = WithProperties('ssh %(remote_host)s rm -r %(remote_dir)s/*')
        f.addStep(ShellCommand(name="rsync lldb-server",
                               command=['rsync',
                                        '-havL',
                                        'bin/lldb-server',
                                        WithProperties('%(remote_host)s:%(remote_dir)s')],
                               description="rsync lldb-server " + stepDesc,
                               haltOnFailure=True,
                               env=env,
                               workdir='%s' % llvm_builddir))
        f.addStep(ShellCommand(name="rsync python2.7",
                               command=['rsync',
                                        '-havL',
                                        'lib/python2.7',
                                        WithProperties('%(remote_host)s:%(remote_dir)s')],
                               description="rsync python2.7 " + stepDesc,
                               haltOnFailure=True,
                               env=env,
                               workdir='%s' % llvm_builddir))
    elif remote_config.platform is 'android':
        shellcmd = ['adb',
                    '-s',
                    WithProperties('%(deviceid)s'),
                    'shell']
        hostname = '127.0.0.1'
        launchcmd = ['screen', '-d', '-m'] + shellcmd + [WithProperties("TMPDIR=%(remote_dir)s/tmp")]
        terminatecmd = 'ps | grep lldb-server | awk \'{print $2}\' | xargs'
        terminatecmd = WithProperties('adb -s %(deviceid)s shell ' + terminatecmd + ' adb -s %(deviceid)s shell kill')
        cleandircmd = WithProperties('adb -s %(deviceid)s shell rm -rf %(remote_dir)s/*')
        # compile lldb-server for target platform
        f = getLLDBCmakeAndCompileSteps(f,
                                        'gcc',
                                        build_type,
                                        ['lldb-server'],
                                        bindir,
                                        remote_config.platform,
                                        remote_config.host_arch,
                                        env)

        f.addStep(ShellCommand(name="adb push lldb-server " + stepDesc,
                               command=['adb',
                                        '-s',
                                        WithProperties('%(deviceid)s'),
                                        'push',
                                        remote_config.platform+'-' + remote_config.host_arch + '/bin/lldb-server',
                                        WithProperties('%(remote_dir)s/')],
                               description="lldb-server",
                               env=env,
                               haltOnFailure=True,
                               workdir='%s' % llvm_builddir))
        f.addStep(ShellCommand(name="Build fingerprint " + stepDesc,
                               command=['adb',
                                        '-s',
                                        WithProperties('%(deviceid)s'),
                                        'shell',
                                        'getprop',
                                        'ro.build.fingerprint'],
                               description="get build fingerprint",
                               env=env,
                               haltOnFailure=False,
                               workdir='%s' % llvm_builddir))
    # launch lldb-server
    f.addStep(ShellCommand(name="launch lldb-server " + stepDesc,
                           command=launchcmd +
                                   [WithProperties('%(remote_dir)s/lldb-server'),
                                    'platform',
                                    '--listen',
                                    WithProperties(hostname + ':%(remote_port)s'),
                                    '--server'],
                           description="launch lldb-server on remote host",
                           env=env,
                           haltOnFailure=True,
                           workdir='%s' % llvm_builddir))
    # test steps
    f = getLLDBTestSteps(f,
                         bindir,
                         remote_config.test_archs,
                         remote_config.test_compilers,
                         remote_config.platform,
                         '%(remote_host)s',
                         '%(remote_port)s',
                         '%(remote_dir)s',
                         env)
    # terminate lldb-server on remote host
    f.addStep(ShellCommand(name="terminate lldb-server " + stepDesc,
                           command=terminatecmd,
                           description="terminate lldb-server",
                           env=env,
                           workdir='%s' % llvm_builddir))
    # clean remote test directory
    f.addStep(ShellCommand(name="clean remote dir " + stepDesc,
                           command=cleandircmd,
                           description="clean remote dir",
                           env=env))
    return f

# Cmake bulid on Ubuntu
# Build command sequence - cmake, ninja, ./dosep
# Note: If test_archs or test_compilers is not specified, lldb-test will not be added to build factory
def getLLDBUbuntuCMakeBuildFactory(build_compiler,
                                   build_type,
                                   local_test_archs=None,
                                   local_test_compilers=None,
                                   remote_configs=None,
                                   jobs='%(jobs)s',
                                   env=None):
    """Generate factory steps for ubuntu cmake builder

       Arguments:
       build_compiler       -- string of compile name, example 'clang',
                               the compiler will be used to build binaries for host platform
       build_type           -- 'Debug' or 'Release',
                               used to define build type for host platform as well as remote platform if any
       local_test_archs     -- list of architectures, example ['i386','x86_64'],
                               defines architectures to run local tests against, if None, local tests won't be executed
       local_test_compiler  -- list of compilers, example ['clang','gcc4.8.2'],
                               definds compilers to run local tests with, if None, local tests won't be executed
       remote_configs       -- list of RemoteConfig objects, example [RemoteConfig(...)], if None, remote tests won't be executed
       jobs                 -- number of threads for compilation step, example 40
                               default value is jobs number defined during slave creation
       env                  -- environment variables passed to shell commands

    """
    if env is None:
        env = {}

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
    # Determine the binary directory of *-tblgen.
    f.addStep(SetProperty(name="get tblgen dir",
                          command=["echo", WithProperties(bindir)],
                          property="tblgen_bindir",
                          description="set tblgen dir",
                          workdir="."))
    # Get source code
    f = getLLDBSource(f,llvm_srcdir)

    # Clean Build Folder
    f.addStep(ShellCommand(name="clean",
                           command="rm -rf *",
                           description="clear build folder",
                           env=env,
                           workdir='%s' % llvm_builddir))

    f = getLLDBCmakeAndCompileSteps(f,
                                    build_compiler,
                                    build_type,
                                    [],
                                    bindir,
                                    'linux',
                                    'x86_64',
                                    env)

    # TODO: it will be good to check that architectures listed in test_archs are compatible with host architecture
    # For now, the caller of this function should make sure that each target architecture is supported by builder machine

    # Add local test steps
    f = getLLDBTestSteps(f,
                         bindir,
                         local_test_archs,
                         local_test_compilers)
    # Remote test steps
    if remote_configs is not None:
        for config in remote_configs:
            f = getLLDBRemoteTestSteps(f,
                                       bindir,
                                       build_type,
                                       config,
                                       env)
    # archive test traces
    f = archiveLLDBTestTraces(f, "build/lldb-test-traces-*")
    return f

# zip and upload test traces to google storage
def archiveLLDBTestTraces(f, test_trace):
    f.addStep(ShellCommand(name="compress test traces",
                           command=WithProperties("zip -r build-%(buildnumber)s " + test_trace),
                           description="zip",
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           workdir='.'))
    f.addStep(ShellCommand(name="upload test traces",
                           command=['gsutil',
                                    'mv',
                                    WithProperties('build-%(buildnumber)s.zip'),
                                    WithProperties('gs://lldb_test_traces/%(buildername)s/')],
                           description="upload to Google Storage",
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           workdir='.'))
    return f

# for cmake and compile
def getLLDBCmakeAndCompileSteps(f,
                                build_compiler,
                                build_type,
                                ninja_target,
                                bindir,
                                target_platform,
                                target_arch,
                                env=None):

    if env is None:
        env={}
    llvm_builddir = 'build'
    if target_platform is 'android':
        llvm_builddir = 'build/android-' + target_arch
    # Configure
    f = getLLDBCMakeStep(f,
                         build_compiler,
                         build_type,
                         bindir,
                         target_platform,
                         target_arch,
                         env)
    # Compile
    f.addStep(WarningCountingShellCommand(name='ninja-%s-%s'%(target_platform, target_arch),
                                          command=['nice','-n', '10',
                                                   'ninja',
                                                   WithProperties('-j%(jobs)s')] + ninja_target,
                                          env=env,
                                          haltOnFailure=True,
                                          workdir=llvm_builddir))
    return f

def getLLDBCMakeStep(f,
                     build_compiler,
                     build_type,
                     bindir,
                     target_platform,
                     target_arch,
                     env=None):
    if target_platform is 'linux':
        return getLLDBLinuxCMakeStep(f,
                                     build_compiler,
                                     build_type,
                                     target_arch,
                                     env)
    elif target_platform is 'android':
        return getLLDBAndroidCMakeStep(f,
                                       build_compiler,
                                       build_type,
                                       bindir,
                                       target_arch,
                                       env)

def getCCompilerCmd(compiler):
  if compiler == "clang":
    return "clang"
  elif compiler == "gcc":
    return "gcc"

def getCxxCompilerCmd(compiler):
  if compiler == "clang":
    return "clang++"
  elif compiler == "gcc":
    return "g++"

def getLLDBLinuxCMakeStep(f,
                          build_compiler,
                          build_type,
                          target_arch,
                          env=None):
    if env is None:
        env = {}
    llvm_srcdir = 'llvm'
    llvm_builddir = 'build'
    # Construct cmake
    cmake_args = ["cmake", "-GNinja"]
    cmake_args.append(WithProperties("-DCMAKE_BUILD_TYPE=%s" % build_type))
    cmake_args.append(WithProperties('%(builddir)s/' + llvm_srcdir))
    cmake_args.append("-DCMAKE_C_COMPILER=%s" % getCCompilerCmd(build_compiler))
    cmake_args.append("-DCMAKE_CXX_COMPILER=%s" % getCxxCompilerCmd(build_compiler))

    f.addStep(Configure(name='cmake-linux-%s' % (target_arch),
                        command=cmake_args,
                        env=env,
                        haltOnFailure=True,
                        workdir=llvm_builddir))
    return f

def getLLDBAndroidCMakeStep(f,
                            build_compiler,
                            build_type,
                            bindir,
                            target_arch,
                            env):
    if env is None:
        env = {}
    llvm_srcdir = 'llvm'
    llvm_builddir = 'build/android-' + target_arch
    abiMap={
            'i386':'x86',
            'arm':'armeabi',
            'aarch64':'aarch64'
           }
    # Construct cmake
    cmake_args = ["cmake", "-GNinja"]
    cmake_args.append(WithProperties("-DCMAKE_BUILD_TYPE=%s" % build_type))
    cmake_args.append(WithProperties('%(builddir)s/' + llvm_srcdir))
    cmake_args.append(WithProperties('-DCMAKE_TOOLCHAIN_FILE=' + '%(builddir)s/' + llvm_srcdir + '/tools/lldb/cmake/platforms/Android.cmake'))
    cmake_args.append(WithProperties('-DANDROID_TOOLCHAIN_DIR=' + '%(toolchain_build)s'))
    cmake_args.append('-DANDROID_ABI=' + abiMap[target_arch])
    cmake_args.append('-DCMAKE_CXX_COMPILER_VERSION=4.9')
    cmake_args.append('-DLLVM_TARGET_ARCH=' + target_arch)
    cmake_args.append('-DLLVM_HOST_TRIPLE=' + target_arch + '-unknown-linux-android')
    cmake_args.append(WithProperties('-DLLVM_TABLEGEN=%(tblgen_bindir)s/llvm-tblgen'))
    cmake_args.append(WithProperties('-DCLANG_TABLEGEN=%(tblgen_bindir)s/clang-tblgen'))

    f.addStep(Configure(name='cmake-android-%s' % target_arch,
                        command=cmake_args,
                        env=env,
                        haltOnFailure=True,
                        workdir=llvm_builddir))
    return f
# Set symbolic links, so the folder structure will be llvm, llvm/tools/clang, llvm/tools/lldb
def getSymbLinkSteps(f, lldb_srcdir):
    f.addStep(ShellCommand(name='set symbolic link clang',
                           command=['ln', '-nfs',
                                    WithProperties('%(builddir)s/' + lldb_srcdir + '/llvm/tools/clang'),
                                    'clang'],
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(ShellCommand(name='set symbolic link lldb',
                           command=['ln', '-nfs',
                                    WithProperties('%(builddir)s/' + lldb_srcdir),
                                    lldb_srcdir + '/llvm/tools/lldb'],
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(ShellCommand(name='set symbolic link llvm',
                           command=['ln', '-nfs',
                                    WithProperties('%(builddir)s/' + lldb_srcdir + '/llvm'),
                                    'llvm'],
                           workdir=WithProperties('%(builddir)s')))
    return f

def getLLDBxcodebuildFactory(use_cc=None,
                             build_type='Debug',
                             remote_configs=None,
                             env=None):
    if env is None:
        env = {}
    f = buildbot.process.factory.BuildFactory()
    f.addStep(SetProperty(name='get_builddir',
                          command=['pwd'],
                          property='builddir',
                          description='set build dir',
                          workdir='.'))
    lldb_srcdir = 'lldb'
    OBJROOT='%(builddir)s/' + lldb_srcdir + '/build'
    f.addStep(SetProperty(name='get_bindir',
                          command=['echo',
                                   WithProperties('%(builddir)s/' + lldb_srcdir + '/build/' + build_type)],
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
                           command='rm -rf build/*',
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           workdir='.'))
    # Remove symbolic link to lldb, otherwise xcodebuild will have circular dependency
    f.addStep(ShellCommand(name='remove symbolic link lldb',
                           command=['rm',
                                    lldb_srcdir + '/llvm/tools/lldb'],
                           haltOnFailure=False,
                           flunkOnFailure=False,
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
    buildcmd = ' '.join(['xcrun',
                         'xcodebuild',
                         '-target',
                         'desktop',
                         '-configuration',
                         build_type,
                         'SYMROOT=' + OBJROOT,
                         'OBJROOT=' + OBJROOT])
    f.addStep(ShellCommand(name='lldb-build',
                           command=WithProperties(buildcmd + " || " + buildcmd),
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
    DOTEST_OPTS = ' '.join(['--executable',
                            '%(lldb_bindir)s/lldb',
                            '--filecheck',
                            '%(lldb_bindir)s/FileCheck',
                            '--framework', '%(lldb_bindir)s/LLDB.framework',
                            '-A', 'x86_64',
                            '-C', 'clang',
                            '-s', '../../build/lldb-test-traces'])
    f.addStep(LitTestCommand(name='lldb-test',
                             command=['./dosep.py',
                                      '--options',
                                      WithProperties(DOTEST_OPTS)],
                             haltOnFailure=False,
                             workdir='%s/test' % lldb_srcdir,
                             env={'DYLD_FRAMEWORK_PATH' : WithProperties('%(lldb_bindir)s')}))
# Remote test steps
    if remote_configs is not None:
        # Source structure to use cmake command
        f.addStep(SetProperty(name='get tblgen bindir',
                              command=['echo',
                                       WithProperties('%(builddir)s/' + lldb_srcdir + '/llvm-build/Release+Asserts/x86_64/Release+Asserts/bin')],
                              property='tblgen_bindir',
                              description='set tblgen binaries dir',
                              workdir='.'))
        f = getSymbLinkSteps(f, lldb_srcdir)
        for config in remote_configs:
            f = getLLDBRemoteTestSteps(f,
                                       '%(lldb_bindir)s',
                                       build_type,
                                       config,
                                       env={'DYLD_FRAMEWORK_PATH' : WithProperties('%(lldb_bindir)s')})
# Compress and upload test log
    f = archiveLLDBTestTraces(f, "build/lldb-test-traces*")

# Results go in a directory coded named according to the date and time of the test run, e.g.:
#
# 2012-10-16-11_26_48/Failure-x86_64-_Applications_Xcode.app_Contents_Developer_Toolchains_XcodeDefault.xctoolchain_usr_bin_clang-TestLogging.LogTestCase.test_with_dsym.log
#
# Possible results are ExpectedFailure, Failure, SkippedTest, UnexpectedSuccess, and Error.    return f
    return f

def getShellCommandStep(f,
                        name,
                        command,
                        description="",
                        flunkOnFailure=True,
                        haltOnFailure=True,
                        alwaysRun=False,
                        workdir='scripts',
                        env=None):
    if env is None:
        env = {}
    f.addStep(ShellCommand(name=name,
                           command=command,
                           description=description,
                           env=env,
                           flunkOnFailure=flunkOnFailure,
                           haltOnFailure=haltOnFailure,
                           alwaysRun=alwaysRun,
                           workdir=workdir))

# get configuration of tests
# config file should be placed under builddir on builder machine
# file name: test_cfg.json
# content: json format with keys test[num]:target-compiler-architecture
# example: {"test1":"android-gcc4.9-i386",
#           "test2":"local-clang-x86",
#           "test3":"local-clang-i386"}
def getTestConfig(f):
    def getRemoteCfg(rc, stdout, stderr):
        return json.loads(stdout)
    f.addStep(SetProperty(name="get test config",
                          command="cat test_cfg.json",
                          extract_fn=getRemoteCfg,
                          description="get remote target",
                          workdir="scripts"))
    return f
def getTestSteps(f, scriptExt, pathSep):
    # buildbot doesn't support dynamic step creation, so create 9 test steps as place holder
    # then each builder will define available tests in test_cfg.json
    # if there're less than 9 tests defined on certain builder, extra steps will be skipped and hidden from test details view
    # **hide step is not supported by buildbot 0.8.5
    # flunkOnFailure only takes boolean value, and cannot take configurable property.
    # workaround: don't flunk the last three tests
    # put non flunkable tests at the last three, test7, test8, test9
    getTestConfig(f)
    for x in range(1, 10):
        test='test'+str(x)
        f.addStep(LitTestCommand(name=test,
                                 command=[pathSep + 'test' + scriptExt,
                                          Property(test)],
                                 description=["testing"],
                                 descriptionDone=[WithProperties('%('+test+':-)s')],
                                 doStepIf=lambda step: step.build.hasProperty(step.name),
                                 flunkOnFailure=(x<7),
                                 warnOnFailure=(x<7),
                                 workdir='scripts'))

def getLLDBScriptCommandsFactory(
                       downloadBinary=True,
                       buildAndroid=False,
                       runTest=True,
                       scriptExt='.sh',
                       extra_cmake_args=None,
                       depends_on_projects=None,
                       ):
    if scriptExt is '.bat':
        pathSep = '.\\'
    else:
        pathSep = './'

    if extra_cmake_args is None:
        extra_cmake_args = []

    if depends_on_projects is None:
        f = buildbot.process.factory.BuildFactory()
    else:
        f = LLVMBuildFactory(
                depends_on_projects=depends_on_projects)

    # Update scripts
    getShellCommandStep(f, name='update scripts',
                        command=['updateScripts' + scriptExt])

    # Acquire lock
    if downloadBinary:
        getShellCommandStep(f, name='acquire lock',
                            command=[pathSep + 'acquireLock' + scriptExt,
                                     'totBuild'],
                            description='get')

    # Checkout source code
    getShellCommandStep(f, name='checkout source code',
                        command=[pathSep + 'checkoutSource' + scriptExt,
                                 WithProperties('%(revision)s')])

    # Set source revision
    f.addStep(SetProperty(name="set revision",
              command=[pathSep + 'getRevision' + scriptExt],
              property="got_revision",
              workdir="scripts"))

    # Configure
    getShellCommandStep(f, name='cmake local',
                        command=[pathSep + 'cmake' + scriptExt] + extra_cmake_args)

    # Build
    getShellCommandStep(f, name='ninja build local',
                        command=[pathSep + 'buildLocal' + scriptExt])
    if buildAndroid:
        getShellCommandStep(f, name='build android',
                            command=[pathSep + 'buildAndroid' + scriptExt])

    # Get lldb-server binaries
    if downloadBinary:
        getShellCommandStep(f, name='get lldb-server binaries',
                            command=[pathSep + 'downloadBinaries' + scriptExt,
                                      WithProperties('%(got_revision)s')])

    # Test
    if runTest:
        f.addStep(LitTestCommand(name="run unit tests",
                                 command=[pathSep + 'testUnit' + scriptExt],
                                 description=["testing"],
                                 descriptionDone=["unit test"],
                                 workdir='scripts'))
        getTestSteps(f, scriptExt, pathSep)
        # upload test traces
        getShellCommandStep(f, name='upload test traces',
                            command=[pathSep + 'uploadTestTrace' + scriptExt,
                                     WithProperties('%(buildnumber)s'),
                                     WithProperties('%(buildername)s')],
                            flunkOnFailure=False)

    # Upload lldb-server binaries and trigger android builders
    if buildAndroid:
        getShellCommandStep(f, name='upload lldb-server binaries',
                            command=[pathSep + 'uploadBinaries' + scriptExt])
        f.addStep(trigger.Trigger(schedulerNames=['lldb_android_scheduler'],
                                  updateSourceStamp=False,
                                  waitForFinish=False))
    # Release lock
    if downloadBinary:
        getShellCommandStep(f, name='release lock',
                            command=[pathSep + 'releaseLock' + scriptExt,
                                     'totBuild'],
                            description='release',
                            alwaysRun=True)
    return f
