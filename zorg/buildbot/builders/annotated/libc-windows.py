
import annotated_builder
import util

import argparse
import os
import subprocess
import sys
import traceback
from contextlib import contextmanager

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--asan', action='store_true', default=False,
                    help='Build with address sanitizer enabled.')
    ap.add_argument('--debug', action='store_true', default=False,
                    help='Build in debug mode.')
    args, _ = ap.parse_known_args()

    source_dir = os.path.join('..', 'llvm-project')
    vc_vars = annotated_builder.get_vcvars(vs_tools=None, arch='amd64')
    for (var, val) in vc_vars.items():
        os.environ[var] = val

    with step('cmake', halt_on_fail=True):
        # On most systems the default generator is make and the default
        # compilers are gcc and g++. We make it explicit here that we want
        # clang and ninja which reduces one step of setting environment
        # variables when setting up workers.
        ## adjust compiler location definitions based on VM config
        cmake_args = ['-GNinja',
                      '-DCMAKE_C_COMPILER=clang-cl',
                      '-DCMAKE_CXX_COMPILER=clang-cl']
        if args.debug:
            cmake_args.append('-DCMAKE_BUILD_TYPE=Debug')
        else:
            cmake_args.append('-DCMAKE_BUILD_TYPE=Release')

        if args.asan:
            cmake_args.append('-DLLVM_USE_SANITIZER=Address')

        cmake_args.append('-DLLVM_ENABLE_PROJECTS=libc')
        cmake_args.append('-DLLVM_TARGETS_TO_BUILD=X86')
        cmake_args.append('-DLLVM_FORCE_BUILD_RUNTIME=libc')
        cmake_args.append('-DLLVM_NATIVE_ARCH=x86_64')
        cmake_args.append('-DLLVM_HOST_TRIPLE=x86_64-window-x86-gnu')
        cmake_args.append('-DLLVM_LIBC_MPFR_INSTALL_PATH=C:/src/install')

        run_command(['cmake', os.path.join(source_dir, 'llvm')] + cmake_args)

    with step('build llvmlibc', halt_on_fail=True):
        run_command(['ninja', 'llvmlibc'])

    with step('check-libc'):
        run_command(['ninja', 'check-libc'])


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
