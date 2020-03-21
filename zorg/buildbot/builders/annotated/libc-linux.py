#!/usr/bin/python

import os
import subprocess
import sys
import traceback
import util
from contextlib import contextmanager
import annotated_builder


def main(argv):
    ap = annotated_builder.get_argument_parser()
    ap.add_argument('--asan', action='store_true', default=False)
    args = ap.parse_args(argv[1:])

    extra_cmake_args = ['-DCMAKE_BUILD_TYPE=Debug']
    if args.asan:
        extra_cmake_args.append('-DLLVM_USE_SANITIZER=Address')

    projects = ['llvm', 'libc']
    check_targets = ['check-libc']

    builder = annotated_builder.AnnotatedBuilder()
    builder.run_steps(projects=projects,
                      check_targets=check_targets,
                      extra_cmake_args=extra_cmake_args)

    # AOR tests step
    if not args.asan:
        with step('AOR Tests'):
            aor_dir = os.path.join('..', 'llvm-project', 'libc', 'AOR_v20.02')
            run_command(['make', 'check'], directory=aor_dir)


@contextmanager
def step(step_name, halt_on_fail=True):
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
