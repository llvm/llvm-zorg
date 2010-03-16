import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.ClangTestCommand import ClangTestCommand

def getLLVMBuildFactory(triple=None, clean=True, test=True,
                        expensive_checks=False, examples=False, valgrind=False,
                        jobs='%(jobs)s', timeout=20, make='make',
                        enable_shared=False):
    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))

    # Checkout sources.
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir='llvm'))

    # Force without llvm-gcc so we don't run afoul of Frontend test failures.
    configure_args = ["./configure", "--without-llvmgcc", "--without-llvmgxx"]
    config_name = 'Debug'
    if expensive_checks:
        configure_args.append('--enable-expensive-checks')
        config_name += '+Checks'
    if triple:
        configure_args += ['--build=%s' % triple,
                           '--host=%s' % triple,
                           '--target=%s' % triple]
    if enable_shared:
        configure_args.append('--enable-shared')
    f.addStep(Configure(command=configure_args,
                        workdir='llvm',
                        description=['configuring',config_name],
                        descriptionDone=['configure',config_name]))
    if clean:
        f.addStep(WarningCountingShellCommand(name="clean-llvm",
                                              command=[make, 'clean'],
                                              haltOnFailure=True,
                                              description="cleaning llvm",
                                              descriptionDone="clean llvm",
                                              workdir='llvm'))
    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description="compiling llvm",
                                          descriptionDone="compile llvm",
                                          workdir='llvm',
                                          timeout=timeout*60))
    if examples:
        f.addStep(WarningCountingShellCommand(name="compile.examples",
                                              command=['nice', '-n', '10',
                                                       make, WithProperties("-j%s" % jobs),
                                                       'BUILD_EXAMPLES=1'],
                                              haltOnFailure=True,
                                              description=["compiling", "llvm", "examples"],
                                              descriptionDone=["compile", "llvm", "examples"],
                                              workdir='llvm',
                                              timeout=timeout*60))
    if test:
        litTestArgs = '-v'
        if valgrind:
            litTestArgs += ' --vg '
            litTestArgs += ' --vg-arg --leak-check=full'
        f.addStep(ClangTestCommand(name='test-llvm',
                                   command=[make, "check-lit", "VERBOSE=1",
                                            "LIT_ARGS=%s" % litTestArgs],
                                   description=["testing", "llvm"],
                                   descriptionDone=["test", "llvm"],
                                   workdir='llvm'))
    return f
