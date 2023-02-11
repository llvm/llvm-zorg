from importlib import reload

from buildbot.plugins import util

from buildbot.process.properties import WithProperties

from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.builders import FlangBuilder
from zorg.buildbot.builders import PollyBuilder
from zorg.buildbot.builders import LLDBBuilder
from zorg.buildbot.builders import SanitizerBuilder
from zorg.buildbot.builders import OpenMPBuilder
from zorg.buildbot.builders import SphinxDocsBuilder
from zorg.buildbot.builders import ABITestsuitBuilder
from zorg.buildbot.builders import ClangLTOBuilder
from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.builders import AOSPBuilder
from zorg.buildbot.builders import AnnotatedBuilder
from zorg.buildbot.builders import LLDPerformanceTestsuite
from zorg.buildbot.builders import FuchsiaBuilder
from zorg.buildbot.builders import XToolchainBuilder
from zorg.buildbot.builders import TestSuiteBuilder
from zorg.buildbot.builders import BOLTBuilder

from zorg.buildbot.builders import HtmlDocsBuilder
from zorg.buildbot.builders import DoxygenDocsBuilder

reload(HtmlDocsBuilder)
reload(DoxygenDocsBuilder)


all = [

# Clang fast builders.

    {'name' : "clang-x86_64-debian-fast",
    'tags'  : ["clang", "fast"],
    'collapseRequests': False,
    'workernames':["gribozavr4"],
    'builddir':"clang-x86_64-debian-fast",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    llvm_srcdir="llvm.src",
                    obj_dir="llvm.obj",
                    clean=True,
                    depends_on_projects=['llvm','clang','clang-tools-extra','compiler-rt'],
                    extra_configure_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DCOMPILER_RT_BUILD_BUILTINS:BOOL=OFF",
                        "-DCOMPILER_RT_BUILD_ORC:BOOL=OFF",
                        "-DCOMPILER_RT_BUILD_SANITIZERS:BOOL=OFF",
                        "-DCOMPILER_RT_BUILD_XRAY:BOOL=OFF",
                        "-DCOMPILER_RT_INCLUDE_TESTS:BOOL=OFF",
                        "-DCOMPILER_RT_BUILD_LIBFUZZER:BOOL=OFF",
                        "-DCMAKE_C_FLAGS=-Wdocumentation -Wno-documentation-deprecated-sync",
                        "-DCMAKE_CXX_FLAGS=-std=c++11 -Wdocumentation -Wno-documentation-deprecated-sync",
                    ],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'clang', 'CXX': 'clang++',
                    })},

    {'name' : "llvm-clang-x86_64-win-fast",
    'tags'  : ["clang", "fast"],
    'collapseRequests': False,
    'workernames' : ["as-builder-3"],
    'builddir': "llvm-clang-x86_64-win-fast",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    vs="autodetect",
                    depends_on_projects=['llvm', 'clang'],
                    clean=True,
                    checks=[
                    "check-llvm-unit",
                    "check-clang-unit"],
                    extra_configure_args=[
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DLLVM_TARGETS_TO_BUILD=ARM",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=armv7-unknown-linux-eabihf",
                        "-DLLVM_ENABLE_ASSERTIONS=OFF",
                        "-DLLVM_OPTIMIZED_TABLEGEN=OFF",
                        "-DLLVM_LIT_ARGS=-v --threads=32"])},

    {'name': "llvm-clang-x86_64-sie-ubuntu-fast",
    'tags'  : ["clang", "llvm", "clang-tools-extra", "lld", "cross-project-tests"],
    'workernames': ["sie-linux-worker"],
    'builddir': "llvm-clang-x86_64-sie-ubuntu-fast",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm','clang','clang-tools-extra','lld','cross-project-tests'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=gcc",
                        "-DCMAKE_CXX_COMPILER=g++",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_CLANGD=OFF",
                        "-DLLVM_BUILD_RUNTIME=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_INCLUDE_EXAMPLES=OFF",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=x86_64-scei-ps4",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=--verbose -j100",
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DLLVM_USE_LINKER=gold"])},

# Expensive checks builders.

    {'name' : "llvm-clang-x86_64-expensive-checks-ubuntu",
    'tags'  : ["llvm", "expensive-checks"],
    'workernames' : ["as-builder-4"],
    'builddir': "llvm-clang-x86_64-expensive-checks-ubuntu",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=["llvm", "lld"],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DLLVM_USE_SPLIT_DWARF=ON",
                        "-DLLVM_USE_LINKER=gold",
                        "-DCMAKE_BUILD_TYPE=Debug",
                        "-DCMAKE_CXX_FLAGS=-U_GLIBCXX_DEBUG -Wno-misleading-indentation",
                        "-DLLVM_LIT_ARGS=-vv -j32"])},

    {'name' : "llvm-clang-x86_64-expensive-checks-win",
    'tags'  : ["llvm", "expensive-checks"],
    'workernames' : ["as-worker-93"],
    'builddir': "llvm-clang-x86_64-expensive-checks-win",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    vs="autodetect",
                    depends_on_projects=["llvm", "lld"],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DCMAKE_BUILD_TYPE=Debug"])},

    {'name' : "llvm-clang-x86_64-expensive-checks-debian",
    'tags'  : ["llvm", "expensive-checks"],
    'collapseRequests' : False,
    'workernames' : ["gribozavr4"],
    'builddir': "llvm-clang-x86_64-expensive-checks-debian",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=["llvm", "lld"],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCMAKE_CXX_FLAGS=-U_GLIBCXX_DEBUG",
                        "-DLLVM_LIT_ARGS=-v -vv -j96"],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'clang', 'CXX': 'clang++',
                    })},

# Cross builders.

    {'name' : "llvm-clang-win-x-armv7l",
    'tags'  : ["clang", "llvm", "compiler-rt", "cross", "armv7"],
    'workernames' : ["as-builder-1"],
    'builddir': "x-armv7l",
    'factory' : XToolchainBuilder.getCmakeWithMSVCBuildFactory(
                    vs="autodetect",
                    clean=True,
                    checks=[
                    "check-llvm",
                    "check-clang",
                    "check-lld",
                    "check-compiler-rt-armv7-unknown-linux-gnueabihf"
                    ],
                    checks_on_target = [
                        ("libunwind",
                            ["python", "bin/llvm-lit.py",
                            "-v", "-vv", "--threads=32",
                            "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libunwind/test"]),
                        ("libc++abi",
                            ["python", "bin/llvm-lit.py",
                            "-v", "-vv", "--threads=32",
                            "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libcxxabi/test"]),
                        ("libc++",
                            ['python', 'bin/llvm-lit.py',
                            '-v', '-vv', '--threads=32',
                            'runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libcxx/test',
                            ])
                    ],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=ARM",
                        "-DTOOLCHAIN_TARGET_TRIPLE=armv7-unknown-linux-gnueabihf",
                        "-DDEFAULT_SYSROOT=C:/buildbot/.arm-ubuntu",
                        "-DZLIB_ROOT=C:/buildbot/.zlib-win32",
                        "-DLLVM_LIT_ARGS=-v -vv --threads=32",
                        WithProperties("%(remote_test_host:+-DREMOTE_TEST_HOST=)s%(remote_test_host:-)s"),
                        WithProperties("%(remote_test_user:+-DREMOTE_TEST_USER=)s%(remote_test_user:-)s"),
                    ],
                    cmake_cache="../llvm-project/clang/cmake/caches/CrossWinToARMLinux.cmake")},

    {'name' : "llvm-clang-win-x-aarch64",
    'tags'  : ["clang", "llvm", "compiler-rt", "cross", "aarch64"],
    'workernames' : ["as-builder-2"],
    'builddir': "x-aarch64",
    'factory' : XToolchainBuilder.getCmakeWithMSVCBuildFactory(
                    vs="autodetect",
                    clean=True,
                    checks=[
                    "check-llvm",
                    "check-clang",
                    "check-lld",
                    "check-compiler-rt-aarch64-unknown-linux-gnu"
                    ],
                    checks_on_target = [
                        ("libunwind",
                            ["python", "bin/llvm-lit.py",
                            "-v", "-vv", "--threads=32",
                            "runtimes/runtimes-aarch64-unknown-linux-gnu-bins/libunwind/test"]),
                        ("libc++abi",
                            ["python", "bin/llvm-lit.py",
                            "-v", "-vv", "--threads=32",
                            "runtimes/runtimes-aarch64-unknown-linux-gnu-bins/libcxxabi/test"]),
                        ("libc++",
                            ['python', 'bin/llvm-lit.py',
                            '-v', '-vv', '--threads=32',
                            'runtimes/runtimes-aarch64-unknown-linux-gnu-bins/libcxx/test',
                            ])
                    ],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DTOOLCHAIN_TARGET_TRIPLE=aarch64-unknown-linux-gnu",
                        "-DDEFAULT_SYSROOT=C:/buildbot/.aarch64-ubuntu",
                        "-DZLIB_ROOT=C:/buildbot/.zlib-win32",
                        "-DLLVM_LIT_ARGS=-v -vv --threads=32",
                        WithProperties("%(remote_test_host:+-DREMOTE_TEST_HOST=)s%(remote_test_host:-)s"),
                        WithProperties("%(remote_test_user:+-DREMOTE_TEST_USER=)s%(remote_test_user:-)s"),
                    ],
                    cmake_cache="../llvm-project/clang/cmake/caches/CrossWinToARMLinux.cmake")},

# Clang builders.

    {'name': "clang-arm64-windows-msvc",
    'tags' : ["llvm", "clang", "lld", "flang"],
    'workernames' : ["linaro-armv8-windows-msvc-04"],
    'builddir': "clang-arm64-windows-msvc",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    vs="manual",
                    clean=False,
                    checkout_flang=True,
                    checkout_lld=True,
                    checkout_compiler_rt=False,
                    extra_cmake_args=[
                        "-DCMAKE_TRY_COMPILE_CONFIGURATION=Release",
                        "-DLLVM_TARGETS_TO_BUILD='AArch64'",
                        "-DCMAKE_C_COMPILER_LAUNCHER=sccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=sccache"])},

    ## ARMv8 check-all
    {'name' : "clang-armv8-quick",
    'tags'  : ["clang"],
    'workernames':["linaro-clang-armv8-quick"],
    'builddir':"clang-armv8-quick",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM'"])},

    # Cortex-A15 LNT test-suite in Benchmark mode
    {'name' : "clang-native-arm-lnt-perf",
    'tags'  : ["clang"],
    'workernames':["linaro-tk1-02"],
    'builddir':"clang-native-arm-lnt-perf",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    checks=[],
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-O3 -mcpu=cortex-a15 -mthumb',
                        '--threads=1', '--build-threads=4',
                        '--use-perf=all',
                        '--benchmarking-only', '--exec-multisample=3',
                        '--exclude-stat-from-submission=compile'],
                    extra_cmake_args=[
                        "-DLLVM_TARGETS_TO_BUILD='ARM'",
                        "-DLLVM_PARALLEL_LINK_JOBS=2"],
                    submitURL='http://lnt.llvm.org/submitRun',
                    testerName='LNT-Thumb2v7-A15-O3')},

    # ARMv7 LNT test-suite in test-only mode
    {'name' : "clang-armv7-lnt",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-armv7-lnt"],
    'builddir': "clang-armv7-lnt",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    checks=[],
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-mcpu=cortex-a15 -marm',
                        '--threads=32', '--build-threads=32'])},

    ## ARMv7 check-all 2-stage
    {'name' : "clang-armv7-2stage",
    'tags'  : ["clang"],
    'workernames': ["linaro-clang-armv7-2stage"],
    'builddir':"clang-armv7-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    testStage1=False,
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -marm'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -marm'"])},

    ## ARMv7 run test-suite with GlobalISel enabled
    {'name' : "clang-armv7-global-isel",
    'tags'  : ["clang"],
    'workernames':["linaro-clang-armv7-global-isel"],
    'builddir':"clang-armv7-global-isel",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-mcpu=cortex-a15 -marm -O0 -mllvm -global-isel -mllvm -global-isel-abort=0',
                        '--threads=32', '--build-threads=32'])},

    ## ARMv7 VFPv3 check-all 2-stage
    {'name' : "clang-armv7-vfpv3-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-armv7-vfpv3-2stage"],
    'builddir': "clang-armv7-vfpv3-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    testStage1=False,
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'"])},

    ## AArch64 check-all
    {'name' : "clang-aarch64-quick",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-quick"],
    'builddir': "clang-aarch64-quick",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='AArch64'"])},

    ## AArch64 check-all + LLD + test-suite 2-stage
    {'name' : "clang-aarch64-lld-2stage",
    'tags'  : ["lld"],
    'workernames' : ["linaro-clang-aarch64-lld-2stage"],
    'builddir':"clang-aarch64-lld-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                clean=False,
                useTwoStage=True,
                runTestSuite=True,
                testsuite_flags=[
                    '--cppflags', '-mcpu=cortex-a57 -fuse-ld=lld',
                    '--threads=32', '--build-threads=32'],
                extra_cmake_args=[
                    "-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                    "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                    "-DLLVM_ENABLE_LLD=True",
                    "-DLLVM_LIT_ARGS='-v'"])},

    ## AArch64 run test-suite at -O0 (GlobalISel is now default).
    {'name' : "clang-aarch64-global-isel",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-global-isel"],
    'builddir': "clang-aarch64-global-isel",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-O0',
                        '--threads=32', '--build-threads=32'])},

    ## ARMv7 VFPv3 check-all + compiler-rt + testsuite 2-stage
    {'name' : "clang-armv7-vfpv3-full-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-tk1-06", "linaro-tk1-07", "linaro-tk1-08", "linaro-tk1-09"],
    'builddir': "clang-armv7-vfpv3-full-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    testStage1=False,
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-mcpu=cortex-a15 -mfpu=vfpv3 -marm',
                        '--threads=4', '--build-threads=4'],
                    extra_cmake_args=[
                        "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                        "-DLLVM_PARALLEL_LINK_JOBS=2",
                        "-DCOMPILER_RT_BUILD_GWP_ASAN=OFF"])},

    ## ARMv7 Thumb2 check-all + compiler-rt + testsuite 2-stage
    {'name' : "clang-thumbv7-full-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-tk1-01", "linaro-tk1-03", "linaro-tk1-04", "linaro-tk1-05"],
    'builddir': "clang-thumbv7-full-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_lld=False,
                    testStage1=False,
                    useTwoStage=True,
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-mcpu=cortex-a15 -mthumb',
                        '--threads=4', '--build-threads=4'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                        "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mthumb'",
                        "-DLLVM_PARALLEL_LINK_JOBS=2",
                        "-DCOMPILER_RT_BUILD_GWP_ASAN=OFF"])},

    ## AArch32 Self-hosting Clang+LLVM check-all + LLD + test-suite
    # Sanitizers build disabled due to PR38690
    {'name' : "clang-armv8-lld-2stage",
    'tags'  : ["lld"],
    'workernames' : ["linaro-clang-armv8-lld-2stage"],
    'builddir': "clang-armv8-lld-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    useTwoStage=True,
                    runTestSuite=True,
                    testsuite_flags=[
                        '--cppflags', '-mcpu=cortex-a57 -fuse-ld=lld',
                        '--threads=32', '--build-threads=32'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                        "-DCOMPILER_RT_BUILD_SANITIZERS=OFF",
                        "-DLLVM_ENABLE_LLD=True",
                        # lld tests cause us to hit thread limits
                        "-DLLVM_ENABLE_THREADS=OFF"])},

    # AArch64 check-all + flang + compiler-rt + test-suite 2-stage
    {'name' : "clang-aarch64-full-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-full-2stage"],
    'builddir': "clang-aarch64-full-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_flang=True,
                    checkout_lld=False,
                    useTwoStage=True,
                    testStage1=False,
                    runTestSuite=True,
                    env={
                        'NO_STOP_MESSAGE':'1', # For Fortran test-suite
                    },
                    testsuite_flags=[
                        '--cppflags', '-mcpu=cortex-a57',
                        '--threads=32', '--build-threads=32'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                        "-DLLVM_LIT_ARGS='-v'"])},


    # AArch64 Clang+LLVM+RT+LLD check-all + flang + test-suite +
    # mlir-integration-tests w/SVE-Vector-Length-Agnostic Note that in this and
    # other clang-aarch64-sve-* builders we set -mllvm
    # -treat-scalable-fixed-error-as-warning=false to make compiler fail on
    # non-critical SVE codegen issues.  This helps us notice and fix SVE
    # problems sooner rather than later.
    {'name' : "clang-aarch64-sve-vla",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-sve-vla"],
    'builddir': "clang-aarch64-sve-vla",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_flang=True,
                    runTestSuite=True,
                    env={
                        'NO_STOP_MESSAGE':'1', # For Fortran test-suite
                    },
                    testsuite_flags=[
                        '--cppflags', '-mcpu=a64fx -mllvm -scalable-vectorization=preferred -mllvm -treat-scalable-fixed-error-as-warning=false -O3',
                        '--threads=48', '--build-threads=48'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=a64fx'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=a64fx'",
                        "-DLLVM_ENABLE_LLD=True",
                        "-DMLIR_INCLUDE_INTEGRATION_TESTS=True",
                        "-DMLIR_RUN_ARM_SVE_TESTS=True",
                        "-DLLVM_LIT_ARGS='-v -j12'"])},

    # AArch64 Clang+LLVM+RT+LLD check-all + flang + test-suite 2-stage w/SVE-Vector-Length-Agnostic
    {'name' : "clang-aarch64-sve-vla-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-sve-vla-2stage"],
    'builddir': "clang-aarch64-sve-vla-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_flang=True,
                    useTwoStage=True,
                    testStage1=False,
                    runTestSuite=True,
                    env={
                        'NO_STOP_MESSAGE':'1', # For Fortran test-suite
                    },
                    testsuite_flags=[
                        '--cppflags', '-mcpu=a64fx -mllvm -scalable-vectorization=preferred -mllvm -treat-scalable-fixed-error-as-warning=false -O3',
                        '--threads=48', '--build-threads=48'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=a64fx -mllvm -scalable-vectorization=preferred -mllvm -treat-scalable-fixed-error-as-warning=false'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=a64fx -mllvm -scalable-vectorization=preferred -mllvm -treat-scalable-fixed-error-as-warning=false'",
                        "-DLLVM_ENABLE_LLD=True",
                        "-DLLVM_LIT_ARGS='-v -j12'"])},

    # AArch64 Clang+LLVM+RT+LLD check-all + flang + test-suite w/SVE-Vector-Length-Specific
    {'name' : "clang-aarch64-sve-vls",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-sve-vls"],
    'builddir': "clang-aarch64-sve-vls",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_flang=True,
                    runTestSuite=True,
                    env={
                        'NO_STOP_MESSAGE':'1', # For Fortran test-suite
                    },
                    testsuite_flags=[
                        '--cppflags', '-mcpu=a64fx -msve-vector-bits=512 -mllvm -treat-scalable-fixed-error-as-warning=false -O3',
                        '--threads=48', '--build-threads=48'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=a64fx'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=a64fx'",
                        "-DLLVM_ENABLE_LLD=True",
                        "-DMLIR_INCLUDE_INTEGRATION_TESTS=True",
                        "-DMLIR_RUN_ARM_SVE_TESTS=True",
                        "-DLLVM_LIT_ARGS='-v -j12'"])},

    # AArch64 Clang+LLVM+RT+LLD check-all + flang + test-suite 2-stage w/SVE-Vector-Length-Specific
    {'name' : "clang-aarch64-sve-vls-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-clang-aarch64-sve-vls-2stage"],
    'builddir': "clang-aarch64-sve-vls-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_flang=True,
                    useTwoStage=True,
                    testStage1=False,
                    runTestSuite=True,
                    env={
                        'NO_STOP_MESSAGE':'1', # For Fortran test-suite
                    },
                    testsuite_flags=[
                        '--cppflags', '-mcpu=a64fx -msve-vector-bits=512 -mllvm -treat-scalable-fixed-error-as-warning=false -O3',
                        '--threads=48', '--build-threads=48'],
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-mcpu=a64fx -msve-vector-bits=512 -mllvm -treat-scalable-fixed-error-as-warning=false'",
                        "-DCMAKE_CXX_FLAGS='-mcpu=a64fx -msve-vector-bits=512 -mllvm -treat-scalable-fixed-error-as-warning=false'",
                        "-DLLVM_ENABLE_LLD=True",
                        "-DLLVM_LIT_ARGS='-v -j12'"])},

    {'name' : "clang-arm64-windows-msvc-2stage",
    'tags'  : ["clang"],
    'workernames' : ["linaro-armv8-windows-msvc-01", "linaro-armv8-windows-msvc-02", "linaro-armv8-windows-msvc-03"],
    'builddir': "clang-arm64-windows-msvc-2stage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    vs="manual",
                    useTwoStage=True,
                    checkout_flang=True,
                    extra_cmake_args=[
                        "-DCMAKE_TRY_COMPILE_CONFIGURATION=Release",
                        "-DCMAKE_C_COMPILER_LAUNCHER=sccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=sccache",
                        # FIXME: compiler-rt\lib\sanitizer_common\sanitizer_unwind_win.cpp assumes WIN64 is x86_64,
                        #        so, before that's fixed, disable everything that triggers its build.
                        "-DCOMPILER_RT_BUILD_SANITIZERS=OFF",
                        "-DCOMPILER_RT_BUILD_PROFILE=OFF"])},

    {'name' : 'clang-x64-windows-msvc',
    'tags'  : ["clang"],
    'workernames' : ['windows-gcebot2'],
    'builddir': 'clang-x64-windows-msvc',
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="clang-windows.py",
                    depends_on_projects=['llvm', 'clang', 'lld', 'debuginfo-tests'])},

    {'name' : "clang-m68k-linux",
    'tags'  : ["clang"],
    'workernames' : ["debian-akiko-m68k"],
    'builddir': "clang-m68k-linux",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=False,
                    stage1_config='Release',
                    extra_cmake_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=M68k"])},

    {'name' : "clang-m68k-linux-cross",
    'tags'  : ["clang"],
    'workernames' : ["suse-gary-m68k-cross"],
    'builddir': "clang-m68k-linux-cross",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=False,
                    stage1_config='Release',
                    extra_cmake_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=M68k"])},

    {'name' : "clang-mips64el-linux",
    'tags'  : ["clang"],
    'workernames' : ["debian-tritium-mips64el"],
    'builddir': "clang-mips64el-linux",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=False,
                    stage1_config='Release',
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                      '-DLLVM_PARALLEL_LINK_JOBS=4',
                                      '-DLLVM_TARGETS_TO_BUILD=Mips'])},

    {'name' : "clang-ppc64be-linux-test-suite",
    'tags'  : ["clang", "ppc"],
    'workernames' : ["ppc64be-clang-test-suite"],
    'builddir': "clang-ppc64be-test-suite",
    'factory' : TestSuiteBuilder.getTestSuiteBuildFactory(
                    depends_on_projects=["llvm", "clang", "clang-tools-extra",
                                         "compiler-rt"],
                    enable_runtimes="auto",
                    checks=['check-all', 'check-runtimes'],
                    extra_configure_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_LIT_ARGS=-v",
                        "-DLLVM_CCACHE_BUILD=ON"])},

    {'name' : "clang-ppc64be-linux-multistage",
    'tags'  : ["clang", "ppc"],
    'workernames' : ["ppc64be-clang-multistage-test"],
    'builddir': "clang-ppc64be-multistage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checks=['check-all', 'check-runtimes'],
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    stage1_config='Release',
                    stage2_config='Release',
                    extra_cmake_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_ENABLE_RUNTIMES=compiler-rt",
                        "-DLLVM_CCACHE_BUILD=ON"])},

    {'name' : "clang-ppc64le-linux-test-suite",
    'tags'  : ["clang", "ppc", "ppc64le"],
    'workernames' : ["ppc64le-clang-test-suite"],
    'builddir': "clang-ppc64le-test-suite",
    'factory' : TestSuiteBuilder.getTestSuiteBuildFactory(
                    depends_on_projects=["llvm", "clang", "clang-tools-extra",
                                         "compiler-rt"],
                    enable_runtimes="auto",
                    checks=['check-all', 'check-runtimes'],
                    extra_configure_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_LIT_ARGS=-v",
                        "-DLLVM_CCACHE_BUILD=ON"])},

    {'name' : "clang-ppc64le-linux-multistage",
    'tags'  : ["clang", "ppc", "ppc64le"],
    'workernames' : ["ppc64le-clang-multistage-test"],
    'builddir': "clang-ppc64le-multistage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checks=['check-all', 'check-runtimes'],
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    stage1_config='Release',
                    stage2_config='Release',
                    extra_cmake_args=[
                        '-DLLVM_ENABLE_ASSERTIONS=ON',
                        '-DLLVM_ENABLE_RUNTIMES=compiler-rt',
                        '-DBUILD_SHARED_LIBS=ON',
                        '-DLLVM_CCACHE_BUILD=ON'])},

    {'name' : "clang-ppc64le-rhel",
    'tags'  : ["clang", "ppc", "ppc64le"],
    'workernames' : ["ppc64le-clang-rhel-test"],
    'builddir': "clang-ppc64le-rhel",
    'factory' : TestSuiteBuilder.getTestSuiteBuildFactory(
                    depends_on_projects=["llvm", "clang", "clang-tools-extra",
                                         "lld", "compiler-rt"],
                    enable_runtimes="auto",
                    checks=['check-all', 'check-runtimes'],
                    extra_configure_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=On",
                        "-DCMAKE_C_COMPILER=clang",
                        "-DCMAKE_CXX_COMPILER=clang++",
                        "-DCLANG_DEFAULT_LINKER=lld",
                        "-DLLVM_TOOL_GOLD_BUILD=0",
                        "-DCMAKE_C_COMPILER_EXTERNAL_TOOLCHAIN:PATH=/usr",
                        "-DCMAKE_CXX_COMPILER_EXTERNAL_TOOLCHAIN:PATH=/usr",
                        "-DLLVM_BINUTILS_INCDIR=/usr/include",
                        "-DBUILD_SHARED_LIBS=ON", "-DLLVM_ENABLE_WERROR=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_LIT_ARGS=-vj 20"])},

    {'name' : "clang-ppc64-aix",
    'tags'  : ["clang", "aix", "ppc"],
    'workernames' : ["aix-ppc64"],
    'builddir': "clang-ppc64-aix",
    'factory' : TestSuiteBuilder.getTestSuiteBuildFactory(
                    depends_on_projects=["llvm", "clang", "compiler-rt"],
                    enable_runtimes="auto",
                    clean=False,
                    extra_configure_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=On",
                        "-DCMAKE_C_COMPILER=/usr/local/clang-15.0.0/bin/clang",
                        "-DCMAKE_CXX_COMPILER=/usr/local/clang-15.0.0/bin/clang++",
                        "-DPython3_EXECUTABLE:FILEPATH=/opt/freeware/bin/python3_64",
                        "-DLLVM_ENABLE_ZLIB=OFF", "-DLLVM_APPEND_VC_REV=OFF",
                        "-DLLVM_PARALLEL_LINK_JOBS=2",
                        "-DLLVM_ENABLE_WERROR=ON"]),
    'env' : {'OBJECT_MODE': '64'}},

    {'name' : "clang-s390x-linux",
    'tags'  : ["clang"],
    'workernames' : ["systemz-1"],
    'builddir': "clang-s390x-linux",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=4,
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=False,
                    stage1_config='Release',
                    extra_cmake_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=-v -j4 --param run_long_tests=true"])},

    {'name' : "clang-s390x-linux-multistage",
    'tags'  : ["clang"],
    'workernames' : ["systemz-1"],
    'builddir': "clang-s390x-linux-multistage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=4,
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    stage1_config='Release',
                    stage2_config='Release',
                    extra_cmake_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON"])},

    {'name' : "clang-s390x-linux-lnt",
    'tags'  : ["clang"],
    'workernames' : ["systemz-1"],
    'builddir': "clang-s390x-linux-lnt",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=4,
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=False,
                    runTestSuite=True,
                    stage1_config='Release',
                    testsuite_flags=['--threads=4', '--build-threads=4'],
                    extra_cmake_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON"])},

    {'name' : "clang-sparc64-linux-multistage",
    'tags'  : ["clang"],
    'workernames' : ["debian-stadler-sparc64"],
    'builddir': "clang-sparc64-linux-multistage",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_lld=False,
                    useTwoStage=True,
                    stage1_config='Release',
                    stage2_config='Release',
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                      '-DLLVM_PARALLEL_LINK_JOBS=4',
                                      '-DLLVM_TARGETS_TO_BUILD=Sparc'])},

    ## LoongArch64 Clang+LLVM build check-all + test-suite
    {'name' : 'clang-loongarch64-linux',
    'tags'  : ['clang'],
    'workernames' : ['loongson-loongarch64-clfs-clang-01'],
    'builddir': 'clang-loongarch64-linux',
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    runTestSuite=True,
                    checkout_clang_tools_extra=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    testsuite_flags=['--threads=32', '--build-threads=32'],
                    extra_cmake_args=['-DLLVM_TARGETS_TO_BUILD=',
                                      '-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=LoongArch',
                                      '-DLLVM_ENABLE_PROJECTS=clang'])},

    {'name' : "clang-hexagon-elf",
    'tags'  : ["clang"],
    'workernames' : ["hexagon-build-02", "hexagon-build-03"],
    'builddir': "clang-hexagon-elf",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=16,
                    checkout_clang_tools_extra=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    env={'LD_LIBRARY_PATH': '/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/lib'},
                    extra_cmake_args=[
                        "-DCMAKE_BUILD_TYPE:STRING=Release",
                        "-DLLVM_TARGETS_TO_BUILD:STRING=Hexagon",
                        "-DTARGET_TRIPLE:STRING=hexagon-unknown-elf",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE:STRING=hexagon-unknown-elf",
                        "-DLLVM_TARGET_ARCH:STRING=hexagon-unknown-elf",
                        "-DLLVM_BUILD_RUNTIME:BOOL=OFF",
                        "-DCMAKE_VERBOSE_MAKEFILE:BOOL=ON",
                        "-DLLVM_ENABLE_PIC:BOOL=ON",
                        "-DLLVM_ENABLE_ASSERTIONS:BOOL=ON",
                        "-DLLVM_INCLUDE_TOOLS:BOOL=ON",
                        "-DLLVM_LIT_ARGS:STRING=-v",
                        "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                        "-DWITH_POLLY:BOOL=OFF",
                        "-DLINK_POLLY_INTO_TOOLS:BOOL=OFF",
                        "-DPOLLY_BUILD_SHARED_LIB:BOOL=OFF",
                        "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang",
                        "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang++"])},

    ## X86_64 AVX2 Clang+LLVM check-all + test-suite
    {'name' : "clang-cmake-x86_64-avx2-linux",
    'tags'  : ["clang"],
    'workernames' : ["sde-avx512-intel64"],
    'builddir': "clang-cmake-x86_64-avx2-linux",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_clang_tools_extra=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    useTwoStage=False,
                    runTestSuite=True,
                    testsuite_flags=['--cflag', '-march=cascadelake', '--threads=32', '--build-threads=32'],
                    env={'PATH':'/usr/bin/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                    extra_cmake_args=[
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DCMAKE_C_FLAGS='-march=cascadelake'",
                        "-DCMAKE_CXX_FLAGS='-march=cascadelake'",
                        "-DLLVM_TARGETS_TO_BUILD='X86'"])},

    ## X86_64 AVX2 LNT test-suite in Benchmark mode
    {'name' : "clang-cmake-x86_64-avx2-linux-perf",
    'tags'  : ["clang"],
    'workernames' : ["avx2-intel64"],
    'builddir': "clang-cmake-x86_64-avx2-linux-perf",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    clean=False,
                    checkout_clang_tools_extra=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    checks=[],
                    useTwoStage=False,
                    runTestSuite=True,
                    testsuite_flags=['--cflag', '-march=cascadelake', '--threads=1', '--build-threads=32', '--use-perf=all',
                            '--benchmarking-only', '--exec-multisample=4', '--exclude-stat-from-submission=compile'],
                    env={'PATH':'/usr/bin/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                    extra_cmake_args=[
                        "-DCMAKE_C_FLAGS='-march=cascadelake'",
                        "-DCMAKE_CXX_FLAGS='-march=cascadelake'",
                        "-DLLVM_TARGETS_TO_BUILD='X86'"],
                    submitURL='http://lnt.llvm.org/submitRun',
                    testerName='LNT-Cascadelake-AVX2-O1')},

    {'name' : "llvm-avr-linux",
    'tags'  : ["clang"],
    'workernames' : ["avr-build-01"],
    'builddir': "llvm-avr-linux",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=8,
                    clean=False,
                    checkout_lld=False,
                    extra_cmake_args=[
                        '-DLLVM_ENABLE_ASSERTIONS=ON',
                        # We need to compile the X86 backend due to a few generic CodeGen tests.
                        '-DLLVM_TARGETS_TO_BUILD=X86',
                        '-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=AVR',
                        '-DBUILD_SHARED_LIBS=ON'])},

    {'name' : "clang-xcore-ubuntu-20-x64",
    'tags'  : ["clang"],
    'workernames' : ["xcore-ubuntu20-x64"],
    'builddir': "clang-xcore-ubuntu-20-x64",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=4,
                    checkout_clang_tools_extra=False,
                    checkout_compiler_rt=False,
                    checkout_lld=False,
                    testStage1=True,
                    useTwoStage=False,
                    stage1_config='Release',
                    extra_cmake_args=[
                        "-DLLVM_TARGETS_TO_BUILD:STRING=XCore",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE:STRING=xcore-unknown-unknown-elf",
                        "-DLLVM_ENABLE_THREADS:BOOL=OFF"])},

    {'name' : "llvm-clang-x86_64-sie-win",
    'tags'  : ["llvm", "clang", "clang-tools-extra", "lld", "cross-project-tests"],
    'workernames' : ["sie-win-worker"],
    'builddir': "llvm-clang-x86_64-sie-win",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    vs="autodetect",
                    target_arch='x64',
                    depends_on_projects=['llvm','clang','clang-tools-extra','lld','cross-project-tests'],
                    clean=True,
                    extra_configure_args=[
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_CLANGD=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=x86_64-sie-ps5",
                        "-DLLVM_INCLUDE_EXAMPLES=OFF",
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DLLVM_VERSION_SUFFIX=",
                        "-DLLVM_BUILD_RUNTIME=OFF",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=--verbose",
                        "-DPYTHON_EXECUTABLE=C:\Python310\python.exe"])},

    {'name': "cross-project-tests-sie-ubuntu",
    'tags'  : ["clang", "llvm", "lldb", "cross-project-tests"],
    'workernames': ["doug-worker-1a"],
    'builddir': "cross-project-tests-sie-ubuntu",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm','clang','lldb','cross-project-tests'],
                    checks = ['check-cross-project'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=gcc",
                        "-DCMAKE_CXX_COMPILER=g++",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DLLDB_ENABLE_PYTHON=TRUE",
                        "-DLLVM_INCLUDE_EXAMPLES=OFF",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=--verbose",
                        "-DLLVM_PARALLEL_LINK_JOBS=8",
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DLLVM_USE_LINKER=gold"])},

    {'name': "cross-project-tests-sie-ubuntu-dwarf5",
    'tags'  : ["clang", "llvm", "lldb", "cross-project-tests"],
    'workernames': ["doug-worker-1b"],
    'builddir': "cross-project-tests-sie-ubuntu-dwarf5",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm','clang','lldb','cross-project-tests'],
                    checks = ['check-cross-project'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=gcc",
                        "-DCMAKE_CXX_COMPILER=g++",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DLLDB_ENABLE_PYTHON=TRUE",
                        "-DLLVM_INCLUDE_EXAMPLES=OFF",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=--verbose",
                        "-DLLVM_PARALLEL_LINK_JOBS=8",
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DLLVM_USE_LINKER=gold"])},

    {'name': "llvm-clang-x86_64-gcc-ubuntu",
    'tags'  : ["llvm", "clang", "clang-tools-extra", "compiler-rt", "lld", "cross-project-tests"],
    'workernames': ["doug-worker-2a"],
    'builddir': "llvm-clang-x86_64-gcc-ubuntu",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm','clang','clang-tools-extra','compiler-rt','lld','cross-project-tests'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=gcc",
                        "-DCMAKE_CXX_COMPILER=g++",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCLANG_ENABLE_CLANGD=OFF",
                        "-DLLVM_BUILD_RUNTIME=ON",
                        "-DLLVM_BUILD_TESTS=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_INCLUDE_EXAMPLES=OFF",
                        "-DLLVM_LIT_ARGS=--verbose -j48",
                        "-DLLVM_PARALLEL_LINK_JOBS=16",
                        "-DLLVM_USE_LINKER=gold"])},

# Polly builders.

    {'name' : "polly-arm-linux",
    'tags'  : ["polly"],
    'workernames' : ["hexagon-build-02", "hexagon-build-03"],
    'builddir': "polly-arm-linux",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=True,
                    install=True,
                    make='ninja',
                    jobs=16,
                    env={'LD_LIBRARY_PATH': '/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/lib'},
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=arm-linux-gnueabi",
                        "-DLLVM_TARGET_ARCH=arm-linux-gnueabi",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=OFF",
                        "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang",
                        "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang++"])},

    {'name' : "polly-x86_64-linux",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce1"],
    'builddir': "polly-x86_64-linux",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON"
                        ])},

    {'name' : "polly-x86_64-linux-plugin",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce1"],
    'builddir': "polly-x86_64-linux-plugin",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DLLVM_POLLY_LINK_INTO_TOOLS=OFF",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=OFF"  # Not all required symbols available in opt executable
                        ])},

    {'name' : "polly-x86_64-linux-noassert",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce1"],
    'builddir': "polly-x86_64-linux-noassert",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=False",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON"
                        ])},

    {'name' : "polly-x86_64-linux-shared",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce2"],
    'builddir': "polly-x86_64-linux-shared",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON"
                        ])},

    {'name' : "polly-x86_64-linux-shared-plugin",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce2"],
    'builddir': "polly-x86_64-linux-shared-plugin",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_POLLY_LINK_INTO_TOOLS=OFF",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON"
                        ])},

    {'name' : "polly-x86_64-linux-shlib",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce2"],
    'builddir': "polly-x86_64-linux-shlib",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DLLVM_BUILD_LLVM_DYLIB=ON",
                        "-DLLVM_LINK_LLVM_DYLIB=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON"
                        ])},

    {'name' : "polly-x86_64-linux-shlib-plugin",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-gce2"],
    'builddir': "polly-x86_64-linux-shlib-plugin",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DLLVM_BUILD_LLVM_DYLIB=ON",
                        "-DLLVM_LINK_LLVM_DYLIB=ON",
                        "-DLLVM_POLLY_LINK_INTO_TOOLS=OFF",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON"
                        ])},

    {'name' : "polly-x86_64-linux-test-suite",
    'tags'  : ["polly"],
    'workernames' : ["polly-x86_64-fdcserver", "minipc-1050ti-linux"],
    'builddir': "polly-x86_64-linux-test-suite",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=False,
                    install=False,
                    make='ninja',
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF"
                        ],
                    testsuite=True,
                    extraTestsuiteCmakeArgs=[
                        "-G", "Ninja",
                        "-DTEST_SUITE_COLLECT_COMPILE_TIME=OFF",
                        "-DTEST_SUITE_COLLECT_STATS=OFF",
                        "-DTEST_SUITE_COLLECT_CODE_SIZE=OFF",
                        WithProperties("-DTEST_SUITE_EXTERNALS_DIR=%(builddir)s/../../test-suite-externals"),
                      ]
                    )},

# AOSP builders.

    {'name' : "aosp-O3-polly-before-vectorizer-unprofitable",
    'tags'  : ["polly", "aosp"],
    'workernames' : ["hexagon-build-03"],
    'builddir': "aosp",
    'factory' : AOSPBuilder.getAOSPBuildFactory(
                    device="angler",
                    extra_cmake_args=[
                        "-G", "Ninja",
                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=arm-linux-androideabi",
                        "-DLLVM_TARGET_ARCH=arm-linux-androideabi",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=OFF",
                        "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang",
                        "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang++"],
                    timeout=240,
                    target_clang=None,
                    target_flags="-Wno-error -O3 -mllvm -polly -mllvm -polly-position=before-vectorizer -mllvm -polly-process-unprofitable -fcommon",
                    jobs=32,
                    extra_make_args=None,
                    env={'LD_LIBRARY_PATH': '/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/lib'},
                    clean=False,
                    sync=False,
                    patch=None)},

# Reverse iteration builders.

    {'name' : "reverse-iteration",
    'tags'  : ["rev_iter"],
    'workernames' : ["hexagon-build-02", "hexagon-build-03"],
    'builddir': "reverse-iteration",
    'factory' : PollyBuilder.getPollyBuildFactory(
                    clean=True,
                    make='ninja',
                    jobs=16,
                    checkAll=True,
                    env={'LD_LIBRARY_PATH': '/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/lib'},
                    extraCmakeArgs=[
                        "-G", "Ninja",
                        "-DLLVM_REVERSE_ITERATION:BOOL=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=True",
                        "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                        "-DPOLLY_ENABLE_GPGPU_CODEGEN=ON",
                        "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang",
                        "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-12.0.0-x86_64-linux-gnu-ubuntu-16.04/bin/clang++"])},

# LLDB builders.

    {'name' : "lldb-x86_64-debian",
    'tags'  : ["lldb"],
    'workernames' : ["lldb-x86_64-debian"],
    'builddir': "lldb-x86_64-debian",
    'factory' : LLDBBuilder.getLLDBCMakeBuildFactory(
                    test=True,
                    extra_cmake_args=[
                        '-DLLVM_ENABLE_ASSERTIONS=True',
                        '-DLLVM_USE_LINKER=gold',
                        '-DLLDB_ENABLE_PYTHON=True',
                        '-DLLDB_TEST_USER_ARGS=-t',
                        '-DPYTHON_EXECUTABLE=/usr/bin/python3',
                        '-DCMAKE_C_COMPILER=clang',
                        '-DCMAKE_CXX_COMPILER=clang++'])},

    {'name' : "lldb-aarch64-ubuntu",
    'tags'  : ["lldb"],
    'workernames' : ["linaro-lldb-aarch64-ubuntu"],
    'builddir': "lldb-aarch64-ubuntu",
    'factory' : LLDBBuilder.getLLDBCMakeBuildFactory(
                    test=True,
                    clean=True,
                    extra_cmake_args=[
                        '-DLLVM_ENABLE_ASSERTIONS=True',
                        '-DLLVM_LIT_ARGS=-svj 4',
                        '-DLLVM_USE_LINKER=gold'])},

    {'name' : "lldb-arm-ubuntu",
    'tags'  : ["lldb"],
    'workernames' : ["linaro-lldb-arm-ubuntu"],
    'builddir': "lldb-arm-ubuntu",
    'factory' : LLDBBuilder.getLLDBCMakeBuildFactory(
                    test=True,
                    clean=True,
                    extra_cmake_args=[
                        '-DLLVM_ENABLE_ASSERTIONS=True',
                        '-DLLVM_LIT_ARGS=-svj 4',
                        '-DLLVM_USE_LINKER=gold'])},

    {'name' : "lldb-x64-windows-ninja",
    'tags'  : ["lldb"],
    'workernames' : ["win-py3-buildbot"],
    'builddir': "lldb-x64-windows-ninja",
    'factory' : LLDBBuilder.getLLDBCMakeBuildFactory(
                    clean=True,
                    target_arch='x64',
                    vs="autodetect",
                    test=True,
                    extra_cmake_args=[
                        '-DLLDB_ENABLE_PYTHON=TRUE',
                        '-DLLDB_TEST_USER_ARGS=--skip-category=watchpoint',
                        '-DLLVM_ENABLE_ASSERTIONS=OFF',
                        '-DLLVM_ENABLE_ZLIB=FALSE',
                        '-DLLVM_LIT_ARGS=-vj 8'])},

    {'name' : "lldb-aarch64-windows",
    'tags'  : ["lldb"],
    'workernames' : ["linaro-armv8-windows-msvc-05"],
    'builddir': "lldb-aarch64-windows",
    'factory' : LLDBBuilder.getLLDBCMakeBuildFactory(
                    clean=True,
                    test=True,
                    extra_cmake_args=[
                        "-DCMAKE_C_COMPILER_LAUNCHER=sccache",
                        "-DCMAKE_CXX_COMPILER_LAUNCHER=sccache",
                        '-DLLDB_TEST_USER_ARGS=--skip-category=watchpoint'])},

# LLD builders.

    {'name' : "lld-x86_64-win",
    'tags'  : ["lld"],
    'workernames' : ["as-worker-93"],
    'builddir': "lld-x86_64-win",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    depends_on_projects=['llvm', 'lld'],
                    vs="autodetect",
                    extra_configure_args = [
                        '-DLLVM_ENABLE_WERROR=OFF'])},

    {'name' : "ppc64le-lld-multistage-test",
    'tags'  : ["lld", "ppc", "ppc64le"],
    'workernames' : ["ppc64le-lld-multistage-test"],
    'builddir': "ppc64le-lld-multistage-test",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaMultistageBuildFactory(
                    extra_configure_args=[
                        '-DLLVM_ENABLE_ASSERTIONS=ON',
                        '-DLLVM_LIT_ARGS=-svj 256',
                        '-DLLVM_CCACHE_BUILD=ON'],
                    depends_on_projects=['llvm', 'clang', 'lld'])},

    {'name' : "lld-x86_64-ubuntu-fast",
    'tags'  : ["lld"],
    'collapseRequests': False,
    'workernames' : ["as-builder-4"],
    'builddir' : "lld-x86_64-ubuntu-fast",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                            clean=True,
                            extra_configure_args=[
                                '-DLLVM_ENABLE_WERROR=OFF'],
                            depends_on_projects=['llvm', 'lld'])},

    {'name' : "lld-perf-testsuite",
    'tags'  : ["lld","performance"],
    'workernames' : ["as-worker-5"],
    'builddir' : "lld-perf-testsuite",
    'factory' : LLDPerformanceTestsuite.getFactory(targets=["bin/lld"])},

# LTO and ThinLTO builders.

    {'name' : "clang-with-thin-lto-ubuntu",
    'tags'  : ["clang","lld","LTO"],
    'workernames' : ["as-worker-92"],
    'builddir': "clang-with-thin-lto-ubuntu",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(
                    jobs=72,
                    lto='thin',
                    )},

    {'name' : "clang-with-thin-lto-wpd-ubuntu",
    'tags'  : ["clang","lld","LTO"],
    'workernames' : ["thinlto-x86-64-bot1", "thinlto-x86-64-bot2"],
    'builddir': "clang-with-thin-lto-wpd-ubuntu",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(
                    jobs=72,
                    lto='thin',
                    extra_configure_args=[
                        '-DLLVM_CCACHE_BUILD=ON',
                    ],
                    extra_configure_args_lto_stage=[
                        '-DCMAKE_CXX_FLAGS=-O3 -Xclang -fwhole-program-vtables -fno-split-lto-unit',
                        '-DCMAKE_C_FLAGS=-O3 -Xclang -fwhole-program-vtables -fno-split-lto-unit',
                        '-DCMAKE_EXE_LINKER_FLAGS=-Wl,--lto-whole-program-visibility -fuse-ld=lld'])},

    {'name' : "clang-with-lto-ubuntu",
    'tags'  : ["clang","lld","LTO"],
    'workernames' : ["as-worker-91"],
    'builddir': "clang-with-lto-ubuntu",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(
                    jobs=72,
                    extra_configure_args_lto_stage=[
                        '-DLLVM_PARALLEL_LINK_JOBS=14',
                    ])},
]

# Common builders options for MLIR.
mlir_ubuntu_workers = [f"mlir-ubuntu-worker{i}" for i in range(5)]
mlir_default_cmake_options = [
  '-DLLVM_CCACHE_BUILD=ON',
  '-DLLVM_ENABLE_PROJECTS=mlir',
  '-DLLVM_TARGETS_TO_BUILD=host;NVPTX;AMDGPU',
  '-DLLVM_BUILD_EXAMPLES=ON',
  '-DMLIR_INCLUDE_INTEGRATION_TESTS=ON',
  '-DMLIR_ENABLE_BINDINGS_PYTHON=ON',
]

all += [

    {'name' : "mlir-ubuntu-asan-ubsan-clang-12.0",
    'tags'  : ["mlir"],
    'workernames' : mlir_ubuntu_workers,
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    llvm_srcdir="llvm.src",
                    obj_dir="llvm.obj",
                    clean=True,
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    depends_on_projects=['llvm','mlir'],
                    extra_configure_args= mlir_default_cmake_options + [
                        '-DLLVM_ENABLE_LLD=ON',
                        '-DBUILD_SHARED_LIBS=ON',
                        '-DLLVM_USE_SANITIZER=Address;Undefined',
                        '-DCMAKE_C_COMPILER=/compilers/clang-12.0/bin/clang',
                        '-DCMAKE_CXX_COMPILER=/compilers/clang-12.0/bin/clang++',
                    ])},

    {'name' : "mlir-ubuntu-gcc5.5-shared-libs",
    'tags'  : ["mlir"],
    'workernames' : mlir_ubuntu_workers,
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    llvm_srcdir="llvm.src",
                    obj_dir="llvm.obj",
                    clean=True,
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    depends_on_projects=['llvm','mlir'],
                    extra_configure_args= mlir_default_cmake_options + [
                        '-DBUILD_SHARED_LIBS=ON',
                        '-DCMAKE_C_COMPILER=/usr/bin/gcc-5',
                        '-DCMAKE_CXX_COMPILER=/usr/bin/g++-5',
                    ])},

    {'name' : "mlir-ubuntu-clang-5-link-llvm-dylib",
    'tags'  : ["mlir"],
    'workernames' : mlir_ubuntu_workers,
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    llvm_srcdir="llvm.src",
                    obj_dir="llvm.obj",
                    clean=True,
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    depends_on_projects=['llvm','mlir'],
                    extra_configure_args= mlir_default_cmake_options + [
                        '-DLLVM_ENABLE_LLD=OFF', # lld-5 is subject to http://llvm.org/pr49915
                        '-DLLVM_LINK_LLVM_DYLIB=ON',
                        '-DCMAKE_C_COMPILER=/compilers/clang-5.0/bin/clang',
                        '-DCMAKE_CXX_COMPILER=/compilers/clang-5.0/bin/clang++',
                    ])},

    {'name' : "mlir-ubuntu-gcc11-release-intel-sde",
    'tags'  : ["mlir"],
    'workernames' : mlir_ubuntu_workers,
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    llvm_srcdir="llvm.src",
                    obj_dir="llvm.obj",
                    clean=True,
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    depends_on_projects=['llvm','mlir'],
                    extra_configure_args= mlir_default_cmake_options + [
                        '-DLLVM_ENABLE_LLD=ON',
                        '-DLLVM_ENABLE_ASSERTIONS=OFF',
                        '-DCMAKE_C_COMPILER=/usr/bin/gcc-11',
                        '-DCMAKE_CXX_COMPILER=/usr/bin/g++-11',
                        '-DMLIR_RUN_X86VECTOR_TESTS=ON',
                        '-DMLIR_RUN_AMX_TESTS=ON',
                        '-DINTEL_SDE_EXECUTABLE=/intel_sde/sde64'
                    ])},

    {'name' : "mlir-nvidia",
    'tags'  : ["mlir"],
    'workernames' : ["mlir-nvidia"],
    'builddir': "mlir-nvidia",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    llvm_srcdir="llvm.src",
                    obj_dir="llvm.obj",
                    clean=True,
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    depends_on_projects=['llvm','mlir'],
                    extra_configure_args=[
                        '-DLLVM_BUILD_EXAMPLES=ON',
                        '-DLLVM_TARGETS_TO_BUILD=host;NVPTX',
                        '-DLLVM_ENABLE_PROJECTS=mlir',
                        '-DMLIR_ENABLE_CUDA_RUNNER=1',
                        '-DMLIR_INCLUDE_INTEGRATION_TESTS=ON',
                        '-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc',
                        '-DMLIR_ENABLE_VULKAN_RUNNER=1',
                        '-DBUILD_SHARED_LIBS=ON',
                        '-DLLVM_CCACHE_BUILD=ON',
                        '-DMLIR_ENABLE_BINDINGS_PYTHON=ON',
                        '-DMLIR_RUN_CUDA_TENSOR_CORE_TESTS=ON',
                    ],
                    env={
                        'CC':'clang',
                        'CXX': 'clang++',
                        'LD': 'lld',
                    })},

    {'name' : "mlir-windows",
    'tags'  : ["mlir"],
    'workernames' : ["win-mlir-buildbot"],
    'builddir': "mlir-x64-windows-ninja",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    clean=True,
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    depends_on_projects=['llvm','mlir'],
                    vs="autodetect",
                    extra_configure_args=[
                        "-DLLVM_BUILD_EXAMPLES=ON",
                        "-DLLVM_ENABLE_PROJECTS=mlir",
                        "-DMLIR_ENABLE_BINDINGS_PYTHON=ON",
                        "-DLLVM_ENABLE_WERROR=ON",
                        "-DLLVM_TARGETS_TO_BUILD='host;NVPTX;AMDGPU'",
                    ])},

    {'name' : 'ppc64le-mlir-rhel-clang',
    'tags'  : ["mlir", "ppc", "ppc64le"],
    'collapseRequests' : False,
    'workernames' : ['ppc64le-mlir-rhel-test'],
    'builddir': 'ppc64le-mlir-rhel-clang-build',
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm', 'mlir'],
                    targets = ['check-mlir-build-only'],
                    checks = ['check-mlir'],
                    extra_configure_args=[
                        '-DLLVM_TARGETS_TO_BUILD=PowerPC',
                        '-DLLVM_INSTALL_UTILS=ON',
                        '-DCMAKE_CXX_STANDARD=17',
                        '-DLLVM_ENABLE_PROJECTS=mlir',
                        '-DLLVM_LIT_ARGS=-vj 256',
                        '-DLLVM_CCACHE_BUILD=ON',
                    ],
                    env={
                            'CC': 'clang',
                            'CXX': 'clang++',
                            'LD': 'lld',
                            'LD_LIBRARY_PATH': '/usr/lib64',
                    })},

    {'name' : 'mlir-s390x-linux',
    'tags'  : ["mlir", "s390x"],
    'workernames' : ["systemz-1"],
    'builddir': 'mlir-s390x-linux',
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm', 'mlir'],
                    checks=['check-mlir'],
                    extra_configure_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        '-DLLVM_TARGETS_TO_BUILD=SystemZ',
                        '-DLLVM_ENABLE_PROJECTS=mlir',
                        '-DLLVM_LIT_ARGS=-vj 4',
                    ])},

# Sanitizer builders.
#
# bootstrap-asan, bootstrap-msan, and sanitizer-x86_64-linux-fast have steps
# with large memory usage, so assign them to different workers.

    {'name' : "sanitizer-x86_64-linux",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot1",
        "sanitizer-buildbot2",
    ],
    'builddir': "sanitizer-x86_64-linux",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory()},

    {'name' : "sanitizer-x86_64-linux-fast",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot3",
        "sanitizer-buildbot4",
    ],
    'builddir': "sanitizer-x86_64-linux-fast",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-x86_64-linux-bootstrap-asan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot1",
        "sanitizer-buildbot2",
    ],
    'builddir': "sanitizer-x86_64-linux-bootstrap-asan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-x86_64-linux-bootstrap-msan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot5",
        "sanitizer-buildbot6",
    ],
    'builddir': "sanitizer-x86_64-linux-bootstrap-msan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-x86_64-linux-bootstrap-ubsan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot3",
        "sanitizer-buildbot4",
    ],
    'builddir': "sanitizer-x86_64-linux-bootstrap-ubsan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-x86_64-linux-autoconf",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot5",
        "sanitizer-buildbot6",
    ],
    'builddir': "sanitizer-x86_64-linux-autoconf",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory()},

    {'name' : "sanitizer-x86_64-linux-qemu",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot3",
        "sanitizer-buildbot4",
    ],
    'builddir': "sanitizer-x86_64-linux-qemu",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory()},

    {'name' : "sanitizer-x86_64-linux-fuzzer",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot1",
        "sanitizer-buildbot2",
    ],
    'builddir': "sanitizer-x86_64-linux-fuzzer",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory()},

    {'name' : "sanitizer-x86_64-linux-android",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot-android",
    ],
    'builddir': "sanitizer-x86_64-linux-android",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory()},

    {'name' : "sanitizer-aarch64-linux-bootstrap-asan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot7",
        "sanitizer-buildbot9",
        "sanitizer-buildbot11",
    ],
    'builddir': "sanitizer-aarch64-linux-bootstrap-asan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-aarch64-linux-bootstrap-hwasan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot7",
        "sanitizer-buildbot9",
        "sanitizer-buildbot11",
    ],
    'builddir': "sanitizer-aarch64-linux-bootstrap-hwasan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-aarch64-linux-bootstrap-msan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot8",
        "sanitizer-buildbot10",
        "sanitizer-buildbot12",
    ],
    'builddir': "sanitizer-aarch64-linux-bootstrap-msan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-aarch64-linux-bootstrap-ubsan",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot8",
        "sanitizer-buildbot10",
        "sanitizer-buildbot12",
    ],
    'builddir': "sanitizer-aarch64-linux-bootstrap-ubsan",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(
        extra_depends_on_projects=["mlir", "clang-tools-extra"]
    )},

    {'name' : "sanitizer-aarch64-linux-fuzzer",
    'tags'  : ["sanitizer"],
    'workernames' : [
        "sanitizer-buildbot8",
        "sanitizer-buildbot10",
        "sanitizer-buildbot12",
    ],
    'builddir': "sanitizer-aarch64-linux-fuzzer",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory()},

    {'name' : "sanitizer-ppc64be-linux",
    'tags'  : ["sanitizer", "ppc"],
    'workernames' : ["ppc64be-sanitizer"],
    'builddir': "sanitizer-ppc64be",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(timeout=1800)},

    {'name' : "sanitizer-ppc64le-linux",
    'tags'  : ["sanitizer", "ppc", "ppc64le"],
    'workernames' : ["ppc64le-sanitizer"],
    'builddir': "sanitizer-ppc64le",
    'factory' : SanitizerBuilder.getSanitizerBuildFactory(timeout=1800)},

    {'name' : "sanitizer-windows",
    'tags'  : ["sanitizer"],
    'workernames' : ["sanitizer-windows"],
    'builddir': "sanitizer-windows",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="sanitizer-windows.py",
                    depends_on_projects=["llvm", "clang", "lld", "compiler-rt"])},

# OpenMP builders.

    {'name' : "openmp-gcc-x86_64-linux-debian",
    'tags'  : ["openmp"],
    'workernames' : ["gribozavr4"],
    'builddir': "openmp-gcc-x86_64-linux-debian",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                    extraCmakeArgs=[
                        '-DLLVM_CCACHE_BUILD=ON',
                    ],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'clang', 'CXX': 'clang++',
                    })},

    {'name' : "openmp-clang-x86_64-linux-debian",
    'tags'  : ["openmp"],
    'workernames' : ["gribozavr4"],
    'builddir': "openmp-clang-x86_64-linux-debian",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                    extraCmakeArgs=[
                        '-DLLVM_CCACHE_BUILD=ON',
                    ],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'clang', 'CXX': 'clang++',
                    })},

    {'name' : "openmp-offload-cuda-project",
    'tags'  : ["openmp"],
    'workernames' : ["minipc-1050ti-linux"],
    'builddir': "openmp-offload-cuda-project",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                        clean=False,
                        enable_runtimes=[],
                        extraCmakeArgs=[
                                "-DCUDA_TOOLKIT_ROOT_DIR=/opt/cuda",
                                "-DLIBOMPTARGET_BUILD_NVPTX_BCLIB=ON",
                                "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                                "-DCLANG_ENABLE_ARCMT=OFF",
                                "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                                "-DLLVM_TARGETS_TO_BUILD=X86;NVPTX",
                                "-DLLVM_ENABLE_LLD=ON",
                                '-DLLVM_PARALLEL_LINK_JOBS=2',
                            ],
                        install=True,
                        testsuite=True,
                        testsuite_sollvevv=True,
                        extraTestsuiteCmakeArgs=[
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_CFLAGS=-fopenmp-targets=nvptx64-nvidia-cuda;--cuda-path=/opt/cuda",
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_LDFLAGS=-fopenmp-targets=nvptx64-nvidia-cuda;--cuda-path=/opt/cuda",
                        ],
                    )},

    {'name' : "openmp-offload-cuda-runtime",
    'tags'  : ["openmp"],
    'workernames' : ["minipc-1050ti-linux"],
    'builddir': "openmp-offload-cuda-runtime",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                        clean=True,
                        enable_runtimes=['openmp'],
                        extraCmakeArgs=[
                                "-DCUDA_TOOLKIT_ROOT_DIR=/opt/cuda",
                                "-DLIBOMPTARGET_BUILD_NVPTX_BCLIB=ON",
                                "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                                "-DCLANG_ENABLE_ARCMT=OFF",
                                "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                                "-DLLVM_TARGETS_TO_BUILD=X86;NVPTX",
                                "-DLLVM_ENABLE_LLD=ON",
                                '-DLLVM_PARALLEL_LINK_JOBS=2',
                                "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                                "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                            ],
                        install=True,
                        testsuite=True,
                        testsuite_sollvevv=True,
                        extraTestsuiteCmakeArgs=[
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_CFLAGS=-fopenmp-targets=nvptx64-nvidia-cuda;--cuda-path=/opt/cuda",
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_LDFLAGS=-fopenmp-targets=nvptx64-nvidia-cuda;--cuda-path=/opt/cuda",
                        ],
                    )},

# OpenMP AMDGPU Builders
    {'name' : "openmp-offload-amdgpu-runtime",
    'tags'  : ["openmp"],
    'workernames' : ["omp-vega20-0"],
    'builddir': "openmp-offload-amdgpu-runtime",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                        clean=True,
                        enable_runtimes=['openmp'],
                        depends_on_projects=['llvm','clang','lld','openmp'],
                        extraCmakeArgs=[
                            "-DCMAKE_BUILD_TYPE=Release",
                            "-DCLANG_DEFAULT_LINKER=lld",
                            "-DLLVM_TARGETS_TO_BUILD=X86;AMDGPU",
                            "-DLLVM_ENABLE_ASSERTIONS=ON",
                            "-DLLVM_ENABLE_RUNTIMES=openmp",
                            "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                            "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                            ],
                        install=True,
                        testsuite=False,
                        testsuite_sollvevv=False,
                        extraTestsuiteCmakeArgs=[
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_CFLAGS=-fopenmp-targets=amdgcn-amd-amdhsa;-Xopenmp-target=amdgcn-amd-amdhsa",
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_LDLAGS=-fopenmp-targets=amdgcn-amd-amdhsa;-Xopenmp-target=amdgcn-amd-amdhsa",
                        ],
                    )},

    {'name' : "openmp-offload-amdgpu-runtime-experimental",
    'tags'  : ["openmp"],
    'workernames' : ["omp-vega20-1"],
    'builddir': "openmp-offload-amdgpu-runtime-experimental",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                        clean=True,
                        enable_runtimes=['openmp'],
                        depends_on_projects=['llvm','clang','lld','openmp'],
                        extraCmakeArgs=[
                            "-DCMAKE_BUILD_TYPE=Release",
                            "-DCLANG_DEFAULT_LINKER=lld",
                            "-DLLVM_TARGETS_TO_BUILD=X86;AMDGPU",
                            "-DLLVM_ENABLE_ASSERTIONS=ON",
                            "-DLLVM_ENABLE_RUNTIMES=openmp",
                            "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                            "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                            "-DLIBOMPTARGET_FOUND_AMDGPU_GPU=ON",
                            ],
                        install=True,
                        testsuite=False,
                        testsuite_sollvevv=False,
                        extraTestsuiteCmakeArgs=[
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_CFLAGS=-fopenmp;-fopenmp-targets=amdgcn-amd-amdhsa;-Xopenmp-target=amdgcn-amd-amdhsa;-march=gfx906",
                            "-DTEST_SUITE_SOLLVEVV_OFFLOADING_LDLAGS=-fopenmp;-fopenmp-targets=amdgcn-amd-amdhsa;-Xopenmp-target=amdgcn-amd-amdhsa;-march=gfx906",
                        ],
                    )},


# Whole-toolchain builders.

    {'name': "fuchsia-x86_64-linux",
    'tags'  : ["toolchain"],
    'workernames' :["fuchsia-debian-64-us-central1-a-1", "fuchsia-debian-64-us-central1-b-1"],
    'builddir': "fuchsia-x86_64-linux",
    'factory': FuchsiaBuilder.getFuchsiaToolchainBuildFactory()},

# libc Builders.

    {'name' : 'libc-x86_64-windows-dbg',
    'tags'  : ["libc"],
    'workernames' : ['libc-x86_64-windows'],
    'builddir': 'libc-x86_64-windows',
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-windows.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : 'libc-arm32-debian-dbg',
    'tags'  : ["libc"],
    'workernames' : ['libc-arm32-debian'],
    'builddir': 'libc-arm32-debian-dbg',
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : 'libc-aarch64-ubuntu-dbg',
    'tags'  : ["libc"],
    'workernames' : ['libc-aarch64-ubuntu'],
    'builddir': 'libc-aarch64-ubuntu',
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : "libc-aarch64-ubuntu-fullbuild-dbg",
    'tags'  : ["libc"],
    'workernames' : ["libc-aarch64-ubuntu"],
    'builddir': "libc-aarch64-ubuntu-fullbuild-dbg",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : 'libc-x86_64-debian',
    'tags'  : ["libc"],
    'workernames' : ['libc-x86_64-debian'],
    'builddir': 'libc-x86_64-debian',
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'])},

    {'name' : "libc-x86_64-debian-dbg",
    'tags'  : ["libc"],
    'workernames' : ["libc-x86_64-debian"],
    'builddir': "libc-x86_64-debian-dbg",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : "libc-x86_64-debian-dbg-asan",
    'tags'  : ["libc"],
    'workernames' : ["libc-x86_64-debian"],
    'builddir': "libc-x86_64-debian-dbg-asan",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug', '--asan'])},

    {'name' : "libc-x86_64-debian-dbg-runtimes-build",
    'tags'  : ["libc"],
    'workernames' : ["libc-x86_64-debian"],
    'builddir': "libc-x86_64-debian-dbg-runtimes-build",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : "libc-x86_64-debian-fullbuild-dbg",
    'tags'  : ["libc"],
    'workernames' : ["libc-x86_64-debian-fullbuild"],
    'builddir': "libc-x86_64-debian-fullbuild-dbg",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : "libc-x86_64-debian-gcc-fullbuild-dbg",
    'tags'  : ["libc"],
    'workernames' : ["libc-x86_64-debian-fullbuild"],
    'builddir': "libc-x86_64-debian-gcc-fullbuild-dbg",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug'])},

    {'name' : "libc-x86_64-debian-fullbuild-dbg-asan",
    'tags'  : ["libc"],
    'workernames' : ["libc-x86_64-debian-fullbuild"],
    'builddir': "libc-x86_64-debian-fullbuild-dbg-asan",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="libc-linux.py",
                    depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
                    extra_args=['--debug', '--asan'])},

# Flang builders.

    {'name' : "flang-aarch64-dylib",
    'tags'  : ["flang"],
    'workernames' : ["linaro-flang-aarch64-dylib"],
    'builddir': "flang-aarch64-dylib",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DLLVM_BUILD_LLVM_DYLIB=ON",
                        "-DLLVM_LINK_LLVM_DYLIB=ON",
                        "-DCMAKE_CXX_STANDARD=17",
                    ])},

    {'name' : "flang-aarch64-sharedlibs",
    'tags'  : ["flang"],
    'workernames' : ["linaro-flang-aarch64-sharedlibs"],
    'builddir': "flang-aarch64-sharedlibs",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_BUILD_EXAMPLES=ON",
                        "-DFLANG_BUILD_EXAMPLES=ON",
                        "-DCMAKE_CXX_STANDARD=17",
                    ])},

    {'name' : "flang-aarch64-out-of-tree",
    'tags'  : ["flang"],
    'workernames' : ["linaro-flang-aarch64-out-of-tree"],
    'builddir': "flang-aarch64-out-of-tree",
    'factory' : FlangBuilder.getFlangOutOfTreeBuildFactory(
                    checks=['check-flang'],
                    llvm_extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DCMAKE_CXX_STANDARD=17",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                    ],
                    flang_extra_configure_args=[
                        "-DFLANG_ENABLE_WERROR=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                    ])},

    {'name' : "flang-aarch64-debug",
    'tags'  : ["flang"],
    'workernames' : ["linaro-flang-aarch64-debug"],
    'builddir': "flang-aarch64-debug",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DCMAKE_BUILD_TYPE=Debug",
                        "-DCMAKE_CXX_STANDARD=17",
                        "-DLLVM_USE_LINKER=lld",
                    ])},

    {'name' : "flang-aarch64-latest-clang",
    'tags'  : ['flang'],
    'workernames' : ["linaro-flang-aarch64-latest-clang"],
    'builddir': "flang-aarch64-latest-clang",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DLLVM_INSTALL_UTILS=ON",
                        "-DCMAKE_CXX_STANDARD=17",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DFLANG_ENABLE_WERROR=ON",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_ENABLE_LIBCXX=On",
                        "-DCMAKE_BUILD_TYPE=Release",
                        ])},

    {'name' : "flang-aarch64-release",
    'tags'  : ["flang"],
    'workernames' : ["linaro-flang-aarch64-release"],
    'builddir': "flang-aarch64-release",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCMAKE_CXX_STANDARD=17",
                    ])},

    {'name' : "flang-aarch64-rel-assert",
    'tags'  : ["flang"],
    'workernames' : ["linaro-flang-aarch64-rel-assert"],
    'builddir': "flang-aarch64-rel-assert",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DFLANG_BUILD_EXAMPLES=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCMAKE_CXX_STANDARD=17",
                    ])},

    {'name' : "flang-aarch64-latest-gcc",
    'tags'  : ['flang'],
    'workernames' : ["linaro-flang-aarch64-latest-gcc"],
    'builddir': "flang-aarch64-latest-gcc",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    checks=['check-flang'],
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DLLVM_INSTALL_UTILS=ON",
                        "-DCMAKE_CXX_STANDARD=17",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DFLANG_ENABLE_WERROR=ON",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DCMAKE_BUILD_TYPE=Release",
                    ])},

    {'name' : "flang-x86_64-knl-linux",
    'tags'  : ["flang"],
    'workernames' : ["alcf-theta-flang"],
    'builddir': "flang-x86_64-knl-linux",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DCMAKE_C_COMPILER=gcc",
                        "-DCMAKE_CXX_COMPILER=g++",
                        "-DLLVM_INSTALL_UTILS=ON",
                        "-DCMAKE_CXX_STANDARD=17",
                    ])},

    {'name' : 'ppc64le-flang-rhel-clang',
    'tags'  : ["flang", "ppc", "ppc64le"],
    'collapseRequests' : False,
    'workernames' : ['ppc64le-flang-rhel-test'],
    'builddir': 'ppc64le-flang-rhel-clang-build',
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm', 'mlir', 'clang', 'flang'],
                    checks=['check-flang'],
                    extra_configure_args=[
                        '-DLLVM_TARGETS_TO_BUILD=PowerPC',
                        '-DLLVM_INSTALL_UTILS=ON',
                        '-DCMAKE_CXX_STANDARD=17',
                        '-DLLVM_LIT_ARGS=-vj 256',
                        '-DLLVM_CCACHE_BUILD=ON'
                    ],
                    env={
                        'CC': 'clang',
                        'CXX': 'clang++',
                        'LD': 'lld'
                    })},

    {'name' : "flang-x86_64-windows",
    'tags'  : ["flang"],
    'workernames' : ["minipc-ryzen-win"],
    'builddir': "flang-x86_64-windows",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm','mlir','clang','flang'],
                    checks=['check-flang'],
                    install_dir="flang.install",
                    extra_configure_args=[
                        "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                        "-DCLANG_ENABLE_ARCMT=OFF",
                        "-DCLANG_ENABLE_OBJC_REWRITER=OFF",
                        "-DLLVM_TARGETS_TO_BUILD=X86",
                        "-DLLVM_INSTALL_UTILS=ON",
                        "-DCMAKE_C_COMPILER=cl",
                        "-DCMAKE_CXX_COMPILER=cl",
                        "-DCMAKE_CXX_STANDARD=17",
                        '-DLLVM_PARALLEL_COMPILE_JOBS=4',
                    ])},

# Builders responsible building Sphinx documentation.

    {'name' : "llvm-sphinx-docs",
    'tags'  : ["llvm", "doc"],
    'workernames' : ["gribozavr3"],
    'builddir': "llvm-sphinx-docs",
    'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(llvm_html=True, llvm_man=True)},

    {'name' : "clang-sphinx-docs",
    'tags'  : ["clang", "doc"],
    'workernames' : ["gribozavr3"],
    'builddir': "clang-sphinx-docs",
    'factory' : SphinxDocsBuilder.getSphinxDocsBuildFactory(clang_html=True)},

    {'name' : "clang-tools-sphinx-docs",
    'tags'  : ["clang-tools", "doc"],
    'workernames':["gribozavr3"],
    'builddir':"clang-tools-sphinx-docs",
    'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(clang_tools_html=True)},

    {'name' : "lld-sphinx-docs",
    'tags'  : ["lld", "doc"],
    'workernames' : ["gribozavr3"],
    'builddir': "lld-sphinx-docs",
    'factory' : SphinxDocsBuilder.getSphinxDocsBuildFactory(lld_html=True)},

    {'name':"libunwind-sphinx-docs",
    'tags'  : ["libunwind", "doc"],
    'workernames':["gribozavr3"],
    'builddir':"libunwind-sphinx-docs",
    'factory': SphinxDocsBuilder.getSphinxRuntimesDocsBuildFactory(libunwind_html=True)},

    # Sphinx doc Publisher
    {'name' : "publish-sphinx-docs",
    'tags'  : ["doc"],
    'workernames' : ["as-worker-4"],
    'builddir': "publish-sphinx-docs",
    'factory' : SphinxDocsBuilder.getLLVMDocsBuildFactory(clean=True)},

    {'name' : "publish-runtimes-sphinx-docs",
    'tags'  : ["doc"],
    'workernames' : ["as-worker-4"],
    'builddir': "publish-runtimes-sphinx-docs",
    'factory' : SphinxDocsBuilder.getLLVMRuntimesDocsBuildFactory(clean=True)},

    {'name' : "publish-lnt-sphinx-docs",
    'tags'  : ["doc"],
    'workernames' : ["as-worker-4"],
    'builddir': "publish-lnt-sphinx-docs",
    'factory' : HtmlDocsBuilder.getHtmlDocsBuildFactory()},

    {'name' : "publish-doxygen-docs",
    'tags'  : ["doc"],
    'workernames' : ["as-worker-4"], #FIXME: Temporarily disabled failing doxygen build - as-builder-8.
    'builddir': "publish-doxygen-docs",
    'factory' : DoxygenDocsBuilder.getLLVMDocsBuildFactory(
                    # Doxygen builds the final result for really
                    # long time without any output.
                    # We have to have a long timeout here.
                    timeout=172800)},

    {'name' : "polly-sphinx-docs",
    'tags'  : ["llvm", "doc"],
    'workernames' : ["polly-x86_64-gce1"],
    'builddir': "polly-sphinx-docs",
    'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(polly_html=True)},

# CUDA builders.

    {'name' : "clang-cuda-k80",
    'tags'  : ["clang"],
    'workernames' : ["cuda-k80-0"],
    'builddir': "clang-cuda-k80",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="/buildbot/cuda-build",
                    checkout_llvm_sources=False)},

    {'name' : "clang-cuda-p4",
    'tags'  : ["clang"],
    'workernames' : ["cuda-p4-0"],
    'builddir': "clang-cuda-p4",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="/buildbot/cuda-build",
                    checkout_llvm_sources=False)},

    {'name' : "clang-cuda-t4",
    'tags'  : ["clang"],
    'workernames' : ["cuda-t4-0"],
    'builddir': "clang-cuda-t4",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="/buildbot/cuda-build",
                    checkout_llvm_sources=False)},
# HIP builders.

    {'name' : "clang-hip-vega20",
    'tags'  : ["clang"],
    'workernames' : ["hip-vega20-0"],
    'builddir': "clang-hip-vega20",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="hip-build.sh",
                    checkout_llvm_sources=False,
                    script_interpreter=None)},

# VE builders.
    {'name' : "clang-ve-ninja",
    'tags'  : ["clang"],
    'workernames':["hpce-ve-main"],
    'builddir':"clang-ve-ninja",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="ve-linux.py",
                    depends_on_projects=['llvm', 'clang', 'compiler-rt', 'libcxx'])},
    {'name' : "clang-ve-staging",
    'tags'  : ["clang"],
    'workernames':["hpce-ve-staging"],
    'builddir':"clang-ve-staging",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="ve-linux.py",
                    depends_on_projects=['llvm', 'clang', 'compiler-rt', 'libcxx'])},

    # Build the LLVM dylib .so with all backends and link tools to it
    {'name' : 'llvm-x86_64-debian-dylib',
    'tags'  : ['llvm'],
    'collapseRequests': False,
    'workernames': ['gribozavr4'],
    'builddir': 'llvm-x86_64-debian-dylib',
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm'],
                    checks=['check-all'],
                    extra_configure_args=[
                        '-DCMAKE_BUILD_TYPE=Release',
                        '-DLLVM_ENABLE_ASSERTIONS=On',
                        '-DLLVM_BUILD_EXAMPLES=Off',
                        "-DLLVM_LIT_ARGS=-v --xunit-xml-output test-results.xml",
                        '-DLLVM_TARGETS_TO_BUILD=all',
                        '-DCMAKE_EXPORT_COMPILE_COMMANDS=1',
                        '-DLLVM_BUILD_LLVM_DYLIB=On',
                        '-DLLVM_LINK_LLVM_DYLIB=On',
                        '-DBUILD_SHARED_LIBS=Off',
                        '-DLLVM_ENABLE_LLD=Off',
                        '-DLLVM_ENABLE_BINDINGS=Off',
                        '-DLLVM_CCACHE_BUILD=ON',
                    ],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'clang', 'CXX': 'clang++',
                    })},

    {'name' : "clang-solaris11-amd64",
    'tags' : ["clang"],
    'workernames' : ["solaris11-amd64"],
    'builddir': "clang-solaris11-amd64",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=8,
                    clean=False,
                    timeout=1800,
                    checkout_lld=False,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                    '-DLLVM_TARGETS_TO_BUILD=X86',
                                    '-DLLVM_HOST_TRIPLE=amd64-pc-solaris2.11',
                                    '-DLLVM_PARALLEL_LINK_JOBS=4'])},

    {'name' : "clang-solaris11-sparcv9",
    'tags' : ["clang"],
    'workernames' : ["solaris11-sparcv9"],
    'builddir': "clang-solaris11-sparcv9",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                    jobs=8,
                    clean=False,
                    timeout=1800,
                    checkout_lld=False,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                    '-DLLVM_TARGETS_TO_BUILD=Sparc',
                                    '-DLLVM_HOST_TRIPLE=sparcv9-sun-solaris2.11',
                                    '-DLLVM_PARALLEL_LINK_JOBS=4'])},

# Builders for ML-driven compiler optimizations.

    # Development mode build bot: tensorflow C APIs are present, and
    # we can dynamically load models, and produce training logs.
    {'name' : "ml-opt-dev-x86-64",
    'tags'  : ['ml_opt'],
    'collapseRequests': False,
    'workernames' : ["ml-opt-dev-x86-64-b1", "ml-opt-dev-x86-64-b2"],
    'builddir': "ml-opt-dev-x86-64-b1",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm'],
                    extra_configure_args=[
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DTENSORFLOW_C_LIB_PATH=/tmp/tensorflow",
                        "-C", "/tmp/tflitebuild/tflite.cmake",
                        "-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON"
                    ])},

    # Both tensorflow C library, and the pip package, are present.
    {'name' : "ml-opt-devrel-x86-64",
    'tags'  : ["ml_opt"],
    'collapseRequests': False,
    'workernames' : ["ml-opt-devrel-x86-64-b1", "ml-opt-devrel-x86-64-b2"],
    'builddir': "ml-opt-devrel-x86-64-b1",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm'],
                    extra_configure_args= [
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DTENSORFLOW_C_LIB_PATH=/tmp/tensorflow",
                        "-C", "/tmp/tflitebuild/tflite.cmake",
                        "-DTENSORFLOW_AOT_PATH=/var/lib/buildbot/.local/lib/python3.7/site-packages/tensorflow",
                        "-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON"
                    ])},

    # Release mode build bot: the model is pre-built and linked in the
    # compiler. Only the tensorflow pip package is needed, and out of it,
    # only saved_model_cli (the model compiler) and the thin C++ wrappers
    # in xla_aot_runtime_src (and include files)
    {'name' : "ml-opt-rel-x86-64",
    'tags'  : ["ml_opt"],
    'collapseRequests': False,
    'workernames' : ["ml-opt-rel-x86-64-b1", "ml-opt-rel-x86-64-b2"],
    'builddir': "ml-opt-rel-x86-64-b1",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm'],
                    extra_configure_args= [
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DTENSORFLOW_AOT_PATH=/var/lib/buildbot/.local/lib/python3.7/site-packages/tensorflow"
                    ])},

    # build clangd with remote-index enabled and check with TSan
    {'name': "clangd-ubuntu-tsan",
     'tags': ["clangd"],
     'workernames': ["clangd-ubuntu-clang"],
     'builddir': "clangd-ubuntu-tsan",
     'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
         clean=True,
         depends_on_projects=["llvm", "clang", "clang-tools-extra"],
         checks=["check-clangd"],
         targets=["clangd", "clangd-index-server", "clangd-indexer"],
         extra_configure_args=[
             "-DLLVM_CCACHE_BUILD=ON",
             "-DLLVM_USE_SANITIZER=Thread",
             "-DCMAKE_BUILD_TYPE=Release",
             "-DCLANGD_ENABLE_REMOTE=ON",
             "-DLLVM_ENABLE_ASSERTIONS=ON",
             "-DGRPC_INSTALL_PATH=/usr/local/lib/grpc",
             "-DLLVM_OPTIMIZED_TABLEGEN=ON"
         ])},

    # Build in C++20 configuration.
    {'name': "clang-debian-cpp20",
     'tags': ["clang", "c++20"],
     'workernames': ["clang-debian-cpp20"],
     'builddir': "clang-debian-cpp20",
     'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
         clean=True,
         depends_on_projects=["llvm", "clang", "clang-tools-extra"],
         extra_configure_args=[
             "-DCMAKE_CXX_STANDARD=20",
             "-DLLVM_CCACHE_BUILD=ON",
             "-DCMAKE_BUILD_TYPE=Release",
             "-DLLVM_ENABLE_ASSERTIONS=ON",
             # FIXME: Re-enable after cleaning up LLVM.
             #        https://github.com/llvm/llvm-project/issues/60101
             "-DCMAKE_CXX_FLAGS=-Wno-deprecated-enum-enum-conversion -Wno-deprecated-declarations -Wno-deprecated-anon-enum-enum-conversion -Wno-ambiguous-reversed-operator",
         ])},

    # Target ARC from Synopsys
    {'name': "arc-builder",
     'tags': ["clang", "lld"],
     'workernames' : ["arc-worker"],
     'builddir': "arc-folder",
     'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
        depends_on_projects=["llvm", "clang", "lld"],
        extra_configure_args=[
             "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON",
             "-DLLVM_ENABLE_ASSERTIONS:BOOL=ON",
             "-DLLVM_TOOL_CLANG_TOOLS_EXTRA_BUILD=0",
             "-DLLVM_ENABLE_LIBPFM=OFF",
             "-DLLVM_TARGETS_TO_BUILD=X86",
             "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=ARC",
         ])},


    # BOLT builders managed by Meta
    {'name' : 'bolt-x86_64-ubuntu-nfc',
    'tags'  : ["bolt"],
    'collapseRequests': False,
    'workernames' : ['bolt-worker'],
    'builddir': "bolt-x86_64-ubuntu-nfc",
    'factory' : BOLTBuilder.getBOLTCmakeBuildFactory(
                    bolttests=True,
                    depends_on_projects=['bolt', 'llvm'],
                    extra_configure_args=[
                        "-DLLVM_APPEND_VC_REV=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_PROJECTS=clang;lld;bolt",
                        "-DLLVM_TARGETS_TO_BUILD=X86;AArch64",
                        ],
                    is_nfc=True,
                    )},

    {'name': "bolt-x86_64-ubuntu-clang",
    'tags': ["bolt"],
    'workernames':["bolt-worker"],
    'builddir': "bolt-x86_64-ubuntu-clang",
    'factory' : BOLTBuilder.getBOLTCmakeBuildFactory(
                    bolttests=False,
                    clean=True,
                    depends_on_projects=['bolt', 'clang', 'lld', 'llvm'],
                    caches=[
                        'clang/cmake/caches/BOLT.cmake',
                        'clang/cmake/caches/BOLT-PGO.cmake',
                    ],
                    targets=['clang-bolt'],
                    checks=['stage2-clang-bolt'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=gcc",
                        "-DCMAKE_CXX_COMPILER=g++",
                        "-DLLVM_APPEND_VC_REV=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DBOOTSTRAP_LLVM_ENABLE_LLD=ON",
                        "-DBOOTSTRAP_BOOTSTRAP_LLVM_ENABLE_LLD=ON",
                        "-DBOOTSTRAP_LLVM_CCACHE_BUILD=ON",
                        "-DPGO_INSTRUMENT_LTO=Thin",
                        ],
                    )},

    {'name': "bolt-x86_64-ubuntu-dylib",
    'tags': ["bolt"],
    'workernames':["bolt-worker"],
    'builddir': "bolt-x86_64-ubuntu-dylib",
    'factory' : BOLTBuilder.getBOLTCmakeBuildFactory(
                    bolttests=False,
                    depends_on_projects=['bolt', 'llvm'],
                    extra_configure_args=[
                        "-DLLVM_APPEND_VC_REV=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_PROJECTS=bolt",
                        "-DLLVM_TARGETS_TO_BUILD=X86;AArch64",
                        "-DLLVM_LINK_LLVM_DYLIB=ON",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DBOLT_CLANG_EXE=/usr/bin/clang",
                        "-DBOLT_LLD_EXE=/usr/bin/ld.lld",
                        ],
                    )},

    {'name': "bolt-x86_64-ubuntu-shared",
    'tags': ["bolt"],
    'workernames':["bolt-worker"],
    'builddir': "bolt-x86_64-ubuntu-shared",
    'factory' : BOLTBuilder.getBOLTCmakeBuildFactory(
                    bolttests=False,
                    depends_on_projects=['bolt', 'llvm'],
                    extra_configure_args=[
                        "-DLLVM_APPEND_VC_REV=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_PROJECTS=bolt",
                        "-DLLVM_TARGETS_TO_BUILD=X86;AArch64",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_ENABLE_LLD=ON",
                        "-DBOLT_CLANG_EXE=/usr/bin/clang",
                        "-DBOLT_LLD_EXE=/usr/bin/ld.lld",
                        ],
                    )},

    {'name': "bolt-aarch64-ubuntu-clang-shared",
    'tags': ["bolt"],
    'workernames':["bolt-worker-aarch64"],
    'builddir': "bolt-aarch64-ubuntu-clang-shared",
    'factory' : BOLTBuilder.getBOLTCmakeBuildFactory(
                    bolttests=True,
                    depends_on_projects=['bolt', 'llvm'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=clang",
                        "-DCMAKE_CXX_COMPILER=clang++",
                        "-DLLVM_APPEND_VC_REV=OFF",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_PROJECTS=bolt",
                        "-DLLVM_TARGETS_TO_BUILD=X86;AArch64",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_USE_LINKER=mold",
                        "-DBOLT_CLANG_EXE=/usr/bin/clang",
                        "-DBOLT_LLD_EXE=/usr/bin/ld.lld",
                        ],
                    )},

    # AMD ROCm support.
    {'name' : 'mlir-rocm-mi200',
     'tags'  : ["mlir"],
     'collapseRequests' : False,
     'workernames' : ['mi200-buildbot'],
     'builddir': 'mlir-rocm-mi200',
     'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
         clean=True,
         depends_on_projects=['llvm', 'mlir'],
         targets = ['check-mlir-build-only'],
         checks = ['check-mlir'],
         extra_configure_args= mlir_default_cmake_options + [
             '-DLLVM_CCACHE_BUILD=ON',
             '-DLLVM_ENABLE_ASSERTIONS=ON',
             '-DLLVM_ENABLE_LLD=ON',
             '-DMLIR_ENABLE_ROCM_RUNNER=ON',
             '-DMLIR_ENABLE_ROCM_CONVERSIONS=ON',
             '-DMLIR_INCLUDE_INTEGRATION_TESTS=ON',
         ],
         env={
             'CC': 'clang',
             'CXX': 'clang++',
             'LD': 'lld',
         })},

    # Standalone builder
    {'name' : "standalone-build-x86_64",
    'tags'  : ["clang"],
    'workernames':["standalone-build-x86_64"],
    'builddir':"standalone-build-x86_64",
    'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
                    script="standalone-build.sh",
                    checkout_llvm_sources=False,
                    script_interpreter=None)},

    ## CSKY check-all + test-suite in soft-float
    {'name' : "clang-csky-soft",
    'tags'  : ["clang"],
    'workernames' : ["thead-clang-csky"],
    'builddir':"clang-csky-softfp",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                clean=False,
                checkout_clang_tools_extra=False,
                checkout_compiler_rt=False,
                checkout_lld=False,
                testStage1=True,
                useTwoStage=False,
                stage1_config='Release',
                runTestSuite=True,
                testsuite_flags=[
                    '--cflags', '-mcpu=c860 -latomic -DSMALL_PROBLEM_SIZE',
                    '--cppflags', '-mcpu=c860 -latomic -DSMALL_PROBLEM_SIZE',
                    '--run-under=/mnt/qemu/bin/qemu-cskyv2 -cpu c860 -csky-extend denormal=on -L /mnt/gcc-csky/csky-linux-gnuabiv2/libc/ck860 -E LD_LIBRARY_PATH=/mnt/gcc-csky/csky-linux-gnuabiv2/lib/ck860',
                    '--cmake-define=SMALL_PROBLEM_SIZE=On',
                    '--cmake-define=TEST_SUITE_USER_MODE_EMULATION=True',
                    '--threads=32', '--build-threads=32'],
                extra_cmake_args=[
                    "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD='CSKY'",
                    "-DLLVM_DEFAULT_TARGET_TRIPLE='csky-unknown-linux'",
                    "-DGCC_INSTALL_PREFIX=/mnt/gcc-csky/"])},

    ## CSKY check-all + test-suite in hard-float
    {'name' : "clang-csky-hardfp",
    'tags'  : ["clang"],
    'workernames' : ["thead-clang-csky"],
    'builddir':"clang-csky-hardfp",
    'factory' : ClangBuilder.getClangCMakeBuildFactory(
                clean=False,
                checkout_clang_tools_extra=False,
                checkout_compiler_rt=False,
                checkout_lld=False,
                testStage1=True,
                useTwoStage=False,
                stage1_config='Release',
                runTestSuite=True,
                testsuite_flags=[
                    '--cflags', '-mcpu=c860 -latomic -mhard-float -DSMALL_PROBLEM_SIZE',
                    '--cppflags', '-mcpu=c860 -latomic -mhard-float -DSMALL_PROBLEM_SIZE',
                    '--run-under=/mnt/qemu/bin/qemu-cskyv2 -cpu c860 -csky-extend denormal=on -L /mnt/gcc-csky/csky-linux-gnuabiv2/libc/ck860/hard-fp -E LD_LIBRARY_PATH=/mnt/gcc-csky/csky-linux-gnuabiv2/lib/ck860/hard-fp',
                    '--cmake-define=SMALL_PROBLEM_SIZE=On',
                    '--cmake-define=TEST_SUITE_USER_MODE_EMULATION=True',
                    '--threads=32', '--build-threads=32'],
                extra_cmake_args=[
                    "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD='CSKY'",
                    "-DLLVM_DEFAULT_TARGET_TRIPLE='csky-unknown-linux'",
                    "-DGCC_INSTALL_PREFIX=/mnt/gcc-csky/"])},

    # NVPTX builders
    {'name' : "llvm-nvptx-nvidia-ubuntu",
    'tags'  : ["llvm", "nvptx"],
    'collapseRequests': False,
    'workernames' : ["as-builder-7"],
    'builddir': "llvm-nvptx-nvidia-ubuntu",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=["llvm"],
                    clean=True,
                    checks=["check-llvm"],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=X86;NVPTX",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=nvptx-nvidia-cuda",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=-vv --threads=32",
                        "-DLLVM_USE_LINKER=gold",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_OPTIMIZED_TABLEGEN=ON"])},

    {'name' : "llvm-nvptx64-nvidia-ubuntu",
    'tags'  : ["llvm", "nvptx"],
    'collapseRequests': False,
    'workernames' : ["as-builder-7"],
    'builddir': "llvm-nvptx64-nvidia-ubuntu",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=["llvm"],
                    clean=True,
                    checks=["check-llvm"],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=X86;NVPTX",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=nvptx64-nvidia-cuda",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=-vv --threads=32",
                        "-DLLVM_USE_LINKER=gold",
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DLLVM_OPTIMIZED_TABLEGEN=ON"])},

    {'name' : "llvm-nvptx-nvidia-win",
    'tags'  : ["llvm", "nvptx"],
    'workernames' : ["as-builder-8"],
    'builddir': "llvm-nvptx-nvidia-win",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    vs="autodetect",
                    depends_on_projects=["llvm"],
                    clean=True,
                    checks=["check-llvm"],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=X86;NVPTX",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=nvptx-nvidia-cuda",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=-vv --threads=32",
                        "-DLLVM_OPTIMIZED_TABLEGEN=ON"])},

    {'name' : "llvm-nvptx64-nvidia-win",
    'tags'  : ["llvm", "nvptx"],
    'workernames' : ["as-builder-8"],
    'builddir': "llvm-nvptx64-nvidia-win",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    vs="autodetect",
                    depends_on_projects=["llvm"],
                    clean=True,
                    checks=["check-llvm"],
                    extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=X86;NVPTX",
                        "-DLLVM_DEFAULT_TARGET_TRIPLE=nvptx64-nvidia-cuda",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_LIT_ARGS=-vv --threads=32",
                        "-DLLVM_OPTIMIZED_TABLEGEN=ON"])},

]
