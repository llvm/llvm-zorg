#! /usr/bin/python

import argparse
import os

BUILD_DIR = "build"
MONO_REPO_DIR = "llvm-project"


def get_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asan", action="store_true",
                        help="Build with address sanitizer enabled.")
    parser.add_argument("--clean", action="store_true",
                        help="Do a clobber/clean build.")
    return parser.parse_args()


def run_cmd(cmd, pwd):
    print("Running command: %s" % cmd)
    print("Currently all commands are passthrough.")
    return 0


def run_step(step_name, cmd, pwd=None):
    print("@@@BUILD_STEP %s@@@" % step_name)
    retcode = run_cmd(cmd, pwd)
    if retcode == 0:
        print("@@@BUILD_STEP %s@@@" % step_name)
    else:
        print("@@@STEP_FAILURE@@@")


def create_build_dir(opts):
    if not os.path.exists(BUILD_DIR):
      run_step("create_build_dir", ["mkdir", "build"])


def clean_build(opts):
    should_clobber = (os.environ.get("BUILDBOT_CLOBBER", "0") == "1")
    if opts.clean or should_clobber:
        run_step("clean_build", ["rm", "-rf", "*"], BUILD_DIR)


def update_monorepo(opts):
    if not os.path.exists(MONO_REPO_DIR):
        run_step("clone_llvm_monorepo",
                 ["git", "clone", "https://github.com/llvm/llvm-project.git"])
    run_step("update_llvm_monorepo", ["git", "pull", "-r"], MONO_REPO_DIR)

    revision = os.environ.get("BUILDBOT_REVISION")
    run_step("checkout_revision", ["git", "checkout", revision], MONO_REPO_DIR)


def cmake_configure(opts):
    cmd = ["cmake", "-G", "Ninja", "../llvm_project/llvm",
           "-DLLVM_ENABLE_PROJECTS=libc"]
    if opts.asan:
        cmd.append("-DLLVM_ENABLE_SANITIZER=Address")
    run_step("cmake_configure", cmd, BUILD_DIR)


def build_llvmlibc(opts):
    cmd = ["ninja", "llvmlibc"]
    run_step("build_llvmlibc", cmd, BUILD_DIR)


def run_unittests(opts):
    cmd = ["ninja", "llvm_libc_unittests"]
    run_step("unittests", cmd, BUILD_DIR)


STEPS = [
    create_build_dir,
    clean_build,
    update_monorepo,
    cmake_configure,
    build_llvmlibc,
    run_unittests,
]


def main():
    opts = get_options()
    for step in STEPS:
        step(opts)


if __name__ == "__main__":
    main()
