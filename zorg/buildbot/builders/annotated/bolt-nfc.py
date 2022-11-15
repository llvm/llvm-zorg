#!/usr/bin/python3

import os
import subprocess
import sys
import traceback
import util
from contextlib import contextmanager

def main():
    source_dir = os.path.join('..', 'llvm-project')
    tests_dir = os.path.join('..', 'bolt-tests')

    with step('fetch large-bolt-tests'):
        if os.path.exists(tests_dir):
            run_command(['git', '-C', tests_dir, 'fetch', 'origin'])
            run_command(['git', '-C', tests_dir, 'reset', '--hard',
                         'origin/main'])
        else:
            run_command(['git', 'clone',
                         'https://github.com/rafaelauler/bolt-tests',
                         tests_dir])

    with step('cmake'):
        cmake_args = ['-GNinja',
                      '-DCMAKE_BUILD_TYPE=Release',
                      '-DLLVM_APPEND_VC_REV=OFF',
                      '-DLLVM_CCACHE_BUILD=ON',
                      '-DLLVM_ENABLE_ASSERTIONS=ON',
                      '-DLLVM_ENABLE_LLD=ON',
                      '-DLLVM_ENABLE_PROJECTS=clang;lld;bolt',
                      '-DLLVM_TARGETS_TO_BUILD=X86;AArch64',
                      '-DLLVM_EXTERNAL_PROJECTS=bolttests',
                      '-DLLVM_EXTERNAL_BOLTTESTS_SOURCE_DIR='+tests_dir,
                      ]

        util.clean_dir('.')
        run_command(['cmake', os.path.join(source_dir, 'llvm')] + cmake_args)

    with step('build bolt'):
        run_command(['ninja', 'bolt'])

    with step('check-bolt'):
        run_command(['ninja', 'check-bolt'])

    with step('check-large-bolt'):
        run_command(['ninja', 'check-large-bolt'])

    with step('nfc-check-setup'):
        run_command([os.path.join(source_dir, 'bolt', 'utils',
            'nfc-check-setup.py')])

    with step('nfc-check-bolt', warn_on_fail=True, halt_on_fail=False):
        run_command([os.path.join('bin', 'llvm-lit'), '-sv', '-j2',
            # bolt-info will always mismatch in NFC mode
            '--xfail=bolt-info.test',
            'tools/bolt/test'])

    with step('nfc-check-large-bolt', warn_on_fail=True, halt_on_fail=False):
        run_command([os.path.join('bin', 'llvm-lit'), '-sv', '-j2',
            'tools/bolttests'])


@contextmanager
def step(step_name, warn_on_fail=False, halt_on_fail=True):
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

        if warn_on_fail:
            util.report('@@@STEP_WARNINGS@@@')
        else:
            util.report('@@@STEP_FAILURE@@@')
    finally:
        sys.stdout.flush()


def run_command(cmd, directory='.'):
    util.report_run_cmd(cmd, cwd=directory)


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main())
