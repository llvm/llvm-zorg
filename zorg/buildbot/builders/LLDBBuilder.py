import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import SetProperty, ShellCommand, WarningCountingShellCommand
from buildbot.process.properties import WithProperties

import ClangBuilder

def isNewLLVMRevision(build_status):
    if build_status.getNumber() == 0:
        return true

    current_llvmrev = build_status.getProperty('llvmrev')
    try:
        prev_build_no = build_status.getNumber()-1
        prev_build_status = build_status.getBuilder().getBuild(prev_build_no)
        prev_llvmrev = prev_build_status.getProperty('llvmrev')
        return prev_llvmrev != current_llvmrev
    except IndexError:
        return true

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
                  baseURL='http://llvm.org/svn/llvm-project/lldb/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lldb' % llvm_srcdir))
    f.addStep(SetProperty(command='grep ^our.*llvm_revision scripts/build-llvm.pl | cut -d \\" -f 2',
                          property='llvmrev',
                          workdir='%s/tools/lldb' % llvm_srcdir))

    same_llvmrev = lambda step: not isNewLLVMRevision(step.build.getStatus())
    new_llvmrev = lambda step: isNewLLVMRevision(step.build.getStatus())

    # Clean LLVM only if its revision number changed since the last build.
    # Otherwise, only clean LLDB.
    clean_lldb = \
        WarningCountingShellCommand(name="clean-lldb",
                                    command=['make', "clean"],
                                    haltOnFailure=True,
                                    description="cleaning lldb",
                                    descriptionDone="clean lldb",
                                    workdir='%s/tools/lldb' % llvm_1_objdir,
                                    doStepIf=same_llvmrev)

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
                                               clean=new_llvmrev,
                                               extra_clean_step=clean_lldb,
                                               *args, **kwargs)
    f.steps += clangf.steps

    # Test.
    f.addStep(ShellCommand(name="test",
                           command=['nice', '-n', '10',
                                    'make'],
                           haltOnFailure=True, description="test lldb",
                           workdir='%s/tools/lldb/test' % llvm_1_objdir))

    return f
