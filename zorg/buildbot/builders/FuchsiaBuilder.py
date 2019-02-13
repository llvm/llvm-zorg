import platform

from buildbot.process.properties import WithProperties
from buildbot.steps.shell import ShellCommand
from buildbot.steps.slave import RemoveDirectory
from buildbot.steps.source import SVN

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory, svn_repos

def getToolchainBuildFactory(
        clean=False,
        test=True,
        env=None, # Environmental variables for all steps.
        extra_configure_args=None):
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        "TERM" : "dumb", # Make sure Clang doesn't use color escape sequences.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    src_dir = "llvm.src"
    obj_dir = "llvm.obj"
    install_dir = "llvm.install"

    f = LLVMBuildFactory(
            depends_on_projects=[
                "llvm",
                "clang",
                "clang-tools-extra",
                "compiler-rt",
                "libcxx",
                "libcxxabi",
                "libunwind",
                "lld"
            ])

    # Get Fuchsia SDK.
    sdk_dir = "fuchsia.sdk"
    sdk_platform = {
        "Linux": "linux-amd64",
        "Darwin": "mac-amd64",
    }[platform.system()]
    sdk_version = "latest"

    sdk_url = WithProperties(
        "https://chrome-infra-packages.appspot.com/dl/"
        "fuchsia/sdk/%(sdk_platform)s/+/%(sdk_version)s",
        sdk_platform=lambda _: sdk_platform,
        sdk_version=lambda _: sdk_version)

    f.addStep(RemoveDirectory(name="clean-sdk",
                              dir=sdk_dir,
                              haltOnFailure=True))

    f.addStep(ShellCommand(name="fetch-sdk",
                           command=["curl", "-SLf", "-o", "sdk.cipd", sdk_url],
                           description=["download", "fuchsia sdk"],
                           workdir=sdk_dir))

    f.addStep(ShellCommand(name="extract-sdk",
                           command=["unzip", "-fo", "sdk.cipd"],
                           description=["extract", "fuchsia sdk"],
                           workdir=sdk_dir))

    cleanCheckoutRequested = lambda step: step.build.getProperty("clean", default=False) or clean

    # Clean up llvm sources.
    f.addStep(RemoveDirectory(name="clean-llvm.src",
                              dir=src_dir,
                              haltOnFailure=True,
                              doStepIf=cleanCheckoutRequested))

    # Get sources.
    for project in f.depends_on_projects:
        _, baseURL = svn_repos[project]
        f.addStep(SVN(name="svn-%s" % project,
                      workdir=src_dir + "/" + project,
                      baseURL=baseURL))

    cleanBuildRequested = lambda step: step.build.getProperty("clean", default=step.build.getProperty("clean_obj")) or clean

    # Clean up llvm build.
    f.addStep(RemoveDirectory(name="clean-llvm.obj",
                              dir=obj_dir,
                              haltOnFailure=True,
                              doStepIf=cleanBuildRequested))

    # Configure.
    if extra_configure_args is None:
        cmake_options = []
    else:
        cmake_options = extra_configure_args[:]

    # Some options are required for this stage no matter what.
    CmakeCommand.applyRequiredOptions(cmake_options, [
        ("-G",                      "Ninja"),
        ("-DLLVM_ENABLE_PROJECTS=", "clang;clang-tools-extra;lld"),
        ("-DLLVM_ENABLE_RUNTIMES=", "compiler-rt;libcxx;libcxxabi;libunwind"),
        ])

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_options, [
        ("-DBOOTSTRAP_LLVM_ENABLE_LTO=", "OFF"),
        ("-DLLVM_ENABLE_LTO=",           "OFF"),
        ])

    cmake_options.append(
        WithProperties(
            "-DCMAKE_INSTALL_PREFIX=%(workdir)s/" + install_dir
        ))
    cmake_options.append(
        WithProperties(
            "-DFUCHSIA_SDK=%(workdir)s/" + sdk_dir
        ))

    CmakeCommand.applyRequiredOptions(cmake_options, [
        ("-C", "../" + src_dir + "/clang/cmake/caches/Fuchsia.cmake"),
        ])

    f.addStep(CmakeCommand(name="cmake-configure",
                           options=cmake_options,
                           path='../' + src_dir + '/llvm',
                           haltOnFailure=True,
                           description=["configure"],
                           workdir=obj_dir,
                           env=merged_env,
                           doStepIf=FileDoesNotExist("CMakeCache.txt")))

    # Build distribution.
    f.addStep(NinjaCommand(name="ninja-build",
                           targets=["stage2-distribution"],
                           haltOnFailure=True,
                           description=["build"],
                           workdir=obj_dir,
                           env=merged_env))

    # Test llvm, clang and lld.
    f.addStep(NinjaCommand(name="check",
                           targets=["stage2-check-%s" % p for p in ("llvm", "clang", "lld")],
                           haltOnFailure=True,
                           description=["check"],
                           workdir=obj_dir,
                           env=merged_env,
                           doStepIf=test))

    # Install distribution.
    f.addStep(NinjaCommand(name="install",
                           targets=["stage2-install-distribution"],
                           haltOnFailure=True,
                           description=["install"],
                           workdir=obj_dir,
                           env=merged_env))

    return f
