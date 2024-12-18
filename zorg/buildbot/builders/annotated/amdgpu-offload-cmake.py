#!/usr/bin/python

import argparse
import os
import subprocess
import sys
import traceback
import util
from contextlib import contextmanager


def main(argv):
    source_dir = os.path.join("..", "llvm-project")
    offload_base_dir = os.path.join(source_dir, "offload")
    of_cmake_cache_base_dir = os.path.join(offload_base_dir, "cmake/caches")

    with step("cmake", halt_on_fail=True):
        # TODO make the name of the cache file an argument to the script.
        cmake_cache_file = os.path.join(of_cmake_cache_base_dir, "AMDGPUBot.cmake")

        # Use Ninja as the generator.
        # The other important settings alrady come from the CMake CMake
        # cache file inside LLVM
        cmake_args = ["-GNinja", "-C %s" % cmake_cache_file]

        run_command(["cmake", os.path.join(source_dir, "llvm")] + cmake_args)

    with step("build cmake config"):
        run_command(["ninja"])


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
