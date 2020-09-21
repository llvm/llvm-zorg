from buildbot.steps.shell import SetProperty
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.steps.slave import RemoveDirectory
from buildbot.process.properties import WithProperties, Property

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.builders.Util import getVisualStudioEnvironment
from zorg.buildbot.builders.Util import extractSlaveEnvironment
from zorg.buildbot.process.factory import LLVMBuildFactory

# CMake builds
def getLLDBCMakeBuildFactory(
            clean=False,
            jobs="%(jobs)s",

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

    # Determine Slave Environment and Set MSVC environment.
    if vs:
        f.addStep(SetProperty(
            command=getVisualStudioEnvironment(vs, target_arch),
            extract_fn=extractSlaveEnvironment))

    f.addGetSourcecodeSteps()

    build_cmd=['ninja']
    install_cmd = ['ninja','install']
    test_cmd = ['ninja','check-lldb']

    if jobs:
        build_cmd.append(WithProperties("-j%s" % jobs))
        install_cmd.append(WithProperties("-j%s" % jobs))
        test_cmd.append(WithProperties("-j%s" % jobs))

    ############# CLEANING
    cleanBuildRequested = lambda step: clean or step.build.getProperty("clean", default=step.build.getProperty("clean_obj"))
    f.addStep(RemoveDirectory(name='clean '+build_dir,
                dir=build_dir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    rel_src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, f.obj_dir)
    cmake_options = [
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=" + config,
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
                           env=Property('slave_env'),
                           workdir=build_dir))

    f.addStep(WarningCountingShellCommand(name='build',
                          command=build_cmd,
                          haltOnFailure=True,
                          description='ninja build',
                          workdir=build_dir,
                          env=Property('slave_env')))

    ignoreInstallFail = bool(install != 'ignoreFail')
    f.addStep(ShellCommand(name='install',
                          command=install_cmd,
                          flunkOnFailure=ignoreInstallFail,
                          description='ninja install',
                          workdir=build_dir,
                          doStepIf=bool(install),
                          env=Property('slave_env')))

    ignoreTestFail = bool(test != 'ignoreFail')
    f.addStep(ShellCommand(name='test',
                          command=test_cmd,
                          flunkOnFailure=ignoreTestFail,
                          timeout=testTimeout,
                          description='ninja test',
                          workdir=build_dir,
                          doStepIf=bool(test),
                          env=Property('slave_env')))

    return f
