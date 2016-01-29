from zorg.buildbot.builders import ClangBuilder
reload(ClangBuilder)
from zorg.buildbot.builders import ClangBuilder

from zorg.buildbot.builders import LLVMBuilder
reload(LLVMBuilder)
from zorg.buildbot.builders import LLVMBuilder

from zorg.buildbot.builders import LNTBuilder
reload(LNTBuilder)
from zorg.buildbot.builders import LNTBuilder

from zorg.buildbot.builders import NightlytestBuilder
reload(NightlytestBuilder)
from zorg.buildbot.builders import NightlytestBuilder

from zorg.buildbot.builders import PollyBuilder
reload(PollyBuilder)
from zorg.buildbot.builders import PollyBuilder

from zorg.buildbot.builders import LLDBBuilder
reload(LLDBBuilder)
from zorg.buildbot.builders import LLDBBuilder
from zorg.buildbot.builders.LLDBBuilder import RemoteConfig

from zorg.buildbot.builders import LLDBuilder
reload(LLDBuilder)
from zorg.buildbot.builders import LLDBuilder

from zorg.buildbot.builders import LLGoBuilder
reload(LLGoBuilder)
from zorg.buildbot.builders import LLGoBuilder

from zorg.buildbot.builders import ClangAndLLDBuilder
reload(ClangAndLLDBuilder)
from zorg.buildbot.builders import ClangAndLLDBuilder

from zorg.buildbot.builders import SanitizerBuilder
reload(SanitizerBuilder)
from zorg.buildbot.builders import SanitizerBuilder

from zorg.buildbot.builders import SanitizerBuilderII
reload(SanitizerBuilderII)
from zorg.buildbot.builders import SanitizerBuilderII

from zorg.buildbot.builders import SanitizerBuilderWindows
reload(SanitizerBuilderWindows)
from zorg.buildbot.builders import SanitizerBuilderWindows

from zorg.buildbot.builders import Libiomp5Builder
reload(Libiomp5Builder)
from zorg.buildbot.builders import Libiomp5Builder

from zorg.buildbot.builders import LibcxxAndAbiBuilder
reload(LibcxxAndAbiBuilder)
from zorg.buildbot.builders import LibcxxAndAbiBuilder

from zorg.buildbot.builders import SphinxDocsBuilder
reload(SphinxDocsBuilder)
from zorg.buildbot.builders import SphinxDocsBuilder

from zorg.buildbot.builders import ABITestsuitBuilder
reload(ABITestsuitBuilder)
from zorg.buildbot.builders import ABITestsuitBuilder

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
        {'name': "llvm-aarch64-linux",
         'slavenames':["aarch64-foundation"],
         'builddir':"llvm-aarch64-linux",
         'factory': LLVMBuilder.getLLVMBuildFactory(config_name='Release+Asserts',
                                                    extra_configure_args=["--host=aarch64-linux-gnu"])},
        {'name': "llvm-hexagon-elf",
         'slavenames':["hexagon-build-03"],
         'builddir':"llvm-hexagon-elf",
         'factory': LLVMBuilder.getLLVMBuildFactory("hexagon-unknown-elf", timeout=40, config_name='Release+Asserts',
                                                       extra_configure_args=['--build=x86_64-linux-gnu',
                                                                             '--host=x86_64-linux-gnu',
                                                                             '--target=hexagon-unknown-elf',
                                                                             '--enable-targets=hexagon'])},
        ]

# Clang fast builders.
def _get_clang_fast_builders():
    return [
        {'name': "clang-x86_64-debian-fast",
         'slavenames':["gribozavr4"],
         'builddir':"clang-x86_64-debian-fast",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                     withLLD=False,
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
                     prefixCommand=None, # This is a designaed builder, so no need to be nice.
                     env={'PATH':'/opt/llvm_37/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})},
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
        # FIXME: Move this to CMake (see below)
        {'name' : "clang-native-arm-lnt-perf",
         'slavenames':["linaro-chrome-02"],
         'builddir':"clang-native-arm-lnt-perf",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=2,
                      clean=False,
                      checkout_compiler_rt=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      nt_flags=['--cflag', '-mcpu=cortex-a15',
                                '--threads=1', '--build-threads=2', '--use-perf',
                                '--benchmarking-only', '--multisample=8'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
                      submitURL='http://llvm.org/perf/submitRun',
                      testerName='LNT-ARMv7-A15-O3')},

        # Cortex-A15 LNT test-suite in test-only mode
        {'name' : "clang-native-arm-lnt",
         'slavenames':["linaro-chrome-03"],
         'builddir':"clang-native-arm-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=2,
                      clean=False,
                      checkout_compiler_rt=False,
                      test=False,
                      useTwoStage=False,
                      runTestSuite=True,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      nt_flags=['--cflag', '-mcpu=cortex-a15'],
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## Cortex-A15 check-all self-host NEON with CMake builder
        {'name': "clang-cmake-armv7-a15-selfhost-neon",
         'slavenames':["linaro-chrome-04"],
         'builddir':"clang-cmake-armv7-a15-selfhost-neon",
         'factory' : ClangBuilder.getClangCMakeGCSBuildFactory(
                      jobs=2,
                      clean=True,
                      checkout_compiler_rt=False,
                      useTwoStage=True,
                      testStage1=True,
                      stage1_upload_directory='clang-cmake-armv7a',
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                           'BOTO_CONFIG':'/var/buildbot/llvmlab-build-artifacts.boto'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS=-mcpu=cortex-a15",
                                        "-DCMAKE_CXX_FLAGS=-mcpu=cortex-a15",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## Cortex-A15 check-all with CMake builder
        {'name': "clang-cmake-armv7-a15",
         'slavenames':["linaro-a15-01"],
         'builddir':"clang-cmake-armv7-a15",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
                      clean=False,
                      checkout_compiler_rt=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## Cortex-A15 check-all with CMake T2 builder
        {'name': "clang-cmake-thumbv7-a15",
         'slavenames':["linaro-a15-04"],
         'builddir':"clang-cmake-thumbv7-a15",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
                      clean=False,
                      checkout_compiler_rt=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -mthumb'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3 -mthumb'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## Cortex-A15 check-all self-host with CMake builder
        {'name': "clang-cmake-armv7-a15-selfhost",
         'slavenames':["linaro-a15-02"],
         'builddir':"clang-cmake-armv7-a15-selfhost",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                      jobs=4,
                      clean=True,
                      checkout_compiler_rt=False,
                      useTwoStage=True,
                      testStage1=False,
                      env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

        ## AArch64 Clang+LLVM check-all + test-suite
        {'name': "clang-cmake-aarch64-quick",
         'slavenames':["linaro-apm-01"],
         'builddir':"clang-cmake-aarch64-quick",
         'factory' : ClangBuilder.getClangCMakeGCSBuildFactory(
                      jobs=8,
                      clean=False,
                      checkout_compiler_rt=False,
                      test=True,
                      useTwoStage=False,
                      runTestSuite=True,
                      stage1_upload_directory='clang-cmake-aarch64',
                      env={'PATH':'/usr/lib64/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                           'BOTO_CONFIG':'/var/buildbot/llvmlab-build-artifacts.boto'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
                      nt_flags=['--cflag', '-mcpu=cortex-a57'],
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

        {'name' : "clang-ppc64be-linux-lnt",
         'slavenames' :["ppc64be-clang-lnt-test"],
         'builddir' :"clang-ppc64be-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name' : "clang-ppc64le-linux-lnt",
         'slavenames' :["ppc64le-clang-lnt-test"],
         'builddir' :"clang-ppc64le-lnt",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=False,
                                                            runTestSuite=True,
                                                            stage1_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name' : "clang-ppc64be-linux-multistage",
         'slavenames' :["ppc64be-clang-multistage-test"],
         'builddir' :"clang-ppc64be-multistage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
         'category' : 'clang'},

        {'name' : "clang-ppc64le-linux-multistage",
         'slavenames' :["ppc64le-clang-multistage-test"],
         'builddir' :"clang-ppc64le-multistage",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(clean=False,
                                                            useTwoStage=True,
                                                            stage1_config='Release',
                                                            stage2_config='Release',
                                                            extra_cmake_args=["-DLLVM_ENABLE_ASSERTIONS=ON"]),
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
        {'name' : "clang-x86_64-darwin13-cross-mingw32",
         'slavenames' :["as-bldslv9"],
         'builddir' :"clang-x86_64-darwin13-cross-mingw32",
         'factory' : ClangBuilder.getClangBuildFactory(use_pty_in_tests=True,
                                                       test=False,
                                                       env = { 'CC' : 'clang',
                                                               'CXX' : 'clang++',
                                                               'CXXFLAGS' : '-stdlib=libc++'},
                                                       extra_configure_args=['--build=x86_64-apple-darwin13',
                                                                             '--host=x86_64-apple-darwin13',
                                                                             '--target=i686-pc-mingw32'])},

        {'name' : "clang-x86_64-darwin13-cross-arm",
         'slavenames' :["as-bldslv9"],
         'builddir' :"clang-x86_64-darwin13-cross-arm",
         'factory' : ClangBuilder.getClangBuildFactory(use_pty_in_tests=True,
                                                       env = { 'CC' : 'clang',
                                                               'CXX' : 'clang++',
                                                               'CXXFLAGS' : '-stdlib=libc++'},
                                                       test=False,
                                                       extra_configure_args=['--build=x86_64-apple-darwin13',
                                                                             '--host=x86_64-apple-darwin13',
                                                                             '--target=arm-eabi',
                                                                             '--enable-targets=arm'])},

        {'name' : "clang-x86_64-ubuntu-gdb-75",
         'slavenames' :["hpproliant1"],
         'builddir' :"clang-x86_64-ubuntu-gdb-75",
         'factory' : ClangBuilder.getClangBuildFactory(stage1_config='Release+Asserts', run_modern_gdb=True, clean=False)},

        {'name' : "clang-hexagon-elf",
         'slavenames' :["hexagon-build-03"],
         'builddir' :"clang-hexagon-elf",
         'factory' : ClangBuilder.getClangBuildFactory(
                     triple='x86_64-linux-gnu',
                     stage1_config='Release+Asserts',
                     extra_configure_args=['--enable-shared',
                                           '--target=hexagon-unknown-elf',
                                           '--enable-targets=hexagon'])},

        {'name' : "clang-aarch64-lnt",
         'slavenames' :["aarch64-qemu-lnt"],
         'builddir' :"clang-aarch64-lnt",
         'factory' : LNTBuilder.getLNTFactory(triple='aarch64-linux-gnu',
                                              nt_flags=['--llvm-arch=AArch64', '-j4'],
                                              package_cache="http://webkit.inf.u-szeged.hu/llvm/",
                                              jobs=4, use_pty_in_tests=True, clean=False,
                                              testerName='LNT-TestOnly-AArch64', run_cxx_tests=True)},
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
                                                       modules=True,
                                                       clean=False,
                                                       stage1_config='Release',
                                                       stage2_config='Release',
                                                       extra_configure_args=['-DCMAKE_C_COMPILER=clang',
                                                                             '-DCMAKE_CXX_COMPILER=clang++',
                                                                             '-DCMAKE_CXX_FLAGS=-stdlib=libc++',
                                                                             '-DLLVM_ENABLE_ASSERTIONS=ON'],
                                                       cmake='cmake')},

        {'name' : "clang-x64-ninja-win7",
         'slavenames' : ["windows7-buildbot"],
         'builddir' : "clang-x64-ninja-win7",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        clean=False,
                        vs='%VS120COMNTOOLS%',
                        vs_target_arch='x64',
                        testStage1=True,
                        useTwoStage=True,
                        stage1_config='Release',
                        stage2_config='Release',
                        extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                          '-DLLVM_TARGETS_TO_BUILD=X86'])},
        ]

# Polly builders.
def _get_polly_builders():
    return [
        {'name': "polly-amd64-linux",
         'slavenames':["grosser1"],
         'builddir':"polly-amd64-linux",
         'factory': PollyBuilder.getPollyBuildFactory()},

        {'name': "perf-x86_64-penryn-O3-polly-fast",
         'slavenames':["pollyperf10"],
         'builddir': "perf-x86_64-penryn-O3-polly-fast",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '-j16' ],
                                                    reportBuildslave=False,
                                                    build_type='Release+Asserts',
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    testerName='x86_64-penryn-O3-polly-fast')},

        {'name': "perf-x86_64-penryn-O3-polly-parallel-fast",
         'slavenames':["pollyperf6"],
         'builddir': "perf-x86_64-penryn-O3-polly-parallel-fast",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '--mllvm=-polly-parallel', '-j16', '--cflag=-lgomp' ],
                                                    reportBuildslave=False,
                                                    build_type='Release+Asserts',
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    testerName='x86_64-penryn-O3-polly-parallel-fast')},

        {'name': "perf-x86_64-penryn-O3-polly-unprofitable",
         'slavenames':["pollyperf6"],
         'builddir': "perf-x86_64-penryn-O3-polly-unprofitable",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=1', '--mllvm=-polly', '--mllvm=-polly-process-unprofitable', '-j16'],
                                                    reportBuildslave=False,
                                                    build_type='Release+Asserts',
                                                    package_cache="http://parkas1.inria.fr/packages",
                                                    testerName='x86_64-penryn-O3-polly-unprofitable')},

        {'name': "perf-x86_64-penryn-O3-polly",
         'slavenames':["pollyperf11", "pollyperf7", "pollyperf14"],
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
        {'name': "lldb-x86-windows-msvc",
         'slavenames': ["zturner-win2008"],
         'builddir': "lldb-windows-x86",
         'factory': LLDBBuilder.getLLDBWindowsCMakeBuildFactory(config='Debug')},
        {'name': "lldb-x86-win7-msvc",
         'slavenames': ["hexagon-build-01"],
         'builddir': "builddir/lldb-win7-msvc",
         'factory': LLDBBuilder.getLLDBWindowsCMakeBuildFactory(config='Debug')},
        {'name': "lldb-x86_64-ubuntu-14.04-buildserver",
         'slavenames': ["lldb-linux-android-buildserver"],
         'builddir': "lldb-android-buildserver",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    buildAndroid=True,
                    runTest=False)},
        {'name': "lldb-amd64-ninja-netbsd7",
         'slavenames': ["lldb-amd64-ninja-netbsd7"],
         'builddir': "build",
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
         'slavenames' :["as-bldslv4"],
         'builddir':"lld-x86_64-win7",
         'factory': LLDBuilder.getLLDWinBuildFactory(),
         'category'   : 'lld'},

        {'name': "lld-x86_64-freebsd",
         'slavenames' :["as-bldslv5"],
         'builddir':"lld-x86_64-freebsd",
         'factory': LLDBuilder.getLLDBuildFactory(extra_configure_args=[
                                                      '-DCMAKE_EXE_LINKER_FLAGS=-lcxxrt',
                                                      '-DLLVM_ENABLE_WERROR=OFF'],
                                                  env={'CXXFLAGS' : "-std=c++11 -stdlib=libc++"}),
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

          {'name': "sanitizer_x86_64-freebsd",
           'slavenames':["as-bldslv5"],
           'builddir':"sanitizer_x86_64-freebsd",
           'factory' : SanitizerBuilderII.getSanitizerBuildFactoryII(
                        clean=True,
                        sanitizers=['sanitizer','asan','lsan','tsan','ubsan'],
                        common_cmake_options=['-DCMAKE_EXE_LINKER_FLAGS=-lcxxrt',
                                              '-DLIBCXXABI_USE_LLVM_UNWINDER=ON'])},

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
           'factory': SanitizerBuilderWindows.getSanitizerWindowsBuildFactory()},

          ## Cortex-A15 check-all full (compiler-rt) with CMake builder; Needs x86 for ASAN tests
          {'name': "clang-cmake-armv7-a15-full",
           'slavenames':["linaro-a15-03"],
           'builddir':"clang-cmake-armv7-a15-full",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        jobs=4,
                        clean=False,
                        env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mfpu=vfpv3'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

          ## Cortex-A15 Thumb2 check-all full (compiler-rt) with CMake builder; Needs x86 for ASAN tests
          {'name': "clang-cmake-thumbv7-a15-full-sh",
           'slavenames':["linaro-chrome-05"],
           'builddir':"clang-cmake-thumbv7-a15-full-sh",
           'factory' : ClangBuilder.getClangCMakeBuildFactory(
                        jobs=2,
                        clean=True,
                        useTwoStage=True,
                        testStage1=True,
                        env={'PATH':'/usr/lib/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                        extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DCOMPILER_RT_TEST_COMPILER_CFLAGS='-mcpu=cortex-a15 -mthumb'",
                                          "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"])},

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
                      testStage1=True,
                      runTestSuite=True,
                      env={'PATH':'/usr/lib64/ccache:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'},
                      extra_cmake_args=["-DCMAKE_C_FLAGS='-mcpu=cortex-a57'",
                                        "-DCMAKE_CXX_FLAGS='-mcpu=cortex-a57'",
                                        "-DLLVM_TARGETS_TO_BUILD='ARM;AArch64'"],
                      nt_flags=['--cflag', '-mcpu=cortex-a57'],
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
           'slavenames':["mips-kl-m001"],
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
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'}),
         'category' : 'libomp'},

        {'name': "libomp-clang-x86_64-linux-debian",
         'slavenames':["gribozavr4"],
         'builddir':"libomp-clang-x86_64-linux-debian",
         'factory' : Libiomp5Builder.getLibompCMakeBuildFactory(
                         c_compiler="clang",
                         cxx_compiler="clang++",
                         env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin'}),
         'category' : 'libomp'},
        ]

def _get_libcxx_builders():
    return [
        {'name': 'libcxx-libcxxabi-x86_64-linux-debian',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-x86_64-linux-debian',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'}),
         'category': 'libcxx'},

        # x86_64 -fno-exceptions libcxx builder
        {'name': 'libcxx-libcxxabi-x86_64-linux-debian-noexceptions',
         'slavenames': ['gribozavr4'],
         'builddir': 'libcxx-libcxxabi-x86_64-linux-debian-noexceptions',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
             env={'CC': 'clang', 'CXX': 'clang++'},
             cmake_extra_opts={'LIBCXX_ENABLE_EXCEPTIONS': 'OFF'}),
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
            lit_extra_opts={'std': 'c++11'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx14',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std':'c++14'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx1z',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-cxx1z',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            lit_extra_opts={'std':'c++1z'}),
        'category': 'libcxx'},

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'slavenames': ['ericwf-buildslave'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-asan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Address'},
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

        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-tsan',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LLVM_USE_SANITIZER': 'Thread'},
            lit_extra_opts={'std':'c++1z'}),
        'category': 'libcxx'},
        
        {'name': 'libcxx-libcxxabi-x86_64-linux-ubuntu-unstable-abi',
         'slavenames': ['ericwf-buildslave2'],
         'builddir' : 'libcxx-libcxxabi-x86_64-linux-ubuntu-unstable-abi',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'PATH': '/usr/local/bin:/usr/bin:/bin',
                 'CC': 'clang', 'CXX': 'clang++'},
            cmake_extra_opts={'LIBCXX_ABI_UNSTABLE': 'ON'}),
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
        {'name': 'libcxx-libcxxabi-arm-linux',
         'slavenames': ['linaro-chrome-01'],
         'builddir': 'libcxx-libcxxabi-arm-linux',
         'category': 'libcxx',
         'factory': LibcxxAndAbiBuilder.getLibcxxAndAbiBuilder(
            env={'CC': 'clang', 'CXX': 'clang++'},
            # FIXME: there should be a way to merge autodetected with user-defined linker flags
            # See: libcxxabi/test/lit.cfg
            lit_extra_opts={'link_flags': '"-lc++abi -lc -lm -lpthread -lunwind -ldl -L/opt/llvm/lib/clang/3.6.0/lib/linux -lclang_rt.builtins-arm"'},
            cmake_extra_opts={'LIBCXXABI_USE_LLVM_UNWINDER': 'True',
                              'CMAKE_C_FLAGS': '-mcpu=cortex-a15',
                              'CMAKE_CXX_FLAGS': '-mcpu=cortex-a15'})},
    ]

# Experimental and stopped builders
def _get_on_demand_builders():
    return [
        ]

def _get_experimental_scheduled_builders():
    return [
        {'name': "clang-atom-d525-fedora",
         'slavenames':["atom-buildbot"],
         'builddir':"clang-atom-d525-fedora",
         'factory' : ClangBuilder.getClangCMakeBuildFactory(
                       clean=False,
                       checkout_compiler_rt=False,
                       useTwoStage=False,
                       stage1_config='Debug',
                       test=True,
                       testStage1=True,
                       extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                         '-DLLVM_USE_INTEL_JITEVENTS=TRUE']),
         'category' : 'clang'},

        {'name' : "clang-bpf-build",
         'slavenames' : ["bpf-build-slave01"],
         'builddir' : "clang-bpf-build",
         'factory' : ClangBuilder.getClangBuildFactory(useTwoStage=False,
                                                       clean=False,
                                                       test=True,
                                                       stage1_config='Release',
                                                       cmake='cmake'),
         'category' : 'clang'},

        # lldb builders
        {'name': "lldb-x86_64-debian-clang",
         'slavenames': ["gribozavr5"],
         'builddir': "lldb-x86_64-clang-ubuntu-14.04",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBBuildFactory(triple=None, # use default
                                                    extra_configure_args=['--enable-cxx11', '--enable-optimized', '--enable-assertions'],
                                                    env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games'})},
        {'name': "lldb-x86_64-ubuntu-14.10",
         'slavenames': ["hexagon-build-03"],
         'builddir': "lldb-x86_64-ubuntu-14.10",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBBuildFactory(
                    triple=None,
                    extra_configure_args=[
                        '--enable-cxx11',
                        '--enable-optimized',
                        '--enable-assertions'],
                    env={'SHELL':"/bin/bash"})},
        {'name': "lldb-x86_64-ubuntu-14.04-cmake",
         'slavenames': ["lldb-build1-ubuntu-1404"],
         'builddir': "buildWorkingDir",
         'category' : 'lldb',
         'factory': LLDBBuilder.getLLDBScriptCommandsFactory(
                    downloadBinary=False,
                    buildAndroid=False,
                    runTest=True)},
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


# Offline:
# Plain LLVM builders
{'name': "llvm-x86_64-linux-vg_leak",
 'slavenames':["osu8"],
 'builddir':"llvm-x86_64-linux-vg_leak",
 'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", valgrind=True,
                                     valgrindLeakCheck=True,
                                     valgrindSuppressions='utils/valgrind/x86_64-pc-linux-gnu.supp')},
{'name': "llvm-x86_64-ubuntu",
 'slavenames':["arxan_davinci"],
 'builddir':"llvm-x86_64-ubuntu",
 'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", jobs=4,
                                            timeout=30)},
{'name': "llvm-x86_64-linux",
 'slavenames': ["gcc14"],
 'builddir': "llvm-x86_64",
 'factory': LLVMBuilder.getLLVMBuildFactory(triple="x86_64-pc-linux-gnu")},
{'name': "llvm-alpha-linux",
 'slavenames':["andrew1"],
 'builddir':"llvm-alpha",
 'factory': LLVMBuilder.getLLVMBuildFactory("alpha-linux-gnu", jobs=2)},
{'name': "llvm-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"llvm-i386-auroraux",
 'factory': LLVMBuilder.getLLVMBuildFactory("i386-pc-auroraux", jobs="%(jobs)s", make='gmake')},
{'name': "llvm-ppc-linux",
 'slavenames':["nick1"],
 'builddir':"llvm-ppc",
 'factory': LLVMBuilder.getLLVMBuildFactory("ppc-linux-gnu", jobs=1, clean=False, timeout=40)},
{'name': "llvm-i686-linux",
 'slavenames': ["dunbar1"],
 'builddir': "llvm-i686",
 'factory': LLVMBuilder.getLLVMBuildFactory("i686-pc-linux-gnu", jobs=2, enable_shared=True)},

# Clang builders
{'name': "clang-native-mingw32-win7",
 'slavenames':["as-bldslv7"],
 'builddir':"clang-native-mingw32-win7",
 'category':'clang',
 'factory' : ClangBuilder.getClangBuildFactory(triple='i686-pc-mingw32',
                                                       useTwoStage=True, test=False,
                                                       stage1_config='Release+Asserts',
                                                       stage2_config='Release+Asserts')},
# Cortex-A9 triple check-all bots with autoconf builder
{'name': "clang-native-arm-cortex-a9",
 'slavenames':["as-bldslv1", "as-bldslv2", "as-bldslv3"],
 'builddir':"clang-native-arm-cortex-a9",
 'factory' : ClangBuilder.getClangBuildFactory(
               stage1_config='Release+Asserts',
               clean=False,
               env = { 'CXXFLAGS' : '-Wno-psabi', 'CFLAGS' : '-Wno-psabi'},
               extra_configure_args=['--build=armv7l-unknown-linux-gnueabihf',
                                     '--host=armv7l-unknown-linux-gnueabihf',
                                     '--target=armv7l-unknown-linux-gnueabihf',
                                     '--with-cpu=cortex-a9',
                                     '--with-fpu=neon',
                                     '--with-float=hard',
                                     '--enable-targets=arm'])},
{'name' : "clang-x64-ninja-win7-debug",
 'slavenames' : ["windows7-buildbot"],
 'builddir' : "clang-x64-ninja-win7-debug",
 'factory' : ClangBuilder.getClangCMakeBuildFactory(
                          clean=False,
                          vs='%VS120COMNTOOLS%',
                          vs_target_arch='x64',
                          testStage1=True,
                          useTwoStage=True,
                          stage1_config='Debug',
                          stage2_config='Debug',
                          extra_cmake_args=['-DLLVM_ENABLE_ASSERTIONS=ON',
                                            '-DLLVM_TARGETS_TO_BUILD=X86'])},
{'name' : "clang-native-aarch64",
 'slavenames' :["juno-aarch64-01"],
 'builddir' :"clang-native-aarch64",
 'factory' : ClangBuilder.getClangCMakeBuildFactory(
                          jobs=4,
                          clean=False,
                          checkout_compiler_rt=False,
                          useTwoStage=True,
                          testStage1=True)},
{'name': "clang-x86_64-linux-vg",
 'slavenames':["osu8"],
 'builddir':"clang-x86_64-linux-vg",
 'factory': ClangBuilder.getClangBuildFactory(valgrind=True)},
{'name' : "clang-x86_64-linux-selfhost-rel",
 'slavenames' : ["osu8"],
 'builddir' : "clang-x86_64-linux-selfhost-rel",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Release+Asserts')},
clang_x86_64_linux_xfails = [
    'LLC.SingleSource/UnitTests/Vector/SSE/sse.expandfft',
    'LLC.SingleSource/UnitTests/Vector/SSE/sse.stepfft',
    'LLC_compile.SingleSource/UnitTests/Vector/SSE/sse.expandfft',
    'LLC_compile.SingleSource/UnitTests/Vector/SSE/sse.stepfft',
]
{'name' : "clang-x86_64-linux-fnt",
 'slavenames' : ['osu8'],
 'builddir' : "clang-x86_64-linux-fnt",
 'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-pc-linux-gnu',
                                                               stage1_config='Release+Asserts',
                                                               test=False,
                                                               xfails=clang_x86_64_linux_xfails)},
{'name' : "clang-x86_64-debian-fnt",
 'slavenames' : ['gcc20'],
 'builddir' : "clang-x86_64-debian-fnt",
 'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-pc-linux-gnu',
                                                               stage1_config='Release+Asserts',
                                                               test=False,
                                                               xfails=clang_x86_64_linux_xfails)},
{'name': "clang-x86_64-ubuntu",
 'slavenames':["arxan_raphael"],
 'builddir':"clang-x86_64-ubuntu",
 'factory' : ClangBuilder.getClangBuildFactory(extra_configure_args=['--enable-shared'])},
{'name': "llvm-clang-lld-x86_64-ubuntu-13.04",
 'slavenames':["gribozavr2"],
 'builddir':"llvm-clang-lld-x86_64-ubuntu-13.04",
 'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
             env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                  'CC': 'ccache clang', 'CXX': 'ccache clang++',
                  'CCACHE_CPP2': 'yes'})},
{'name': "llvm-clang-lld-x86_64-centos-6.5",
 'slavenames':["gribozavr3"],
 'builddir':"llvm-clang-lld-x86_64-centos-6.5",
 'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
              env={'PATH': '/opt/centos/devtoolset-1.1/root/usr/bin:/home/llvmbb/bin:/bin:/usr/bin',
                   'LD_LIBRARY_PATH': '/opt/centos/devtoolset-1.1/root/usr/lib64',
                   'CC': 'ccache clang', 'CXX': 'ccache clang++',
                   'CCACHE_CPP2': 'yes'},
              withLLD=False,
              extraCompilerOptions=['--gcc-toolchain=/opt/centos/devtoolset-1.1/root/usr'])},

# TODO: The following tests marked as expected failures on FreeBSD temporarily.
# Remove after http://llvm.org/bugs/show_bug.cgi?id=18089
# and http://llvm.org/bugs/show_bug.cgi?id=18056 will be fixed and closed.
clang_x86_64_freebsd_xfails = [
    'LLC.MultiSource/Benchmarks/nbench/nbench',
    'LLC_compile.MultiSource/Benchmarks/nbench/nbench',
    'LLC.SingleSource/Benchmarks/Misc/mandel',
    'LLC_compile.SingleSource/Benchmarks/Misc/mandel',
]
{'name': "clang-mergefunc-x86_64-freebsd",
 'slavenames':["as-bldslv5"],
 'builddir':"clang-mergefunc-x86_64-freebsd",
 'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-unknown-freebsd10.0',
                                         stage1_config='Release+Asserts',
                                         merge_functions=True,
                                         make='gmake',
                                         test=False,
                                         xfails=clang_x86_64_freebsd_xfails)},
{'name': "clang-native-arm-cortex-a15",
 'slavenames':["linaro-chrome-01"],
 'builddir':"clang-native-arm-cortex-a15",
 'factory' : ClangBuilder.getClangBuildFactory(
             stage1_config='Release+Asserts',
             clean=False,
             env = { 'CXXFLAGS' : '-Wno-psabi', 'CFLAGS' : '-Wno-psabi'},
             extra_configure_args=['--build=armv7l-unknown-linux-gnueabihf',
                                   '--host=armv7l-unknown-linux-gnueabihf',
                                   '--target=armv7l-unknown-linux-gnueabihf',
                                   '--with-cpu=cortex-a15',
                                   '--with-fpu=neon',
                                   '--with-float=hard',
                                   '--enable-targets=arm'])},
{'name': "clang-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"clang-i386-auroraux",
 'factory': ClangBuilder.getClangBuildFactory("i386-pc-auroraux",
                                              jobs="%(jobs)s", make='gmake')},
{'name': "clang-x86_64-linux",
 'slavenames':["gcc14"],
 'builddir':"clang-x86_64-linux",
 'factory': ClangBuilder.getClangBuildFactory(examples=True)},
{'name': "clang-i686-linux",
 'slavenames':["dunbar1"],
 'builddir':"clang-i686-linux",
 'factory': ClangBuilder.getClangBuildFactory()},
{'name': "clang-arm-linux",
 'slavenames':["nick3"],
 'builddir':"clang-arm-linux",
 'factory': ClangBuilder.getClangBuildFactory()},
{'name' : "clang-i686-darwin10",
 'slavenames' :["dunbar-darwin10"],
 'builddir' :"clang-i686-darwin10",
 'factory': ClangBuilder.getClangBuildFactory(triple='i686-apple-darwin10',
                                              stage1_config='Release')},
{'name' : "clang-i686-xp-msvc9",
 'slavenames' :['dunbar-win32-2'],
 'builddir' :"clang-i686-xp-msvc9",
 'factory' : ClangBuilder.getClangMSVCBuildFactory(jobs=2)},
{'name' : "clang-x86_64-darwin10-selfhost",
 'slavenames' : ["dunbar-darwin10"],
 'builddir' : "clang-x86_64-darwin10-selfhost",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Debug+Asserts')},
{'name': "clang-i686-freebsd",
 'slavenames':["freebsd1"],
 'builddir':"clang-i686-freebsd",
 'factory': ClangBuilder.getClangBuildFactory(clean=True, use_pty_in_tests=True)},

clang_i386_linux_xfails = [
    'LLC.MultiSource/Applications/oggenc/oggenc',
    'LLC.MultiSource/Benchmarks/VersaBench/bmm/bmm',
    'LLC.MultiSource/Benchmarks/VersaBench/dbms/dbms',
    'LLC.SingleSource/Benchmarks/Misc-C++/Large/sphereflake',
    'LLC.SingleSource/Regression/C++/EH/ConditionalExpr',
    'LLC_compile.MultiSource/Applications/oggenc/oggenc',
    'LLC_compile.MultiSource/Benchmarks/VersaBench/bmm/bmm',
    'LLC_compile.MultiSource/Benchmarks/VersaBench/dbms/dbms',
    'LLC_compile.SingleSource/Benchmarks/Misc-C++/Large/sphereflake',
    'LLC_compile.SingleSource/Regression/C++/EH/ConditionalExpr',
]
{'name' : "clang-i686-linux-fnt",
 'slavenames' : ['balint1'],
 'builddir' : "clang-i686-linux-fnt",
 'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='i686-pc-linux-gnu',
                                                               stage1_config='Release+Asserts',
                                                               test=False,
                                                               xfails=clang_i386_linux_xfails) },
{'name' : "clang-x86_64-darwin11-cross-linux-gnu",
 'slavenames' :["as-bldslv11"],
 'builddir' :"clang-x86_64-darwin11-cross-linux-gnu",
 'factory' : ClangBuilder.getClangBuildFactory(jobs=4,  use_pty_in_tests=True,
                                               run_cxx_tests=True,
                                               extra_configure_args=['--build=x86_64-apple-darwin11',
                                                                     '--host=x86_64-apple-darwin11',
                                                                     '--target=i686-pc-linux-gnu '])},
{'name': "clang-x86_64-debian",
 'slavenames':["gcc12"],
 'builddir':"clang-x86_64-debian",
 'factory': ClangBuilder.getClangBuildFactory(extra_configure_args=['--enable-shared'])},
{'name' : "clang-x86_64-debian-selfhost-rel",
 'slavenames' : ["gcc13"],
 'builddir' : "clang-x86_64-debian-selfhost-rel",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                                useTwoStage=True,
                                                stage1_config='Release+Asserts',
                                                stage2_config='Release+Asserts')},
{'name': "clang-x86_64-darwin11-self-mingw32",
 'slavenames':["as-bldslv11"],
 'builddir':"clang-x86_64-darwin11-self-mingw32",
 'factory' : ClangBuilder.getClangBuildFactory(jobs=4, test=False,
                                                       env = { 'PATH' : "/mingw_build_tools/install_with_gcc/bin:/opt/local/bin:/opt/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin",
                                                               'CC' : 'clang',
                                                               'CXX' : 'clang++',
                                                               'CXXFLAGS' : '-stdlib=libc++'},
                                                       extra_configure_args=['--build=x86_64-apple-darwin11',
                                                                             '--host=i686-pc-mingw32',
                                                                             '--target=i686-pc-mingw32'])},
{'name': "clang-X86_64-freebsd",
 'slavenames':["as-bldslv6"],
 'builddir':"clang-X86_64-freebsd",
 'factory': NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-unknown-freebsd8.2',
                                                              stage1_config='Release+Asserts',
                                                              test=True)},

# Polly builders
{'name': "polly-intel32-linux",
 'slavenames':["botether"],
 'builddir':"polly-intel32-linux",
 'factory': PollyBuilder.getPollyBuildFactory()},

# LLDB builders
{'name': "lldb-x86_64-linux",
 'slavenames': ["gcc20"],
 'builddir': "lldb-x86_64",
 'factory': LLDBBuilder.getLLDBBuildFactory(triple="x86_64-pc-linux-gnu",
                                            env={'CXXFLAGS' : '-std=c++0x'})},
#   gcc_m32_latest_env = gcc_latest_env.copy()
#   gcc_m32_latest_env['CC'] += ' -m32'
#   gcc_m32_latest_env['CXX'] += ' -m32'
#{'name': "lldb-i686-debian",
# 'slavenames': ["gcc15"],
# 'builddir': "lldb-i686-debian",
# 'factory': LLDBBuilder.getLLDBBuildFactory(triple="i686-pc-linux-gnu",
#                                            env=gcc_m32_latest_env)},

# Random other unused builders...
{'name': "clang-amd64-openbsd",
 'slavenames':["openbsd-buildslave"],
 'builddir':"clang-openbsd",
 'factory' : ClangBuilder.getClangBuildFactory(stage1_config='Release+Asserts'),
 'category' : 'clang'},
{'name': "lldb-x86_64-freebsd",
 'slavenames': ["as-bldslv5"],
 'builddir': "lldb-x86_64-freebsd",
 'category' : 'lldb',
 'factory': LLDBBuilder.getLLDBBuildFactory(triple=None, # use default
                                            make='gmake',
                                            extra_configure_args=['--enable-cxx11',
                                                                  '--enable-optimized',
                                                                  '--enable-assertions'])},
{'name': "clang-x86_64-openbsd",
 'slavenames':["ocean1"],
 'builddir':"clang-x86_64-openbsd",
 'factory': ClangBuilder.getClangBuildFactory(),
 'category':'clang.exp'},
{'name': "clang-x86_64-linux-checks",
 'slavenames':["osu2"],
 'builddir':"clang-x86_64-linux-checks",
 'factory': ClangBuilder.getClangBuildFactory(stage1_config='Debug+Asserts+Checks'),
 'category':'clang.exp'},
{'name' : "clang-i386-darwin10-selfhost-rel",
 'slavenames' : ["dunbar-darwin10"],
 'builddir' : "clang-i386-darwin10-selfhost-rel",
 'factory' : ClangBuilder.getClangBuildFactory(triple='i386-apple-darwin10',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Release+Asserts'),
 'category' : 'clang.exp' },
{'name' : "clang-x86_64-darwin10-selfhost-rel",
 'slavenames' : ["dunbar-darwin10"],
 'builddir' : "clang-x86_64-darwin10-selfhost-rel",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Release+Asserts'),
 'category' : 'clang.exp' },
{'name' : "clang-i686-xp-msvc9_alt",
 'slavenames' :['adobe1'],
 'builddir' :"clang-i686-xp-msvc9_alt",
 'factory' : ClangBuilder.getClangMSVCBuildFactory(jobs=2),
 'category' : 'clang.exp' },
{'name': "clang-i686-freebsd-selfhost-rel",
 'slavenames':["freebsd1"],
 'builddir':"clang-i686-freebsd-selfhost-rel",
 'factory': ClangBuilder.getClangBuildFactory(triple='i686-pc-freebsd',
                                              useTwoStage=True,
                                              stage1_config='Release+Asserts',
                                              stage2_config='Release+Asserts'),
 'category' : 'clang.exp' },
{'name': "llvm-x86_64-debian-debug-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"llvm-x86-64-debian-debug-werror",
 'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu",
                                            config_name='Debug+Asserts',
                                            extra_configure_args=["--enable-werror"]),
 'category' : 'llvm'},
{'name': "llvm-x86_64-debian-release-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"llvm-x86-64-debian-release-werror",
 'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu",
                                            config_name='Release+Asserts',
                                            extra_configure_args=["--enable-werror"]),
 'category' : 'llvm'},
{'name': "clang-x86_64-debian-debug-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"clang-x86-64-debian-debug-werror",
 'factory': ClangBuilder.getClangBuildFactory(triple="x86_64-pc-linux-gnu",
                                             useTwoStage=True,
                                             stage1_config='Debug+Asserts',
                                             stage2_config='Debug+Asserts',
                                             extra_configure_args=["--enable-werror"]),
 'category' : 'clang'},
# Cortex-A9 check-all self-host
{'name': "clang-native-arm-cortex-a9-self-host",
 'slavenames':["linaro-panda-02"],
 'builddir':"clang-native-arm-cortex-a9-self-host",
 'factory' : ClangBuilder.getClangBuildFactory(
             stage1_config='Release+Asserts',
             stage2_config='Release+Asserts',
             useTwoStage=True,
             clean=False,
             test=True,
             extra_configure_args=[ '--with-cpu=cortex-a9',
                                    '--with-fpu=neon',
                                    '--with-float=hard',
                                    '--enable-targets=arm']),
 'category' : 'clang'},
{'name': "clang-x86_64-debian-release-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"clang-x86-64-debian-release-werror",
 'factory': ClangBuilder.getClangBuildFactory(triple="x86_64-pc-linux-gnu",
                                             useTwoStage=True,
                                             stage1_config='Release+Asserts',
                                             stage2_config='Release+Asserts',
                                             extra_configure_args=["--enable-werror"]),
 'category' : 'clang'},
{'name': "clang-native-mingw64-win7",
 'slavenames':["sschiffli1"],
 'builddir':"clang-native-mingw64-win7",
 'factory' : ClangBuilder.getClangMinGWBuildFactory(),
 'category' : 'clang'},
LabPackageCache = 'http://10.1.1.2/packages/'
{'name' : "clang-x86_64-darwin12-nt-O3-vectorize",
 'slavenames' :["lab-mini-03"],
 'builddir' :"clang-x86_64-darwin12-nt-O3-vectorize",
 'factory' : LNTBuilder.getLNTFactory(triple='x86_64-apple-darwin12',
                                      nt_flags=['--mllvm=-vectorize', '--multisample=3'], jobs=2,
                                      use_pty_in_tests=True, testerName='O3-vectorize',
                                      run_cxx_tests=True, package_cache=LabPackageCache),
 'category' : 'clang'},
{'name' : "clang-x86_64-darwin10-nt-O0-g",
 'slavenames' :["lab-mini-03"],
 'builddir' :"clang-x86_64-darwin10-nt-O0-g",
 'factory' : LNTBuilder.getLNTFactory(triple='x86_64-apple-darwin10',
                                      nt_flags=['--multisample=3', 
                                                '--optimize-option',
                                                '-O0', '--cflag', '-g'],
                                      jobs=2,  use_pty_in_tests=True,
                                      testerName='O0-g', run_cxx_tests=True,
                                      package_cache=LabPackageCache),
 'category' : 'clang'},
{'name' : "clang-x86_64-darwin12-gdb",
 'slavenames' :["lab-mini-04"],
 'builddir' :"clang-x86_64-darwin12-gdb",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin12', stage1_config='Release+Asserts', run_gdb=True),
 'category' : 'clang'},
{'name': "llvm-ppc-darwin",
 'slavenames':["arxan_bellini"],
 'builddir':"llvm-ppc-darwin",
 'factory': LLVMBuilder.getLLVMBuildFactory("ppc-darwin", jobs=2, clean=True,
                    config_name = 'Release',
                    env = { 'CC' : "/usr/bin/gcc-4.2",
                            'CXX': "/usr/bin/g++-4.2" },
                    extra_configure_args=['--enable-shared'],
                    timeout=600),
 'category' : 'llvm'},
{'name': "lldb-x86_64-darwin12",
'slavenames': ["lab-mini-02"],
'builddir': "build.lldb-x86_64-darwin12",
'factory': LLDBBuilder.getLLDBxcodebuildFactory()},
