from importlib import reload

from buildbot.plugins import util, steps

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
from zorg.buildbot.builders import XToolchainBuilder


# Release builders.

all = [

# Clang builders.

    {'name' : "llvm-clang-x86_64-win-release",
    'tags'  : ["clang"],
    'workernames' : ["as-builder-3"],
    'builddir': "llvm-clang-x86_64-win-rel",
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

# Expensive checks builders.


    {'name' : "llvm-clang-x86_64-expensive-checks-ubuntu-release",
    'tags'  : ["llvm", "expensive-checks"],
    'workernames' : ["as-builder-4-rel"],
    'builddir': "llvm-clang-x86_64-expensive-checks-ubuntu-rel",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=["llvm", "lld"],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DLLVM_USE_SPLIT_DWARF=ON",
                        "-DLLVM_USE_LINKER=gold",
                        "-DCMAKE_BUILD_TYPE=Debug",
                        "-DCMAKE_CXX_FLAGS=-U_GLIBCXX_DEBUG -Wno-misleading-indentation",
                        "-DLLVM_LIT_ARGS=-vv --time-tests"],
                    env={
                        'CCACHE_DIR' : util.Interpolate("%(prop:builddir)s/ccache-db"),
                    })},

    {'name' : "llvm-clang-x86_64-expensive-checks-win-release",
    'tags'  : ["llvm", "expensive-checks"],
    'workernames' : ["as-worker-93"],
    'builddir': "llvm-clang-x86_64-expensive-checks-win-rel",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    vs="autodetect",
                    depends_on_projects=["llvm", "lld"],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DCMAKE_BUILD_TYPE=Debug"])},

    {'name' : "llvm-clang-x86_64-expensive-checks-debian-release",
    'tags'  : ["llvm", "expensive-checks"],
    'workernames' : ["gribozavr4"],
    'builddir': "llvm-clang-x86_64-expensive-checks-debian-rel",
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

    {'name' : "llvm-clang-win-x-armv7l-release",
    'tags'  : ["clang", "llvm", "clang-tools-extra", "compiler-rt", "libc++", "libc++abi", "libunwind", "cross", "armv7"],
    'workernames' : ["as-builder-1"],
    'builddir': "x-armv7l-rel",
    'factory' : UnifiedTreeBuilder.getCmakeExBuildFactory(
                    depends_on_projects = [
                        'llvm',
                        'compiler-rt',
                        'clang',
                        'clang-tools-extra',
                        'libunwind',
                        'libcxx',
                        'libcxxabi',
                        'lld',
                    ],
                    vs="autodetect",
                    clean=True,
                    checks=[
                        "check-llvm",
                        "check-clang",
                        "check-lld",
                        "check-compiler-rt-armv7-unknown-linux-gnueabihf",
                    ],
                    checks_on_target = [
                        ("libunwind",
                            ["python", "bin/llvm-lit.py",
                            "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libunwind/test",
                            ]),
                        ("libc++abi",
                            ["python", "bin/llvm-lit.py",
                            "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libcxxabi/test",
                            ]),
                        ("libc++",
                            ['python', 'bin/llvm-lit.py',
                            'runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libcxx/test',
                            ])
                    ],
                    cmake_definitions = {
                        "LLVM_TARGETS_TO_BUILD"         : "ARM",
                        "LLVM_INCLUDE_BENCHMARKS"       : "OFF",
                        "LLVM_CCACHE_BUILD"             : "ON",
                        "LLVM_LIT_ARGS"                 : "-v -vv --threads=32 --time-tests",
                        "TOOLCHAIN_TARGET_TRIPLE"       : "armv7-unknown-linux-gnueabihf",
                        "TOOLCHAIN_TARGET_SYSROOTFS"    : util.Interpolate("%(prop:sysroot_path_tk1)s"),
                        "ZLIB_ROOT"                     : util.Interpolate("%(prop:zlib_root_path)s"),
                        "REMOTE_TEST_HOST"              : util.Interpolate("%(prop:remote_host_tk1_rel)s"),
                        "REMOTE_TEST_USER"              : util.Interpolate("%(prop:remote_user_tk1_rel)s"),
                        "CMAKE_CXX_FLAGS"               : "-D__OPTIMIZE__",
                    },
                    cmake_options = [
                        "-C", util.Interpolate("%(prop:srcdir_relative)s/clang/cmake/caches/CrossWinToARMLinux.cmake"),
                    ],
                    install_dir = "install",
                    env = {
                        'CCACHE_DIR' : util.Interpolate("%(prop:builddir)s/ccache-db"),
                        # TMP/TEMP within the build dir (to utilize a ramdisk).
                        'TMP'        : util.Interpolate("%(prop:builddir)s/build"),
                        'TEMP'       : util.Interpolate("%(prop:builddir)s/build"),
                    },
                )
        },

    {'name' : "llvm-clang-win-x-aarch64-release",
    'tags'  : ["clang", "llvm", "clang-tools-extra", "compiler-rt", "libc++", "libc++abi", "libunwind", "cross", "aarch64"],
    'workernames' : ["as-builder-2"],
    'builddir': "x-aarch64-rel",
    'factory' : UnifiedTreeBuilder.getCmakeExBuildFactory(
                    depends_on_projects = [
                        'llvm',
                        'compiler-rt',
                        'clang',
                        'clang-tools-extra',
                        'libunwind',
                        'libcxx',
                        'libcxxabi',
                        'lld',
                    ],
                    vs = "autodetect",
                    clean = True,
                    checks = [
                        "check-llvm",
                        "check-clang",
                        "check-lld",
                        "check-compiler-rt-aarch64-unknown-linux-gnu"
                    ],
                    checks_on_target = [
                        ("libunwind",
                            ["python", "bin/llvm-lit.py",
                            "-v", "-vv", "--threads=32",
                            "runtimes/runtimes-aarch64-unknown-linux-gnu-bins/libunwind/test",
                            ]),
                        ("libc++abi",
                            ["python", "bin/llvm-lit.py",
                            "-v", "-vv", "--threads=32",
                            "runtimes/runtimes-aarch64-unknown-linux-gnu-bins/libcxxabi/test",
                            ]),
                        ("libc++",
                            ['python', 'bin/llvm-lit.py',
                            '-v', '-vv', '--threads=32',
                            'runtimes/runtimes-aarch64-unknown-linux-gnu-bins/libcxx/test',
                            ])
                    ],
                    cmake_definitions = {
                        "LLVM_TARGETS_TO_BUILD"         : "AArch64",
                        "LLVM_INCLUDE_BENCHMARKS"       : "OFF",
                        "LLVM_LIT_ARGS"                 : "-v -vv --threads=32 --time-tests",
                        "TOOLCHAIN_TARGET_TRIPLE"       : "aarch64-unknown-linux-gnu",
                        "TOOLCHAIN_TARGET_SYSROOTFS"    : util.Interpolate("%(prop:sysroot_path_tx2)s"),
                        "REMOTE_TEST_HOST"              : util.Interpolate("%(prop:remote_host_tx2_rel)s"),
                        "REMOTE_TEST_USER"              : util.Interpolate("%(prop:remote_user_tx2_rel)s"),
                        "ZLIB_ROOT"                     : util.Interpolate("%(prop:zlib_root_path)s"),
                        "CMAKE_CXX_FLAGS"               : "-D__OPTIMIZE__",
                        "CMAKE_C_COMPILER_LAUNCHER"     : "ccache",
                        "CMAKE_CXX_COMPILER_LAUNCHER"   : "ccache",
                    },
                    cmake_options = [
                        "-C", util.Interpolate("%(prop:srcdir_relative)s/clang/cmake/caches/CrossWinToARMLinux.cmake"),
                    ],
                    install_dir = "install",
                    post_finalize_steps = [
                        #Note: requires for Jetson TX2/Linux Ubuntu 18.
                        steps.ShellCommand(name = "restart-target-finalize",
                            command = [ "ssh", util.Interpolate("%(prop:remote_user_tx2_rel)s@%(prop:remote_host_tx2_rel)s"),
                                        "((sleep 5 && sudo reboot) > /dev/null 2>&1 &); exit 0;"
                            ],
                            alwaysRun = True,
                        ),
                    ],
                    env = {
                        'CCACHE_DIR' : util.Interpolate("%(prop:builddir)s/ccache-db"),
                    },
                )
        },

# LLD builders.

    {'name' : "lld-x86_64-win-release",
    'tags'  : ["lld"],
    'workernames' : ["as-worker-93"],
    'builddir': "lld-x86_64-win-rel",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    depends_on_projects=['llvm', 'lld'],
                    vs="autodetect",
                    extra_configure_args = [
                        '-DLLVM_ENABLE_WERROR=OFF'])},

    {'name' : "lld-x86_64-ubuntu-release",
    'tags'  : ["lld"],
    'workernames' : ["as-builder-4-rel"],
    'builddir' : "lld-x86_64-ubuntu-rel",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=['llvm', 'lld'],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_CCACHE_BUILD=ON",
                        '-DLLVM_ENABLE_WERROR=OFF'],
                    env={
                        'CCACHE_DIR' : util.Interpolate("%(prop:builddir)s/ccache-db"),
                    })},

# LTO and ThinLTO builders.

    {'name' : "clang-with-thin-lto-ubuntu-release",
    'tags'  : ["clang", "lld", "LTO"],
    'workernames' : ["as-worker-92"],
    'builddir': "clang-with-thin-lto-ubuntu-rel",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(jobs=72, lto='thin')},

    {'name' : "clang-with-lto-ubuntu-release",
    'tags'  : ["clang", "lld", "LTO"],
    'workernames' : ["as-worker-91"],
    'builddir': "clang-with-lto-ubuntu-rel",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(
                    jobs=72,
                    extra_configure_args_lto_stage=[
                        '-DLLVM_PARALLEL_LINK_JOBS=14',
                    ])},

# OpenMP builders.

    {'name' : "openmp-clang-x86_64-linux-debian-release",
    'tags'  : ["openmp"],
    'workernames' : ["gribozavr4"],
    'builddir': "openmp-clang-x86_64-linux-debian-rel",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                    extraCmakeArgs=[
                        '-DLLVM_CCACHE_BUILD=ON',
                    ],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'clang', 'CXX': 'clang++',
                    })},

# Sony builders.

    {'name' : "llvm-clang-x86_64-sie-win-release",
    'tags'  : ["llvm", "clang", "clang-tools-extra", "lld", "cross-project-tests"],
    'workernames' : ["sie-win-worker"],
    'builddir': "x86_64-sie-win-rel",
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
                        "-DLLVM_LIT_ARGS=--verbose"])},

    {'name': "llvm-clang-x86_64-gcc-ubuntu-release",
    'tags'  : ["llvm", "clang", "clang-tools-extra", "compiler-rt", "lld", "cross-project-tests"],
    'workernames': ["sie-linux-worker3"],
    'builddir': "x86_64-gcc-rel",
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
                        "-DLLVM_LIT_ARGS=--verbose",
                        "-DLLVM_USE_LINKER=gold"])},

    {'name': "llvm-clang-aarch64-darwin-release",
    'tags'  : ["llvm", "clang", "clang-tools-extra", "lld", "cross-project-tests"],
    'workernames': ["doug-worker-4"],
    'builddir': "aarch64-darwin-rel",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    clean=True,
                    depends_on_projects=['llvm','clang','clang-tools-extra','lld','cross-project-tests'],
                    extra_configure_args=[
                        "-DCMAKE_C_COMPILER=clang",
                        "-DCMAKE_CXX_COMPILER=clang++",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DLLVM_BUILD_TESTS=ON",
                        "-DLLVM_CCACHE_BUILD=ON",
                        "-DLLVM_ENABLE_ASSERTIONS=ON",
                        "-DLLVM_INCLUDE_EXAMPLES=OFF",
                        "-DLLVM_LIT_ARGS=--verbose",
                        "-DLLVM_TARGETS_TO_BUILD=AArch64"])},

]
