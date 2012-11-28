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
from zorg.buildbot.commands import DejaGNUCommand

from zorg.buildbot.builders.Util import getConfigArgs

def getClangBuildFactory(
            triple=None,
            clean=True,
            test=True,
            package_dst=None,
            run_cxx_tests=False,
            examples=False,
            valgrind=False,
            valgrindLeakCheck=False,
            outOfDir=False,
            useTwoStage=False,
            completely_clean=False, 
            make='make',
            jobs="%(jobs)s",
            stage1_config='Debug+Asserts',
            stage2_config='Release+Asserts',
            env={}, # Environmental variables for all steps.
            extra_configure_args=[],
            use_pty_in_tests=False,
            trunk_revision=None,
            force_checkout=False,
            extra_clean_step=None,
            checkout_compiler_rt=False,
            run_gdb=False,
            run_modern_gdb=False,
            run_gcc=False):
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    if run_gdb or run_gcc or run_modern_gdb:
        outOfDir = True
        
    # Don't use in-dir builds with a two stage build process.
    inDir = not outOfDir and not useTwoStage
    if inDir:
        llvm_srcdir = "llvm"
        llvm_1_objdir = "llvm"
        llvm_1_installdir = None
    else:
        llvm_srcdir = "llvm.src"
        llvm_1_objdir = "llvm.obj"
        llvm_1_installdir = "llvm.install.1"
        llvm_2_objdir = "llvm.obj.2"
        llvm_2_installdir = "llvm.install"

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir=".",
                                               env=merged_env))

    # Blow away completely, if requested.
    if completely_clean:
        f.addStep(ShellCommand(name="rm-llvm.src",
                               command=["rm", "-rf", llvm_srcdir],
                               haltOnFailure=True,
                               description=["rm src dir", "llvm"],
                               workdir=".",
                               env=merged_env))

    # Checkout sources.
    if trunk_revision:
        # The SVN build step provides no mechanism to check out a specific revision
        # based on a property, so just run the commands directly here.
        svn_co = ['svn', 'checkout']
        if force_checkout:
            svn_co += ['--force']
        svn_co += ['--revision', WithProperties(trunk_revision)]

        svn_co_llvm = svn_co + \
          [WithProperties('http://llvm.org/svn/llvm-project/llvm/trunk@%s' %
                          trunk_revision),
           llvm_srcdir]
        svn_co_clang = svn_co + \
          [WithProperties('http://llvm.org/svn/llvm-project/cfe/trunk@%s' %
                          trunk_revision),
           '%s/tools/clang' % llvm_srcdir]
        svn_co_clang_tools_extra = svn_co + \
          [WithProperties('http://llvm.org/svn/llvm-project/clang-tools-extra/trunk@%s' %
                          trunk_revision),
           '%s/tools/clang/tools/extra' % llvm_srcdir]

        f.addStep(ShellCommand(name='svn-llvm',
                               command=svn_co_llvm,
                               haltOnFailure=True,
                               workdir='.'))
        f.addStep(ShellCommand(name='svn-clang',
                               command=svn_co_clang,
                               haltOnFailure=True,
                               workdir='.'))
        f.addStep(ShellCommand(name='svn-clang-tools-extra',
                               command=svn_co_clang_tools_extra,
                               haltOnFailure=True,
                               workdir='.'))
    else:
        f.addStep(SVN(name='svn-llvm',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/llvm/',
                      defaultBranch='trunk',
                      workdir=llvm_srcdir))
        f.addStep(SVN(name='svn-clang',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/cfe/',
                      defaultBranch='trunk',
                      workdir='%s/tools/clang' % llvm_srcdir))
        f.addStep(SVN(name='svn-clang-tools-extra',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/clang-tools-extra/',
                      defaultBranch='trunk',
                      workdir='%s/tools/clang/tools/extra' % llvm_srcdir))
        if checkout_compiler_rt:
            f.addStep(SVN(name='svn-compiler-rt',
                          mode='update',
                          baseURL='http://llvm.org/svn/llvm-project/compiler-rt/',
                          defaultBranch='trunk',
                          workdir='%s/projects/compiler-rt' % llvm_srcdir))

    # Clean up llvm (stage 1); unless in-dir.
    if clean and llvm_srcdir != llvm_1_objdir:
        f.addStep(ShellCommand(name="rm-llvm.obj.stage1",
                               command=["rm", "-rf", llvm_1_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm"],
                               workdir=".",
                               env=merged_env))

    # Force without llvm-gcc so we don't run afoul of Frontend test failures.
    base_configure_args = [WithProperties("%%(builddir)s/%s/configure" % llvm_srcdir),
                           '--disable-bindings']
    base_configure_args += extra_configure_args
    if triple:
        base_configure_args += ['--build=%s' % triple,
                                '--host=%s' % triple]
    args = base_configure_args + ["--without-llvmgcc", "--without-llvmgxx"]
    args.append(WithProperties("--prefix=%%(builddir)s/%s" % llvm_1_installdir))
    args += getConfigArgs(stage1_config)
    f.addStep(Configure(command=args,
                        workdir=llvm_1_objdir,
                        description=['configuring',stage1_config],
                        descriptionDone=['configure',stage1_config],
                        env=merged_env))

    # Make clean if using in-dir builds.
    if clean and llvm_srcdir == llvm_1_objdir:
        f.addStep(WarningCountingShellCommand(name="clean-llvm",
                                              command=[make, "clean"],
                                              haltOnFailure=True,
                                              description="cleaning llvm",
                                              descriptionDone="clean llvm",
                                              workdir=llvm_1_objdir,
                                              doStepIf=clean,
                                              env=merged_env))

    if extra_clean_step:
        f.addStep(extra_clean_step)

    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling", stage1_config],
                                          descriptionDone=["compile", stage1_config],
                                          workdir=llvm_1_objdir,
                                          env=merged_env))

    if examples:
        f.addStep(WarningCountingShellCommand(name="compile.examples",
                                              command=['nice', '-n', '10',
                                                       make, WithProperties("-j%s" % jobs),
                                                       "BUILD_EXAMPLES=1"],
                                              haltOnFailure=True,
                                              description=["compilinge", stage1_config, "examples"],
                                              descriptionDone=["compile", stage1_config, "examples"],
                                              workdir=llvm_1_objdir,
                                              env=merged_env))

    clangTestArgs = llvmTestArgs = '-v -j %s' % jobs
    if valgrind:
        clangTestArgs += ' --vg'
        if valgrindLeakCheck:
            clangTestArgs += ' --vg-leak'
        clangTestArgs += ' --vg-arg --suppressions=%(builddir)s/llvm/tools/clang/utils/valgrind/x86_64-pc-linux-gnu_gcc-4.3.3.supp --vg-arg --suppressions=%(builddir)s/llvm/utils/valgrind/x86_64-pc-linux-gnu.supp'
    extraTestDirs = ''
    if run_cxx_tests:
        extraTestDirs += '%(builddir)s/llvm/tools/clang/utils/C++Tests'
    if test:
        f.addStep(ClangTestCommand(name='check-all',
                                   command=[make, "check-all", "VERBOSE=1",
                                            WithProperties("LIT_ARGS=%s" % llvmTestArgs)],
                                   description=["checking"],
                                   descriptionDone=["checked"],
                                   workdir=llvm_1_objdir,
                                   usePTY=use_pty_in_tests,
                                   env=merged_env))

    # Install llvm and clang.
    if llvm_1_installdir:
        f.addStep(ShellCommand(name="rm-install.clang.stage1",
                               command=["rm", "-rf", llvm_1_installdir],
                               haltOnFailure=True,
                               description=["rm install dir", "clang"],
                               workdir=".",
                               env=merged_env))
        f.addStep(WarningCountingShellCommand(name="install.clang.stage1",
                                              command = ['nice', '-n', '10',
                                                         make, 'install-clang'],
                                              haltOnFailure=True,
                                              description=["install", "clang",
                                                           stage1_config],
                                              workdir=llvm_1_objdir,
                                              env=merged_env))

    if run_gdb or run_gcc or run_modern_gdb:
        ignores = getClangTestsIgnoresFromPath(os.path.expanduser('~/public/clang-tests'), 'clang-x86_64-darwin10')
        install_prefix = "%%(builddir)s/%s" % llvm_1_installdir
        if run_gdb:
            addClangGDBTests(f, ignores, install_prefix)
        if run_modern_gdb:
            addModernClangGDBTests(f, jobs, install_prefix)
        if run_gcc:
            addClangGCCTests(f, ignores, install_prefix)

    if not useTwoStage:
        if package_dst:
            name = WithProperties(
                "%(builddir)s/" + llvm_1_objdir +
                "/clang-r%(got_revision)s-b%(buildnumber)s.tgz")
            f.addStep(ShellCommand(name='pkg.tar',
                                   description="tar root",
                                   command=["tar", "zcvf", name, "./"],
                                   workdir=llvm_1_installdir,
                                   warnOnFailure=True,
                                   flunkOnFailure=False,
                                   haltOnFailure=False,
                                   env=merged_env))
            f.addStep(ShellCommand(name='pkg.upload',
                                   description="upload root",
                                   command=["scp", name,
                                            WithProperties(
                            package_dst + "/%(buildername)s")],
                                   workdir=".",
                                   warnOnFailure=True,
                                   flunkOnFailure=False,
                                   haltOnFailure=False,
                                   env=merged_env))

        return f

    # Clean up llvm (stage 2).
    if clean:
        f.addStep(ShellCommand(name="rm-llvm.obj.stage2",
                               command=["rm", "-rf", llvm_2_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm", "(stage 2)"],
                               workdir=".",
                               env=merged_env))

    # Configure llvm (stage 2).
    args = base_configure_args + ["--without-llvmgcc", "--without-llvmgxx"]
    args.append(WithProperties("--prefix=%(builddir)s/" + llvm_2_installdir))
    args += getConfigArgs(stage2_config)
    local_env = dict(merged_env)
    local_env.update({
        'CC'  : WithProperties("%%(builddir)s/%s/bin/clang"   % llvm_1_installdir),
        'CXX' : WithProperties("%%(builddir)s/%s/bin/clang++" % llvm_1_installdir)})

    f.addStep(Configure(name="configure.llvm.stage2",
                        command=args,
                        haltOnFailure=True,
                        workdir=llvm_2_objdir,
                        description=["configure", "llvm", "(stage 2)",
                                     stage2_config],
                        env=local_env))

    # Build llvm (stage 2).
    f.addStep(WarningCountingShellCommand(name="compile.llvm.stage2",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling", "(stage 2)",
                                                       stage2_config],
                                          descriptionDone=["compile", "(stage 2)",
                                                           stage2_config],
                                          workdir=llvm_2_objdir,
                                          env=merged_env))

    if test:
        f.addStep(ClangTestCommand(name='check-all',
                                   command=[make, "check-all", "VERBOSE=1",
                                            WithProperties("LIT_ARGS=%s" % llvmTestArgs)],
                                   description=["checking"],
                                   descriptionDone=["checked"],
                                   workdir=llvm_2_objdir,
                                   usePTY=use_pty_in_tests,
                                   env=merged_env))

    # Install clang (stage 2).
    f.addStep(ShellCommand(name="rm-install.clang.stage2",
                           command=["rm", "-rf", llvm_2_installdir],
                           haltOnFailure=True,
                           description=["rm install dir", "clang"],
                           workdir=".",
                           env=merged_env))
    f.addStep(WarningCountingShellCommand(name="install.clang.stage2",
                                          command = ['nice', '-n', '10',
                                                     make, 'install-clang'],
                                          haltOnFailure=True,
                                          description=["install", "clang",
                                                       "(stage 2)"],
                                          workdir=llvm_2_objdir,
                                          env=merged_env))

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
                               haltOnFailure=False,
                               env=merged_env))
        f.addStep(ShellCommand(name='pkg.upload',
                               description="upload root",
                               command=["scp", name,
                                        WithProperties(
                        package_dst + "/%(buildername)s")],
                               workdir=".",
                               warnOnFailure=True,
                               flunkOnFailure=False,
                               haltOnFailure=False,
                               env=merged_env))

    return f

def getClangMSVCBuildFactory(update=True, clean=True, vcDrive='c', jobs=1, cmake=r"cmake"):
    f = buildbot.process.factory.BuildFactory()

    if update:
        f.addStep(SVN(name='svn-llvm',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                      defaultBranch='trunk',
                      workdir='llvm'))
        f.addStep(SVN(name='svn-clang',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                      defaultBranch='trunk',
                      workdir='llvm/tools/clang'))
        f.addStep(SVN(name='svn-clang-tools-extra',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/clang-tools-extra/',
                      defaultBranch='trunk',
                      workdir='llvm/tools/clang/tools/extra'))

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
                                         "-DLLVM_INCLUDE_EXAMPLES:=OFF",
                                         "-DLLVM_INCLUDE_TESTS:=OFF",
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

# Builds on Windows using CMake, MinGW(32|64), and no Microsoft tools.
def getClangMinGWBuildFactory(update=True, clean=True, jobs=6, cmake=r"cmake"):
    f = buildbot.process.factory.BuildFactory()

    if update:
        f.addStep(SVN(name='svn-llvm',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                      defaultBranch='trunk',
                      workdir='llvm'))
        f.addStep(SVN(name='svn-clang',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                      defaultBranch='trunk',
                      workdir='llvm/tools/clang'))
        f.addStep(SVN(name='svn-clang-tools-extra',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/clang-tools-extra/',
                      defaultBranch='trunk',
                      workdir='llvm/tools/clang/tools/extra'))

    # Full & fast clean.
    if clean:
        # note: This command is redundant as the next command removes everything
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

    # Create the Makefiles.

    # Use batch files instead of ShellCommand directly, Windows quoting is
    # borked. FIXME: See buildbot ticket #595 and buildbot ticket #377.
    f.addStep(BatchFileDownload(name='cmakegen',
                                command=[cmake,
                                         "-DLLVM_TARGETS_TO_BUILD:=X86",
                                         "-DLLVM_INCLUDE_EXAMPLES:=OFF",
                                         "-DLLVM_INCLUDE_TESTS:=OFF",
                                         "-DLLVM_TARGETS_TO_BUILD:=X86",
                                         "-G",
                                         "Ninja",
                                         ".."],
                                workdir="llvm\\build"))
    f.addStep(ShellCommand(name='cmake',
                           command=['cmakegen.bat'],
                           haltOnFailure=True,
                           description='cmake gen',
                           workdir='llvm\\build'))

    # Build it.
    f.addStep(BatchFileDownload(name='makeall',
                                command=["ninja", "-j", "%d" % jobs],
                                haltOnFailure=True,
                                workdir='llvm\\build'))

    f.addStep(WarningCountingShellCommand(name='makeall',
                                          command=['makeall.bat'],
                                          haltOnFailure=True,
                                          description='makeall',
                                          workdir='llvm\\build'))

    # Build global check project (make check) (sources not checked out...).
    if 0:
        f.addStep(BatchFileDownload(name='makecheck',
                                    command=["ninja", "check"],
                                    workdir='llvm\\build'))
        f.addStep(WarningCountingShellCommand(name='check',
                                              command=['makecheck.bat'],
                                              description='make check',
                                              workdir='llvm\\build'))

    # Build clang-test project (make clang-test).
    f.addStep(BatchFileDownload(name='maketest',
                                command=["ninja", "clang-test"],
                                workdir="llvm\\build"))
    f.addStep(ClangTestCommand(name='clang-test',
                               command=["maketest.bat"],
                               workdir="llvm\\build"))

    return f

def addClangGCCTests(f, ignores={}, install_prefix="%(builddir)s/llvm.install",
                     languages = ('gcc', 'g++', 'objc', 'obj-c++')):
    make_vars = [WithProperties(
            'CC_UNDER_TEST=%s/bin/clang' % install_prefix),
                 WithProperties(
            'CXX_UNDER_TEST=%s/bin/clang++' % install_prefix)]
    f.addStep(SVN(name='svn-clang-tests', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/clang-tests/',
                  defaultBranch='trunk', workdir='clang-tests'))
    gcc_dg_ignores = ignores.get('gcc-4_2-testsuite', {})
    for lang in languages:
        f.addStep(DejaGNUCommand.DejaGNUCommand(
            name='test-gcc-4_2-testsuite-%s' % lang,
            command=["make", "-k", "check-%s" % lang] + make_vars,
            description="gcc-4_2-testsuite (%s)" % lang,
            workdir='clang-tests/gcc-4_2-testsuite',
            logfiles={ 'dg.sum' : 'obj/%s/%s.sum' % (lang, lang),
                       '%s.log' % lang : 'obj/%s/%s.log' % (lang, lang)},
            ignore=gcc_dg_ignores.get(lang, [])))

def addClangGDBTests(f, ignores={}, install_prefix="%(builddir)s/llvm.install"):
    make_vars = [WithProperties(
            'CC_UNDER_TEST=%s/bin/clang' % install_prefix),
                 WithProperties(
            'CXX_UNDER_TEST=%s/bin/clang++' % install_prefix)]
    f.addStep(SVN(name='svn-clang-tests', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/clang-tests/',
                  defaultBranch='trunk', workdir='clang-tests'))
    f.addStep(DejaGNUCommand.DejaGNUCommand(
            name='test-gdb-1472-testsuite',
            command=["make", "-k", "check"] + make_vars,
            description="gdb-1472-testsuite",
            workdir='clang-tests/gdb-1472-testsuite',
            logfiles={ 'dg.sum' : 'obj/filtered.gdb.sum',
                       'gdb.log' : 'obj/gdb.log' }))

def addModernClangGDBTests(f, jobs, install_prefix):
    make_vars = [WithProperties('RUNTESTFLAGS=CC_FOR_TARGET="{0}/bin/clang" CXX_FOR_TARGET="{0}/bin/clang++" CFLAGS_FOR_TARGET="-w"'.format(install_prefix)),
                 "FORCE_PARALLEL=1"]
    f.addStep(SVN(name='svn-clang-tests', mode='update',
                  svnurl='http://llvm.org/svn/llvm-project/clang-tests-external/trunk/gdb/7.5',
                  workdir='clang-tests/src'))
    f.addStep(Configure(command='../src/gdb/testsuite/configure',
                        workdir='clang-tests/build/'))
    f.addStep(DejaGNUCommand.DejaGNUCommand(
            name='gdb-75-check',
            command=["make", "-k", WithProperties("-j%s" % jobs), "check"] + make_vars,
            env={'PATH': os.pathsep.join(['${HOME}/gdb-install/bin', '${PATH}'])},
            workdir='clang-tests/build',
            logfiles={'dg.sum':'gdb.sum', 
                      'gdb.log':'gdb.log'}))



# FIXME: Deprecated.
addClangTests = addClangGCCTests

def getClangTestsIgnoresFromPath(path, key):
    def readList(path):
        if not os.path.exists(path):
            return []

        f = open(path)
        lines = [ln.strip() for ln in f]
        f.close()
        return lines

    ignores = {}

    gcc_dg_ignores = {}
    for lang in ('gcc', 'g++', 'objc', 'obj-c++'):
        lang_path = os.path.join(path, 'gcc-4_2-testsuite', 'expected_results',
                                 key, lang)
        gcc_dg_ignores[lang] = (
            readList(os.path.join(lang_path, 'FAIL.txt')) +
            readList(os.path.join(lang_path, 'UNRESOLVED.txt')) +
            readList(os.path.join(lang_path, 'XPASS.txt')))
    ignores['gcc-4_2-testsuite' ] = gcc_dg_ignores

    ignores_path = os.path.join(path, 'gdb-1472-testsuite', 'expected_results',
                                key)
    gdb_dg_ignores = (
        readList(os.path.join(ignores_path, 'FAIL.txt')) +
        readList(os.path.join(ignores_path, 'UNRESOLVED.txt')) +
        readList(os.path.join(ignores_path, 'XPASS.txt')))
    ignores['gdb-1472-testsuite' ] = gdb_dg_ignores

    return ignores
