#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile
import traceback
import util

from contextlib import contextmanager


@contextmanager
def step(step_name, halt_on_fail=False):
    util.report(f'@@@BUILD_STEP {step_name}@@@')
    if halt_on_fail:
        util.report('@@@HALT_ON_FAILURE@@@')
    try:
        yield
    except subprocess.CalledProcessError as e:
        util.report(f'{e.cmd} exited with return code {e.returncode}.')
        util.report('@@@STEP_FAILURE@@@')
    except:
        util.report('The build step threw an exception...')
        traceback.print_exc()
        util.report('@@@STEP_EXCEPTION@@@')


def run_command(cmd, directory=os.getcwd()):
    util.report_run_cmd(cmd, cwd=directory)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--sdk-dir', default='/usr/local/fuchsia/sdk',
                        help='Path to Fuchsia SDK')
    args, _ = parser.parse_known_args()

    buildbot_buildername = os.environ.get('BUILDBOT_BUILDERNAME')
    buildbot_clobber = bool(os.environ.get('BUILDBOT_CLOBBER'))
    buildbot_revision = os.environ.get('BUILDBOT_REVISION', 'origin/main')

    cwd = os.getcwd()

    if buildbot_clobber:
        with step('clean', halt_on_fail=True):
            util.clean_dir(cwd)

    build_dir = tempfile.mkdtemp(prefix='llvm-build-', dir=cwd)
    source_dir = os.path.join(cwd, '..', 'llvm-project')

    with step('configure', halt_on_fail=True):
        cmake_args = [
            '-S', f'{source_dir}/llvm',
            '-B', build_dir,
            '-G', 'Ninja',
            '-D', 'LLVM_CCACHE_BUILD=ON',
            '-D', 'LLVM_ENABLE_LTO=OFF',
            '-D', f'FUCHSIA_SDK={args.sdk_dir}',
            '-D', 'LLVM_RUNTIME_MULTILIBS=',
            '-C', f'{source_dir}/clang/cmake/caches/Fuchsia-stage2.cmake',
        ]

        run_command(['cmake'] + cmake_args)

    with step('build'):
        run_command(['ninja', '-C', build_dir, 'toolchain-distribution'])

    with step('check'):
        run_command(['ninja', '-C', build_dir] +
                    [f'check-{p}' for p in ('llvm', 'clang', 'lld')])

    return 0


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
