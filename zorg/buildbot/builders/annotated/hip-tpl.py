#!/usr/bin/python3

import argparse
import os
import subprocess
import sys
import traceback
import util
import tempfile
from contextlib import contextmanager


def main(argv):
    source_dir = os.path.join("..", "llvm-project")
    test_suite_source_dir = os.path.join("/opt/botworker/llvm", "llvm-test-suite")
    test_suite_build_dir = "TS-build"

    offload_base_dir = os.path.join(source_dir, "offload")
    of_cmake_cache_base_dir = os.path.join(offload_base_dir, "cmake/caches")

    with step("clean build", halt_on_fail=True):
        # We have to "hard clean" the build directory, since we use a CMake cache
        # If we do not do this, the resident config will take precedence and changes
        # to the cache file are ignored.
        cwd = os.getcwd()
        tdir = tempfile.mkdtemp()
        os.chdir(tdir)
        util.clean_dir(cwd)
        os.chdir(cwd)
        util.rmtree(tdir)

    with step("cmake", halt_on_fail=True):
        # TODO make the name of the cache file an argument to the script.
        cmake_cache_file = os.path.join(of_cmake_cache_base_dir, "AMDGPUBot.cmake")

        # Use Ninja as the generator.
        # The other important settings alrady come from the CMake CMake
        # cache file inside LLVM
        cmake_args = ["-GNinja", "-C %s" % cmake_cache_file, "-DLLVM_ENABLE_RUNTIMES=compiler-rt"]

        run_command(["cmake", os.path.join(source_dir, "llvm")] + cmake_args)

    with step("build cmake config"):
        run_command(["ninja"])

    with step("update llvm-test-suite", halt_on_fail=True):
        # Hard-coded as assumed to run inside AMDGPU HIP Buildbot container
        if not os.path.isdir(test_suite_source_dir):
            raise RuntimeError("directory does not exist")

        # Change pwd, update the test suite repo and change dir back.
        old_cwd = os.getcwd()
        os.chdir(test_suite_source_dir)
        run_command(["git", "reset", "--hard", "origin/main"])
        run_command(["git", "pull"])
        os.chdir(old_cwd)

    with step("configure test suite", halt_on_fail=True):
        compiler_bin_base_path = os.getcwd()
        compiler_bin_path = os.path.join(compiler_bin_base_path, "bin/")
        clang_binary = os.path.join(compiler_bin_path, "clang")
        clangpp_binary = os.path.join(compiler_bin_path, "clang++")

        test_suite_cmake_args = ["-GNinja", "-B", test_suite_build_dir, "-S", "."]
        test_suite_cmake_args.append("-DTEST_SUITE_EXTERNALS_DIR=/opt/botworker/llvm/External")
        # XXX: Use some utility to determine arch?
        test_suite_cmake_args.append("-DAMDGPU_ARCHS=gfx90a")
        test_suite_cmake_args.append("-DTEST_SUITE_SUBDIRS=External")
        # Giving only this flag enables to pull the default Kokkos version.
        test_suite_cmake_args.append("-DEXTERNAL_HIP_TESTS_KOKKOS=ON")

        # Pick up compilers from build tree
        test_suite_cmake_args.append("-DCMAKE_CXX_COMPILER=%s" % clangpp_binary)
        test_suite_cmake_args.append("-DCMAKE_C_COMPILER=%s" % clang_binary)

        old_cwd = os.getcwd()
        os.chdir(test_suite_source_dir)
        if os.path.isdir(test_suite_build_dir):
            util.rmtree(test_suite_build_dir)

        cmake_command = ["cmake"]
        cmake_command.extend(test_suite_cmake_args)

        run_command(cmake_command)

        os.chdir(old_cwd)

    with step("build kokkos and test suite", halt_on_fail=True):
        old_cwd = os.getcwd()
        os.chdir(test_suite_source_dir)

        run_command(["cmake", "--build", test_suite_build_dir, "--parallel", "--target", "build-kokkos"])

        os.chdir(old_cwd)

    with step("run kokkos test suite", halt_on_fail=True):
        os.chdir(test_suite_source_dir)
        run_command(["cmake", "--build", test_suite_build_dir, "--target", "test-kokkos"])


@contextmanager
def step(step_name, halt_on_fail=False):
    util.report("@@@BUILD_STEP {}@@@".format(step_name))
    if halt_on_fail:
        util.report("@@@HALT_ON_FAILURE@@@")
    try:
        yield
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            util.report("{} exited with return code {}.".format(e.cmd, e.returncode))
        util.report("The build step threw an exception...")
        traceback.print_exc()

        util.report("@@@STEP_FAILURE@@@")
    finally:
        sys.stdout.flush()


def run_command(cmd, directory="."):
    util.report_run_cmd(cmd, cwd=directory)


if __name__ == "__main__":
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
