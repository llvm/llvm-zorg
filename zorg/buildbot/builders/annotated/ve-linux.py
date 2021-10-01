#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import traceback
import util
from contextlib import contextmanager


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--asan', action='store_true', default=False,
                    help='Build with address sanitizer enabled.')
    args, _ = ap.parse_known_args()

    source_dir = os.path.join('..', 'llvm-project')

    llvm_build_dir='build_llvm'

    with step('prepare', halt_on_fail=True):
        util.mkdirp(llvm_build_dir)

    with step('cmake', halt_on_fail=True):
        # Tool config.
        cmake_args = ['-GNinja',
                      '-DCMAKE_C_COMPILER=gcc',
                      '-DCMAKE_CXX_COMPILER=g++']

        # Build config.
        cmake_args += ['-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                       '-DLLVM_BUILD_LLVM_DYLIB=On',
                       '-DLLVM_LINK_LLVM_DYLIB=On',
                       '-DCLANG_LINK_CLANG_DYLIB=On',
                       '-DLLVM_TARGETS_TO_BUILD="X86"',
                       '-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD="VE"',
                       '-DLLVM_ENABLE_PROJECTS="clang"']

        if args.asan:
            cmake_args.append('-DLLVM_USE_SANITIZER=Address')

        run_command(['cmake', os.path.join(source_dir, 'llvm')] + cmake_args, directory=llvm_build_dir)

    with step('build llvm', halt_on_fail=True):
        run_command(['ninja', 'all'],directory=llvm_build_dir)

    with step('check llvm'):
        run_command(['ninja', 'check-llvm'])

    with step('check clang'):
        run_command(['ninja', 'check-clang'])

    # TODO: crt, libunwind, libcxx, libcxxabi

@contextmanager
def step(step_name, halt_on_fail=False):
    util.report('@@@BUILD_STEP {}@@@'.format(step_name))
    if halt_on_fail:
        util.report('@@@HALT_ON_FAILURE@@@')
    try:
        yield
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            util.report(
                '{} exited with return code {}.'.format(e.cmd, e.returncode)
            )
        util.report('The build step threw an exception...')
        traceback.print_exc()

        util.report('@@@STEP_FAILURE@@@')
    finally:
        sys.stdout.flush()


def run_command(cmd, directory='.'):
    util.report_run_cmd(cmd, cwd=directory)

if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
