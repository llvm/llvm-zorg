import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand, SetProperty

from zorg.buildbot.commands.NinjaCommand import NinjaCommand

# NOTE: The llgo builder does not currently support Windows,
# on account of the shell commands. That's okay for now, as
# llgo is only tested and known to work on Linux x86-64.

def getLLGoBuildFactory(
            clean=True,
            build_type='Release+Asserts',
            test_libgo=True,             # run 'check-libgo' target if True
    ):
    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"
    llgo_srcdir = '%s/tools/llgo' % llvm_srcdir
    clang_srcdir = '%s/tools/clang' % llvm_srcdir

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f.addStep(SetProperty(name="get_builddir",
                          command=["pwd"],
                          property="builddir",
                          description="set build dir",
                          workdir="."))
    # Get LLVM, clang and llgo
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
    f.addStep(SVN(name='svn-llgo',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llgo/',
                  defaultBranch='trunk',
                  workdir=llgo_srcdir))

    # Clean build directory, if requested.
    f.addStep(ShellCommand(name="rm-llvm_objdir",
                           command=["rm", "-rf", llvm_objdir],
                           haltOnFailure=True,
                           description=["rm build dir", "llvm"],
                           workdir=".",
                           doStepIf=clean))

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                           command=["mkdir", "-p", llvm_objdir],
                           haltOnFailure=False,
                           description=["create build dir"],
                           workdir="."))
    cmakeCommand = [
        "cmake", "-G", "Ninja",
        "../%s" %llvm_srcdir,
        "-DCMAKE_BUILD_TYPE=" + build_type,
    ]
    f.addStep(ShellCommand(name="cmake-configure",
                           command=cmakeCommand,
                           haltOnFailure=False,
                           description=["cmake configure"],
                           workdir=llvm_objdir))

    # Build llgo
    f.addStep(NinjaCommand(name="build_llgo",
                           targets=["llgo"],
                           haltOnFailure=True,
                           description=["build llgo"],
                           workdir=llvm_objdir))
    # Build libgo
    f.addStep(NinjaCommand(name="build_libgo",
                           targets=["libgo"],
                           haltOnFailure=True,
                           logfiles={
                               'libgo-build-out': 'tools/llgo/libgo-prefix/src/libgo-stamp/libgo-build-out.log',
                               'libgo-build-err': 'tools/llgo/libgo-prefix/src/libgo-stamp/libgo-build-err.log',
                               'libgo-configure-out': 'tools/llgo/libgo-prefix/src/libgo-stamp/libgo-configure-out.log',
                               'libgo-configure-err': 'tools/llgo/libgo-prefix/src/libgo-stamp/libgo-configure-err.log',
                           },
                           lazylogfiles=True,
                           description=["build libgo"],
                           workdir=llvm_objdir))
    # Build llgoi
    f.addStep(NinjaCommand(name="build_llgoi",
                           targets=["llgoi"],
                           haltOnFailure=True,
                           description=["build llgoi"],
                           workdir=llvm_objdir))
    # Test llgo
    f.addStep(NinjaCommand(name="test_llgo",
                           targets=["check-llgo"],
                           haltOnFailure=True,
                           description=["test llgo"],
                           workdir=llvm_objdir))
    # Test libgo
    f.addStep(NinjaCommand(name="test_libgo",
                           targets=["check-libgo"],
                           haltOnFailure=True,
                           description=["test libgo"],
                           workdir=llvm_objdir))
    return f

