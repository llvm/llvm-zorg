from importlib import reload

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
                        'CCACHE_DIR' : WithProperties("%(builddir)s/ccache-db"),
                        # TMP/TEMP within the build dir (to utilize a ramdisk).
                        'TMP'        : WithProperties("%(builddir)s/build"),
                        'TEMP'       : WithProperties("%(builddir)s/build"),
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
    'tags'  : ["clang", "llvm", "compiler-rt", "cross", "armv7"],
    'workernames' : ["as-builder-5"],
    'builddir': "x-armv7l-rel",
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

    {'name' : "llvm-clang-win-x-aarch64-release",
    'tags'  : ["clang", "llvm", "compiler-rt", "cross", "aarch64"],
    'workernames' : ["as-builder-6"],
    'builddir': "x-aarch64-rel",
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
                        'CCACHE_DIR' : WithProperties("%(builddir)s/ccache-db"),
                        # TMP/TEMP within the build dir (to utilize a ramdisk).
                        'TMP'        : WithProperties("%(builddir)s/build"),
                        'TEMP'       : WithProperties("%(builddir)s/build"),
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
    'workernames': ["doug-worker-2a"],
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
                        "-DLLVM_LIT_ARGS=--verbose -j48",
                        "-DLLVM_PARALLEL_LINK_JOBS=16",
                        "-DLLVM_USE_LINKER=gold"])},

]
