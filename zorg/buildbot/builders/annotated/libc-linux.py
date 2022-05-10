#!/usr/bin/python

import argparse
import os
import subprocess
import sys
import traceback
import util
from contextlib import contextmanager


def is_fullbuild_builder(builder_name):
    return ('fullbuild' in builder_name.split('-'))

def is_runtimes_builder(builder_name):
    return ('runtimes' in builder_name.split('-'))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--asan', action='store_true', default=False,
                    help='Build with address sanitizer enabled.')
    ap.add_argument('--debug', action='store_true', default=False,
                    help='Build in debug mode.')
    args, _ = ap.parse_known_args()

    source_dir = os.path.join('..', 'llvm-project')
    builder_name = os.environ.get('BUILDBOT_BUILDERNAME')
    fullbuild = is_fullbuild_builder(builder_name)
    runtimes_build = is_runtimes_builder(builder_name)

    with step('cmake', halt_on_fail=True):
        # On most systems the default generator is make and the default
        # compilers are gcc and g++. We make it explicit here that we want
        # clang and ninja which reduces one step of setting environment
        # variables when setting up workers.
        cmake_args = ['-GNinja',
                      '-DCMAKE_C_COMPILER=clang',
                      '-DCMAKE_CXX_COMPILER=clang++']

        if runtimes_build:
          projects = ['llvm', 'clang']
          cmake_args.append('-DLLVM_ENABLE_RUNTIMES=libc')
        else:
          projects = ['llvm', 'libc']

        if args.debug:
            cmake_args.append('-DCMAKE_BUILD_TYPE=Debug')
        else:
            cmake_args.append('-DCMAKE_BUILD_TYPE=Release')

        if args.asan:
            cmake_args.append('-DLLVM_USE_SANITIZER=Address')

        if fullbuild and not args.asan:
            projects.extend(['clang', 'compiler-rt'])

        cmake_args.append('-DLLVM_ENABLE_PROJECTS={}'.format(';'.join(projects)))

        if fullbuild and not args.asan:
            cmake_args.append('-DLLVM_LIBC_INCLUDE_SCUDO=ON')
            cmake_args.append('-DLIBC_INCLUDE_BENCHMARKS=ON')

        if fullbuild:
            cmake_args.extend(['-DLLVM_LIBC_FULL_BUILD=ON']),

        run_command(['cmake', os.path.join(source_dir, 'llvm')] + cmake_args)

    with step('build llvmlibc', halt_on_fail=True):
        run_command(['ninja', 'llvmlibc'])

    with step('check-libc'):
        if runtimes_build:
          run_command(['ninja', 'check-llvmlibc'])
        else:
          run_command(['ninja', 'check-libc'])

    if fullbuild and not args.asan:
        with step('libc-integration-tests'):
            run_command(['ninja', 'libc-integration-tests'])
        with step('libc-api-test'):
            run_command(['ninja', 'libc-api-test'])
        with step('libc-fuzzer'):
            run_command(['ninja', 'libc-fuzzer'])
        with step('libc-scudo-integration-test'):
            run_command(['ninja', 'libc-scudo-integration-test'])
        with step('AOR Tests'):
            aor_dir = os.path.join(source_dir, 'libc', 'AOR_v20.02')
            # Remove the AOR build dir.
            util.clean_dir(os.path.join(aor_dir, 'build'))
            run_command(['make', 'check'], directory=aor_dir)
        with step('Benchmark Utils Tests'):
            run_command(['ninja', 'libc-benchmark-util-tests'])


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
