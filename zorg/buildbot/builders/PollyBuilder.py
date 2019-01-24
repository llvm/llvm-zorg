import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN, Git
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.builders import LNTBuilder
from zorg.buildbot.builders import ClangBuilder

def getPollyBuildFactory(
    clean=False,
    install=False,
    make='make',
    jobs=None,
    checkAll=False,
    env=None,
    extraCmakeArgs=[]):
    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"
    llvm_instdir = "llvm.inst"
    polly_srcdir = '%s/tools/polly' % llvm_srcdir
    clang_srcdir = '%s/tools/clang' % llvm_srcdir
    jobs_cmd = []
    if jobs is not None:
        jobs_cmd = ["-j"+str(jobs)]
    build_cmd = [make] + jobs_cmd
    install_cmd = [make, 'install'] + jobs_cmd
    check_all_cmd = [make, 'check-all'] + jobs_cmd
    check_polly_cmd = [make, 'check-polly'] + jobs_cmd
    cmake_install = []
    if install:
        cmake_install = ["-DCMAKE_INSTALL_PREFIX=../%s" % llvm_instdir]
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
                 }
    if env:
        merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
    # Get LLVM, Clang and Polly
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-clang',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir=clang_srcdir))
    f.addStep(SVN(name='svn-polly',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/polly/',
                  defaultBranch='trunk',
                  workdir=polly_srcdir))

    # Clean build dir
    if clean:
        f.addStep(ShellCommand(name='clean-build-dir',
                               command=['rm', '-rf', llvm_objdir],
                               warnOnFailure=True,
                               description=["clean build dir"],
                               workdir='.',
                               env=merged_env))

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                           command=["mkdir", "-p", llvm_objdir],
                           haltOnFailure=False,
                           description=["create build dir"],
                           workdir=".",
                           env=merged_env))
    cmakeCommand = ["cmake", "../%s" %llvm_srcdir,
                    "-DCMAKE_COLOR_MAKEFILE=OFF",
                    "-DPOLLY_TEST_DISABLE_BAR=ON",
                    "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON",
                    "-DCMAKE_BUILD_TYPE=Release"] + cmake_install + extraCmakeArgs
    f.addStep(ShellCommand(name="cmake-configure",
                           command=cmakeCommand,
                           haltOnFailure=False,
                           description=["cmake configure"],
                           workdir=llvm_objdir,
                           env=merged_env))

    # Build
    f.addStep(ShellCommand(name="build",
                           command=build_cmd,
                           haltOnFailure=True,
                           description=["build"],
                           workdir=llvm_objdir,
                           env=merged_env))

    # Clean install dir
    if install and clean:
        f.addStep(ShellCommand(name='clean-install-dir',
                               command=['rm', '-rf', llvm_instdir],
                               haltOnFailure=False,
                               description=["clean install dir"],
                               workdir='.',
                               env=merged_env))

    # Install
    if install:
        f.addStep(ShellCommand(name="install",
                               command=install_cmd,
                               haltOnFailure=False,
                               description=["install"],
                               workdir=llvm_objdir,
                               env=merged_env))

    # Test
    if checkAll:
        f.addStep(ShellCommand(name="check_all",
                               command=check_all_cmd,
                               haltOnFailure=False,
                               description=["check all"],
                               workdir=llvm_objdir,
                               env=merged_env))
    else:
        f.addStep(ShellCommand(name="check_polly",
                               command=check_polly_cmd,
                               haltOnFailure=False,
                               description=["check polly"],
                               workdir=llvm_objdir,
                               env=merged_env))

    return f

def AddExternalPollyBuildFactory(f, llvm_installdir, build_type = "Release"):
    polly_srcdir = 'polly.src'
    polly_objdir = 'polly.obj'
    polly_installdir = 'polly.install'

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
    f.addStep(SVN(name='svn-polly',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/polly/',
                  defaultBranch='trunk',
                  workdir=polly_srcdir))

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", polly_objdir],
                               haltOnFailure=False,
                               description=["create build dir"],
                               workdir="."))
    cmakeCommand = ["cmake", "../%s" % polly_srcdir]

    cmakeCommand.append('-DCMAKE_PREFIX_PATH=../%s/lib/cmake/llvm' % llvm_installdir)
    cmakeCommand.append('-DCMAKE_BUILD_TYPE=' + build_type)
    cmakeCommand.append('-DCMAKE_INSTALL_PREFIX=../' + polly_installdir)
    cmakeCommand.append('-DCMAKE_COLOR_MAKEFILE=OFF')

    f.addStep(ShellCommand(name="cmake-configure",
                               command=cmakeCommand,
                               haltOnFailure=False,
                               description=["cmake configure"],
                               workdir=polly_objdir))
    # Build Polly
    f.addStep(ShellCommand(name="build-polly",
                               command=["make"],
                               haltOnFailure=True,
                               description=["build polly"],
                               workdir=polly_objdir))
    f.addStep(ShellCommand(name="remove-polly-install",
                           command=["rm", "-rf", polly_installdir],
                           haltOnFailure=True,
                           description=["remove polly install"],
                           workdir="."))
    f.addStep(ShellCommand(name="install-polly",
                           command=["make", "install"],
                           haltOnFailure=True,
                           description=["install polly"],
                           workdir=polly_objdir))

def getPollyLNTFactory(triple, nt_flags, xfails=[], clean=False, test=False,
                       build_type="Release", extra_cmake_args=[], **kwargs):
    lnt_args = {}
    lnt_arg_names = ['submitURL', 'package_cache', 'testerName', 'reportBuildslave']

    for argname in lnt_arg_names:
        if argname in kwargs:
            lnt_args[argname] = kwargs.pop(argname)

    llvm_install_dir = 'stage1.install'

    f = ClangBuilder.getClangCMakeBuildFactory(
        test=False,
        useTwoStage=False,
        clean=clean,
        checkout_clang_tools_extra=False,
        checkout_compiler_rt=False,
        extra_cmake_args=extra_cmake_args,
        stage1_config=build_type)

    f.addStep(ShellCommand(name="install-llvm-and-clang",
                           command=["ninja", "install"],
                           haltOnFailure=True,
                           description=["install llvm and clang"],
                           workdir="stage1"))

    AddExternalPollyBuildFactory(f, llvm_install_dir, build_type)

    nt_flags.append('--cflag=' + '-Xclang')
    nt_flags.append('--cflag=' + '-load')
    nt_flags.append('--cflag=' + '-Xclang')
    nt_flags.append(WithProperties("--cflag=%s/polly.install/lib/LLVMPolly.so",
                                   'builddir'))

    # Add an LNT test runner.
    LNTBuilder.AddLNTTestsToFactory(f, nt_flags,
                                    cc_path=(llvm_install_dir+'/bin/clang'),
                                    cxx_path=(llvm_install_dir+'/bin/clang++'),
                                    **lnt_args);

    return f
