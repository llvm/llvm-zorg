from buildbot.steps.shell import SetProperty
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.process.properties import WithProperties, Property
from buildbot.plugins import steps

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.builders.Util import getVisualStudioEnvironment
from zorg.buildbot.builders.Util import extractVSEnvironment
from zorg.buildbot.process.factory import LLVMBuildFactory

# CMake builds
def getLLDBCMakeBuildFactory(
            clean=False,

            # Source directory containing a built python
            python_source_dir=None,

            # Default values for VS devenv and build configuration
            vs=None,
            config='Release',
            target_arch='x86',

            extra_cmake_args=None,
            test=False,
            testTimeout=2400,
            install=False):

    ############# PREPARING

    # Global configurations
    build_dir='build'

    f = LLVMBuildFactory(
            depends_on_projects=["llvm", "clang", "lldb", "lld"],
            obj_dir=build_dir)

    env = {}
    if vs and vs != 'manual':
        f.addStep(SetProperty(
            command=getVisualStudioEnvironment(vs, target_arch),
            extract_fn=extractVSEnvironment))
        env = Property('vs_env')

    f.addGetSourcecodeSteps()

    ############# CLEANING
    cleanBuildRequested = lambda step: clean or step.build.getProperty("clean", default=step.build.getProperty("clean_obj"))
    f.addStep(steps.RemoveDirectory(name='clean '+build_dir,
                dir=build_dir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    rel_src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, f.obj_dir)
    cmake_options = [
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=" + config,
        "-DLLVM_LIT_ARGS=-v",
        "-DCMAKE_INSTALL_PREFIX=../install",
        "-DLLVM_ENABLE_PROJECTS=%s" % ";".join(f.depends_on_projects),
        ]
    if python_source_dir:
        cmake_options.append("-DPYTHON_HOME=" + python_source_dir)
    if extra_cmake_args:
        cmake_options += extra_cmake_args

    f.addStep(CmakeCommand(name="cmake-configure",
                           description=["cmake configure"],
                           haltOnFailure=True,
                           options=cmake_options,
                           path=rel_src_dir,
                           env=env,
                           workdir=build_dir))

    f.addStep(NinjaCommand(name='build',
                          haltOnFailure=True,
                          description='ninja build',
                          workdir=build_dir,
                          env=env))

    ignoreInstallFail = bool(install != 'ignoreFail')
    f.addStep(NinjaCommand(targets=['install'],
                          name='install',
                          flunkOnFailure=ignoreInstallFail,
                          description='ninja install',
                          workdir=build_dir,
                          doStepIf=bool(install),
                          env=env))

    ignoreTestFail = bool(test != 'ignoreFail')
    f.addStep(NinjaCommand(targets=['check-lldb'],
                          name='test',
                          flunkOnFailure=ignoreTestFail,
                          timeout=testTimeout,
                          description='ninja check-lldb',
                          workdir=build_dir,
                          doStepIf=bool(test),
                          env=env))

    return f
