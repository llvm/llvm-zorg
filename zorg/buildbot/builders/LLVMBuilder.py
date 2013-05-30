import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.LitTestCommand import LitTestCommand

from Util import getConfigArgs

def getLLVMBuildFactory(
                  triple               = None,             # Triple to build, host, and target.
                  clean                = True,             # "clean-llvm" step is requested if true.
                  test                 = True,             # "test-llvm" step is requested if true.
                  expensive_checks     = False,
                  examples             = False,            # "compile.examples" step is requested if true.
                  valgrind             = False,            # Valgrind is used on "test-llvm" step if true.
                  valgrindLeakCheck    = False,            # Valgrind leak check is requested if true.
                  valgrindSuppressions = None,             # Valgrind suppression file.
                  jobs                 = '%(jobs)s',       # Number of concurrent jobs.
                  timeout              = 20,               # Timeout if no activity seen (minutes).
                  make                 = 'make',           # Make command.
                  enable_shared        = False,            # Enable shared (--enable-shared configure parameters added) if true.
                  enable_targets       = None,             # List of enabled targets (--enable-targets configure param).
                  defaultBranch        = 'trunk',          # Branch to build.
                  llvmgccdir           = None,             # Path to llvm-gcc.
                  config_name          = 'Debug+Asserts',  # Configuration name.
                  env                  = {},               # Environmental variables for all steps.
                  extra_configure_args = [],               # Extra args for the conigure step.
                  outOfDir             = False):           # Enable out-of-dir build (for cross-compile builds).
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

    if outOfDir:
        llvm_srcdir = "llvm.src"
        llvm_objdir = "llvm.obj"
    else:
        llvm_srcdir = "llvm"
        llvm_objdir = "llvm"

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

    # Force without llvm-gcc so we don't run afoul of Frontend test failures.
    configure_args = [WithProperties("%%(builddir)s/%s/configure" % llvm_srcdir)]
    if llvmgccdir:
        configure_args += ['--with-llvmgccdir=%s' % llvmgccdir]
    else:
        configure_args += ["--without-llvmgcc", "--without-llvmgxx"]
    configure_args += getConfigArgs(config_name)
    if enable_targets is not None:
        configure_args.append('--enable-targets=%s' % enable_targets)
    if triple:
        configure_args += ['--build=%s' % triple,
                           '--host=%s' % triple,
                           '--target=%s' % triple]
    if enable_shared:
        configure_args.append('--enable-shared')
    configure_args.extend(extra_configure_args)
    f.addStep(
        Configure(
            command         = configure_args,
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
    if examples:
        f.addStep(
            WarningCountingShellCommand(
                name            = "compile.examples",
                command         = ['nice', '-n', '10',
                                   make, WithProperties("-j%s" % jobs),
                                   'BUILD_EXAMPLES=1'],
                haltOnFailure   = True,
                description     = ["compiling", "llvm", "examples"],
                descriptionDone = ["compile",   "llvm", "examples"],
                workdir         = llvm_objdir,
                env             = merged_env,
                timeout         = timeout * 60))
    if test:
        litTestArgs = '-v -j %s' % jobs
        if valgrind:
            litTestArgs += ' --vg '
            if valgrindLeakCheck:
                litTestArgs += ' --vg-leak'
            if valgrindSuppressions is not None:
                litTestArgs += ' --vg-arg --suppressions=%%(builddir)s/llvm/%s' % valgrindSuppressions
        f.addStep(
            LitTestCommand(
                name            = 'test-llvm',
                command         = [make, "check-lit", "VERBOSE=1",
                                   WithProperties("LIT_ARGS=%s" % litTestArgs)],
                description     = ["testing", "llvm"],
                descriptionDone = ["test",    "llvm"],
                workdir         = llvm_objdir,
                env             = merged_env))
    return f
