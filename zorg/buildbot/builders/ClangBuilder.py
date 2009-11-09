import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.steps.transfer import FileDownload
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.ClangTestCommand import ClangTestCommand
from zorg.buildbot.commands.BatchFileDownload import BatchFileDownload

def getClangBuildFactory(triple, clean=True, test=True):
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
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='llvm/tools/clang'))
    f.addStep(Configure(command=['./configure',
                                 '--build', triple,
                                 '--host', triple,
                                 '--target', triple],
                        workdir='llvm',
                        description=['configuring','Debug'],
                        descriptionDone=['configure','Debug']))
    if clean:
        f.addStep(WarningCountingShellCommand(name="clean-llvm",
                                              command="make clean",
                                              haltOnFailure=True,
                                              description="cleaning llvm",
                                              descriptionDone="clean llvm",
                                              workdir='llvm'))
    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=WithProperties("nice -n 10 make -j%(jobs)d"),
                                          haltOnFailure=True,
                                          description="compiling llvm & clang",
                                          descriptionDone="compile llvm & clang",
                                          workdir='llvm'))
    if test:
        f.addStep(ClangTestCommand(name='test-llvm',
                                   command=["make", "check-lit", "VERBOSE=1"],
                                   description=["testing", "llvm"],
                                   descriptionDone=["test", "llvm"],
                                   workdir='llvm'))
        f.addStep(ClangTestCommand(name='test-clang',
                                   command=WithProperties("nice -n 10 make test VERBOSE=1"),
                                   workdir='llvm/tools/clang'))
    return f

def getClangMSVCBuildFactory(update=True, clean=True, vcDrive='c', jobs=1):
    f = buildbot.process.factory.BuildFactory()

    if update:
        f.addStep(SVN(name='svn-llvm',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                      defaultBranch='trunk',
                      workdir='llvm'))

    if update:
        f.addStep(SVN(name='svn-clang',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                      defaultBranch='trunk',
                      workdir='llvm/tools/clang'))

    # Full & fast clean.
    if clean:
        f.addStep(ShellCommand(name='clean-1',
                               command=['del','/s/q','build'],
                               warnOnFailure=True,
                               description='cleaning',
                               descriptionDone='clean',
                               workdir='llvm'))
        f.addStep(ShellCommand(name='clean-2',
                               command=['rmdir','/s/q','build'],
                               warnOnFailure=True,
                               description='cleaning',
                               descriptionDone='clean',
                               workdir='llvm'))

    # Create the project files.

    # Use batch files instead of ShellCommand directly, Windows quoting is
    # borked. FIXME: See buildbot ticket #595 and buildbot ticket #377.
    f.addStep(BatchFileDownload(name='cmakegen',
                                command=[r"c:\Program Files\CMake 2.6\bin\cmake",
                                         "-DLLVM_TARGETS_TO_BUILD:=X86",
                                         "-G",
                                         "Visual Studio 9 2008",
                                         ".."],
                                workdir="llvm\\build"))
    f.addStep(ShellCommand(name='cmake',
                           command=['cmakegen.bat'],
                           haltOnFailure=True,
                           description='cmake gen',
                           workdir='llvm\\build'))

    # Build it.
    f.addStep(BatchFileDownload(name='vcbuild',
                                command=[vcDrive + r""":\Program Files\Microsoft Visual Studio 9.0\VC\VCPackages\vcbuild.exe""",
                                         "/M%d" % jobs,
                                         "LLVM.sln",
                                         "Debug|Win32"],
                                workdir="llvm\\build"))
    f.addStep(WarningCountingShellCommand(name='vcbuild',
                                          command=['vcbuild.bat'],
                                          haltOnFailure=True,
                                          description='vcbuild',
                                          workdir='llvm\\build',
                                          warningPattern=" warning C.*:"))

    # Build clang-test project.
    f.addStep(BatchFileDownload(name='vcbuild_test',
                                command=[vcDrive + r""":\Program Files\Microsoft Visual Studio 9.0\VC\VCPackages\vcbuild.exe""",
                                         "clang-test.vcproj",
                                         "Debug|Win32"],
                                workdir="llvm\\build\\tools\\clang\\test"))
    f.addStep(ClangTestCommand(name='test-clang',
                               command=["vcbuild_test.bat"],
                               workdir="llvm\\build\\tools\\clang\\test"))

    return f
