import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

import ClangBuilder
import LLVMBuilder
reload(LLVMBuilder)
import LLVMBuilder
from Util import getConfigArgs

from zorg.buildbot.commands.DejaGNUCommand import DejaGNUCommand

def getKLEEBuildFactory(triple, jobs='%(jobs)d', llvm_branch='trunk',
                        config_name='Release+Asserts', clean=True, llvmgccdir=None,
                        *args, **kwargs):
    if False:
        f = buildbot.process.factory.BuildFactory()

        # Determine the build directory.
        f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                                   command=["pwd"],
                                                   property="builddir",
                                                   description="set build dir",
                                                   workdir="."))
    else:
        # If we are building from trunk, we need to build Clang as
        # well so we have access to an LLVM capable compiler.
        if llvm_branch == 'trunk':
            f = ClangBuilder.getClangBuildFactory(triple, jobs=jobs,
                                                  stage1_config=config_name, extra_configure_args=['--with-built-clang',
                                                                                                   '--enable-targets=host',
                                                                                                   '--with-llvmcc=clang'],
                                                  clean=clean, test=False, *args, **kwargs)
        else:
            f = LLVMBuilder.getLLVMBuildFactory(triple, jobs=jobs, defaultBranch=llvm_branch,
                                                config_name=config_name, llvmgccdir=llvmgccdir,
                                                enable_targets='x86', clean=clean, test=False,
                                                *args, **kwargs)

    # Checkout sources.
    f.addStep(SVN(name='svn-klee',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/klee/',
                  defaultBranch='trunk', workdir='klee'))

    # Configure.
    configure_args = ["./configure", WithProperties("--with-llvm=%(builddir)s/llvm")]
    configure_args += getConfigArgs(config_name)
    if triple:
        configure_args += ['--build=%s' % triple,
                           '--host=%s' % triple,
                           '--target=%s' % triple]
    f.addStep(Configure(command=configure_args, workdir='klee',
                        description=['configure','klee',config_name]))

    # Clean, if requested.
    if clean:
        f.addStep(WarningCountingShellCommand(name="clean-klee",
                                              command=['make', 'clean'],
                                              haltOnFailure=True,
                                              description="clean klee",
                                              workdir='klee'))

    # Compile.
    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   'make', WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True, description="compile klee",
                                          workdir='klee'))

    # Test.
    f.addStep(DejaGNUCommand(name="test",
                             command=['nice', '-n', '10',
                                      'make', 'check'],
                             haltOnFailure=True, description="test klee",
                             workdir='klee',
                             logfiles={ 'dg.sum' : 'test/testrun.sum' }))

    return f
