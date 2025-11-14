# RUN: python %s

# Lit Regression Tests for UnifiedTreeBuilder.getCmakeExBuildFactory factory.
#
# Local check cmd: lit -v test/buildbot

import sys

from buildbot.plugins import steps, util

import zorg
from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.process.factory import LLVMBuildFactory

from zorg.buildbot.tests import factory_has_num_steps, factory_has_step, DEFAULT_ENV

# Use all defaults.
f = UnifiedTreeBuilder.getCmakeExBuildFactory()
print(f"default factory: {f}\n")

assert len(f.depends_on_projects) == 1
assert "llvm" in f.depends_on_projects
assert len(f.enable_runtimes) == 0
assert len(f.enable_projects) == 1
assert "llvm" in f.enable_projects
assert f.monorepo_dir == "llvm-project"
assert f.src_to_build_dir == "llvm"
assert f.obj_dir == "build"
assert f.install_dir is None
assert f.llvm_srcdir == "llvm-project/llvm"
assert f.repourl_prefix == "https://github.com/llvm/"

assert factory_has_num_steps(f, 7)
assert factory_has_step(f, "set-props")
assert factory_has_step(f, "clean-src-dir")
assert factory_has_step(f, "clean-obj-dir")
assert factory_has_step(f, "checkout")

assert factory_has_step(f, "cmake-configure")
assert factory_has_step(f, "cmake-configure", hasarg = "generator", contains = "Ninja")
assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'      : 'llvm',
                                                                        'CMAKE_BUILD_TYPE'          : 'Release',
                                                                        'LLVM_ENABLE_ASSERTIONS'    : 'ON',
                                                                        'LLVM_LIT_ARGS'             : '-v --time-tests'
                                                                    })
assert factory_has_step(f, "cmake-configure", hasarg = "options", contains = {})
assert factory_has_step(f, "cmake-configure", hasarg = "env", contains = DEFAULT_ENV)

assert factory_has_step(f, "build-default")
assert factory_has_step(f, "build-default", hasarg = 'options', contains = ['--build', '.'])
assert factory_has_step(f, "build-default", hasarg = "env", contains = DEFAULT_ENV)
assert factory_has_step(f, "test-check-all")
assert factory_has_step(f, "test-check-all", hasarg = "env", contains = DEFAULT_ENV)

# Change argument dirs
f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        llvm_srcdir = "my-llvm-project",
        src_to_build_dir = "llvmex",
        obj_dir = "obj.build",
    )
print(f"Updated some arg dirs: {f}\n")

assert f.monorepo_dir == "my-llvm-project"
assert f.src_to_build_dir == "llvmex"
assert f.obj_dir == "obj.build"
assert f.install_dir is None
assert f.llvm_srcdir == "my-llvm-project/llvmex"

assert factory_has_num_steps(f, 7)

assert factory_has_step(f, "cmake-configure", hasarg = "path", contains = "../my-llvm-project/llvmex")
assert factory_has_step(f, "cmake-configure", hasarg = "workdir", contains = "obj.build")

# Check depends_on_projects/enable_runtimes
f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        depends_on_projects = ["llvm", "clang"],
        #enable_runtimes = "auto",
    )
print(f"Check depended projects (1): {f}\n")

assert len(f.depends_on_projects) == 2
assert "llvm" in f.depends_on_projects
assert "clang" in f.depends_on_projects
assert len(f.enable_runtimes) == 0
assert len(f.enable_projects) == 2
assert "llvm" in f.enable_projects
assert "clang" in f.enable_projects

assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'      : 'clang;llvm',
                                                                    })

f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        depends_on_projects = ["llvm", "clang", "compiler-rt", "libcxx"],
        #enable_runtimes = "auto",
    )
print(f"Check depended projects (2): {f}\n")

assert len(f.depends_on_projects) == 4
assert "llvm" in f.depends_on_projects
assert "clang" in f.depends_on_projects
assert "compiler-rt" in f.depends_on_projects
assert "libcxx" in f.depends_on_projects
assert len(f.enable_runtimes) == 2
assert len(f.enable_projects) == 2
assert "llvm" in f.enable_projects
assert "clang" in f.enable_projects
assert "compiler-rt" in f.enable_runtimes
assert "libcxx" in f.enable_runtimes

assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'      : 'clang;llvm',
                                                                        'LLVM_ENABLE_RUNTIMES'      : 'compiler-rt;libcxx',
                                                                    })

# With installation prefix and custom build/test targets
EXPECTED_ENV = {'TERM': 'vt100', 'HOST_ID': 'DEMO11', 'NINJA_STATUS': '%e [%u/%r/%f] '}

f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        install_dir = "install-staged",
        targets = ["clang", "flang", "libunwind"],
        checks = ["check-clang", "check-flang"],
        checks_on_target = [
            ("libunwind",
                ["python", "bin/llvm-lit.py", "-v", "--time-tests", "--threads=32",
                    "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libunwind/test"]
            ),
        ],
        env = {'TERM': 'vt100', 'HOST_ID': 'DEMO11'},
    )
print(f"factory with install prefix: {f}\n")

assert f.install_dir == "install-staged"

assert factory_has_num_steps(f, 13)
assert factory_has_step(f, "set-props")
assert factory_has_step(f, "clean-src-dir")
assert factory_has_step(f, "clean-obj-dir")
assert factory_has_step(f, "checkout")

assert factory_has_step(f, "clean-install-dir")
assert factory_has_step(f, "cmake-configure")
assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'      : 'llvm',
                                                                        'CMAKE_BUILD_TYPE'          : 'Release',
                                                                        'LLVM_ENABLE_ASSERTIONS'    : 'ON',
                                                                        'LLVM_LIT_ARGS'             : '-v --time-tests',
                                                                        'CMAKE_INSTALL_PREFIX'      : '../install-staged',
                                                                    })
assert factory_has_step(f, "cmake-configure", hasarg = "options", contains = {})
assert factory_has_step(f, "build-clang")
assert factory_has_step(f, "build-clang", hasarg = 'options', contains = ['--build', '.', '--target', 'clang'])
assert factory_has_step(f, "build-clang", hasarg = "env", contains = EXPECTED_ENV)
assert factory_has_step(f, "build-flang")
assert factory_has_step(f, "build-flang", hasarg = 'options', contains = ['--build', '.', '--target', 'flang'])
assert factory_has_step(f, "build-flang", hasarg = "env", contains = EXPECTED_ENV)
assert factory_has_step(f, "build-libunwind")
assert factory_has_step(f, "build-libunwind", hasarg = 'options', contains = ['--build', '.', '--target', 'libunwind'])
assert factory_has_step(f, "build-libunwind", hasarg = "env", contains = EXPECTED_ENV)
assert factory_has_step(f, "test-check-clang")
assert factory_has_step(f, "test-check-clang", hasarg = 'command', contains = ['--build', '.', '--target', 'check-clang'])
assert factory_has_step(f, "test-check-clang", hasarg = "env", contains = EXPECTED_ENV)
assert factory_has_step(f, "test-check-flang")
assert factory_has_step(f, "test-check-flang", hasarg = 'command', contains = ['--build', '.', '--target', 'check-flang'])
assert factory_has_step(f, "test-check-flang", hasarg = "env", contains = EXPECTED_ENV)
assert factory_has_step(f, "test-libunwind")
assert factory_has_step(f, "test-libunwind", hasarg = 'command')
assert factory_has_step(f, "test-libunwind", hasarg = "env", contains = EXPECTED_ENV)
#TODO: Transforom rendering is currently unsupported to check the step name.
#assert factory_has_step(f, "install")

# Specify Visual Studio configuration.
f = UnifiedTreeBuilder.getCmakeExBuildFactory(vs = "autodetect")
print(f"factory with VS environment autodetect: {f}\n")

assert factory_has_num_steps(f, 8)
assert factory_has_step(f, "set-props.vs_env")

f = UnifiedTreeBuilder.getCmakeExBuildFactory(vs = "manual", vs_arch = "amd64")
print(f"factory with VS environment manual: {f}\n")

assert factory_has_num_steps(f, 8)
assert factory_has_step(f, "set-props.vs_env")

# Check custom CMake generator
f = UnifiedTreeBuilder.getCmakeExBuildFactory(generator = "Unix Makefiles")
print(f"factory with CMake generator: {f}\n")

assert factory_has_step(f, "cmake-configure", hasarg = "generator", contains = "Unix Makefiles")

# Check custom CMake definitions and options.
f = UnifiedTreeBuilder.getCmakeExBuildFactory(allow_cmake_defaults = False)
print(f"No CMake defaults: {f}\n")

assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'          : 'llvm',
                                                                    })

f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        cmake_definitions = {
            # Override defaults.
            'CMAKE_BUILD_TYPE'              : 'Debug',
            # Custom extra definitions.
            'LLVM_TARGETS_TO_BUILD'         : 'all',
            'CMAKE_EXPORT_COMPILE_COMMANDS' : '1',

        },
        cmake_options = [
            "-C", "%(prop:srcdir_relative)s/clang/cmake/caches/CrossWinToARMLinux.cmake"
        ],
        allow_cmake_defaults = True
    )
print(f"Custom CMake definitions/options (1): {f}\n")

assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'          : 'llvm',
                                                                        'CMAKE_BUILD_TYPE'              : 'Debug',
                                                                        'LLVM_ENABLE_ASSERTIONS'        : 'ON',
                                                                        'LLVM_LIT_ARGS'                 : '-v --time-tests',
                                                                        # Custom extra definitions.
                                                                        'LLVM_TARGETS_TO_BUILD'         : 'all',
                                                                        'CMAKE_EXPORT_COMPILE_COMMANDS' : '1',
                                                                    })
assert factory_has_step(f, "cmake-configure", hasarg = "options", contains = [
                                                                        "-C", "%(prop:srcdir_relative)s/clang/cmake/caches/CrossWinToARMLinux.cmake"
                                                                    ])
# without defaults  (allow_cmake_defaults = False)
f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        cmake_definitions = {
            'CMAKE_BUILD_TYPE'              : 'Debug',
            'LLVM_TARGETS_TO_BUILD'         : 'all',
            'CMAKE_EXPORT_COMPILE_COMMANDS' : '1',

        },
        allow_cmake_defaults = False
    )
print(f"Custom CMake definitions/options (1): {f}\n")

assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        'LLVM_ENABLE_PROJECTS'          : 'llvm',
                                                                        'CMAKE_BUILD_TYPE'              : 'Debug',
                                                                        'LLVM_TARGETS_TO_BUILD'         : 'all',
                                                                        'CMAKE_EXPORT_COMPILE_COMMANDS' : '1',
                                                                    })

# Check the step extensions.

cbf = LLVMBuildFactory()
cbf.addStep(
    steps.SetProperty(
        name = "pre_configure_step",
        property = "SomeProperty",
        value = "SomeValue"
    )
)

f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        # Force adding a default installation target step.
        install_dir = "install-staged",
        pre_configure_steps = cbf,    # Single step within the build factory
        post_build_steps = [
            steps.SetProperty(
                name = "post_build_step1",
                property = "SomeProperty",
                value = "SomeValue"
            ),
            steps.ShellCommand(
                name = "post_build_step2",
                command = ["ls"],
            ),
        ],
        pre_install_steps = [
            steps.SetProperty(
                name = "pre_install_step",
                property = "SomeProperty",
                value = "SomeValue"
            ),
        ],
        post_finalize_steps =[
            steps.SetProperty(
                name = "post_finalize_step",
                property = "SomeProperty",
                value = "SomeValue"
            ),
        ],
    )
print(f"Step Extendions: {f}")

assert factory_has_num_steps(f, 9 + 5)

assert factory_has_step(f, "pre_configure_step", hasarg = "property", contains = "SomeProperty")
assert factory_has_step(f, "post_build_step1", hasarg = "property", contains = "SomeProperty")
assert factory_has_step(f, "post_build_step2", hasarg = "command", contains = ["ls"])
assert factory_has_step(f, "pre_install_step", hasarg = "property", contains = "SomeProperty")
assert factory_has_step(f, "post_finalize_step", hasarg = "property", contains = "SomeProperty")


# Hint
f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        hint = "stage-hint"
    )
print(f"Hint option: {f}\n")

assert factory_has_step(f, "cmake-configure-stage-hint")
assert factory_has_step(f, "build-default-stage-hint")

# user proprs
f = UnifiedTreeBuilder.getCmakeExBuildFactory(
        user_props = {
            "user-prop1" : "myprop",
            "user-prop2" : util.Property("srcdir"),
            "user-prop3" : util.Interpolate("%(prop:srcdir)s"),
        }
    )
print(f"User-prop option: {f}\n")
assert factory_has_step(f, "set-user-props")
