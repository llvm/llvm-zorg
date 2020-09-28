from buildbot.process.properties import WithProperties
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.plugins import steps
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.process.factory import LLVMBuildFactory

def getPollyBuildFactory(
    clean=False,
    install=False,
    make='make',
    jobs=None,
    checkAll=False,
    env=None,
    extraCmakeArgs=None,
    testsuite=False,extraTestsuiteCmakeArgs=None,
    **kwargs):

    if extraCmakeArgs is None:
        extraCmakeArgs=[]
    if extraTestsuiteCmakeArgs is None:
        extraTestsuiteCmakeArgs = []

    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"
    llvm_instdir = "llvm.inst"
    testsuite_srcdir = "test-suite.src"
    testsuite_builddir = "test-suite.build"

    jobs_cmd = []
    if jobs is not None:
        jobs_cmd = ["-j{}".format(jobs)]
    build_cmd = [make] + jobs_cmd
    install_cmd = [make, 'install'] + jobs_cmd
    check_all_cmd = [make, 'check-all'] + jobs_cmd
    check_polly_cmd = [make, 'check-polly'] + jobs_cmd
    cmake_install = []
    if install:
        cmake_install = ["-DCMAKE_INSTALL_PREFIX=../%s" % llvm_instdir]
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
                 }
    if env:
        merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

    depends_on_projects = ['llvm','clang','polly']
    if testsuite:
        # XRay tests in test-suite require compiler-rt
        depends_on_projects += ['compiler-rt']

    cleanBuildRequestedByProperty = lambda step: step.build.getProperty("clean", False)
    cleanBuildRequested = lambda step: clean or step.build.getProperty("clean", default=step.build.getProperty("clean_obj"))

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=llvm_objdir,
            install_dir=llvm_instdir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    f.addStep(steps.RemoveDirectory(name='clean-src-dir',
                           dir=f.monorepo_dir,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequestedByProperty))

    # Get the source code.
    f.addGetSourcecodeSteps(**kwargs)

    # Clean build dir
    f.addStep(steps.RemoveDirectory(name='clean-build-dir',
                           dir=llvm_objdir,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequested))

    # Create configuration files with cmake
    cmakeCommand = ["cmake", "../%s/llvm" % llvm_srcdir,
                    "-DCMAKE_COLOR_MAKEFILE=OFF",
                    "-DPOLLY_TEST_DISABLE_BAR=ON",
                    "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DLLVM_POLLY_LINK_INTO_TOOLS=ON",
                    "-DLLVM_ENABLE_PROJECTS=%s" % ";".join(f.depends_on_projects),
                   ] + cmake_install + extraCmakeArgs
    f.addStep(ShellCommand(name="cmake-configure",
                           command=cmakeCommand,
                           haltOnFailure=False,
                           description=["cmake configure"],
                           workdir=llvm_objdir,
                           env=merged_env))

    # Build
    f.addStep(WarningCountingShellCommand(name="build",
                           command=build_cmd,
                           haltOnFailure=True,
                           description=["build"],
                           workdir=llvm_objdir,
                           env=merged_env))

    clangexe = "%(builddir)s/" + llvm_objdir + "/bin/clang"
    clangxxexe = "%(builddir)s/" + llvm_objdir + "/bin/clang++"
    litexe = "%(builddir)s/" + llvm_objdir + "/bin/llvm-lit"
    sizeexe = "%(builddir)s/" + llvm_objdir + "/bin/llvm-size"

    # Clean install dir
    if install:
        f.addStep(steps.RemoveDirectory(name='clean-install-dir',
                               dir=llvm_instdir,
                               haltOnFailure=False,
                               doStepIf=cleanBuildRequested))

        f.addStep(ShellCommand(name="install",
                               command=install_cmd,
                               haltOnFailure=True,
                               description=["install"],
                               workdir=llvm_objdir,
                               env=merged_env))

        # If installing, use the installed version of clang.
        clangexe = "%(builddir)s/" + llvm_instdir + "/bin/clang"
        clangxxexe = "%(builddir)s/" + llvm_instdir + "/bin/clang++"
        sizeexe = "%(builddir)s/" + llvm_instdir + "/bin/llvm-size"

    # Test
    if checkAll:
        f.addStep(LitTestCommand(name="check_all",
                               command=check_all_cmd,
                               haltOnFailure=False,
                               description=["check all"],
                               workdir=llvm_objdir,
                               env=merged_env))
    else:
        f.addStep(LitTestCommand(name="check_polly",
                               command=check_polly_cmd,
                               haltOnFailure=False,
                               description=["check polly"],
                               workdir=llvm_objdir,
                               env=merged_env))

    if testsuite:
        f.addStep(steps.RemoveDirectory(name='test-suite_clean-src-dir',
                           dir=testsuite_srcdir,
                           haltOnFailure=False,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequestedByProperty))

        f.addGetSourcecodeForProject(
            project='test-suite',
            src_dir=testsuite_srcdir,
            alwaysUseLatest=True)

        f.addStep(steps.RemoveDirectory(name='test-suite_clean-build-dir',
                           dir=testsuite_builddir,
                           haltOnFailure=False,
                           warnOnFailure=True))

        # -Wno-unused-command-line-argument is needed because linking will not uses the "-mllvm -polly" argument.
        f.addStep(ShellCommand(name='test-suite_cmake-configure',
                           description=["Test-Suite: cmake"],
                           command=["cmake", '-B', testsuite_builddir, '-S', testsuite_srcdir,
                                    "-DCMAKE_BUILD_TYPE=Release",
                                    "-DTEST_SUITE_COLLECT_STATS=ON",
                                    "-DTEST_SUITE_EXTRA_C_FLAGS=-Wno-unused-command-line-argument -mllvm -polly",
                                    "-DTEST_SUITE_EXTRA_CXX_FLAGS=-mllvm -polly",
                                    "-DTEST_SUITE_LIT_FLAGS=-vv;-o;report.json",
                                    WithProperties("-DCMAKE_C_COMPILER=" + clangexe),
                                    WithProperties("-DCMAKE_CXX_COMPILER=" + clangxxexe),
                                    WithProperties("-DTEST_SUITE_LLVM_SIZE=" + sizeexe),
                                    WithProperties("-DTEST_SUITE_LIT=" + litexe),
                                ] + extraTestsuiteCmakeArgs,
                           haltOnFailure=True,
                           workdir='.',
                           env=merged_env))

        f.addStep(WarningCountingShellCommand(name='test-suite_build',
                           description=["Test-Suite: build"],
                           # Continue building; programs that don't compile will fail with NOEXE.
                           command=[make, 'all', '-k0'] + jobs_cmd,
                           haltOnFailure=False,
                           flunkOnFailure=True,
                           workdir=testsuite_builddir,
                           env=merged_env))

        f.addStep(LitTestCommand(name='test-suite_run',
                            description=['Test-Suite: run'],
                            command=[WithProperties(litexe), '-vv', '-o', 'report.json', '.'],
                            haltOnFailure=True,
                            workdir=testsuite_builddir,
                            logfiles={
                                'test.log'   : 'test.log',
                                'report.json': 'report.json'
                                 },
                            env=merged_env))

    return f
