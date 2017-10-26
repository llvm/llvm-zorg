import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.LitTestCommand import LitTestCommand

from Util import getConfigArgs

def getLLVMCMakeBuildFactory(
                  clean                = True,             # "clean-llvm" step is requested if true.
                  test                 = True,             # "test-llvm" step is requested if true.
                  jobs                 = '%(jobs)s',       # Number of concurrent jobs.
                  timeout              = 20,               # Timeout if no activity seen (minutes).
                  make                 = 'make',           # Make command.
                  enable_shared        = False,            # Enable shared (-DBUILD_SHARED_LIBS=ON configure parameters added) if true.
                  defaultBranch        = 'trunk',          # Branch to build.
                  config_name          = 'Debug',          # Configuration name.
                  env                  = None,             # Environmental variables for all steps.
                  extra_cmake_args = []):                  # Extra args for the cmake step.
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(
        buildbot.steps.shell.SetProperty(
            name        = "get_builddir",
            command     = ["pwd"],
            property    = "builddir",
            description = "set build dir",
            workdir     = ".",
            env         = merged_env))

    # Checkout sources.
    f.addStep(
        SVN(
            name          = 'svn-llvm',
            mode          = 'update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
            defaultBranch = defaultBranch,
            workdir       = llvm_srcdir))

    cmake_args = ['cmake']
    cmake_args += ["-DCMAKE_BUILD_TYPE="+config_name]
    if enable_shared:
        cmake_args.append('-DBUILD_SHARED_LIBS=ON')
    cmake_args.extend(extra_cmake_args)
    cmake_args += ['../' + llvm_srcdir]
    f.addStep(
        Configure(
            command         = cmake_args,
            description     = ['configuring', config_name],
            descriptionDone = ['configure',   config_name],
            workdir         = llvm_objdir,
            env             = merged_env))
    if clean:
        f.addStep(
            WarningCountingShellCommand(
                name            = "clean-llvm",
                command         = [make, 'clean'],
                haltOnFailure   = True,
                description     = "cleaning llvm",
                descriptionDone = "clean llvm",
                workdir         = llvm_objdir,
                env             = merged_env))
    f.addStep(
        WarningCountingShellCommand(
            name            = "compile",
            command         = ['nice', '-n', '10',
                               make, WithProperties("-j%s" % jobs)],
            haltOnFailure   = True,
            description     = "compiling llvm",
            descriptionDone = "compile llvm",
            workdir         = llvm_objdir,
            env             = merged_env,
            timeout         = timeout * 60))
    if test:
        litTestArgs = '-v -j %s' % jobs
        f.addStep(
            LitTestCommand(
                name            = 'test-llvm',
                command         = [make, "check-all", "VERBOSE=1",
                                   WithProperties("-j%s" % jobs),
                                   WithProperties("LIT_ARGS=%s" % litTestArgs)],
                description     = ["testing", "llvm"],
                descriptionDone = ["test",    "llvm"],
                workdir         = llvm_objdir,
                env             = merged_env))
    return f
