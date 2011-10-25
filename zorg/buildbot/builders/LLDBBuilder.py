import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import SetProperty, ShellCommand
from buildbot.process.properties import WithProperties

import ClangBuilder

def getLLDBBuildFactory(triple, outOfDir=False, useTwoStage=False,
                        always_install=False, extra_configure_args=[],
                        *args, **kwargs):
    # FIXME: this code is copied from getClangBuildFactory
    inDir = not outOfDir and not useTwoStage
    if inDir:
        llvm_srcdir = "llvm"
        llvm_1_objdir = "llvm"
        if always_install:
            llvm_1_installdir = "llvm.install"
        else:
            llvm_1_installdir = None
    else:
        llvm_srcdir = "llvm.src"
        llvm_1_objdir = "llvm.obj"
        llvm_1_installdir = "llvm.install.1"
        llvm_2_objdir = "llvm.obj.2"
        llvm_2_installdir = "llvm.install"

    f = buildbot.process.factory.BuildFactory()

    f.addStep(SVN(name='svn-lldb',
                  mode='update',
                  baseURL='https://llvm.org/svn/llvm-project/lldb/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lldb' % llvm_srcdir))
    f.addStep(SetProperty(command='grep ^our.*llvm_revision scripts/build-llvm.pl | cut -d \\" -f 2',
                          property='llvmrev',
                          workdir='%s/tools/lldb' % llvm_srcdir))

    # We use force_checkout to ensure the initial checkout is not aborted due to
    # the presence of the tools/lldb directory
    clangf = ClangBuilder.getClangBuildFactory(triple, test=False,
                                               outOfDir=outOfDir,
                                               useTwoStage=useTwoStage,
                                               always_install=always_install,
                                               extra_configure_args=
                                                 extra_configure_args+
                                                 ['--enable-targets=host'],
                                               trunk_revision='%(llvmrev)s',
                                               force_checkout=True,
                                               *args, **kwargs)
    f.steps += clangf.steps

    # Test.
    f.addStep(ShellCommand(name="test",
                           command=['nice', '-n', '10',
                                    'make'],
                           haltOnFailure=True, description="test lldb",
                           workdir='%s/tools/lldb/test' % llvm_1_objdir))

    return f
