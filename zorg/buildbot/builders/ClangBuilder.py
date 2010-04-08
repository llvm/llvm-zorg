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

from Util import getConfigArgs

def getClangBuildFactory(triple=None, clean=True, test=True, package_dst=None,
                         run_cxx_tests=False, examples=False, valgrind=False,
                         valgrindLeakCheck=False, outOfDir=False, useTwoStage=False,
                         completely_clean=False, always_install=False,
                         make='make', jobs="%(jobs)s",
                         stage1_config='Debug', stage2_config='Release',
                         extra_configure_args=[]):
    # Don't use in-dir builds with a two stage build process.
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
        llvm_2_installdir = "llvm.install.2"

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))

    # Blow away completely, if requested.
    if completely_clean:
        f.addStep(ShellCommand(name="rm-llvm.src",
                               command=["rm", "-rf", llvm_srcdir],
                               haltOnFailure=True,
                               description=["rm src dir", "llvm"],
                               workdir="."))

    # Checkout sources.
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='%s/tools/clang' % llvm_srcdir))

    # Clean up llvm (stage 1); unless in-dir.
    if clean and llvm_srcdir != llvm_1_objdir:
        f.addStep(ShellCommand(name="rm-llvm.obj.stage1",
                               command=["rm", "-rf", llvm_1_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm"],
                               workdir="."))
        
    # Force without llvm-gcc so we don't run afoul of Frontend test failures.
    base_configure_args = [WithProperties("%%(builddir)s/%s/configure" % llvm_srcdir),
                           '--disable-bindings']
    base_configure_args += extra_configure_args
    if triple:
        base_configure_args += ['--build=%s' % triple, 
                                '--host=%s' % triple,
                                '--target=%s' % triple]
    args = base_configure_args + ["--without-llvmgcc", "--without-llvmgxx"]
    args.append(WithProperties("--prefix=%%(builddir)s/%s" % llvm_1_installdir))
    args += getConfigArgs(stage1_config)
    f.addStep(Configure(command=args,
                        workdir=llvm_1_objdir,
                        description=['configuring',stage1_config],
                        descriptionDone=['configure',stage1_config]))

    # Make clean if using in-dir builds.
    if clean and llvm_srcdir == llvm_1_objdir:
        f.addStep(WarningCountingShellCommand(name="clean-llvm",
                                              command=[make, "clean"],
                                              haltOnFailure=True,
                                              description="cleaning llvm",
                                              descriptionDone="clean llvm",
                                              workdir=llvm_1_objdir))

    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling", stage1_config],
                                          descriptionDone=["compile", stage1_config],
                                          workdir=llvm_1_objdir))

    if examples:
        f.addStep(WarningCountingShellCommand(name="compile.examples",
                                              command=['nice', '-n', '10',
                                                       make, WithProperties("-j%s" % jobs),
                                                       "BUILD_EXAMPLES=1"],
                                              haltOnFailure=True,
                                              description=["compilinge", stage1_config, "examples"],
                                              descriptionDone=["compile", stage1_config, "examples"],
                                              workdir=llvm_1_objdir))

    clangTestArgs = '-v'
    if valgrind:
        clangTestArgs += ' --vg '
        if valgrindLeakCheck:
            clangTestArgs += ' --vg-leak'
        else:
            clangTestArgs += ' --vg-arg --leak-check=no'
        clangTestArgs += ' --vg-arg --suppressions=%(builddir)s/llvm/tools/clang/utils/valgrind/x86_64-pc-linux-gnu_gcc-4.3.3.supp'
    extraTestDirs = ''
    if run_cxx_tests:
        extraTestDirs += '%(builddir)s/llvm/tools/clang/utils/C++Tests'
    if test:
        f.addStep(ClangTestCommand(name='test-llvm',
                                   command=[make, "check-lit", "VERBOSE=1"],
                                   description=["testing", "llvm"],
                                   descriptionDone=["test", "llvm"],
                                   workdir=llvm_1_objdir))
        f.addStep(ClangTestCommand(name='test-clang',
                                   command=[make, 'test', WithProperties('TESTARGS=%s' % clangTestArgs),
                                            WithProperties('EXTRA_TESTDIRS=%s' % extraTestDirs)],
                                   workdir='%s/tools/clang' % llvm_1_objdir))

    # Install llvm and clang.
    if llvm_1_installdir:
        f.addStep(ShellCommand(name="rm-install.clang.stage1",
                               command=["rm", "-rf", llvm_1_installdir],
                               haltOnFailure=True,
                               description=["rm install dir", "clang"],
                               workdir="."))
        f.addStep(WarningCountingShellCommand(name="install.clang.stage1",
                                              command = ['nice', '-n', '10',
                                                         make, 'install-clang'],
                                              haltOnFailure=True,
                                              description=["install", "clang",
                                                           stage1_config],
                                              workdir=llvm_1_objdir))

    if not useTwoStage:
        return f

    # Clean up llvm (stage 2).
    if clean:
        f.addStep(ShellCommand(name="rm-llvm.obj.stage2",
                               command=["rm", "-rf", llvm_2_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm", "(stage 2)"],
                               workdir="."))

    # Configure llvm (stage 2).
    args = base_configure_args + ["--without-llvmgcc", "--without-llvmgxx"]
    args.append(WithProperties("--prefix=%(builddir)s/" + llvm_2_installdir))
    args += getConfigArgs(stage2_config)
    f.addStep(Configure(name="configure.llvm.stage2",
                        command=args,
                        env={'CC' : WithProperties("%%(builddir)s/%s/bin/clang" % llvm_1_installdir),
                             'CXX' :  WithProperties("%%(builddir)s/%s/bin/clang++" % llvm_1_installdir),},
                        haltOnFailure=True,
                        workdir=llvm_2_objdir,
                        description=["configure", "llvm", "(stage 2)",
                                     stage2_config]))

    # Build llvm (stage 2).
    f.addStep(WarningCountingShellCommand(name="compile.llvm.stage2",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling", "(stage 2)",
                                                       stage2_config],
                                          descriptionDone=["compile", "(stage 2)",
                                                           stage2_config],
                                          workdir=llvm_2_objdir))

    if test:
        f.addStep(ClangTestCommand(name='test-llvm',
                                   command=[make, "check-lit", "VERBOSE=1"],
                                   description=["testing", "llvm"],
                                   descriptionDone=["test", "llvm"],
                                   workdir=llvm_2_objdir))
        f.addStep(ClangTestCommand(name='test-clang',
                                   command=[make, 'test', WithProperties('TESTARGS=%s' % clangTestArgs),
                                            WithProperties('EXTRA_TESTDIRS=%s' % extraTestDirs)],
                                   workdir='%s/tools/clang' % llvm_2_objdir))

    # Install clang (stage 2).
    f.addStep(ShellCommand(name="rm-install.clang.stage2",
                           command=["rm", "-rf", llvm_2_installdir],
                           haltOnFailure=True,
                           description=["rm install dir", "clang"],
                           workdir="."))
    f.addStep(WarningCountingShellCommand(name="install.clang.stage2",
                                          command = ['nice', '-n', '10',
                                                     make, 'install-clang'],
                                          haltOnFailure=True,
                                          description=["install", "clang",
                                                       "(stage 2)"],
                                          workdir=llvm_2_objdir))

    if package_dst:
        name = WithProperties(
            "%(builddir)s/" + llvm_2_objdir +
            "/clang-r%(got_revision)s-b%(buildnumber)s.tgz")
        f.addStep(ShellCommand(name='pkg.tar',
                               description="tar root",
                               command=["tar", "zcvf", name, "./"],
                               workdir=llvm_2_installdir,
                               warnOnFailure=True,
                               flunkOnFailure=False,
                               haltOnFailure=False))
        f.addStep(ShellCommand(name='pkg.upload',
                               description="upload root", 
                               command=["scp", name,
                                        WithProperties(
                        package_dst + "/%(buildername)s")],
                               workdir=".",
                               warnOnFailure=True,
                               flunkOnFailure=False,
                               haltOnFailure=False))

    return f

def getClangMSVCBuildFactory(update=True, clean=True, vcDrive='c', jobs=1,
                             cmake=r"c:\Program Files\CMake 2.6\bin\cmake"):
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
                                command=[cmake,
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
