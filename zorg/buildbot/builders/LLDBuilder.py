import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN, Git from buildbot.steps.shell import Configure, ShellCommand from buildbot.process.properties import WithProperties

from zorg.buildbot.builders import LNTBuilder from zorg.buildbot.builders import ClangBuilder


def getLLDBuildFactory(
           clean = True):

    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
    # Get LLVM and Lld
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-lld',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/lld/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lld' % llvm_srcdir))

    # Clean directory, if requested.
    if clean:
        f.addStep(ShellCommand(name="rm-llvm_objdir",
                               command=["rm", "-rf", llvm_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm"],
                               workdir="."))

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", llvm_objdir],
                               haltOnFailure=False,
                               description=["create build dir"],
                               workdir="."))
    cmakeCommand = [
        "cmake",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_FLAGS=\"-Wall -Werror -std=c++11 -stdlib=libc++ -U__STRICT_ANSI__\"",
        "../%s" % llvm_srcdir]
    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="cmake-configure",
                               description=["cmake configure"],
                               haltOnFailure=True,
                               command=WithProperties(" ".join(cmakeCommand)),
                               env={
                                    'CXX': "clang++",
                                    'C':   "clang"},
                               workdir=llvm_objdir))
    # Build Lld
    f.addStep(ShellCommand(name="build_Lld",
                               command=["make"],
                               haltOnFailure=True,
                               description=["build lld"],
                               workdir=llvm_objdir))
    # Test Lld
    f.addStep(ShellCommand(name="test_lld",
                               command=["make", "lld-test"],
                               haltOnFailure=True,
                               description=["test lld"],
                               workdir=llvm_objdir))

    return f
