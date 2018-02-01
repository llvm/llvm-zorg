from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.builders import LLVMBuilder
from zorg.buildbot.builders import PollyBuilder
from zorg.buildbot.builders import LLDBBuilder
from zorg.buildbot.builders import LLDBuilder
from zorg.buildbot.builders import LLGoBuilder
from zorg.buildbot.builders import ClangAndLLDBuilder
from zorg.buildbot.builders import SanitizerBuilder
from zorg.buildbot.builders import SanitizerBuilderII
from zorg.buildbot.builders import SanitizerBuilderWindows
from zorg.buildbot.builders import OpenMPBuilder
from zorg.buildbot.builders import LibcxxAndAbiBuilder
from zorg.buildbot.builders import SphinxDocsBuilder
from zorg.buildbot.builders import ABITestsuitBuilder
from zorg.buildbot.builders import ClangLTOBuilder3Stage
from zorg.buildbot.builders import ClangLTOBuilder
from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.builders import CUDATestsuiteBuilder
from zorg.buildbot.builders import AOSPBuilder
from zorg.buildbot.builders import AnnotatedBuilder

# Plain LLVM builders.
def _get_llvm_builders():
    return [
        # We currently have to force LLVM_HOST_TRIPLE and
        # LLVM_DEFAULT_TARGET_TRIPLE on this system. CMake gets the value
        # correct for the processor but it's currently not possible to emit O32
        # code using a mips64-* triple. This is a bug and should be fixed soon.
        # We must also force LLVM_TARGET_ARCH so that the ExecutionEngine tests
        # run.
        {'name': "llvm-mips-linux",
         'slavenames':["mipsswbrd002"],
         'builddir':"llvm-mips-linux",
         'factory': LLVMBuilder.getLLVMCMakeBuildFactory(
                        timeout=40, config_name='Release',
                        enable_shared=True,
                        extra_cmake_args=["-DLLVM_HOST_TRIPLE=mips-linux-gnu",
                                          "-DLLVM_DEFAULT_TARGET_TRIPLE=mips-linux-gnu",
                                          "-DLLVM_TARGET_ARCH=Mips",
                                          "-DLLVM_ENABLE_ASSERTIONS=ON",
                                          "-DLLVM_PARALLEL_LINK_JOBS=1"],
                        env={'CC': '/mips/proj/build-compiler/clang-be-o32-latest/bin/clang',
                             'CXX': '/mips/proj/build-compiler/clang-be-o32-latest/bin/clang++',
                            })},
        {'name': "llvm-hexagon-elf",
         'slavenames':["hexagon-build-02", "hexagon-build-03"],
         'builddir':"llvm-hexagon-elf",
         'factory': LLVMBuilder.getLLVMCMakeBuildFactory(
                        timeout=40, config_name='Release',
                        jobs=16,
                        enable_shared=False,
                        env={'LD_LIBRARY_PATH': '/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/lib'},
                        extra_cmake_args=[
                          "-G", "Unix Makefiles",
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
                          "-DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++ -I/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/include/c++/v1'",
                          "-DCMAKE_EXE_LINKER_FLAGS:STRING='-lc++abi -L/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/lib'",
                          "-DCMAKE_SHARED_LINKER_FLAGS:STRING='-lc++abi -L/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/lib'",
                          "-DWITH_POLLY:BOOL=OFF",
                          "-DLINK_POLLY_INTO_TOOLS:BOOL=OFF",
                          "-DPOLLY_BUILD_SHARED_LIB:BOOL=OFF",
                          "-DWITH_POLLY:BOOL=OFF",
                          "-DLINK_POLLY_INTO_TOOLS:BOOL=OFF",
                          "-DPOLLY_BUILD_SHARED_LIB:BOOL=OFF",
                          "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                          "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"
                        ])},
        {'name': "llvm-avr-linux",
         'slavenames':["avr-build-01"],
         'builddir':"llvm-avr-linux",
         'factory': LLVMBuilder.getLLVMCMakeBuildFactory(
                        timeout=40, config_name='Release',
                        enable_shared=True,
                        extra_cmake_args=[
                          "-G", "Unix Makefiles",
                          "-DCMAKE_BUILD_TYPE:STRING=Release",
                          # We need to compile the X86 backend due to a few generic CodeGen tests.
                          "-DLLVM_TARGETS_TO_BUILD:STRING=AVR;X86",
                          "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD:STRING=AVR",
                          "-DBUILD_SHARED_LIBS=ON",
                        ])},
        {'name': "llvm-riscv-linux",
         'slavenames':["riscv-build-01"],
         'builddir':"llvm-riscv-linux",
         'factory': LLVMBuilder.getLLVMCMakeBuildFactory(
                        timeout=40, config_name='Release',
                        enable_shared=True,
                        extra_cmake_args=[
                          "-G", "Unix Makefiles",
                          "-DCMAKE_BUILD_TYPE:STRING=Release",
                          # We need to compile the X86 backend due to a few generic CodeGen tests.
                          "-DLLVM_TARGETS_TO_BUILD:STRING=RISCV;X86",
                          "-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD:STRING=RISCV",
                          "-DBUILD_SHARED_LIBS=ON",
                          "-DCMAKE_C_COMPILER='clang'",
                          "-DCMAKE_CXX_COMPILER='clang++'",
                          "-DLLVM_ENABLE_LLD=True",
                        ])}
        ]

# Clang fast builders.
def _get_clang_fast_builders():
    return [
        {'name': "clang-x86_64-debian-fast",
         'slavenames':["gribozavr4"],
         'builddir':"clang-x86_64-debian-fast",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                     withLLD=False,
                     extraCmakeOptions=[
                       "-DCOMPILER_RT_BUILD_BUILTINS:BOOL=OFF",
                       "-DCOMPILER_RT_BUILD_SANITIZERS:BOOL=OFF",
                       "-DCOMPILER_RT_BUILD_XRAY:BOOL=OFF",
                       "-DCOMPILER_RT_CAN_EXECUTE_TESTS:BOOL=OFF",
                       "-DCOMPILER_RT_INCLUDE_TESTS:BOOL=OFF"],
                     prefixCommand=None, # This is a designated builder, so no need to be nice.
                     env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                         'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes'})},

        {'name': "llvm-clang-lld-x86_64-debian-fast",
         'slavenames':["gribozavr4"],
         'builddir':"llvm-clang-lld-x86_64-debian-fast",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                    env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                         'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes', 'ASM': 'clang'})},

        {'name': "llvm-clang-lld-x86_64-scei-ps4-ubuntu-fast",
         'mergeRequests': False,
         'slavenames': ["ps4-buildslave4"],
         'builddir': "llvm-clang-lld-x86_64-scei-ps4-ubuntu-fast",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                     extraCmakeOptions=["-DCMAKE_C_COMPILER=clang",
                                        "-DCMAKE_CXX_COMPILER=clang++",
                                        "-DCOMPILER_RT_BUILD_BUILTINS:BOOL=OFF",
                                        "-DCOMPILER_RT_BUILD_SANITIZERS:BOOL=OFF",
                                        "-DCOMPILER_RT_CAN_EXECUTE_TESTS:BOOL=OFF",
                                        "-DCOMPILER_RT_INCLUDE_TESTS:BOOL=OFF",
                                        "-DLLVM_TOOL_COMPILER_RT_BUILD:BOOL=OFF",
                                        "-DLLVM_BUILD_TESTS:BOOL=ON",
                                        "-DLLVM_BUILD_EXAMPLES:BOOL=ON",
                                        "-DCLANG_BUILD_EXAMPLES:BOOL=ON",
                                        "-DLLVM_TARGETS_TO_BUILD=X86"],
                     triple="x86_64-scei-ps4",
                     prefixCommand=None, # This is a designated builder, so no need to be nice.
                     env={'PATH':'/opt/llvm_37/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})},

        {'name': "llvm-clang-lld-x86_64-scei-ps4-windows10pro-fast",
         'mergeRequests': True,
         'slavenames': ["ps4-buildslave2"],
         'builddir': "llvm-clang-lld-x86_64-scei-ps4-windows10pro-fast",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                     extraCmakeOptions=["-DLLVM_TOOL_COMPILER_RT_BUILD:BOOL=OFF",
                                        "-DLLVM_BUILD_TESTS:BOOL=ON",
                                        "-DLLVM_BUILD_EXAMPLES:BOOL=ON",
                                        "-DCLANG_BUILD_EXAMPLES:BOOL=ON",
                                        "-DLLVM_TARGETS_TO_BUILD=X86"],
                     triple="x86_64-scei-ps4",
                     isMSVC=True,
                     prefixCommand=None, # This is a designated builder, so no need to be nice.
                     extraLitArgs=["-j80"])},

        {'name': "llvm-clang-x86_64-expensive-checks-win",
         'slavenames':["ps4-buildslave2"],
         'builddir':"llvm-clang-x86_64-expensive-checks-win",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                extra_configure_args = ["-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                                        "-DLLVM_ENABLE_WERROR=OFF",
                                        "-DCMAKE_BUILD_TYPE=Debug",
                                        "-DLLVM_LIT_ARGS='-v'"])},
    ]

# Clang builders.
def _get_clang_builders():
    return [
        {'name': "clang-atom-d525-fedora-rel",
         'slavenames':["atom1-buildbot"],
         'builddir':"clang-atom-d525-fedora-rel",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                       clean=False,
                       checkout_compiler_rt=False,
                       checkout_lld=False,
                       useTwoStage=False,
                       stage1_config='Release',
                       test=True,
                       testStage1=True,
                       extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                         '-DLLVM_USE_INTEL_JITEVENTS=TRUE'])},

        # Cortex-A15 LNT test-suite in Benchmark mode
        {'name' : "clang-native-arm-lnt-perf",
         'slavenames':["linaro-tk1-02"],
         'builddir':"clang-native-arm-lnt-perf",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
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
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"],
                      submitURL='http://lnt.llvm.org/submitRun',
                      testerName='LNT-Thumb2v7-A15-O3')},

        # Cortex-A15 LNT test-suite in test-only mode
        {'name' : "clang-native-arm-lnt",
         'slavenames':["linaro-tk1-03", "linaro-armv8-01-arm-lnt"],
         'builddir':"clang-native-arm-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a15 -marm',
                                       '--threads=4', '--build-threads=4'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all self-host NEON with CMake builder
        {'name': "clang-cmake-armv7-a15-selfhost-neon",
         'slavenames':["linaro-tk1-04", "linaro-armv8-01-arm-selfhost-neon"],
         'builddir':"clang-cmake-armv7-a15-selfhost-neon",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      useTwoStage=True,
                      testStage1=False,
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j2'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all with CMake builder
        {'name': "clang-cmake-armv7-a15",
         'slavenames':["linaro-tk1-06", "linaro-armv8-01-arm-quick"],
         'builddir':"clang-cmake-armv7-a15",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j4'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all self-host with CMake builder
        {'name': "clang-cmake-armv7-a15-selfhost",
         'slavenames':["linaro-tk1-07", "linaro-armv8-01-arm-selfhost"],
         'builddir':"clang-cmake-armv7-a15-selfhost",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      useTwoStage=True,
                      testStage1=False,
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j4'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## AArch64 Clang+LLVM check-all + test-suite
        {'name': "clang-cmake-aarch64-quick",
         'slavenames':["linaro-apm-01", "linaro-armv8-01-aarch64-quick"],
         'builddir':"clang-cmake-aarch64-quick",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a57',
                                       '--threads=8', '--build-threads=8'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

        ## AArch64 Self-hosting Clang+LLVM check-all + LLD + test-suite
        ## TODO: Remove the X86 back-end after fixing the 90 bad tests
        ## TODO: Add Compiler-RT after fixing all the failures
        ## TODO: Fix the three remaining test-suite failures
        {'name': "clang-cmake-aarch64-lld",
         'slavenames':["linaro-apm-04", "linaro-armv8-01-aarch64-lld"],
         'builddir':"clang-cmake-aarch64-lld",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=True,
                      test=True,
                      useTwoStage=True,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags',
                                       '-mcpu=cortex-a57 -fuse-ld=lld',
                                       '--threads=8', '--build-threads=8'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64;X86'",
                                        "-DLLVM_ENABLE_LLD=True"],
               ),
         'category'   : 'lld'},

        ## AArch64 Clang+LLVM run test-suite with GlobalISel enabled
        {'name': "clang-cmake-aarch64-global-isel",
         'slavenames':["linaro-apm-06", "linaro-armv8-01-aarch64-global-isel"],
         'builddir':"clang-cmake-aarch64-global-isel",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=False,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags',
                                       '-mcpu=cortex-a57 -O0 -mllvm -global-isel -mllvm -global-isel-abort=0',
                                       '--threads=8', '--build-threads=8'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

        {'name': 'clang-x86-windows-msvc2015',
         'slavenames': ['windows-gcebot2'],
         'builddir': 'clang-x86-windows-msvc2015',
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        vs='%VS140COMNTOOLS%',
                        vs_target_arch='x86',
                        checkout_compiler_rt=False,
                        checkout_lld=False,
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='RelWithDebInfo',
                        stage2_config='RelWithDebInfo',
                        extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"])},

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
                                                            nt_flags=['--threads=4', '--build-threads=4'],
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        # ABI test-suite with CMake builder
        {'name'          : "clang-x86_64-linux-abi-test",
         'mergeRequests' : False,
         'slavenames'    : ["ps4-buildslave1a"],
         'builddir'      : "clang-x86_64-linux-abi-test",
         'factory'       : ABITestsuitBuilder.getABITestsuitBuildFactory(
                               # TODO: Enable Werror once all the warnings are cleaned.
                               extra_configure_args = ["-DLLVM_ENABLE_WERROR=OFF"])},

        # Clang cross builders.
#        {'name' : "clang-x86_64-darwin13-cross-mingw32",
#         'slavenames' :["as-bldslv9"],
#         'builddir' :"clang-x86_64-darwin13-cross-mingw32",
#         'factory' : ClangBuilder.getClangBuildFactory(use_pty_in_tests=True,
#                                                       test=False,
#                                                       env = { 'CC' : 'clang',
#                                                               'CXX' : 'clang++',
#                                                               'CXXFLAGS' : '-stdlib=libc++'},
#                                                       extra_configure_args=['--build=x86_64-apple-darwin13',
#                                                                             '--host=x86_64-apple-darwin13',
#                                                                             '--target=i686-pc-mingw32'])},

#        {'name' : "clang-x86_64-darwin13-cross-arm",
#         'slavenames' :["as-bldslv9"],
#         'builddir' :"clang-x86_64-darwin13-cross-arm",
#         'factory' : ClangBuilder.getClangBuildFactory(use_pty_in_tests=True,
#                                                       env = { 'CC' : 'clang',
#                                                               'CXX' : 'clang++',
#                                                               'CXXFLAGS' : '-stdlib=libc++'},
#                                                       test=False,
#                                                       extra_configure_args=['--build=x86_64-apple-darwin13',
#                                                                             '--host=x86_64-apple-darwin13',
#                                                                             '--target=arm-eabi',
#                                                                             '--enable-targets=arm'])},

#        {'name' : "clang-x86_64-ubuntu-gdb-75",
#         'slavenames' :["hpproliant1"],
#         'builddir' :"clang-x86_64-ubuntu-gdb-75",
#         'factory' : ClangBuilder.getClangBuildFactory(stage1_config='Release+Asserts', run_modern_gdb=True, clean=False)},

        {'name' : "clang-hexagon-elf",
         'slavenames' :["hexagon-build-02", "hexagon-build-03"],
         'builddir' :"clang-hexagon-elf",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
            jobs=16,
            checkout_clang_tools_extra=False,
            checkout_compiler_rt=False,
            checkout_lld=False,
            env={'LD_LIBRARY_PATH': '/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/lib'},
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
              "-DCMAKE_CXX_FLAGS:STRING='-stdlib=libc++ -I/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/include/c++/v1'",
              "-DCMAKE_EXE_LINKER_FLAGS:STRING='-lc++abi -L/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/lib'",
              "-DCMAKE_SHARED_LINKER_FLAGS:STRING='-lc++abi -L/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/lib'",
              "-DWITH_POLLY:BOOL=OFF",
              "-DLINK_POLLY_INTO_TOOLS:BOOL=OFF",
              "-DPOLLY_BUILD_SHARED_LIB:BOOL=OFF",
              "-DWITH_POLLY:BOOL=OFF",
              "-DLINK_POLLY_INTO_TOOLS:BOOL=OFF",
              "-DPOLLY_BUILD_SHARED_LIB:BOOL=OFF",
              "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
              "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"])},

        {'name': "perf-x86_64-penryn-O3",
         'slavenames':["pollyperf2", "pollyperf3", "pollyperf4", "pollyperf5"],
         'builddir':"perf-x86_64-penryn-O3",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    #nt_flags=['--multisample=10', '--rerun'],
                                                    nt_flags=['--multisample=10'],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://lnt.llvm.org/submitRun'],
                                                    testerName='x86_64-penryn-O3')},
        {'name' : "clang-x86_64-linux-selfhost-modules",
         'slavenames' : ["modules-slave-1"],
         'builddir' : "clang-x86_64-linux-selfhost-modules",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                                       checkout_lld=False,
                                                       useTwoStage=True,
                                                       clean=False,
                                                       stage1_config='Release',
                                                       stage2_config='Release',
                                                       extra_configure_args=['-DCMAKE_C_COMPILER=clang',
                                                                             '-DCMAKE_CXX_COMPILER=clang++',
                                                                             '-DCMAKE_CXX_FLAGS=-stdlib=libc++',
                                                                             '-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                       stage2_extra_configure_args=['-DCMAKE_CXX_FLAGS=-stdlib=libc++',
                                                                                    '-DLLVM_ENABLE_MODULES=1'])},

        {'name' : "clang-x86_64-linux-selfhost-modules-2",
         'slavenames' : ["modules-slave-2"],
         'builddir' : "clang-x86_64-linux-selfhost-modules-2",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                                       checkout_lld=False,
                                                       useTwoStage=True,
                                                       clean=False,
                                                       stage1_config='Release',
                                                       stage2_config='Release',
                                                       extra_configure_args=['-DCMAKE_C_COMPILER=clang',
                                                                             '-DCMAKE_CXX_COMPILER=clang++',
                                                                             '-DCMAKE_CXX_FLAGS=-stdlib=libstdc++',
                                                                             '-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                       stage2_extra_configure_args=['-DCMAKE_CXX_FLAGS=-stdlib=libstdc++',
                                                                                    '-DLLVM_ENABLE_MODULES=1'])},

        {'name' : "clang-x64-ninja-win7",
         'slavenames' : ["windows7-buildbot"],
         'builddir' : "clang-x64-ninja-win7",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        checkout_lld=False,
                        vs='%VS140COMNTOOLS%',
                        vs_target_arch='x64',
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='Release',
                        stage2_config='Release',
                        extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                          '-DLLVM_TARGETS_TO_BUILD=X86'])},

        {'name' : "clang-x86_64-freebsd11",
         'slavenames' : ["freebsd01"],
         'builddir' : "clang-x86_64-freebsd",
         'factory': ClangBuilder.getClangCMakeBuildFactory(
                       checkout_lld=False,
                       clean=False)},

        {'name' : "clang-freebsd11-amd64",
         'slavenames' : ["freebsd11-amd64"],
         'builddir' : "clang-freebsd11-amd64",
         'factory': ClangBuilder.getClangCMakeBuildFactory(
                       checkout_lld=False,
                       clean=True,
                       extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                         '-DCMAKE_BUILD_TYPE:STRING=Release'])},

        {'name': "ubuntu-gcc7.1-werror",
         'slavenames':["am1i-slv2"],
         'builddir':"ubuntu-gcc7.1-werror",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
            depends_on_projects = ['llvm', 'clang'],
            clean = False,
            checks = [],
            extra_configure_args = [
               "-DLLVM_ENABLE_WERROR=ON",
               "-DCMAKE_C_COMPILER=gcc-7.1",
               "-DCMAKE_CXX_COMPILER=g++-7.1",
               # We build with c++11, no need in c++17 warnings.
               "-DCMAKE_CXX_FLAGS=-Wno-noexcept-type",
               # We want the given CXXFLAGS be used for the tablegen as well.
               "-DLLVM_OPTIMIZED_TABLEGEN=OFF",
               "-DBUILD_SHARED_LIBS=ON",
               "-DLLVM_BUILD_TESTS=ON",
               "-DLLVM_BUILD_EXAMPLES=OFF",
               "-DCLANG_BUILD_EXAMPLES=OFF",
               "-DLLVM_TARGETS_TO_BUILD=X86",
            ])},

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

#        {'name' : "clang-3stage-ubuntu",
#         'slavenames' : ["ps4-buildslave1a"],
#         'builddir' : "clang-3stage-ubuntu",
#         'factory': ClangLTOBuilder3Stage.get3StageClangLTOBuildFactory(
#               clean=True,
#               env=None,
#               build_gold=True,
#               cmake_cache_file="../llvm.src/tools/clang/cmake/caches/3-stage.cmake",
#               extra_cmake_options=[
#                   '-GNinja',
#                   '-DLLVM_TARGETS_TO_BUILD=all',
#                   '-DLLVM_BINUTILS_INCDIR=/opt/binutils/include'])},
    ]

# Polly builders.
def _get_polly_builders():
    return [
        {'name': "polly-amd64-linux",
         'slavenames':["grosser1"],
         'builddir':"polly-amd64-linux",
         'factory': PollyBuilder.getPollyBuildFactory()},

        {'name': "perf-x86_64-penryn-O3-polly-fast",
         'slavenames':["pollyperf2"],
         'builddir': "perf-x86_64-penryn-O3-polly-fast",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '-j16' ],
                                                    reportBuildslave=False,
                                                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    testerName='x86_64-penryn-O3-polly-fast')},

        {'name': "perf-x86_64-penryn-O3-polly-parallel-fast",
         'slavenames':["pollyperf6", "pollyperf14"],
         'builddir': "perf-x86_64-penryn-O3-polly-parallel-fast",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '--mllvm=-polly-parallel', '-j16', '--cflag=-lgomp' ],
                                                    reportBuildslave=False,
                                                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    testerName='x86_64-penryn-O3-polly-parallel-fast')},

        {'name': "perf-x86_64-penryn-O3-polly-unprofitable",
         'slavenames':["pollyperf6", "pollyperf14"],
         'builddir': "perf-x86_64-penryn-O3-polly-unprofitable",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '--mllvm=-polly-process-unprofitable', '-j16'],
                                                    reportBuildslave=False,
                                                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    testerName='x86_64-penryn-O3-polly-unprofitable')},

        {'name': "perf-x86_64-penryn-O3-polly",
         'slavenames':["pollyperf11", "pollyperf7", "pollyperf15"],
         'builddir':"perf-x86_64-penryn-O3-polly",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    #nt_flags=['--multisample=10', '--mllvm=-polly', '--rerun'],
                                                    nt_flags=['--multisample=10', '--mllvm=-polly'],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://lnt.llvm.org/submitRun'],
                                                    testerName='x86_64-penryn-O3-polly')},

        {'name': "perf-x86_64-penryn-O3-polly-detect-only",
         'slavenames':["pollyperf15"],
         'builddir':"perf-x86_64-penryn-O3-polly-detect-only",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    #nt_flags=['--multisample=10', '--mllvm=-polly', '--rerun'],
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-only-scop-detection'],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://lnt.llvm.org/submitRun'],
                                                    testerName='x86_64-penryn-O3-polly-before-vectorizer-detect-only')},

        {'name': "polly-arm-linux",
         'slavenames': ["hexagon-build-02", "hexagon-build-03"],
         'builddir': "polly-arm-linux",
         'factory': PollyBuilder.getPollyBuildFactory(
                clean=True,
                install=True,
                make='ninja',
                jobs=16,
                extraCmakeArgs=["-G", "Ninja",
                                "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                "-DLLVM_DEFAULT_TARGET_TRIPLE=arm-linux-gnueabi",
                                "-DLLVM_TARGET_ARCH=arm-linux-gnueabi",
                                "-DLLVM_ENABLE_ASSERTIONS=True",
                                "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                                "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"])}
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
                                  "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                                  "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"],
                timeout=240,
                target_clang=None,
                target_flags="-Wno-error -O3 -mllvm -polly -mllvm -polly-position=before-vectorizer -mllvm -polly-process-unprofitable",
                jobs=8,
                extra_make_args=None,
                env={},
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
                extraCmakeArgs=["-G", "Ninja",
                                "-DLLVM_REVERSE_ITERATION:BOOL=ON",
                                "-DLLVM_ENABLE_ASSERTIONS=True",
                                "-DCMAKE_C_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang",
                                "-DCMAKE_CXX_COMPILER:FILEPATH=/local/clang+llvm-3.7.1-x86_64-linux-gnu-ubuntu-14.04/bin/clang++"])}
    ]

# LLDB builders.
def _get_lldb_builders():
    return [
        {'name': "lldb-x86-windows-msvc2015",
         'slavenames': ["zturner-win2008"],
         'builddir': "lldb-windows-x86",
         'factory': LLDBBuilder.getLLDBWindowsCMakeBuildFactory(test=False)},
        # Disable the builder till we fix the cmake configuration
        #{'name': "lldb-x86-win7-msvc",
        #'slavenames': ["hexagon-build-01"],
        #'builddir': "builddir/lldb-win7-msvc",
        #'factory': LLDBBuilder.getLLDBWindowsCMakeBuildFactory(config='Debug')},
        {'name': "lldb-x86_64-ubuntu-14.04-buildserver",
         'slavenames': ["lldb-linux-android-buildserver"],
         'builddir': "lldb-android-buildserver",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    buildAndroid=True,
                    runTest=False,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON'])},
        {'name': "lldb-x86_64-ubuntu-14.04-cmake",
         'slavenames': ["lldb-build1-ubuntu-1404"],
         'builddir': "buildWorkingDir",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    buildAndroid=False,
                    runTest=True,
                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON'])},
        {'name': "lldb-amd64-ninja-netbsd7",
         'slavenames': ["lldb-amd64-ninja-netbsd7"],
         'builddir': "build",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    runTest=True)},
        {'name': "lldb-amd64-ninja-netbsd8",
         'slavenames': ["lldb-amd64-ninja-netbsd8"],
         'builddir': "netbsd8",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    runTest=False)},
        {'name': "lldb-amd64-ninja-freebsd11",
         'slavenames': ["lldb-amd64-ninja-freebsd11"],
         'builddir': "scratch",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    runTest=False)}
       ]

# LLD builders.
def _get_lld_builders():
    return [
        {'name': "lld-x86_64-darwin13",
         'slavenames' :["as-bldslv9"],
         'builddir':"lld-x86_64-darwin13",
         'factory': LLDBuilder.getLLDBuildFactory(),
         'category'   : 'lld'},

        {'name': "lld-x86_64-win7",
         'mergeRequests': False,
         'slavenames' :["as-bldslv4"],
         'builddir':"lld-x86_64-win7",
         'factory': LLDBuilder.getLLDWinBuildFactory(
                        extra_configure_args = [
                          '-DLLVM_ENABLE_WERROR=OFF'
                        ]),
         'category'   : 'lld'},

        {'name': "lld-x86_64-freebsd",
         'slavenames' :["as-bldslv5"],
         'builddir':"lld-x86_64-freebsd",
         'factory': LLDBuilder.getLLDBuildFactory(extra_configure_args=[
                                                      '-DCMAKE_EXE_LINKER_FLAGS=-lcxxrt',
                                                      '-DLLVM_ENABLE_WERROR=OFF'],
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

        {'name': "clang-with-thin-lto-windows",
         'slavenames' :["windows-lld-thinlto-1"],
         'builddir': "clang-with-thin-lto-windows",
         'factory': AnnotatedBuilder.getAnnotatedBuildFactory(
             script="clang-with-thin-lto-windows.py",
             depends_on_projects=['llvm', 'clang', 'lld']),
         'category'   : 'lld'},

        {'name' : "clang-lld-x86_64-2stage",
         'slavenames' : ["am1i-slv1", "am1i-slv3", "am1i-slv4"],
         'builddir' : "clang-lld-x86_64-2stage",
         'factory': UnifiedTreeBuilder.getCmakeWithNinjaMultistageBuildFactory(
                                  depends_on_projects=['llvm', 'clang', 'lld']),
         'category'   : 'lld'},


         ]

# llgo builders.
def _get_llgo_builders():
    return [
    ]
#Offline
{'name': "llgo-x86_64-linux",
 'slavenames': ["llgo-builder"],
 'builddir': "llgo-x86_64-linux",
 'factory': LLGoBuilder.getLLGoBuildFactory()},

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
           'factory': SanitizerBuilderWindows.getSanitizerWindowsBuildFactory(
                        vs='%VS140COMNTOOLS%')},

          ## Cortex-A15 check-all full (compiler-rt) with CMake builder; Needs x86 for ASAN tests
          {'name': "clang-cmake-armv7-a15-full",
           'slavenames':["linaro-tk1-08", "linaro-tk1-09", "linaro-armv8-01-arm-full"],
           'builddir':"clang-cmake-armv7-a15-full",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        checkout_lld=False,
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                          "-DLLVM_LIT_ARGS='-sv -j4'",
                                          "-DLLVM_PARALLEL_LINK_JOBS=2"])},

          ## Cortex-A15 Thumb2 check-all full (compiler-rt) with CMake builder; Needs x86 for ASAN tests
          {'name': "clang-cmake-thumbv7-a15-full-sh",
           'slavenames':["linaro-tk1-05", "linaro-armv8-01-arm-full-selfhost"],
           'builddir':"clang-cmake-thumbv7-a15-full-sh",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        checkout_lld=False,
                        useTwoStage=True,
                        testStage1=False,
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                          "-DLLVM_LIT_ARGS='-sv -j2'",
                                          "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        # AArch64 Clang+LLVM+RT check-all + test-suite + self-hosting
        {'name': "clang-cmake-aarch64-full",
         'slavenames':["linaro-apm-02", "linaro-apm-05", "linaro-armv8-01-aarch64-full"],
         'builddir':"clang-cmake-aarch64-full",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      clean=False,
                      checkout_compiler_rt=True,
                      checkout_lld=False,
                      test=True,
                      useTwoStage=True,
                      testStage1=False,
                      runTestSuite=True,
                      testsuite_flags=['--cppflags', '-mcpu=cortex-a57',
                                       '--threads=8', '--build-threads=8'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

          # Juno
          {'name' : "clang-native-aarch64-full",
           'slavenames' :["juno-aarch64-01"],
           'builddir':"clang-native-aarch64-full",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        jobs=4,
                        clean=True,
                        checkout_lld=False,
                        useTwoStage=True,
                        testStage1=True,
                        extra_cmake_args=["-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

          # Mips check-all with CMake builder
          # We currently have to force LLVM_HOST_TRIPLE and
          # LLVM_DEFAULT_TARGET_TRIPLE on this system. CMake gets the value
          # correct for the processor but it's currently not possible to emit O32
          # code using a mips64-* triple. This is a bug and should be fixed soon.
          # We must also force LLVM_TARGET_ARCH so that the ExecutionEngine tests
          # run.
          {'name': "clang-cmake-mips",
           'slavenames':["mips-kl-m001","mips-kl-m002"],
           'builddir':"clang-cmake-mips",
           'factory' : ClangBuilder.getClangCMakeGCSBuildFactory(
                           clean=False,
                           checkout_compiler_rt=True,
                           checkout_lld=False,
                           extra_cmake_args=["-DLLVM_HOST_TRIPLE=mips-unknown-linux-gnu",
                                             "-DLLVM_DEFAULT_TARGET_TRIPLE=mips-unknown-linux-gnu",
                                             "-DLLVM_TARGET_ARCH=Mips"],
                           stage1_upload_directory='clang-cmake-mips',
                           env = {'BOTO_CONFIG': '/var/buildbot/llvmlab-build-artifacts.boto'})},
          # Mips check-all with CMake builder
          # We currently have to force LLVM_HOST_TRIPLE and
          # LLVM_DEFAULT_TARGET_TRIPLE on this system. CMake gets the value
          # correct for the processor but it's currently not possible to emit O32
          # code using a mips64-* triple. This is a bug and should be fixed soon.
          # We must also force LLVM_TARGET_ARCH so that the ExecutionEngine tests
          # run.
          {'name': "clang-cmake-mipsel",
           'slavenames':["mips-kl-erpro001"],
           'builddir':"clang-cmake-mipsel",
           'factory' : ClangBuilder.getClangCMakeGCSBuildFactory(
                           clean=False,
                           checkout_compiler_rt=True,
                           checkout_lld=False,
                           extra_cmake_args=["-DLLVM_HOST_TRIPLE=mipsel-unknown-linux-gnu",
                                             "-DLLVM_DEFAULT_TARGET_TRIPLE=mipsel-unknown-linux-gnu",
                                             "-DLLVM_TARGET_ARCH=Mips"],
                           stage1_upload_directory='clang-cmake-mipsel',
                           env = {'BOTO_CONFIG': '/var/buildbot/llvmlab-build-artifacts.boto'})},
          ]

def _get_openmp_builders():
    return [
        {'name': "openmp-gcc-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"openmp-gcc-x86_64-linux-debian",
         'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                         c_compiler="gcc",
                         cxx_compiler="g++",
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'})},

        {'name': "openmp-clang-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"openmp-clang-x86_64-linux-debian",
         'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                         c_compiler="clang",
                         cxx_compiler="clang++",
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'})},

        {'name': "openmp-clang-ppc64le-linux-debian",
         'slavenames':["ppc64le-nvidia-K40"],
         'builddir':"openmp-clang-ppc64le-linux-debian",
         'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                         c_compiler="clang",
                         cxx_compiler="clang++",
                         env={'PATH':'/home/bbot/opt/cmake/bin:/home/bbot/opt/ninja/bin:/usr/local/bin:/usr/bin:/bin'})},

        ]

def _get_libcxx_builders():
    ericwf_slaves = ['ericwf-buildslave2', 'ericwf-buildslave-fast']
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
             cmake_extra_opts={'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                               'LIBCXXABI_ENABLE_EXCEPTIONS': 'OFF'},
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
             cmake_extra_opts={'LIBCXX_ENABLE_THREADS': 'OFF',
                               'LIBCXX_ENABLE_MONOTONIC_CLOCK': 'OFF',
                               'LIBCXXABI_ENABLE_THREADS': 'OFF'}),
         'category': 'libcxx'},

        # EricWF's builders
        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx03',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx03',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std':'c++03'},
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx11',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx11',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++11', 'enable_warnings': 'true'},
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++14', 'enable_warnings': 'true'},
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx17',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx17',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++17', 'enable_warnings': 'true'},
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx2a',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx2a',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++2a', 'enable_warnings': 'true'},
            check_libcxx_abilist=True),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-32bit',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-32bit',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_BUILD_32_BITS': 'ON'},
            lit_extra_opts={'enable_warnings': 'true'},
            check_libcxx_abilist=False),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Address'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-ubsan',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-ubsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Undefined',
                              'LIBCXX_ABI_UNSTABLE': 'ON'}),
        'category': 'libcxx'},

        # EricWF's builders on ericwf-buildslave2
        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-msan',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-msan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'MemoryWithOrigins'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-libunwind-x86_64-linux-ubuntu',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-libunwind-x86_64-linux-ubuntu',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Thread'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc49-cxx11',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc49-cxx11',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'gcc-4.9', 'CXX': 'g++-4.9'},
            lit_extra_opts={'std': 'c++11'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc-tot-latest-std',
         'slavenames': ericwf_slaves,
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc-tot-latest-std',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': '/opt/gcc-tot/bin/gcc', 'CXX': '/opt/gcc-tot/bin/g++'}),
        'category': 'libcxx'},

        # Cortex-A15 LibC++ and LibC++abi tests (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-arm-linux',
         'slavenames': ['linaro-tk1-01', 'linaro-armv8-01-arm-libcxx'],
         'builddir': 'libcxx-libcxxabi-libunwind-arm-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15 -marm',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15 -marm',
                              'LLVM_PARALLEL_LINK_JOBS': '2'})},

        {'name': 'libcxx-libcxxabi-libunwind-arm-linux-noexceptions',
         'slavenames': ['linaro-tk1-01', 'linaro-armv8-01-arm-libcxx-noeh'],
         'builddir': 'libcxx-libcxxabi-libunwind-arm-linux-noexceptions',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                              'LIBCXXABI_ENABLE_EXCEPTIONS': 'OFF',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15 -mthumb',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15 -mthumb',
                              'LLVM_PARALLEL_LINK_JOBS': '2'})},

        # AArch64 LibC++ and LibC++abi tests (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-aarch64-linux',
         'slavenames': ['linaro-apm-03', 'linaro-armv8-01-aarch64-libcxx'],
         'builddir': 'libcxx-libcxxabi-libunwind-aarch64-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a57',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a57',
                              'LLVM_PARALLEL_LINK_JOBS': '4'})},

        {'name': 'libcxx-libcxxabi-libunwind-aarch64-linux-noexceptions',
         'slavenames': ['linaro-apm-03', 'linaro-armv8-01-aarch64-libcxx-noeh'],
         'builddir': 'libcxx-libcxxabi-libunwind-aarch64-linux-noexceptions',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                              'LIBCXXABI_ENABLE_EXCEPTIONS': 'OFF',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a57',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a57',
                              'LLVM_PARALLEL_LINK_JOBS': '4'})},

    ]

# Experimental and stopped builders
def _get_on_demand_builders():
    return [
        ]

def _get_experimental_scheduled_builders():
    return [
        {'name' : "clang-bpf-build",
         'slavenames' : ["bpf-build-slave01"],
         'builddir' : "clang-bpf-build",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(useTwoStage=False,
                                                            checkout_lld=False,
                                                            clean=False,
                                                            test=True,
                                                            stage1_config='Release'),
         'category' : 'clang'},

        {'name' : "clang-cuda-build",
         'slavenames' : ["cuda-build-test-01"],
         'builddir' : "clang-cuda-build",
         'factory' : CUDATestsuiteBuilder.getCUDATestsuiteBuildFactory(
                     useTwoStage=False,
                     test=True,
                     stage1_config='Release',
                     extra_cmake_args=[
                         '-DLLVM_ENABLE_ASSERTIONS=ON',
                         "-DCMAKE_C_COMPILER:FILEPATH=/usr/bin/clang-3.8",
                         "-DCMAKE_CXX_COMPILER:FILEPATH=/usr/bin/clang++-3.8"
                     ],
                     externals="/home/botanist/bots/externals",
                     gpu_arch_list=["sm_35"],
                     gpu_devices=[0],   # K40c.
                     extra_ts_cmake_args=[],
                     enable_thrust_tests=False,
         ),
         'category' : 'clang'},

        # lldb builders
        {'name': "lldb-x86_64-darwin-13.4",
         'slavenames': ["lldb-x86_64-darwin-13.4"],
         'builddir': "buildDir",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=True,
                    buildAndroid=False,
                    runTest=True)},
        {'name': "lldb-x86_64-ubuntu-14.04-android",
         'slavenames': ["lldb-lab-linux01"],
         'builddir': "lldb-cross-compile",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=True,
                    buildAndroid=False,
                    runTest=True)},
        {'name': "lldb-windows7-android",
         'slavenames': ["lldb-lab-win01"],
         'builddir': "lldb-win7-android",
         'category': "lldb",
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=True,
                    buildAndroid=False,
                    runTest=True,
                    scriptExt='.bat')},

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
             }
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

    for b in _get_llgo_builders():
        b['category'] = 'llgo'
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
