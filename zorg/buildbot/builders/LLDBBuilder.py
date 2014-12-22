import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, SetProperty
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

# CMake Windows builds
def getLLDBWindowsCMakeBuildFactory(
            clean=True,
            cmake='cmake',
            jobs=None,

            config='Release',

            # Environmental variables for all steps.
            env={},
            extra_cmake_args=[]):

    ############# PREPARING
    f = buildbot.process.factory.BuildFactory()

    # We *must* checkout at least Clang, LLVM, and LLDB.  Once we add a step to run
    # tests (e.g. ninja check-lldb), we will also need to add a step for LLD, since
    # MSVC LD.EXE cannot link executables with DWARF debug info.
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir='llvm'))
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='llvm/tools/clang'))
    f.addStep(SVN(name='svn-lldb',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/lldb/',
                  defaultBranch='trunk',
                  workdir='llvm/tools/lldb'))

    # If jobs not defined, Ninja will choose a suitable value
    jobs_cmd=[]
    if jobs is not None:
        jobs_cmd=["-j"+str(jobs)]
    ninja_cmd=['ninja'] + jobs_cmd

    # Global configurations
    build_dir='build'

    ############# CLEANING
    if clean:
        f.addStep(ShellCommand(name='clean',
                               command=['rmdir', '/S/Q', build_dir],
                               warnOnFailure=True,
                               description='Cleaning',
                               descriptionDone='clean',
                               workdir='.',
                               env=env))

    # Use batch files instead of ShellCommand directly, Windows quoting is
    # borked. FIXME: See buildbot ticket #595 and buildbot ticket #377.
    f.addStep(batch_file_download.BatchFileDownload(name='cmakegen',
                                command=[cmake, "-G", "Ninja", "../llvm",
                                         "-DCMAKE_BUILD_TYPE="+config,
                                         # Need to use our custom built version of python
                                         "-DPYTHON_LIBRARY=C:\\src\\python\\PCbuild\\python27_d.lib",
                                         "-DPYTHON_INCLUDE_DIR=C:\\src\\python\\Include",
                                         "-DPYTHON_EXECUTABLE=C:\\src\\python\\PCbuild\\python_d.exe"]
                                         + extra_cmake_args,
                                workdir=build_dir))

    f.addStep(ShellCommand(name='cmake',
                           command=['cmakegen.bat'],
                           haltOnFailure=True,
                           description='cmake gen',
                           workdir=build_dir,
                           env=env))

    f.addStep(WarningCountingShellCommand(name='build',
                                          command=ninja_cmd,
                                          haltOnFailure=True,
                                          description='ninja build',
                                          workdir=build_dir,
                                          env=env))

    return f

def getLLDBBuildFactory(
            triple,
            outOfDir=False,
            useTwoStage=False,
            make='make',
            jobs='%(jobs)s',
            extra_configure_args=[],
            env={},
            *args,
            **kwargs):

    inDir = not outOfDir and not useTwoStage
    if inDir:
        llvm_srcdir = "llvm"
        llvm_objdir = "llvm"
    else:
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

def getLLDBxcodebuildFactory(use_cc=None):
    f = buildbot.process.factory.BuildFactory()
    f.addStep(SetProperty(name='get_builddir',
                          command=['pwd'],
                          property='builddir',
                          description='set build dir',
                          workdir='.'))
    lldb_srcdir = 'lldb.src'
    OBJROOT='%(builddir)s/' + lldb_srcdir + '/build'
    # cleaning out the build directory is vital for codesigning.
    f.addStep(ShellCommand(name='clean.lldb-buid',
                           command=['rm', '-rf', WithProperties(OBJROOT)],
                           haltOnFailure=True,
                           workdir=WithProperties('%(builddir)s')))
    f.addStep(ShellCommand(name='clean.llvm-buid',
                           command=['rm', '-rf', '%s/llvm-build' % lldb_srcdir ],
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
    
    f.addStep(ShellCommand(name='lldb-test',
                           command=['./dotest.py', '-v', '-C',
                                    WithProperties('%(use_cc)s')],
                           haltOnFailure=True,
                           workdir='%s/test' % lldb_srcdir))

# Results go in a directory coded named according to the date and time of the test run, e.g.:
# 
# 2012-10-16-11_26_48/Failure-x86_64-_Applications_Xcode.app_Contents_Developer_Toolchains_XcodeDefault.xctoolchain_usr_bin_clang-TestLogging.LogTestCase.test_with_dsym.log
# 
# Possible results are ExpectedFailure, Failure, SkippedTest, UnexpectedSuccess, and Error.    return f
    return f
