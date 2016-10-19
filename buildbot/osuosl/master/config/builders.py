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
from zorg.buildbot.builders import Libiomp5Builder
from zorg.buildbot.builders import LibcxxAndAbiBuilder
from zorg.buildbot.builders import SphinxDocsBuilder
from zorg.buildbot.builders import ABITestsuitBuilder
from zorg.buildbot.builders import ClangLTOBuilder3Stage

from zorg.buildbot.builders import ClangLTOBuilder

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
         'slavenames': ["ps4-buildslave1"],
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
                     extraLitArgs=["--use-processes", "-j80"])},
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
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      nt_flags=['--cflag', '-mcpu=cortex-a15', '--cflag', '-mthumb',
                                '--threads=1', '--build-threads=4', '--use-perf',
                                '--benchmarking-only', '--multisample=3',
                                '--exclude-stat-from-submission=compile'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"],
                      submitURL='http://llvm.org/perf/submitRun',
                      testerName='LNT-Thumb2v7-A15-O3')},

        # Cortex-A15 LNT test-suite in test-only mode
        {'name' : "clang-native-arm-lnt",
         'slavenames':["linaro-chrome-03", "linaro-tk1-03"],
         'builddir':"clang-native-arm-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=2,
                      clean=False,
                      checkout_compiler_rt=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      nt_flags=['--cflag', '-mcpu=cortex-a15 -marm',
                                '--threads=2', '--build-threads=2'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all self-host NEON with CMake builder
        {'name': "clang-cmake-armv7-a15-selfhost-neon",
         'slavenames':["linaro-chrome-04", "linaro-tk1-04"],
         'builddir':"clang-cmake-armv7-a15-selfhost-neon",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=2,
                      clean=False,
                      checkout_compiler_rt=False,
                      useTwoStage=True,
                      testStage1=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                           'BOTO_CONFIG':'/var/buildbot/llvmlab-build-artifacts.boto'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j2'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all with CMake builder
        {'name': "clang-cmake-armv7-a15",
         'slavenames':["linaro-a15-01", "linaro-tk1-06"],
         'builddir':"clang-cmake-armv7-a15",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
                      clean=False,
                      checkout_compiler_rt=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j4'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all with CMake T2 builder
        {'name': "clang-cmake-thumbv7-a15",
         'slavenames':["linaro-a15-04", "linaro-tk1-09"],
         'builddir':"clang-cmake-thumbv7-a15",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
                      clean=False,
                      checkout_compiler_rt=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -mthumb'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -mthumb'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j4'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## Cortex-A15 check-all self-host with CMake builder
        {'name': "clang-cmake-armv7-a15-selfhost",
         'slavenames':["linaro-a15-02", "linaro-tk1-07"],
         'builddir':"clang-cmake-armv7-a15-selfhost",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
                      clean=False,
                      checkout_compiler_rt=False,
                      useTwoStage=True,
                      testStage1=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                        "-DLLVM_LIT_ARGS='-sv -j4'",
                                        "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        ## AArch64 Clang+LLVM check-all + test-suite
        {'name': "clang-cmake-aarch64-quick",
         'slavenames':["linaro-apm-01"],
         'builddir':"clang-cmake-aarch64-quick",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=8,
                      clean=False,
                      checkout_compiler_rt=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      nt_flags=['--cflag', '-mcpu=cortex-a57', '--threads=8', '--build-threads=8'],
                      env={'PATH':'/usr/lib64/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                           'BOTO_CONFIG':'/var/buildbot/llvmlab-build-artifacts.boto'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

        {'name': 'clang-x86-win2008-selfhost',
         'slavenames': ['windows-gcebot1'],
         'builddir': 'clang-x86-win2008-selfhost',
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        vs='%VS120COMNTOOLS%',
                        vs_target_arch='x86',
                        checkout_compiler_rt=False,
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='Release',
                        stage2_config='Release',
                        extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"])},

        {'name': 'clang-x86-windows-msvc2015',
         'slavenames': ['windows-gcebot2'],
         'builddir': 'clang-x86-windows-msvc2015',
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        vs='%VS140COMNTOOLS%',
                        vs_target_arch='x86',
                        checkout_compiler_rt=False,
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='RelWithDebInfo',
                        stage2_config='RelWithDebInfo',
                        extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"])},

        {'name' : "clang-ppc64be-linux-lnt",
         'slavenames' :["ppc64be-clang-lnt-test"],
         'builddir' :"clang-ppc64be-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            jobs=16,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            nt_flags=['--threads=16', '--build-threads=16'],
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name' : "clang-ppc64le-linux-lnt",
         'slavenames' :["ppc64le-clang-lnt-test"],
         'builddir' :"clang-ppc64le-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            jobs=6,
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
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON']),
         'category' : 'clang'},

        {'name' : "clang-ppc64le-linux-multistage",
         'slavenames' :["ppc64le-clang-multistage-test"],
         'builddir' :"clang-ppc64le-multistage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON', '-DBUILD_SHARED_LIBS=ON']),
         'category' : 'clang'},

        {'name': "clang-ppc64be-linux",
         'slavenames':["ppc64be-clang-test"],
         'builddir':"clang-ppc64be",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=False,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name': "clang-ppc64le-linux",
         'slavenames':["ppc64le-clang-test"],
         'builddir':"clang-ppc64le",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=False,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name': "clang-s390x-linux",
         'slavenames':["systemz-1"],
         'builddir':"clang-s390x-linux",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=False,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        # ABI test-suite with CMake builder
        {'name'          : "clang-x86_64-linux-abi-test",
         'mergeRequests' : False,
         'slavenames'    : ["as-bldslv8"],
         'builddir'      : "clang-x86_64-linux-abi-test",
         'factory'       : ABITestsuitBuilder.getABITestsuitBuildFactory()},

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
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://llvm.org/perf/submitRun'],
                                                    testerName='x86_64-penryn-O3')},
        {'name' : "clang-x86_64-linux-selfhost-modules",
         'slavenames' : ["modules-slave-1"],
         'builddir' : "clang-x86_64-linux-selfhost-modules",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
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
                       clean=False)},

        {'name' : "clang-3stage-ubuntu",
         'slavenames' : ["ps4-buildslave1a"],
         'builddir' : "clang-3stage-ubuntu",
         'factory': ClangLTOBuilder3Stage.get3StageClangLTOBuildFactory(
               clean=True,
               jobs=16,
               env=None,
               build_gold=True,
               cmake_cache_file="../llvm.src/tools/clang/cmake/caches/3-stage.cmake",
               extra_cmake_options=[
                   '-GNinja',
                   '-DLLVM_TARGETS_TO_BUILD=all',
                   '-DLLVM_BINUTILS_INCDIR=/opt/binutils/include'])},
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
         'slavenames':["pollyperf11", "pollyperf7"],
         'builddir':"perf-x86_64-penryn-O3-polly",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    #nt_flags=['--multisample=10', '--mllvm=-polly', '--rerun'],
                                                    nt_flags=['--multisample=10', '--mllvm=-polly'],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://llvm.org/perf/submitRun'],
                                                    testerName='x86_64-penryn-O3-polly')},
        {'name': "perf-x86_64-penryn-O3-polly-before-vectorizer",
         'slavenames':["pollyperf15"],
         'builddir':"perf-x86_64-penryn-O3-polly-before-vectorizer",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    #nt_flags=['--multisample=10', '--mllvm=-polly', '--rerun'],
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-position=before-vectorizer' ],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://llvm.org/perf/submitRun'],
                                                    testerName='x86_64-penryn-O3-polly-before-vectorizer')},

        {'name': "perf-x86_64-penryn-O3-polly-before-vectorizer-unprofitable",
         'slavenames':["pollyperf6", "pollyperf14"],
         'builddir':"perf-x86_64-penryn-O3-polly-before-vectorizer-unprofitable",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '--mllvm=-polly-position=before-vectorizer', '--mllvm=-polly-process-unprofitable', '-j16' ],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://llvm.org/perf/submitRun'],
                                                    testerName='x86_64-penryn-O3-polly-before-vectorizer-unprofitable')},


        {'name': "perf-x86_64-penryn-O3-polly-before-vectorizer-detect-only",
         'slavenames':["pollyperf15"],
         'builddir':"perf-x86_64-penryn-O3-polly-before-vectorizer-detect-only",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    #nt_flags=['--multisample=10', '--mllvm=-polly', '--rerun'],
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-position=before-vectorizer', '--mllvm=-polly-only-scop-detection'],
                                                    reportBuildslave=False,
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    submitURL=['http://gcc12.fsffrance.org:8808/submitRun','http://llvm.org/perf/submitRun'],
                                                    testerName='x86_64-penryn-O3-polly-before-vectorizer-detect-only')}
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
                    runTest=False)},
        {'name': "lldb-x86_64-ubuntu-14.04-cmake",
         'slavenames': ["lldb-build1-ubuntu-1404"],
         'builddir': "buildWorkingDir",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    buildAndroid=False,
                    runTest=True)},
        {'name': "lldb-amd64-ninja-netbsd7",
         'slavenames': ["lldb-amd64-ninja-netbsd7"],
         'builddir': "build",
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
         'factory': ClangLTOBuilder.getClangWithLTOBuildFactory(),
         'category'   : 'lld'},

        {'name' : "clang-with-thin-lto-ubuntu",
         'slavenames' : ["ps4-buildslave1a"],
         'builddir' : "clang-with-thin-lto-ubuntu",
         'factory': ClangLTOBuilder.getClangWithLTOBuildFactory(lto='thin', jobs=16),
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
           'slavenames' :["sanitizer-buildbot1"],
           'builddir': "sanitizer-x86_64-linux",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-bootstrap",
           'slavenames' :["sanitizer-buildbot2"],
           'builddir': "sanitizer-x86_64-linux-bootstrap",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-fast",
           'slavenames' :["sanitizer-buildbot3"],
           'builddir': "sanitizer-x86_64-linux-fast",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-autoconf",
           'slavenames' :["sanitizer-buildbot4"],
           'builddir': "sanitizer-x86_64-linux-autoconf",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-fuzzer",
           'slavenames' :["sanitizer-buildbot5"],
           'builddir': "sanitizer-x86_64-linux-fuzzer",
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
           'slavenames':["linaro-a15-03", "linaro-tk1-08"],
           'builddir':"clang-cmake-armv7-a15-full",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        jobs=4,
                        clean=False,
                        env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -marm'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                          "-DLLVM_LIT_ARGS='-sv -j4'",
                                          "-DLLVM_PARALLEL_LINK_JOBS=2"])},

          ## Cortex-A15 Thumb2 check-all full (compiler-rt) with CMake builder; Needs x86 for ASAN tests
          {'name': "clang-cmake-thumbv7-a15-full-sh",
           'slavenames':["linaro-chrome-05", "linaro-tk1-05"],
           'builddir':"clang-cmake-thumbv7-a15-full-sh",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        jobs=2,
                        clean=False,
                        useTwoStage=True,
                        testStage1=False,
                        env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'",
                                          "-DLLVM_LIT_ARGS='-sv -j2'",
                                          "-DLLVM_PARALLEL_LINK_JOBS=2"])},

        # AArch64 Clang+LLVM+RT check-all + test-suite + self-hosting
        {'name': "clang-cmake-aarch64-full",
         'slavenames':["linaro-apm-02"],
         'builddir':"clang-cmake-aarch64-full",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=8,
                      clean=True,
                      checkout_compiler_rt=True,
                      test=True,
                      useTwoStage=True,
                      testStage1=False,
                      runTestSuite=True,
                      nt_flags=['--cflag', '-mcpu=cortex-a57', '--threads=8', '--build-threads=8'],
                      env={'PATH':'/usr/lib64/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

        # AArch64 Clang+LLVM+RT check-all at 42-bits VMA
        {'name': "clang-cmake-aarch64-42vma",
         'slavenames':["linaro-apm-03"],
         'builddir':"clang-cmake-aarch64-42vma",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=8,
                      clean=False,
                      checkout_compiler_rt=True,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=False,
                      env={'PATH':'/usr/lib64/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57 -DSANITIZER_AARCH64_VMA=42'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57 -DSANITIZER_AARCH64_VMA=42'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
               )},

          # Juno
          {'name' : "clang-native-aarch64-full",
           'slavenames' :["juno-aarch64-01"],
           'builddir':"clang-native-aarch64-full",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        jobs=4,
                        clean=True,
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
                           extra_cmake_args=["-DLLVM_HOST_TRIPLE=mipsel-unknown-linux-gnu",
                                             "-DLLVM_DEFAULT_TARGET_TRIPLE=mipsel-unknown-linux-gnu",
                                             "-DLLVM_TARGET_ARCH=Mips"],
                           stage1_upload_directory='clang-cmake-mipsel',
                           env = {'BOTO_CONFIG': '/var/buildbot/llvmlab-build-artifacts.boto'})},
          ]

def _get_openmp_builders():
    return [
        {'name': "libomp-gcc-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"libomp-gcc-x86_64-linux-debian",
         'factory' : Libiomp5Builder.getLibompCMakeBuildFactory(
                         c_compiler="gcc",
                         cxx_compiler="g++",
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'})},

        {'name': "libomp-clang-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"libomp-clang-x86_64-linux-debian",
         'factory' : Libiomp5Builder.getLibompCMakeBuildFactory(
                         c_compiler="clang",
                         cxx_compiler="clang++",
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'})},

        {'name': "libomp-ompt-gcc-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"libomp-ompt-gcc-x86_64-linux-debian",
         'factory' : Libiomp5Builder.getLibompCMakeBuildFactory(
                         c_compiler="gcc",
                         cxx_compiler="g++",
                         ompt=True,
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'})},

        {'name': "libomp-ompt-clang-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"libomp-ompt-clang-x86_64-linux-debian",
         'factory' : Libiomp5Builder.getLibompCMakeBuildFactory(
                         c_compiler="clang",
                         cxx_compiler="clang++",
                         ompt=True,
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'})},
        ]

def _get_libcxx_builders():
    return [
        # gribozavr's builders on gribozavr4 
        {'name': 'libcxx-libcxxabi-x86_64-linux-debian',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-x86_64-linux-debian',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             lit_extra_args=['--shuffle']),
         'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-debian-noexceptions',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-x86_64-linux-debian-noexceptions',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             cmake_extra_opts={'LIBCXX_ENABLE_EXCEPTIONS': 'OFF'},
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

        # EricWF's builders on ericwf-buildslave
        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx03',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx03',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std':'c++03'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx11',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx11',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++11', 'enable_warnings': 'true'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++14', 'enable_warnings': 'true'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx1z',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx1z',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std': 'c++1z', 'enable_warnings': 'true'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Address'},
            lit_extra_opts={'std':'c++1z'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-ubsan',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-ubsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Undefined',
                              'LIBCXX_ABI_UNSTABLE': 'ON'},
            lit_extra_opts={'std':'c++1z'}),
        'category': 'libcxx'},

        # EricWF's builders on ericwf-buildslave2
        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-msan',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-msan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'MemoryWithOrigins'},
            lit_extra_opts={'std':'c++1z'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-libunwind-x86_64-linux-ubuntu',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-libunwind-x86_64-linux-ubuntu',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Thread'},
            lit_extra_opts={'std':'c++1z'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc49-cxx11',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-gcc49-cxx11',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'gcc-4.9', 'CXX': 'g++-4.9'},
            lit_extra_opts={'std': 'c++11'}),
        'category': 'libcxx'},

        # Cortex-A15 LibC++ and LibC++abi tests (require Clang+RT)
        {'name': 'libcxx-libcxxabi-libunwind-arm-linux',
         'slavenames': ['linaro-chrome-01', 'linaro-tk1-01'],
         'builddir': 'libcxx-libcxxabi-libunwind-arm-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'CC': 'clang', 'CXX': 'clang++', 'PATH': '/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/llvm/bin'},
            # FIXME: there should be a way to merge autodetected with user-defined linker flags
            # See: libcxxabi/test/lit.cfg
            lit_extra_opts={'link_flags': '"-lc++abi -lc -lm -lpthread -lunwind -ldl -L/opt/llvm/lib/clang/3.9.0/lib/linux -lclang_rt.builtins-armhf"'},
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15 -marm',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15 -marm',
                              'LLVM_PARALLEL_LINK_JOBS': '2'})},

        {'name': 'libcxx-libcxxabi-libunwind-arm-linux-noexceptions',
         'slavenames': ['linaro-chrome-01', 'linaro-tk1-01'],
         'builddir': 'libcxx-libcxxabi-libunwind-arm-linux-noexceptions',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'CC': 'clang', 'CXX': 'clang++', 'PATH': '/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/llvm/bin'},
            # FIXME: there should be a way to merge autodetected with user-defined linker flags
            # See: libcxxabi/test/lit.cfg
            lit_extra_opts={'link_flags': '"-lc++abi -lc -lm -lpthread -lunwind -ldl -L/opt/llvm/lib/clang/3.9.0/lib/linux -lclang_rt.builtins-armhf"'},
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'ON',
                              'LIBCXX_ENABLE_EXCEPTIONS': 'OFF',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15 -mthumb',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15 -mthumb',
                              'LLVM_PARALLEL_LINK_JOBS': '2'})},
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
         'factory' : ClangBuilder.getClangBuildFactory(useTwoStage=False,
                                                       clean=False,
                                                       test=True,
                                                       stage1_config='Release'),
         'category' : 'clang'},

        {'name' : "clang-cuda-build",
         'slavenames' : ["cuda-build-test-01"],
         'builddir' : "clang-cuda-build",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                     useTwoStage=False,
                     clean=False,
                     test=True,
                     stage1_config='Release',
                     extra_cmake_args=[
                         '-DLLVM_ENABLE_ASSERTIONS=ON',
                         "-DCMAKE_C_COMPILER:FILEPATH=/usr/bin/clang-3.8",
                         "-DCMAKE_CXX_COMPILER:FILEPATH=/usr/bin/clang++-3.8"
                     ]),
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

        {'name': "sanitizer_x86_64-freebsd",
         'slavenames':["as-bldslv5"],
         'builddir':"sanitizer_x86_64-freebsd",
         'factory' : SanitizerBuilderII.getSanitizerBuildFactoryII(
                    clean=True,
                    sanitizers=['sanitizer','asan','lsan','tsan','ubsan'],
                    common_cmake_options=['-DCMAKE_EXE_LINKER_FLAGS=-lcxxrt',
                                          '-DLIBCXXABI_USE_LLVM_UNWINDER=ON']),
         'category' : 'sanitizer'},
        ]

# Builders responsible building Sphinix documentation
def _get_documentation_builders():
    return [
             {
               'name':"llvm-sphinx-docs",
               'slavenames':["gribozavr4"],
               'builddir':"llvm-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(llvm_html=True, llvm_man=True),
               'category' : 'llvm'
             },
             {
               'name':"clang-sphinx-docs",
               'slavenames':["gribozavr4"],
               'builddir':"clang-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(clang_html=True),
               'category' : 'clang'
             },
             {
               'name':"clang-tools-sphinx-docs",
               'slavenames':["gribozavr4"],
               'builddir':"clang-tools-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(clang_tools_html=True),
               'category' : 'clang'
             },
             {
               'name':"lld-sphinx-docs",
               'slavenames':["gribozavr4"],
               'builddir':"lld-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(lld_html=True),
               'category' : 'lld'
             },
             {
               'name':"libcxx-sphinx-docs",
               'slavenames':["ericwf-buildslave2"],
               'builddir':"libcxx-sphinx-docs",
               'factory': SphinxDocsBuilder.getSphinxDocsBuildFactory(libcxx_html=True),
               'category' : 'libcxx'
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
