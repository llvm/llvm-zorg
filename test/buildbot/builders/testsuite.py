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

assert factory_has_num_steps(f, 5)
assert factory_has_step(f, "clean-src-dir")
assert factory_has_step(f, "cmake-configure")
assert factory_has_step(f, "build-default")
assert not factory_has_step(f, "rsync-default")
assert factory_has_step(f, "test-check")


print(f"default factory: {f}\n")

f = TestSuiteBuilder.getLlvmTestSuiteSteps(
        cmake_definitions = {
            "TEST_SUITE_REMOTE_HOST"    : "buildbot@arm64-linux-02",
            "TEST_SUITE_LIT_FLAGS"      : "-v --threads=32 --time-tests",
        },
        compiler_dir = util.Interpolate("%(prop:builddir)s/build"),
        hint = None,
    )
    
print(f"default factory (compiler_dir): {f}\n")

assert factory_has_num_steps(f, 6)
assert factory_has_step(f, "clean-src-dir")
assert factory_has_step(f, "cmake-configure")
assert factory_has_step(f, "build-default")
assert factory_has_step(f, "rsync-default")
assert factory_has_step(f, "test-check")
