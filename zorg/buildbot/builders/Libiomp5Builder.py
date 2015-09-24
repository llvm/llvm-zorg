import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

import zorg.buildbot.commands as commands
import zorg.buildbot.commands.LitTestCommand as lit_test_command


def getLibompCMakeBuildFactory(clean=True, env=None, test=True, c_compiler="gcc", cxx_compiler="g++"):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    openmp_srcdir = "openmp.src"
    openmp_builddir = "openmp.build"

    f = buildbot.process.factory.BuildFactory()

    # Get libomp
    f.addStep(SVN(name='svn-libomp',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/openmp/',
                  defaultBranch='trunk',
                  workdir=openmp_srcdir))

    # Clean directory, if requested.
    if clean:
        f.addStep(ShellCommand(name="clean",
                               command=["rm", "-rf",openmp_builddir],
                               warnOnFailure=True,
                               description=["clean"],
                               workdir='.',
                               env=merged_env))

    # CMake
    f.addStep(ShellCommand(name='cmake',
                           command=["cmake", "../"+openmp_srcdir,
                                    "-DCMAKE_C_COMPILER="+c_compiler,
                                    "-DCMAKE_CXX_COMPILER="+cxx_compiler],
                           haltOnFailure=True,
                           description='cmake',
                           workdir=openmp_builddir,
                           env=merged_env))

    # Make
    f.addStep(WarningCountingShellCommand(name='make build',
                                          command=['make'],
                                          haltOnFailure=True,
                                          description='make build',
                                          workdir=openmp_builddir,
                                          env=merged_env))

    # Test, if requested
    if test:
        f.addStep(lit_test_command.LitTestCommand(name='make check-libomp',
                                                  command=['make', 'check-libomp'],
                                                  haltOnFailure=True,
                                                  description=["make check-libomp"],
                                                  descriptionDone=["build checked"],
                                                  workdir=openmp_builddir,
                                                  env=merged_env))

    return f
