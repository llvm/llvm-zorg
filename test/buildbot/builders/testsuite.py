# RUN: python %s

# Lit Regression Tests for TestSuiteBuilder.getTestSuiteBuildFactory factory.

import sys

from buildbot.plugins import steps, util
import buildbot.process.properties

import zorg
from zorg.buildbot.builders import TestSuiteBuilder
from zorg.buildbot.process.factory import LLVMBuildFactory

from zorg.buildbot.tests import factory_has_num_steps, factory_has_step, DEFAULT_ENV

f = TestSuiteBuilder.getLlvmTestSuiteSteps(
        cmake_definitions = {
            "CMAKE_C_COMPILER"          : "/home/buildbot/worker/temp/build/bin/clang",
            "CMAKE_CXX_COMPILER"        : "/home/buildbot/worker/temp/build/bin/clang++",
            "TEST_SUITE_LIT:FILEPATH"   : "/home/buildbot/worker/temp/build/bin/llvm-lit",
        },
        hint = None,
    )

print(f"default factory: {f}\n")

assert factory_has_num_steps(f, 6)
assert factory_has_step(f, "clean-src-dir")
assert factory_has_step(f, "set-props")
assert factory_has_step(f, "cmake-configure")
assert factory_has_step(f, "build-default")
assert not factory_has_step(f, "rsync-default")
assert factory_has_step(f, "test-check")

compiler_flags_ = "-march=armv8l+pauth -mbranch-protection=pac-ret -O2"
linker_flags_ = "-O2 -Wl,--emit-relocs"

f = TestSuiteBuilder.getLlvmTestSuiteSteps(
        cmake_definitions = {
            "TEST_SUITE_REMOTE_HOST"    : "buildbot@arm64-linux-02",
            "TEST_SUITE_LIT_FLAGS"      : "-v --threads=32 --time-tests",
            "CMAKE_CXX_FLAGS"           : "-O0",
            "CMAKE_EXE_LINKER_FLAGS"    : "-O0",
        },
        compiler_dir = util.Interpolate("%(prop:builddir)s/build"),
        compiler_flags = compiler_flags_,
        linker_flags = linker_flags_,
        hint = None,
    )
    
print(f"default factory (compiler_dir): {f}\n")

assert factory_has_num_steps(f, 7)
assert factory_has_step(f, "clean-src-dir")
assert factory_has_step(f, "set-props")
assert factory_has_step(f, "cmake-configure")
assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
                                                                        "CMAKE_C_FLAGS"             : compiler_flags_,
                                                                        "CMAKE_CXX_FLAGS"           : f"-O0 {compiler_flags_}",
                                                                        "CMAKE_EXE_LINKER_FLAGS"    : f"-O0 {linker_flags_}",
                                                                        "CMAKE_MODULE_LINKER_FLAGS" : linker_flags_,
                                                                        "CMAKE_SHARED_LINKER_FLAGS" : linker_flags_,
                                                                    })
assert factory_has_step(f, "build-default")
assert factory_has_step(f, "rsync-default")
assert factory_has_step(f, "test-check")
