#!/usr/bin/python

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

    with step('cmake', halt_on_fail=True):
        projects = ['llvm', 'libc', 'clang', 'clang-tools-extra']

        cmake_args = ['-GNinja', '-DCMAKE_BUILD_TYPE=Debug']
        if args.asan:
            cmake_args.append('-DLLVM_USE_SANITIZER=Address')
        cmake_args.append('-DLLVM_ENABLE_PROJECTS={}'.format(';'.join(projects)))

        run_command(['cmake', os.path.join(source_dir, 'llvm')] + cmake_args)

    with step('build llvmlibc', halt_on_fail=True):
        run_command(['ninja', 'llvmlibc'])

    with step('check-libc'):
        run_command(['ninja', 'check-libc'])

    if not args.asan:
        with step('Loader Tests'):
            run_command(['ninja', 'libc_loader_tests'])
        with step('AOR Tests'):
            aor_dir = os.path.join(source_dir, 'libc', 'AOR_v20.02')
            run_command(['make', 'check'], directory=aor_dir)


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
