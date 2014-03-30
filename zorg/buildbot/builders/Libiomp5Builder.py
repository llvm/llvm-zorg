import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

def getLibiomp5BuildFactory(clean=True, env=None, buildcompiler="gcc"):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    openmp_srcdir = "openmp.src"

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir=".",
                                               env=merged_env))

    # Get libiomp5
    f.addStep(SVN(name='svn-libiomp5',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/openmp/',
                  defaultBranch='trunk',
                  workdir=openmp_srcdir))

    # Clean directory, if requested.
    if clean:
        f.addStep(ShellCommand(name="make clean",
                               command=["make", "clean"],
                               haltOnFailure=True,
                               description=["make clean"],
                               workdir='%s/runtime' % openmp_srcdir,
                               env=merged_env))

    makeCommand = [
        "make",
        "compiler=\"%s\"" % buildcompiler]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="make build",
                           description=["make build"],
                           haltOnFailure=True,
                           command=WithProperties(" ".join(makeCommand)),
                           workdir='%s/runtime' % openmp_srcdir,
                           env=merged_env))
    return f
