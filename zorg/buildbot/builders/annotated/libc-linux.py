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

def is_bootstrap_builder(builder_name):
    return 'bootstrap' in builder_name

def is_gcc_builder(builder_name):
    return ('gcc' in builder_name.split('-'))

def is_lint_builder(builder_name):
    return ('lint' in builder_name.split('-'))

def is_riscv_builder(builder_name):
    return 'riscv' in builder_name

def is_x86_64_builder(builder_name):
    return 'x86_64' in builder_name

def is_riscv32_builder(builder_name):
    return 'riscv32' in builder_name

def is_arm32_builder(builder_name):
    return 'arm32' in builder_name

def is_qemu_builder(builder_name):
  return 'qemu' in builder_name

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
    bootstrap_build = is_bootstrap_builder(builder_name)
    gcc_build = is_gcc_builder(builder_name)
    lint_build = is_lint_builder(builder_name)
    riscv_build = is_riscv_builder(builder_name)
    x86_64_build = is_x86_64_builder(builder_name)
    riscv32_build = is_riscv32_builder(builder_name)
    arm32_build = is_arm32_builder(builder_name)
    qemu_build = is_qemu_builder(builder_name)

    if gcc_build:
        cc = 'gcc'
        cxx = 'g++'
    else:
        if lint_build:
            full_build = True
            cc = '/home/libc-lint-tools/bin/clang'
            cxx = '/home/libc-lint-tools/bin/clang++'
            clang_tidy = '/home/libc-lint-tools/bin/clang-tidy'
        else:
            cc = 'clang'
            cxx = 'clang++'

    with step('cmake', halt_on_fail=True):
        # On most systems the default generator is make, and the default
        # compilers are gcc and g++. We make the compiler and the generator
        # explicit here, which reduces one step of setting environment
        # variables when setting up workers.
        cmake_args = ['-GNinja',
                      '-DCMAKE_C_COMPILER=%s' % cc,
                      '-DCMAKE_CXX_COMPILER=%s' % cxx]
        if lint_build:
            cmake_args.append('-DLLVM_LIBC_CLANG_TIDY=%s' % clang_tidy)

        if bootstrap_build:
            cmake_args.append('-DLLVM_ENABLE_PROJECTS=clang')

        if args.debug:
            cmake_args.append('-DCMAKE_BUILD_TYPE=Debug')
        else:
            cmake_args.append('-DCMAKE_BUILD_TYPE=Release')

        if args.asan:
            cmake_args.append('-DLLVM_USE_SANITIZER=Address')

        runtimes = ['libc']
        if fullbuild and not args.asan and not lint_build and not riscv_build:
            runtimes.append('compiler-rt')
        cmake_args.append('-DLLVM_ENABLE_RUNTIMES={}'.format(';'.join(runtimes)))

        if fullbuild and not args.asan and not lint_build and not riscv_build:
            cmake_args.append('-DLLVM_LIBC_INCLUDE_SCUDO=ON')
            cmake_args.append('-DCOMPILER_RT_BUILD_SCUDO_STANDALONE_WITH_LLVM_LIBC=ON')
            cmake_args.append('-DCOMPILER_RT_BUILD_GWP_ASAN=OFF')
            cmake_args.append('-DCOMPILER_RT_SCUDO_STANDALONE_BUILD_SHARED=OFF')
            # TODO(https://github.com/llvm/llvm-project/issues/119789): re-enable
            # cmake_args.append('-DLIBC_INCLUDE_BENCHMARKS=ON')

        if fullbuild:
            cmake_args.extend(['-DLLVM_LIBC_FULL_BUILD=ON']),

        if riscv32_build:
            cmake_args.append('-DCMAKE_C_FLAGS=-mabi=ilp32d -march=rv32imafdc --target=riscv32-unknown-linux-gnu --sysroot=/opt/riscv/sysroot --gcc-toolchain=/opt/riscv')
            cmake_args.append('-DCMAKE_CXX_FLAGS=-mabi=ilp32d -march=rv32imafdc --target=riscv32-unknown-linux-gnu --sysroot=/opt/riscv/sysroot --gcc-toolchain=/opt/riscv')
            cmake_args.append('-DCMAKE_EXE_LINKER_FLAGS_INIT=-fuse-ld=lld')
            cmake_args.append('-DCMAKE_CROSSCOMPILING_EMULATOR={}/cross.sh'.format(os.getenv('HOME')))
            cmake_args.append('-DLIBC_TARGET_TRIPLE=riscv32-unknown-linux-gnu')
            cmake_args.append('-DCMAKE_SYSTEM_NAME=Linux')
            cmake_args.append('-DLLVM_HOST_TRIPLE=riscv32-unknown-linux-gnu')
            cmake_args.append('-DLLVM_TARGETS_TO_BUILD=RISCV')
            cmake_args.append('-DCMAKE_LINKER=/usr/bin/ld.lld')
            cmake_args.append('-DLLVM_LIBC_MPFR_INSTALL_PATH={}/gmp+mpfr/'.format(os.getenv('HOME')))

        if arm32_build and qemu_build:
            cmake_args.append('-DLIBC_TARGET_TRIPLE=arm-linux-gnueabihf')
            cmake_args.append('-DCMAKE_SYSROOT=/opt/sysroot-deb-armhf-stable')
            cmake_args.append('-DCMAKE_C_COMPILER_TARGET=arm-linux-gnueabihf')
            cmake_args.append('-DCMAKE_CXX_COMPILER_TARGET=arm-linux-gnueabihf')
            cmake_args.append('-DCMAKE_AR=/usr/bin/llvm-ar-20')
            cmake_args.append('-DCMAKE_RANLIB=/usr/bin/llvm-ranlib-20')
            cmake_args.append('-DLIBC_UNITTEST_ENV=QEMU_LD_PREFIX=/opt/sysroot-deb-armhf-stable')

        if bootstrap_build:
            cmake_root = 'llvm'
        else:
            cmake_root = 'runtimes'
        run_command(['cmake', os.path.join(source_dir, cmake_root)] + cmake_args)

    if lint_build:
        with step('lint libc'):
            run_command(['ninja', 'libc-lint'])
        return

    with step('build libc'):
       run_command(['ninja', 'libc'])

    if fullbuild:
       with step('build libc-startup'):
          run_command(['ninja', 'libc-startup'])

    if bootstrap_build:
        with step('check-libc'):
            run_command(['ninja', 'check-libc'])
    else:
        with step('libc-unit-tests'):
            run_command(['ninja', 'libc-unit-tests'])

    if fullbuild and not args.asan:
        if gcc_build or ('riscv' in builder_name):
            # The rest of the targets are either not yet gcc-clean or
            # not yet availabe on riscv.
            return
        with step('libc-integration-tests'):
            run_command(['ninja', 'libc-integration-tests'])
        with step('libc-scudo-integration-test'):
            run_command(['ninja', 'libc-scudo-integration-test'])
        # TODO(https://github.com/llvm/llvm-project/issues/119789): re-enable
        # cmake_args.append('-DLIBC_INCLUDE_BENCHMARKS=ON')
        # with step('Benchmark Utils Tests'):
        #     run_command(['ninja', 'libc-benchmark-util-tests'])

    if not (fullbuild or bootstrap_build) and x86_64_build:
        with step('libc-fuzzer'):
            run_command(['ninja', 'libc-fuzzer'])


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
