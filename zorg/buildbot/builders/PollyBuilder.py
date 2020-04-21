from buildbot.steps.shell import Configure, ShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.builders import LNTBuilder
from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.process.factory import LLVMBuildFactory

def getPollyBuildFactory(
    clean=False,
    install=False,
    make='make',
    jobs=None,
    checkAll=False,
    env=None,
    extraCmakeArgs=None,
    **kwargs):

    if extraCmakeArgs is None:
        extraCmakeArgs=[],
    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"
    llvm_instdir = "llvm.inst"
    jobs_cmd = []
    if jobs is not None:
        jobs_cmd = ["-j"+str(jobs)]
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

    cleanBuildRequestedByProperty = lambda step: step.build.getProperty("clean", False)
    cleanBuildRequested = lambda step: clean or step.build.getProperty("clean", default=step.build.getProperty("clean_obj"))

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=llvm_objdir,
            install_dir=llvm_instdir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    f.addStep(ShellCommand(name='clean-src-dir',
                           command=['rm', '-rf', f.monorepo_dir],
                           warnOnFailure=True,
                           description=["clean src dir"],
                           workdir='.',
                           env=merged_env,
                           doStepIf=cleanBuildRequestedByProperty))

    # Get the source code.
    f.addGetSourcecodeSteps(**kwargs)

    # Clean build dir
    f.addStep(ShellCommand(name='clean-build-dir',
                           command=['rm', '-rf', llvm_objdir],
                           warnOnFailure=True,
                           description=["clean build dir"],
                           workdir='.',
                           env=merged_env,
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
    f.addStep(ShellCommand(name="build",
                           command=build_cmd,
                           haltOnFailure=True,
                           description=["build"],
                           workdir=llvm_objdir,
                           env=merged_env))

    # Clean install dir
    if install:
        f.addStep(ShellCommand(name='clean-install-dir',
                               command=['rm', '-rf', llvm_instdir],
                               haltOnFailure=False,
                               description=["clean install dir"],
                               workdir='.',
                               env=merged_env,
                               doStepIf=cleanBuildRequested))

        f.addStep(ShellCommand(name="install",
                               command=install_cmd,
                               haltOnFailure=False,
                               description=["install"],
                               workdir=llvm_objdir,
                               env=merged_env))

    # Test
    if checkAll:
        f.addStep(ShellCommand(name="check_all",
                               command=check_all_cmd,
                               haltOnFailure=False,
                               description=["check all"],
                               workdir=llvm_objdir,
                               env=merged_env))
    else:
        f.addStep(ShellCommand(name="check_polly",
                               command=check_polly_cmd,
                               haltOnFailure=False,
                               description=["check polly"],
                               workdir=llvm_objdir,
                               env=merged_env))

    return f
