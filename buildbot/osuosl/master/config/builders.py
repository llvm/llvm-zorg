from buildbot.process.properties import WithProperties

from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.builders import FlangBuilder
from zorg.buildbot.builders import PollyBuilder
from zorg.buildbot.builders import LLDBBuilder
from zorg.buildbot.builders import SanitizerBuilder
from zorg.buildbot.builders import OpenMPBuilder
from zorg.buildbot.builders import LibcxxAndAbiBuilder
from zorg.buildbot.builders import SphinxDocsBuilder
from zorg.buildbot.builders import ABITestsuitBuilder
from zorg.buildbot.builders import ClangLTOBuilder
from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.builders import CUDATestsuiteBuilder
from zorg.buildbot.builders import AOSPBuilder
from zorg.buildbot.builders import AnnotatedBuilder
from zorg.buildbot.builders import LLDPerformanceTestsuite
from zorg.buildbot.builders import FuchsiaBuilder
from zorg.buildbot.builders import XToolchainBuilder

# Plain LLVM builders.
def _get_llvm_builders():
    return [
        ]

# Clang fast builders.
def _get_clang_fast_builders():
    return [
        {'name': "clang-x86_64-debian-fast",
         'mergeRequests': False,
         'slavenames':["gribozavr4"],
         'builddir':"clang-x86_64-debian-fast",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        llvm_srcdir="llvm.src",
                        obj_dir="llvm.obj",
                        clean=True,
                        depends_on_projects=['llvm','clang','clang-tools-extra','compiler-rt'],
                        extra_configure_args=[
                            "-DCOMPILER_RT_BUILD_BUILTINS:BOOL=OFF",
                            "-DCOMPILER_RT_BUILD_SANITIZERS:BOOL=OFF",
                            "-DCOMPILER_RT_BUILD_XRAY:BOOL=OFF",
                            "-DCOMPILER_RT_INCLUDE_TESTS:BOOL=OFF",
                            "-DCMAKE_C_FLAGS=-Wdocumentation -Wno-documentation-deprecated-sync",
                            "-DCMAKE_CXX_FLAGS=-std=c++11 -Wdocumentation -Wno-documentation-deprecated-sync",
                        ],
                        env={
                            'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                            'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                        })},

        {'name': "clang-x86_64-debian-new-pass-manager-fast",
         'slavenames':["gribozavr4"],
         'builddir':"clang-x86_64-debian-new-pass-manager-fast",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        llvm_srcdir="llvm.src",
                        obj_dir="llvm.obj",
                        clean=True,
                        depends_on_projects=['llvm','clang','clang-tools-extra','compiler-rt'],
                        extra_configure_args=[
                            "-DCOMPILER_RT_BUILD_BUILTINS:BOOL=OFF",
                            "-DCOMPILER_RT_BUILD_SANITIZERS:BOOL=OFF",
                            "-DCOMPILER_RT_BUILD_XRAY:BOOL=OFF",
                            "-DCOMPILER_RT_INCLUDE_TESTS:BOOL=OFF",
                            "-DENABLE_EXPERIMENTAL_NEW_PASS_MANAGER=ON",
                            "-DCMAKE_C_FLAGS=-Wdocumentation -Wno-documentation-deprecated-sync",
                            "-DCMAKE_CXX_FLAGS=-std=c++11 -Wdocumentation -Wno-documentation-deprecated-sync",
                        ],
                        env={
                            'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                            'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                        })},

        {'name': "llvm-clang-x86_64-expensive-checks-win",
         'slavenames':["ps4-buildslave2"],
         'builddir':"llvm-clang-x86_64-expensive-checks-win",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                      vs="autodetect",
                      clean=True,
                      extra_configure_args=["-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                                            "-DLLVM_ENABLE_WERROR=OFF",
                                            "-DCMAKE_BUILD_TYPE=Debug",
                                            "'-DLLVM_LIT_ARGS=-vv'"])},

        {'name': "llvm-clang-x86_64-expensive-checks-ubuntu",
         'slavenames': ["as-builder-4"],
         'builddir':"llvm-clang-x86_64-expensive-checks-ubuntu",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                      depends_on_projects=["llvm"],
                      clean=True,
                      extra_configure_args=["-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                                            "-DLLVM_ENABLE_WERROR=OFF",
                                            "-DCMAKE_BUILD_TYPE=Debug",
                                            "-DCMAKE_CXX_FLAGS='-U_GLIBCXX_DEBUG'",
                                            "'-DLLVM_LIT_ARGS=-vv -j32'"])},

        {'name': "llvm-clang-x86_64-expensive-checks-debian",
         'mergeRequests': False,
         'slavenames': ["gribozavr4"],
         'builddir':"llvm-clang-x86_64-expensive-checks-debian",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                      depends_on_projects=["llvm"],
                      clean=True,
                      extra_configure_args=["-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                                            "-DLLVM_ENABLE_WERROR=OFF",
                                            "-DCMAKE_BUILD_TYPE=Release",
                                            "-DCMAKE_CXX_FLAGS=-U_GLIBCXX_DEBUG",
                                            "-DLLVM_LIT_ARGS=-v -vv -j96"],
                      env={
                          'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                          'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                      })},

        {'name' : "llvm-clang-x86_64-win-fast",
         'slavenames' : ["as-builder-3"],
         'builddir' : "llvm-clang-x86_64-win-fast",
         'mergeRequests': False,
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
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
                        "-DLLVM_LIT_ARGS='-v --threads=32'"])},

        {'name' : "llvm-clang-win-x-armv7l",
         'slavenames' : ["as-builder-1"],
         'builddir' : "clang-win-x-armv7l",
         'mergeRequests': True,
         'factory': XToolchainBuilder.getCmakeWithMSVCBuildFactory(
                      vs="autodetect",
                      clean=True,
                      checks=[
                        "check-llvm",
                        "check-clang",
                        "check-lld",
                      ],
                      checks_on_target = [
                        ("libunwind",
                         ["python", "bin/llvm-lit.py",
                          "-v", "-vv", "--threads=32",
                          "runtimes/runtimes-bins/libunwind/test"]),
                        ("libc++abi",
                         ["python", "bin/llvm-lit.py",
                          "-v", "-vv", "--threads=32",
                          "runtimes/runtimes-bins/libcxxabi/test"]),
                        ("libc++",
                         ['python', 'bin/llvm-lit.py',
                          '-v', '-vv', '--threads=32',
                          'runtimes/runtimes-bins/libcxx/test',
                         ])
                      ],
                      extra_configure_args=[
                        "-DDEFAULT_SYSROOT=C:/buildbot/.arm-ubuntu",
                        "-DLLVM_LIT_ARGS=-v -vv --threads=32",
                        WithProperties("%(remote_test_host:+-DREMOTE_TEST_HOST=)s%(remote_test_host:-)s"),
                        WithProperties("%(remote_test_user:+-DREMOTE_TEST_USER=)s%(remote_test_user:-)s"),
                      ],
                      cmake_cache="../llvm-project/clang/cmake/caches/CrossWinToARMLinux.cmake")},

        {'name' : "llvm-clang-win-x-aarch64",
         'slavenames' : ["as-builder-2"],
         'builddir' : "clang-win-x-aarch64",
         'slavebuilddir' : "x-aarch64",
         'mergeRequests': True,
         'factory': XToolchainBuilder.getCmakeWithMSVCBuildFactory(
                      vs="autodetect",
                      clean=True,
                      checks=[
                        "check-llvm",
                        "check-clang",
                        "check-lld",
                      ],
                      checks_on_target = [
                        ("libunwind",
                         ["python", "bin/llvm-lit.py",
                          "-v", "-vv", "--threads=32",
                          "runtimes/runtimes-bins/libunwind/test"]),
                        ("libc++abi",
                         ["python", "bin/llvm-lit.py",
                          "-v", "-vv", "--threads=32",
                          "runtimes/runtimes-bins/libcxxabi/test"]),
                        ("libc++",
                         ['python', 'bin/llvm-lit.py',
                          '-v', '-vv', '--threads=32',
                          'runtimes/runtimes-bins/libcxx/test',
                         ])
                      ],
                      extra_configure_args=[
                        "-DLLVM_TARGETS_TO_BUILD=AArch64",
                        "-DCMAKE_C_COMPILER_TARGET=aarch64-linux-gnu",
                        "-DDEFAULT_SYSROOT=C:/buildbot/.aarch64-ubuntu",
                        "-DLLVM_LIT_ARGS=-v -vv --threads=32",
                        WithProperties("%(remote_test_host:+-DREMOTE_TEST_HOST=)s%(remote_test_host:-)s"),
                        WithProperties("%(remote_test_user:+-DREMOTE_TEST_USER=)s%(remote_test_user:-)s"),
                      ],
                      cmake_cache="../llvm-project/clang/cmake/caches/CrossWinToARMLinux.cmake")},

        {'name': "clang-arm64-windows-msvc",
         'slavenames':["linaro-armv8-windows-msvc-01", "linaro-armv8-windows-msvc-02"],
         'builddir':"clang-arm64-windows-msvc",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      vs="manual",
                      test=False, # Disable testing until MCJIT failures are fixed
                      extra_cmake_args=["-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-windows-msvc",
                                        "-DLLVM_HOST_TRIPLE=aarch64-windows-msvc",
                                        "-DLLVM_TARGET_ARCH=AArch64",
                                        "-DCOMPILER_RT_BUILD_SANITIZERS=OFF",
                                        "-DCOMPILER_RT_BUILD_XRAY=OFF"])},
    ]

# Clang builders.
def _get_clang_builders():
    return [
        # Cortex-A15 LNT test-suite in Benchmark mode
        {'name' : "clang-native-arm-lnt-perf",
         'slavenames':["linaro-tk1-02"],
         'builddir':"clang-native-arm-lnt-perf",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-O3 -mcpu=cortex-a15 -mthumb',
                                '--threads=1', '--build-threads=4',
                                '--use-perf=all',
                                '--benchmarking-only', '--exec-multisample=3',
                                '--exclude-stat-from-submission=compile'],
                      extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"],
                      submitURL='http://lnt.llvm.org/submitRun',
                      testerName='LNT-Thumb2v7-A15-O3')},

        # ARMv7 LNT test-suite in test-only mode
        {'name' : "clang-cmake-armv7-lnt",
         'slavenames':["linaro-armv7-lnt"],
         'builddir':"clang-cmake-armv7-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a15 -marm',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM'"])},

        ## ARMv7 check-all self-host NEON with CMake builder
        {'name': "clang-cmake-armv7-selfhost-neon",
         'slavenames':["linaro-armv7-selfhost"],
         'builddir':"clang-cmake-armv7-selfhost-neon",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      useTwoStage=True,
                      testStage1=False,
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## ARMv7 check-all with CMake builder
        {'name': "clang-cmake-armv7-quick",
         'slavenames':["linaro-armv7-quick"],
         'builddir':"clang-cmake-armv7-quick",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## ARMv7 Clang + LLVM run test-suite with GlobalISel enabled
        {'name' : "clang-cmake-armv7-global-isel",
         'slavenames':["linaro-armv7-global-isel"],
         'builddir':"clang-cmake-armv7-global-isel",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a15 -marm -O0 -mllvm -global-isel -mllvm -global-isel-abort=0',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## ARMv7 check-all self-host with CMake builder
        {'name': "clang-cmake-armv7-selfhost",
         'slavenames':["linaro-armv7-selfhost"],
         'builddir':"clang-cmake-armv7-selfhost",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      useTwoStage=True,
                      testStage1=False,
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## AArch64 Clang+LLVM check-all + test-suite
        {'name': "clang-cmake-aarch64-quick",
         'slavenames':["linaro-aarch64-quick"],
         'builddir':"clang-cmake-aarch64-quick",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a57',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

        ## AArch64 Self-hosting Clang+LLVM check-all + LLD + test-suite
        {'name': "clang-cmake-aarch64-lld",
         'slavenames':["linaro-aarch64-lld"],
         'builddir':"clang-cmake-aarch64-lld",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=True,
                      checkout_lld=True,
                      test=True,
                      useTwoStage=True,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a57 -fuse-ld=lld',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_ENABLE_LLD=True"],
               ),
         'category'   : 'lld'},

        ## AArch64 Clang+LLVM run test-suite at -O0 (GlobalISel is now default).
        {'name': "clang-cmake-aarch64-global-isel",
         'slavenames':["linaro-aarch64-global-isel"],
         'builddir':"clang-cmake-aarch64-global-isel",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-O0',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

          ## ARMv7 without neon; check-all 2-stage full compiler-rt + testsuite
          {'name': "clang-cmake-armv7-full",
           'slavenames':["linaro-tk1-06", "linaro-tk1-07", "linaro-tk1-08", "linaro-tk1-09"],
           'builddir':"clang-cmake-armv7-full",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        checkout_lld=False,
                        checkout_compiler_rt=True,
                        testStage1=False,
                        useTwoStage=True,
                        runTestSuite=True,
                        testsuite_flags=['--cppflags', '-mcpu=cortex-a15 -mfpu=vfpv3 -marm',
                                         '--threads=4', '--build-threads=4'],
                        extra_cmake_args=["-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM'",
                                          "-DLLVM_PARALLEL_LINK_JOBS=2"])},

          ## ARMv7 Thumb2 with neon; check-all 2-stage full compiler-rt + testsuite
          {'name': "clang-cmake-thumbv7-full-sh",
           'slavenames':["linaro-tk1-01", "linaro-tk1-03", "linaro-tk1-04", "linaro-tk1-05"],
           'builddir':"clang-cmake-thumbv7-full-sh",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        checkout_lld=False,
                        checkout_compiler_rt=True,
                        testStage1=False,
                        useTwoStage=True,
                        runTestSuite=True,
                        testsuite_flags=['--cppflags', '-mcpu=cortex-a15 -mthumb',
                                         '--threads=4', '--build-threads=4'],
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM'",
                                          "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## AArch32 Self-hosting Clang+LLVM check-all + LLD + test-suite
        # Sanitizers build disabled due to PR38690
        {'name': "clang-cmake-armv8-lld",
         'slavenames':["linaro-armv8-lld"],
         'builddir':"clang-cmake-armv8-lld",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=True,
                      checkout_lld=True,
                      test=True,
                      useTwoStage=True,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a57 -fuse-ld=lld',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DCOMPILER_RT_BUILD_SANITIZERS=OFF",
                                        "-DLLVM_ENABLE_LLD=True"],
               ),
         'category'   : 'lld'},

        # AArch64 Clang+LLVM+RT check-all + flang + test-suite + self-hosting
        {'name': "clang-cmake-aarch64-full",
         'slavenames':["linaro-aarch64-full"],
         'builddir':"clang-cmake-aarch64-full",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=True,
                      checkout_flang=True,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=True,
                      testStage1=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a57',
                                       '--threads=32', '--build-threads=32'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

        {'name': "clang-arm64-windows-msvc-2stage",
         'slavenames':["linaro-armv8-windows-msvc-01", "linaro-armv8-windows-msvc-02"],
         'builddir':"clang-arm64-windows-msvc-2stage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      vs="manual",
                      test=False, # Disable testing until MCJIT failures are fixed
                      useTwoStage=True,
                      testStage1=False,
                      extra_cmake_args=["-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-windows-msvc",
                                        "-DLLVM_HOST_TRIPLE=aarch64-windows-msvc",
                                        "-DLLVM_TARGET_ARCH=AArch64",
                                        "-DCOMPILER_RT_BUILD_SANITIZERS=OFF",
                                        "-DCOMPILER_RT_BUILD_XRAY=OFF"])},

        {'name': 'clang-x64-windows-msvc',
         'slavenames': ['windows-gcebot2'],
         'builddir': 'clang-x64-windows-msvc',
         'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
             script="clang-windows.py",
             depends_on_projects=['llvm', 'clang', 'lld', 'debuginfo-tests'])},

        {'name' : "clang-ppc64be-linux-lnt",
         'slavenames' :["ppc64be-clang-lnt-test"],
         'builddir' :"clang-ppc64be-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            nt_flags=['--threads=16', '--build-threads=16'],
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name' : "clang-ppc64be-linux-multistage",
         'slavenames' :["ppc64be-clang-multistage-test"],
         'builddir' :"clang-ppc64be-multistage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON']),
         'category' : 'clang'},

        {'name' : "clang-ppc64le-linux-lnt",
         'slavenames' :["ppc64le-clang-lnt-test"],
         'builddir' :"clang-ppc64le-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            nt_flags=['--threads=16', '--build-threads=16'],
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},


        {'name' : "clang-ppc64le-linux-multistage",
         'slavenames' :["ppc64le-clang-multistage-test"],
         'builddir' :"clang-ppc64le-multistage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON', '-DBUILD_SHARED_LIBS=ON']),
         'category' : 'clang'},

        {'name': "clang-ppc64be-linux",
         'slavenames':["ppc64be-clang-test"],
         'builddir':"clang-ppc64be",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=False,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name': "clang-ppc64le-linux",
         'slavenames':["ppc64le-clang-test"],
         'builddir':"clang-ppc64le",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=False,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name': "clang-ppc64le-rhel",
         'slavenames':["ppc64le-clang-rhel-test"],
         'builddir':"clang-ppc64le-rhel",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            checkout_clang_tools_extra=True,
                                                            checkout_compiler_rt=True,
                                                            checkout_lld=True,
                                                            checkout_libcxx=False,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            nt_flags=['--threads=16', '--build-threads=16'],
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=On", "-DCMAKE_C_COMPILER=clang",
                                                                              "-DCMAKE_CXX_COMPILER=clang++",
                                                                              "-DCLANG_DEFAULT_LINKER=lld",
                                                                              "-DCMAKE_C_COMPILER_EXTERNAL_TOOLCHAIN:PATH=/opt/rh/devtoolset-7/root/usr",
                                                                              "-DCMAKE_CXX_COMPILER_EXTERNAL_TOOLCHAIN:PATH=/opt/rh/devtoolset-7/root/usr",
                                                                              "-DLLVM_BINUTILS_INCDIR=/usr/include", "-DBUILD_SHARED_LIBS=ON", "-DLLVM_ENABLE_WERROR=ON",
                                                                              "-DLLVM_LIT_ARGS='-vj 64'"]),
         'category' : 'clang'},

        {'name': "clang-s390x-linux",
         'slavenames':["systemz-1"],
         'builddir':"clang-s390x-linux",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(jobs=4,
                                                            clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=False,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON",
                                                                              "-DLLVM_LIT_ARGS='-v -j4 --param run_long_tests=true'"]),
         'category' : 'clang'},

        {'name' : "clang-s390x-linux-multistage",
         'slavenames':["systemz-1"],
         'builddir' :"clang-s390x-linux-multistage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(jobs=4,
                                                            clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON']),
         'category' : 'clang'},

        {'name' : "clang-s390x-linux-lnt",
         'slavenames':["systemz-1"],
         'builddir' :"clang-s390x-linux-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(jobs=4,
                                                            clean=False,
                                                            checkout_lld=False,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            testsuite_flags=['--threads=4', '--build-threads=4'],
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        # ABI test-suite with CMake builder
        {'name'          : "clang-x86_64-linux-abi-test",
         'mergeRequests' : False,
         'slavenames'    : ["ps4-buildslave1a"],
         'builddir'      : "clang-x86_64-linux-abi-test",
         'factory'       : ABITestsuitBuilder.getABITestsuitBuildFactory(
                               # TODO: Enable Werror once all the warnings are cleaned.
                               extra_configure_args = ["-DLLVM_ENABLE_WERROR=OFF","-GNinja"])},

        {'name' : "clang-hexagon-elf",
         'slavenames' :["hexagon-build-02", "hexagon-build-03"],
         'builddir' :"clang-hexagon-elf",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
            jobs=16,
            checkout_clang_tools_extra=False,
            checkout_compiler_rt=False,
            checkout_lld=False,
            env={'LD_LIBRARY_PATH': '/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/lib', 'PATH': ['/local/cmake-3.17.0/bin', '${PATH}']},
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
              "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
              "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"])},

        ## X86_64 AVX2 Clang+LLVM check-all + test-suite
        {'name': "clang-cmake-x86_64-avx2-linux",
         'slavenames':["avx2-intel64"],
         'builddir':"clang-cmake-x86_64-avx2-linux",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
             clean=False,
             checkout_clang_tools_extra=False,
             checkout_compiler_rt=False,
             checkout_lld=False,
             test=True,
             useTwoStage=False,
             runTestSuite=True,
             nt_flags=['--cflag', '-march=broadwell', '--threads=80', '--build-threads=80'],
             env={'PATH':'/usr/bin/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
             extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON",
                               "-DCMAKE_C_FLAGS='-march=broadwell'",
                               "-DCMAKE_CXX_FLAGS='-march=broadwell'",
                               "-DLLVM_TARGETS_TO_BUILD='X86'"])},

        ## X86_64 AVX2 LNT test-suite in Benchmark mode
        {'name': "clang-cmake-x86_64-avx2-linux-perf",
         'slavenames':["avx2-intel64"],
         'builddir':"clang-cmake-x86_64-avx2-linux-perf",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
             clean=False,
             checkout_clang_tools_extra=False,
             checkout_compiler_rt=False,
             checkout_lld=False,
             test=False,
             useTwoStage=False,
             runTestSuite=True,
             nt_flags=['--cflag', '-march=broadwell', '--threads=1', '--build-threads=80', '--use-perf',
                       '--benchmarking-only', '--multisample=4', '--exclude-stat-from-submission=compile'],
             env={'PATH':'/usr/bin/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
             extra_cmake_args=["-DCMAKE_C_FLAGS='-march=broadwell'",
                               "-DCMAKE_CXX_FLAGS='-march=broadwell'",
                               "-DLLVM_TARGETS_TO_BUILD='X86'"],
             submitURL='http://lnt.llvm.org/submitRun',
             testerName='LNT-Broadwell-AVX2-O3')},

        ## X86_64 Clang+LLVM Run test-suite targeting AVX512 on SDE (Emulator)
        {'name': "clang-cmake-x86_64-sde-avx512-linux",
         'slavenames':["sde-avx512-intel64"],
         'builddir':"clang-cmake-x86_64-sde-avx512-linux",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
             clean=False,
             checkout_clang_tools_extra=False,
             checkout_compiler_rt=False,
             checkout_lld=False,
             test=True,
             useTwoStage=False,
             runTestSuite=True,
             nt_flags=['--cflag', '-march=skylake-avx512', '--threads=80',
                 '--build-threads=80', '--make-param', "RUNUNDER=sde64 -skx --", '--make-param', 'USER_MODE_EMULATION=1',
                 '--make-param', 'RUNTIMELIMIT=1200'],
             env={'PATH':'/home/ssglocal/tools/sde/latest:/usr/bin/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
             extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON",
                               "-DCMAKE_C_FLAGS='-march=broadwell'",
                               "-DCMAKE_CXX_FLAGS='-march=broadwell'",
                               "-DLLVM_TARGETS_TO_BUILD='X86'"])},

        ## Armv7 build cache
        {'name': "clang-armv7-linux-build-cache",
         'slavenames':["packet-linux-armv7-slave-1"],
         'builddir':"clang-armv7-linux-build-cache",
         'factory' : ClangBuilder.getClangCMakeGCSBuildFactory(
                      stage1_config='Release',
                      clean=True,
                      checkout_compiler_rt=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=False,
                      checkout_lld=True,
                      checkout_libcxx=True,
                      checkout_clang_tools_extra=False,
                      use_pixz_compression=False,
                      xz_compression_factor=0,
                      stage1_upload_directory='clang-armv7-linux',
                      extra_cmake_args=[
                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64;X86'",
                          "-DCMAKE_C_FLAGS='-mthumb'",
                          "-DCMAKE_CXX_FLAGS='-mthumb'",
                          ],
                      env={'BUCKET': 'llvm-build-artifacts'}
               ),
         'category': 'clang'},

        ## AArch64 build cache
        {'name': "clang-aarch64-linux-build-cache",
         'slavenames':["packet-linux-aarch64-slave-1"],
         'builddir':"clang-aarch64-linux-build-cache",
         'factory' : ClangBuilder.getClangCMakeGCSBuildFactory(
                      stage1_config='Release',
                      clean=True,
                      checkout_compiler_rt=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=False,
                      checkout_lld=True,
                      checkout_libcxx=True,
                      checkout_clang_tools_extra=False,
                      stage1_upload_directory='clang-aarch64-linux',
                      use_pixz_compression=True,
                      extra_cmake_args=[
                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64;X86'",
                          #"-DCMAKE_C_FLAGS=''",
                          #"-DCMAKE_CXX_FLAGS=''",
                          ],
                      env={'BUCKET': 'llvm-build-artifacts'}
               ),
         'category': 'clang'},

        {'name' : "llvm-avr-linux",
         'slavenames' : ["avr-build-01"],
         'builddir' : "llvm-avr-linux",
         'factory': ClangBuilder.getClangCMakeBuildFactory(
                      jobs=8,
                      clean=False,
                      checkout_lld=False,
                      extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                        # We need to compile the X86 backend due to a few generic CodeGen tests.
                                        '-DLLVM_TARGETS_TO_BUILD=X86',
                                        '-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=AVR',
                                        '-DBUILD_SHARED_LIBS=ON'])},

        {'name' : "clang-solaris11-amd64",
         'slavenames' : ["solaris11-amd64"],
         'builddir' : "clang-solaris11-amd64",
         'factory': ClangBuilder.getClangCMakeBuildFactory(
                      jobs=8,
                      clean=False,
                      checkout_lld=False,
                      extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                        '-DLLVM_TARGETS_TO_BUILD=X86',
                                        '-DLLVM_HOST_TRIPLE=amd64-pc-solaris2.11',
                                        '-DLLVM_PARALLEL_LINK_JOBS=4'])},

        {'name' : "clang-solaris11-sparcv9",
         'slavenames' : ["solaris11-sparcv9"],
         'builddir' : "clang-solaris11-sparcv9",
         'factory': ClangBuilder.getClangCMakeBuildFactory(
                      jobs=8,
                      clean=False,
                      checkout_lld=False,
                      extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                        '-DLLVM_TARGETS_TO_BUILD=Sparc',
                                        '-DLLVM_HOST_TRIPLE=sparcv9-sun-solaris2.11',
                                        '-DLLVM_PARALLEL_LINK_JOBS=4'])},

        {'name' : "clang-x64-ninja-win7",
         'slavenames' : ["windows7-buildbot"],
         'builddir' : "clang-x64-ninja-win7",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        checkout_lld=False,
                        vs="autodetect",
                        vs_target_arch='x64',
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='Release',
                        stage2_config='Release',
                        extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                          '-DLLVM_TARGETS_TO_BUILD=X86'])},

        {'name' : "clang-x86-ninja-win10",
         'slavenames' : ["windows10-vs2019"],
         'builddir' : "clang-x86-ninja-win10",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=True,
                        vs="autodetect",
                        vs_target_arch='x86',
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='Release',
                        stage2_config='Release',
                        extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                          '-DLLVM_TARGETS_TO_BUILD=X86',
                                          '-DCMAKE_C_COMPILER_LAUNCHER=sccache',
                                          '-DCMAKE_CXX_COMPILER_LAUNCHER=sccache',
                                          '-DLLVM_ENABLE_ZLIB=OFF',
                                          ])},

    ]

# Polly builders.
def _get_polly_builders():
    return [
        {'name': "polly-arm-linux",
         'slavenames': ["hexagon-build-02", "hexagon-build-03"],
         'builddir': "polly-arm-linux",
         'factory': PollyBuilder.getPollyBuildFactory(
                clean=True,
                install=True,
                make='ninja',
                jobs=16,
                env={'LD_LIBRARY_PATH': '/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/lib', 'PATH': ['/local/cmake-3.17.0/bin', '${PATH}']},
                extraCmakeArgs=["-G", "Ninja",
                                "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                "-DLLVM_DEFAULT_TARGET_TRIPLE=arm-linux-gnueabi",
                                "-DLLVM_TARGET_ARCH=arm-linux-gnueabi",
                                "-DLLVM_ENABLE_ASSERTIONS=True",
                                "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                                "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                                "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"])},
        {'name': "polly-x86_64-linux",
         'slavenames': ["polly-x86_64-fdcserver", "polly-x86_64-gce1"],
         'builddir': "polly-x86_64-linux",
         'factory': PollyBuilder.getPollyBuildFactory(
                clean=False,
                install=False,
                make='ninja',
                extraCmakeArgs=["-G", "Ninja",
                                "-DLLVM_ENABLE_ASSERTIONS=True",
                                "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                                "-DCLANG_ENABLE_ARCMT=OFF",
                                "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                                ])},
        {'name': "polly-x86_64-linux-test-suite",
         'slavenames': ["polly-x86_64-fdcserver", "polly-x86_64-gce2"],
         'builddir':"polly-x86_64-linux-test-suite",
         'factory': PollyBuilder.getPollyBuildFactory(
                clean=False,
                install=False,
                make='ninja',
                extraCmakeArgs=["-G", "Ninja",
                                "-DLLVM_ENABLE_ASSERTIONS=True",
                                "-DLLVM_TARGETS_TO_BUILD='X86;NVPTX'",
                                "-DCLANG_ENABLE_ARCMT=OFF",
                                "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
                                ],
                testsuite=True,
                extraTestsuiteCmakeArgs=["-G", "Ninja"]
                )}
       ]

# AOSP builders.
def _get_aosp_builders():
    return [
        {'name': "aosp-O3-polly-before-vectorizer-unprofitable",
         'slavenames': ["hexagon-build-03"],
         'builddir': "aosp",
         'factory': AOSPBuilder.getAOSPBuildFactory(
                device="angler",
                build_clang=True,
                extra_cmake_args=["-G", "Ninja",
                                  "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                  "-DLLVM_DEFAULT_TARGET_TRIPLE=arm-linux-androideabi",
                                  "-DLLVM_TARGET_ARCH=arm-linux-androideabi",
                                  "-DLLVM_ENABLE_ASSERTIONS=True",
                                  "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                                  "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                                  "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"],
                timeout=240,
                target_clang=None,
                target_flags="-Wno-error -O3 -mllvm -polly -mllvm -polly-position=before-vectorizer -mllvm -polly-process-unprofitable -fcommon",
                jobs=8,
                extra_make_args=None,
                env={'LD_LIBRARY_PATH': '/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/lib', 'PATH': ['/local/cmake-3.17.0/bin', '${PATH}']},
                clean=False,
                sync=False,
                patch=None)}
    ]

# Reverse iteration builders.
def _get_rev_iter_builders():
    return [
        {'name': "reverse-iteration",
         'slavenames': ["hexagon-build-02", "hexagon-build-03"],
         'builddir': "reverse-iteration",
         'factory': PollyBuilder.getPollyBuildFactory(
                clean=True,
                make='ninja',
                jobs=16,
                checkAll=True,
                env={'LD_LIBRARY_PATH': '/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/lib', 'PATH': ['/local/cmake-3.17.0/bin', '${PATH}']},
                extraCmakeArgs=["-G", "Ninja",
                                "-DLLVM_REVERSE_ITERATION:BOOL=ON",
                                "-DLLVM_ENABLE_ASSERTIONS=True",
                                "-DLLVM_ENABLE_LIBCXX:BOOL=ON",
                                "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                                "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"])}
    ]

# LLDB builders.
def _get_lldb_builders():
    return [
        {'name': "lldb-x86_64-fedora",
         'slavenames': ["lldb-x86_64-fedora"],
         'builddir': "lldb-x86_64-fedora",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBCMakeBuildFactory(
                    clean=True,
                    test=True,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=True',
                                      '-DLLVM_USE_LINKER=gold',
                                      '-DLLVM_LIT_ARGS="-v"'])},
        {'name': "lldb-x86_64-debian",
         'slavenames': ["lldb-x86_64-debian"],
         'builddir': "lldb-x86_64-debian",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBCMakeBuildFactory(
                    test=True,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=True',
                                      '-DLLVM_USE_LINKER=gold',
                                      '-DLLDB_ENABLE_PYTHON=True',
                                      '-DPYTHON_EXECUTABLE=/usr/bin/python3',
                                      '-DCMAKE_C_COMPILER=clang',
                                      '-DCMAKE_CXX_COMPILER=clang++'])},
        {'name': "lldb-aarch64-ubuntu",
         'slavenames': ["linaro-aarch64-lldb"],
         'builddir': "lldb-cmake-aarch64",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBCMakeBuildFactory(
                    test=True,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=True',
                                      '-DLLVM_LIT_ARGS="-svj 8"',
                                      '-DLLVM_USE_LINKER=gold'])},
        {'name': "lldb-arm-ubuntu",
         'slavenames': ["linaro-arm-lldb"],
         'builddir': "lldb-cmake-arm",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBCMakeBuildFactory(
                    test=True,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=True',
                                      '-DLLVM_LIT_ARGS="-svj 8"',
                                      '-DLLVM_USE_LINKER=gold'])},
        {'name': "lldb-x64-windows-ninja",
         'slavenames': ["win-py3-buildbot"],
         'builddir': "lldb-x64-windows-ninja",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBCMakeBuildFactory(
                    clean=True,
                    python_source_dir=r'"C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python36_64"',
                    target_arch='x64',
                    vs="autodetect",
                    test=True,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=OFF',
                                      '-DLLVM_ENABLE_ZLIB=FALSE',
                                      '-DLLDB_ENABLE_PYTHON=TRUE'])}
       ]

# LLD builders.
def _get_lld_builders():
    return [
        {'name': "lld-x86_64-darwin",
         'slavenames' :["as-bldslv9"],
         'builddir':"lld-x86_64-darwin",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm', 'lld'],
                        extra_configure_args=[
                            '-DLLVM_ENABLE_WERROR=OFF',
                        ]),
         'category'   : 'lld'},

        {'name': "lld-x86_64-win",
         'slavenames' :["ps4-buildslave2"],
         'builddir':"lld-x86_64-win",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                        depends_on_projects=['llvm', 'lld'],
                        vs="autodetect",
                        extra_configure_args = [
                            '-DLLVM_ENABLE_WERROR=OFF',
                        ]),
         'category'   : 'lld'},

        {'name': "lld-x86_64-freebsd",
         'slavenames' :["as-bldslv5"],
         'builddir':"lld-x86_64-freebsd",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        depends_on_projects=['llvm', 'lld'],
                        extra_configure_args=[
                            '-DCMAKE_EXE_LINKER_FLAGS=-lcxxrt',
                            '-DLLVM_ENABLE_WERROR=OFF',
                        ],
                        env={'CXXFLAGS' : "-std=c++11 -stdlib=libc++"}),
         'category'   : 'lld'},

        {'name' : "clang-with-lto-ubuntu",
         'slavenames' : ["ps4-buildslave1a"],
         'builddir' : "clang-with-lto-ubuntu",
         'factory': ClangLTOBuilder.getClangWithLTOBuildFactory(jobs=32),
         'category'   : 'lld'},

        {'name' : "clang-with-thin-lto-ubuntu",
         'slavenames' : ["ps4-buildslave1"],
         'builddir' : "clang-with-thin-lto-ubuntu",
         'factory': ClangLTOBuilder.getClangWithLTOBuildFactory(jobs=72, lto='thin'),
         'category'   : 'lld'},

        {'name' : "lld-perf-testsuite",
         'slavenames' : ["as-bldslv8"],
         'builddir' : "lld-perf-testsuite",
         'factory': LLDPerformanceTestsuite.getFactory(targets=["bin/lld"]),
         'category'   : 'lld'},

        {'name' : "ppc64le-lld-multistage-test",
         'slavenames' : ["ppc64le-lld-multistage-test"],
         'builddir' : "ppc64le-lld-multistage-test",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaMultistageBuildFactory(
                                    extra_configure_args=[
                                        '-DLLVM_ENABLE_ASSERTIONS=ON',
                                        '-DLLVM_LIT_ARGS="-svj 256"'],
                                    depends_on_projects=['llvm', 'clang', 'lld']),
         'category'   : 'lld'},

        {'name' : "lld-x86_64-ubuntu-fast",
         'slavenames' : ["as-builder-4"],
         'builddir' : "lld-x86_64-ubuntu-fast",
         'mergeRequests': False,
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                                    clean=True,
                                    extra_configure_args=[
                                        '-DLLVM_ENABLE_WERROR=OFF'],
                                    depends_on_projects=['llvm', 'lld']),
         'category' : 'lld'},

        ]

# Builders for MLIR
def _get_mlir_builders():
    return [
        {'name': "mlir-nvidia",
        'slavenames':["mlir-nvidia"],
        'builddir':"mlir-nvidia",
        'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        llvm_srcdir="llvm.src",
                        obj_dir="llvm.obj",
                        clean=True,
                        depends_on_projects=['llvm','mlir'],
                        extra_configure_args=[
                            '-DLLVM_BUILD_EXAMPLES=ON',
                            '-DLLVM_TARGETS_TO_BUILD=host;NVPTX',
                            '-DLLVM_ENABLE_PROJECTS=mlir',
                            '-DMLIR_CUDA_RUNNER_ENABLED=1',
                            '-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc',
                            '-DMLIR_VULKAN_RUNNER_ENABLED=1',
                        ],
                        env={
                            'CC':'clang',
                            'CXX': 'clang++',
                            'LD': 'lld',
                        })},
        {'name': "mlir-windows",
        'slavenames':["win-mlir-buildbot"],
        'builddir': "mlir-x64-windows-ninja",
        'category' : 'mlir',
        'factory': UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm','mlir'],
                        vs="autodetect",
                        checks=['check-mlir'],
                        extra_configure_args=[
                            "-DLLVM_BUILD_EXAMPLES=ON",
                            "-DLLVM_ENABLE_PROJECTS=mlir",
                            "-DLLVM_TARGETS_TO_BUILD='host;NVPTX;AMDGPU'",
                        ])},
       {'name': 'ppc64le-mlir-rhel-clang',
        'mergeRequests': False,
        'slavenames': ['ppc64le-flang+mlir-rhel-test'],
        'builddir': 'ppc64le-mlir-rhel-clang-build',
        'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm', 'mlir'],
                        checks=['check-mlir'],
                        extra_configure_args=[
                            '-DLLVM_TARGETS_TO_BUILD=PowerPC',
                            '-DLLVM_INSTALL_UTILS=ON',
                            '-DCMAKE_CXX_STANDARD=17',
                            '-DLLVM_ENABLE_PROJECTS=mlir',
                            '-DLLVM_LIT_ARGS="-vj 256"',
                        ],
                        env={
                              'CC': 'clang',
                              'CXX': 'clang++',
                              'LD': 'lld',
                        })},
       # Latest stable fedora running on Red Hat internal OpenShift cluster (PSI)  
       {'name': 'x86_64-fedora-clang',
        'mergeRequests': False,
        'slavenames': ['fedora-llvm-x86_64'],
        'builddir': 'fedora-llvm-x86_64',
        'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm', 'clang', 'clang-tools-extra', 'compiler-rt', 'lld', 'mlir'],
                        checks=['check-all'],
                        extra_configure_args=[
                            '-DCMAKE_BUILD_TYPE=Release',
                            '-DCMAKE_C_COMPILER=/usr/bin/gcc',
                            '-DCMAKE_CXX_COMPILER=/usr/bin/g++',
                            '-DLLVM_ENABLE_ASSERTIONS=On',
                            '-DLLVM_BUILD_EXAMPLES=On',
                            "-DLLVM_LIT_ARGS='-v --xunit-xml-output test-results.xml'",
                            '-DLLVM_CCACHE_BUILD=On',
                            '-DLLVM_CCACHE_DIR=/ccache',
                            '-DLLVM_CCACHE_MAXSIZE=20G',
                            '-DLLVM_TARGETS_TO_BUILD=X86',
                            '-DCMAKE_EXPORT_COMPILE_COMMANDS=1',
                            '-DLLVM_BUILD_LLVM_DYLIB=On',
                            '-DLLVM_LINK_LLVM_DYLIB=On',
                            '-DCLANG_LINK_CLANG_DYLIB=On',
                            '-DBUILD_SHARED_LIBS=Off',
                        ])},
    ]

# Sanitizer builders.
def _get_sanitizer_builders():
      return [
          {'name': "sanitizer-x86_64-linux",
           'slavenames' :["sanitizer-buildbot1", "sanitizer-buildbot2"],
           'builddir': "sanitizer-x86_64-linux",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},
          {'name': "sanitizer-x86_64-linux-fast",
           'slavenames' :["sanitizer-buildbot1", "sanitizer-buildbot2"],
           'builddir': "sanitizer-x86_64-linux-fast",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-bootstrap",
           'slavenames' :["sanitizer-buildbot3", "sanitizer-buildbot4"],
           'builddir': "sanitizer-x86_64-linux-bootstrap",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},
          {'name': "sanitizer-x86_64-linux-bootstrap-ubsan",
           'slavenames' :["sanitizer-buildbot3", "sanitizer-buildbot4"],
           'builddir': "sanitizer-x86_64-linux-bootstrap-ubsan",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-bootstrap-msan",
           'slavenames' :["sanitizer-buildbot7", "sanitizer-buildbot8"],
           'builddir': "sanitizer-x86_64-linux-bootstrap-msan",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},
          {'name': "sanitizer-x86_64-linux-autoconf",
           'slavenames' :["sanitizer-buildbot7", "sanitizer-buildbot8"],
           'builddir': "sanitizer-x86_64-linux-autoconf",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},
          {'name': "sanitizer-x86_64-linux-fuzzer",
           'slavenames' :["sanitizer-buildbot7", "sanitizer-buildbot8"],
           'builddir': "sanitizer-x86_64-linux-fuzzer",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

           {'name': "sanitizer-x86_64-linux-android",
           'slavenames' :["sanitizer-buildbot6"],
           'builddir': "sanitizer-x86_64-linux-android",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-ppc64be-linux",
           'slavenames' :["ppc64be-sanitizer"],
           'builddir': "sanitizer-ppc64be",
           'factory': SanitizerBuilder.getSanitizerBuildFactory(timeout=1800)},

          {'name': "sanitizer-ppc64le-linux",
           'slavenames' :["ppc64le-sanitizer"],
           'builddir': "sanitizer-ppc64le",
           'factory': SanitizerBuilder.getSanitizerBuildFactory(timeout=1800)},

          {'name': "sanitizer-windows",
           'slavenames' :["sanitizer-windows"],
           'builddir': "sanitizer-windows",
           'factory': AnnotatedBuilder.getAnnotatedBuildFactory(
             script="sanitizer-windows.py",
             depends_on_projects=["llvm", "clang", "lld", "compiler-rt"])},

          ]

def _get_openmp_builders():
    return [
        {'name': "openmp-gcc-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"openmp-gcc-x86_64-linux-debian",
         'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                         env={
                             'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                             'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                         })},

        {'name': "openmp-clang-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"openmp-clang-x86_64-linux-debian",
         'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                         env={
                             'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                             'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                         })},
        ]

def _get_libcxx_builders():
    docker_slaves = [
        'libcxx-cloud1', 'libcxx-cloud2', 'libcxx-cloud3', 'libcxx-cloud4',
        'libcxx-cloud5'
    ]
    benchmark_opts = ';'.join(
        ['--benchmark_min_time=0.01', '--benchmark_color=false'])
    return [
        # gribozavr's builders on gribozavr4
        {'name': 'libcxx-libcxxabi-x86_64-linux-debian',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-x86_64-linux-debian',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             lit_extra_args=['--shuffle'],
             check_libcxx_abilist=True),
         'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-debian-noexceptions',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-x86_64-linux-debian-noexceptions',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             use_cache='Generic-noexceptions.cmake',
             lit_extra_args=['--shuffle']),
         'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-libunwind-x86_64-linux-debian',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-libunwind-x86_64-linux-debian',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON'},
             lit_extra_args=['--shuffle']),
         'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-singlethreaded-x86_64-linux-debian',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-singlethreaded-x86_64-linux-debian',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             use_cache='Generic-singlethreaded.cmake'),
         'category': 'libcxx'},

        # EricWF's builders
        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx03',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx03',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            use_cache='Generic-cxx03.cmake',
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx11',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx11',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            use_cache='Generic-cxx11.cmake',
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            use_cache='Generic-cxx14.cmake',
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx17',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx17',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXX_BENCHMARK_TEST_ARGS': benchmark_opts},
            use_cache='Generic-cxx17.cmake',
            check_libcxx_abilist=True,
            check_libcxx_benchmarks=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx2a',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx2a',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXX_BENCHMARK_TEST_ARGS': benchmark_opts},
            use_cache='Generic-cxx2a.cmake',
            check_libcxx_abilist=True,
            check_libcxx_benchmarks=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-32bit',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-32bit',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            use_cache='Generic-32bits.cmake',
            check_libcxx_abilist=False),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXX_BENCHMARK_TEST_ARGS': benchmark_opts},
            use_cache='Generic-asan.cmake',
            check_libcxx_benchmarks=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-ubsan',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-ubsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXX_BENCHMARK_TEST_ARGS': benchmark_opts},
            use_cache='Generic-ubsan.cmake',
            check_libcxx_benchmarks=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-msan',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-msan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXX_BENCHMARK_TEST_ARGS': benchmark_opts},
            use_cache='Generic-msan.cmake',
            check_libcxx_benchmarks=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-libunwind-x86_64-linux-ubuntu',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-libunwind-x86_64-linux-ubuntu',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            use_cache='Generic-tsan.cmake'),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc5-cxx11',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc5-cxx11',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': '/opt/gcc-5/bin/gcc', 'CXX': '/opt/gcc-5/bin/g++'},
            use_cache='Generic-cxx11.cmake'),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc-tot-latest-std',
         'slavenames': docker_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc-tot-latest-std',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': '/opt/gcc-tot/bin/gcc', 'CXX': '/opt/gcc-tot/bin/g++'}),
        'category': 'libcxx'},

        # ARMv7 LibC++ and LibC++abi tests (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-armv7-linux',
         'slavenames': ['linaro-tk1-02'],
         'builddir': 'libcxx-libcxxabi-libunwind-armv7-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15 -marm',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15 -marm',
                              'LLVM_PARALLEL_LINK_JOBS': '2'})},

        # ARMv8 LibC++ and LibC++abi tests (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-armv8-linux',
         'slavenames': ['linaro-armv8-libcxx'],
         'builddir': 'libcxx-libcxxabi-libunwind-armv8-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a57 -marm',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a57 -marm'})},

        # ARMv7 LibC++ and LibC++abi tests w/o EH (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-armv7-linux-noexceptions',
         'slavenames': ['linaro-tk1-02'],
         'builddir': 'libcxx-libcxxabi-libunwind-armv7-linux-noexceptions',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                              'LIBCXXABI_ENABLE_EXCEPTIONS': 'OFF',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15 -mthumb',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15 -mthumb',
                              'LLVM_PARALLEL_LINK_JOBS': '2'})},

        # ARMv8 LibC++ and LibC++abi tests w/o EH (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-armv8-linux-noexceptions',
         'slavenames': ['linaro-armv8-libcxx'],
         'builddir': 'libcxx-libcxxabi-libunwind-armv8-linux-noexceptions',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                              'LIBCXXABI_ENABLE_EXCEPTIONS': 'OFF',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a57 -mthumb',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a57 -mthumb'})},

        # AArch64 LibC++ and LibC++abi tests (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-aarch64-linux',
         'slavenames': ['linaro-aarch64-libcxx'],
         'builddir': 'libcxx-libcxxabi-libunwind-aarch64-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a57',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a57'})},

        {'name': 'libcxx-libcxxabi-libunwind-aarch64-linux-noexceptions',
         'slavenames': ['linaro-aarch64-libcxx'],
         'builddir': 'libcxx-libcxxabi-libunwind-aarch64-linux-noexceptions',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                              'LIBCXXABI_ENABLE_EXCEPTIONS': 'OFF',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a57',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a57'})},

    ]

# Toolchain builders.
def _get_toolchain_builders():
      return [
          {'name': "fuchsia-x86_64-linux",
           'slavenames' :["fuchsia-debian-64-us-central1-a-1", "fuchsia-debian-64-us-central1-b-1"],
           'builddir': "fuchsia-x86_64-linux",
           'factory': FuchsiaBuilder.getFuchsiaToolchainBuildFactory(),
           'category': 'fuchsia'},
        ]

# libc Builders
def _get_libc_builders():
    return [
        {'name': 'libc-x86_64-debian',
         'slavenames': ['libc-x86_64-debian'],
         'builddir': 'libc-x86_64-debian',
         'category': 'libc',
         'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
             script="libc-linux.py",
             depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'])},

        {'name': "libc-x86_64-debian-dbg",
         'slavenames': ["libc-x86_64-debian"],
         'builddir': "libc-x86_64-debian-dbg",
         'category' : 'libc',
         'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
             script="libc-linux.py",
             depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
             extra_args=['--debug'])},

        {'name': "libc-x86_64-debian-dbg-asan",
         'slavenames': ["libc-x86_64-debian"],
         'builddir': "libc-x86_64-debian-dbg-asan",
         'category' : 'libc',
         'factory' : AnnotatedBuilder.getAnnotatedBuildFactory(
             script="libc-linux.py",
             depends_on_projects=['llvm', 'libc', 'clang', 'clang-tools-extra'],
             extra_args=['--debug', '--asan'])},
    ]

# Flang builders.
def _get_flang_builders():
    return [
        {'name': "flang-aarch64-ubuntu",
         'slavenames':["flang-aarch64-ubuntu-build"],
         'builddir':"flang-aarch64-ubuntu-build",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm','mlir','clang','flang'],
                        extra_configure_args=[
                            "-DLLVM_TARGETS_TO_BUILD=AArch64",
                            "-DCMAKE_C_COMPILER=/usr/bin/gcc-9",
                            "-DCMAKE_CXX_COMPILER=/usr/bin/g++-9",
                            "-DLLVM_INSTALL_UTILS=ON",
                            "-DFLANG_BUILD_NEW_DRIVER=ON",
                            "-DCMAKE_CXX_STANDARD=17",
                        ],
         ),
         'category' : 'flang'},

        {'name': "flang-aarch64-ubuntu-clang",
         'slavenames':["flang-aarch64-ubuntu-clang-build"],
         'builddir':"flang-aarch64-ubuntu-clang",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm','mlir','clang','flang'],
                        extra_configure_args=[
                            "-DLLVM_TARGETS_TO_BUILD=AArch64",
                            "-DCMAKE_C_COMPILER=/usr/bin/clang-10",
                            "-DCMAKE_CXX_COMPILER=/usr/bin/clang++-10",
                            "-DLLVM_INSTALL_UTILS=ON",
                            "-DCMAKE_CXX_STANDARD=17",
                            "-DLLVM_ENABLE_WERROR=ON",
                            "-DBUILD_SHARED_LIBS=ON",
                            "-DLLVM_ENABLE_ASSERTIONS=ON",
                            "-DLLVM_ENABLE_LIBCXX=On",
                            "-DFLANG_BUILD_NEW_DRIVER=ON",
                            "-DCMAKE_BUILD_TYPE=Release",
                        ],
         ),
         'category' : 'flang'},

        {'name': "flang-aarch64-ubuntu-gcc10",
         'slavenames':["flang-aarch64-ubuntu-gcc10-build"],
         'builddir':"flang-aarch64-ubuntu-gcc10",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm','mlir','clang','flang'],
                        extra_configure_args=[
                            "-DLLVM_TARGETS_TO_BUILD=AArch64",
                            "-DCMAKE_C_COMPILER=/usr/bin/gcc-10",
                            "-DCMAKE_CXX_COMPILER=/usr/bin/g++-10",
                            "-DLLVM_INSTALL_UTILS=ON",
                            "-DCMAKE_CXX_STANDARD=17",
                            "-DLLVM_ENABLE_WERROR=OFF",
                            "-DFLANG_ENABLE_WERROR=ON",
                            "-DBUILD_SHARED_LIBS=ON",
                            "-DLLVM_ENABLE_ASSERTIONS=ON",
                            "-DFLANG_BUILD_NEW_DRIVER=ON",
                            "-DCMAKE_BUILD_TYPE=Release",
                        ],
         ),
         'category' : 'flang'},

        {'name': "flang-aarch64-ubuntu-out-of-tree",
         'slavenames':["linaro-aarch64-flang-oot"],
         'builddir':"flang-aarch64-out-of-tree",
         'factory': FlangBuilder.getFlangOutOfTreeBuildFactory(
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
            ],
        ),
        'category' : 'flang'},

        {'name': "flang-x86_64-linux",
         'slavenames':["nersc-flang"],
         'builddir':"flang-x86_64-linux",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        depends_on_projects=['llvm','mlir','clang','flang'],
                        extra_configure_args=[
                            "-DLLVM_TARGETS_TO_BUILD=X86",
                            "-DLLVM_INSTALL_UTILS=ON",
                            "-DCMAKE_CXX_STANDARD=17",
                        ],
         ),
         'category' : 'flang'},
        {'name': 'ppc64le-flang-rhel-clang',
         'mergeRequests': False,
         'slavenames': ['ppc64le-flang+mlir-rhel-test'],
         'builddir': 'ppc64le-flang-rhel-clang-build',
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                         clean=True,
                         depends_on_projects=['llvm', 'mlir', 'clang', 'flang'],
                         checks=['check-flang'],
                         extra_configure_args=[
                             '-DLLVM_TARGETS_TO_BUILD=PowerPC',
                             '-DLLVM_INSTALL_UTILS=ON',
                             '-DCMAKE_CXX_STANDARD=17',
                             '-DLLVM_ENABLE_PROJECTS=flang',
                             '-DLLVM_LIT_ARGS="-vj 256"'
                         ],
                         env={
                             'CC': 'clang',
                             'CXX': 'clang++',
                             'LD': 'lld'
                         }),
         'category': 'flang'},
        ]

# Experimental and stopped builders
def _get_on_demand_builders():
    return [
        ]

def _get_experimental_scheduled_builders():
    return [
        {'name': "clang-cuda-k80",
         'slavenames' :["cuda-k80-0"],
         'builddir': "clang-cuda-k80",
         'factory': AnnotatedBuilder.getAnnotatedBuildFactory(script="/buildbot/cuda-build",
                                                              checkout_llvm_sources=False),
         'category' : 'clang'},
        {'name': "clang-cuda-p4",
         'slavenames' :["cuda-p4-0"],
         'builddir': "clang-cuda-p4",
         'factory': AnnotatedBuilder.getAnnotatedBuildFactory(script="/buildbot/cuda-build",
                                                              checkout_llvm_sources=False),
         'category' : 'clang'},
        {'name': "clang-cuda-t4",
         'slavenames' :["cuda-t4-0"],
         'builddir': "clang-cuda-t4",
         'factory': AnnotatedBuilder.getAnnotatedBuildFactory(script="/buildbot/cuda-build",
                                                              checkout_llvm_sources=False),
         'category' : 'clang'},
        {'name': "clang-ve-ninja",
         'slavenames':["nec-arrproto41"],
         'builddir':"clang-ve-ninja",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm','clang','openmp'],
                        extra_configure_args=[
                            "-DLLVM_TARGETS_TO_BUILD=X86",
                            "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=VE",
                        ],
         ),
         'category' : 'clang'},
        ]

# Builders responsible building Sphinix documentation
def _get_documentation_builders():
    return [
             {
               'name':"llvm-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"llvm-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(llvm_html=True, llvm_man=True),
               'category' : 'llvm'
             },
             {
               'name':"clang-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"clang-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(clang_html=True),
               'category' : 'clang'
             },
             {
               'name':"clang-tools-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"clang-tools-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(clang_tools_html=True),
               'category' : 'clang'
             },
             {
               'name':"lld-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"lld-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(lld_html=True),
               'category' : 'lld'
             },
             {
               'name':"lldb-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"lldb-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(lldb_html=True),
               'category' : 'lldb'
             },
             {
               'name':"libcxx-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"libcxx-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(libcxx_html=True),
               'category' : 'libcxx'
             },
             {
               'name':"libunwind-sphinx-docs",
               'slavenames':["gribozavr3"],
               'builddir':"libunwind-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(libunwind_html=True),
               'category' : 'libunwind'
             },
             # Sphinx doc Publisher
             {
               'name':"publish-sphinx-docs",
               'slavenames':["as-bldslv5"],
               'builddir':"publish-sphinx-docs",
               'factory': SphinxDocsBuilder.getLLVMDocsBuildFactory(clean=True),
               'category' : 'doc'
             }
           ]

# Builders for ML-driven compiler optimizations.
def _get_ml_compiler_opt_builders():
    common_extra_args = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DLLVM_CCACHE_BUILD=ON",
        "-DLLVM_ENABLE_ASSERTIONS=ON", ]

    return [
        # Development mode build bot: tensorflow C APIs are present, and
        # we can dynamically load models, and produce training logs.
        {'name': "ml-opt-dev-x86-64",
         'mergeRequests': False,
         'slavenames':["ml-opt-dev-x86-64-b1"],
         'builddir':"ml-opt-dev-x86-64-b1",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm'],
                        extra_configure_args=common_extra_args + [
                            "-DTENSORFLOW_API_PATH=/tmp/tensorflow",
                            "-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON"
                        ])},
        # Release mode build bot: the model is pre-built and linked in the
        # compiler. Only the tensorflow pip package is needed, and out of it,
        # only saved_model_cli (the model compiler) and the thin C++ wrappers
        # in xla_aot_runtime_src (and include files)
        {'name': "ml-opt-rel-x86-64",
         'mergeRequests': False,
         'slavenames':["ml-opt-rel-x86-64-b1"],
         'builddir':"ml-opt-rel-x86-64-b1",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm'],
                        extra_configure_args=common_extra_args + [
                            "-DTENSORFLOW_AOT_PATH=/var/lib/buildbot/.local/lib/python3.7/site-packages/tensorflow"
                        ])},
        # Both tensorflow C library, and the pip package, are present.
        {'name': "ml-opt-devrel-x86-64",
         'mergeRequests': False,
         'slavenames':["ml-opt-devrel-x86-64-b1"],
         'builddir':"ml-opt-devrel-x86-64-b1",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                        clean=True,
                        depends_on_projects=['llvm'],
                        extra_configure_args=common_extra_args + [
                            "-DTENSORFLOW_API_PATH=/tmp/tensorflow",
                            "-DTENSORFLOW_AOT_PATH=/var/lib/buildbot/.local/lib/python3.7/site-packages/tensorflow",
                            "-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON"
                        ])},
    ]

def get_builders():
    for b in _get_llvm_builders():
        b['category'] = 'llvm'
        yield b

    for b in _get_clang_fast_builders():
        b['category'] = 'clang_fast'
        yield b

    for b in _get_clang_builders():
        b['category'] = 'clang'
        yield b

    for b in _get_polly_builders():
        b['category'] = 'polly'
        yield b

    for b in _get_aosp_builders():
        b['category'] = 'aosp'
        yield b

    for b in _get_rev_iter_builders():
        b['category'] = 'rev_iter'
        yield b

    for b in _get_lld_builders():
        b['category'] = 'lld'
        yield b

    for b in _get_lldb_builders():
        b['category'] = 'lldb'
        yield b

    for b in _get_mlir_builders():
        b['category'] = 'mlir'
        yield b

    for b in _get_ml_compiler_opt_builders():
        b['category'] = 'ml_opt'
        yield b

    for b in _get_sanitizer_builders():
        b['category'] = 'sanitizer'
        yield b

    for b in _get_openmp_builders():
        b['category'] = 'openmp'
        yield b

    for b in _get_libcxx_builders():
        b['category'] = 'libcxx'
        yield b

    for b in _get_toolchain_builders():
        b['category'] = 'toolchain'
        yield b

    for b in _get_libc_builders():
        b['category'] = 'libc'
        yield b

    for b in _get_flang_builders():
        b['category'] = 'flang'
        yield b

    for b in _get_documentation_builders():
        yield b

    for b in _get_experimental_scheduled_builders():
        if not b.get('category', '').endswith('.exp'):
           b['category'] = b.get('category', '') + '.exp'
        yield b

    for b in _get_on_demand_builders():
        if not b.get('category', '').endswith('.on-demand'):
           b['category'] = b.get('category', '') + '.on-demand'
        yield b
