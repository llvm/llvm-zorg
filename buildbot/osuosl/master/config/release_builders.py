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
from zorg.buildbot.builders import FuchsiaBuilder
from zorg.buildbot.builders import XToolchainBuilder


# Release builders.

all = [

# Clang builders.

    {'name' : "llvm-clang-x86_64-win-release",
    'tags'  : ["clang", "release"],
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
    'tags'  : ["llvm", "expensive-checks", "release"],
    'workernames' : ["as-builder-4"],
    'builddir': "llvm-clang-x86_64-expensive-checks-ubuntu-rel",
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

    {'name' : "llvm-clang-x86_64-expensive-checks-win-release",
    'tags'  : ["llvm", "expensive-checks", "release"],
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
    'tags'  : ["llvm", "expensive-checks", "release"],
    'workernames' : ["gribozavr4"],
    'builddir': "llvm-clang-x86_64-expensive-checks-debian-rel",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                    depends_on_projects=["llvm", "lld"],
                    clean=True,
                    extra_configure_args=[
                        "-DLLVM_ENABLE_EXPENSIVE_CHECKS=ON",
                        "-DLLVM_ENABLE_WERROR=OFF",
                        "-DCMAKE_BUILD_TYPE=Release",
                        "-DCMAKE_CXX_FLAGS=-U_GLIBCXX_DEBUG",
                        "-DLLVM_LIT_ARGS=-v -vv -j96"],
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                    })},

# Cross builders.

    {'name' : "llvm-clang-win-x-armv7l-release",
    'tags'  : ["clang", "llvm", "compiler-rt", "cross"," armv7l", "release"],
    'workernames' : ["as-builder-1"],
    'builddir': "x-armv7l-rel",
    'factory' : XToolchainBuilder.getCmakeWithMSVCBuildFactory(
                    vs="autodetect",
                    clean=True,
                    checks=[
                    "check-llvm",
                    "check-clang",
                    "check-lld",
                    "check-compiler-rt"
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
                        "-DLLVM_TARGETS_TO_BUILD=ARM",
                        "-DTARGET_TRIPLE=armv7-linux-gnueabihf",
                        "-DDEFAULT_SYSROOT=C:/buildbot/.arm-ubuntu",
                        "-DLLVM_LIT_ARGS=-v -vv --threads=32",
                        WithProperties("%(remote_test_host:+-DREMOTE_TEST_HOST=)s%(remote_test_host:-)s"),
                        WithProperties("%(remote_test_user:+-DREMOTE_TEST_USER=)s%(remote_test_user:-)s"),
                    ],
                    cmake_cache="../llvm-project/clang/cmake/caches/CrossWinToARMLinux.cmake")},

    {'name' : "llvm-clang-win-x-aarch64-release",
    'tags'  : ["clang", "llvm", "compiler-rt", "cross", "aarch64", "release"],
    'workernames' : ["as-builder-2"],
    'builddir': "x-aarch64-rel",
    'factory' : XToolchainBuilder.getCmakeWithMSVCBuildFactory(
                    vs="autodetect",
                    clean=True,
                    checks=[
                    "check-llvm",
                    "check-clang",
                    "check-lld",
                    "check-compiler-rt"
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
                        "-DTARGET_TRIPLE=aarch64-linux-gnu",
                        "-DDEFAULT_SYSROOT=C:/buildbot/.aarch64-ubuntu",
                        "-DLLVM_LIT_ARGS=-v -vv --threads=32",
                        WithProperties("%(remote_test_host:+-DREMOTE_TEST_HOST=)s%(remote_test_host:-)s"),
                        WithProperties("%(remote_test_user:+-DREMOTE_TEST_USER=)s%(remote_test_user:-)s"),
                    ],
                    cmake_cache="../llvm-project/clang/cmake/caches/CrossWinToARMLinux.cmake")},

# LLD builders.

    {'name' : "lld-x86_64-win-release",
    'tags'  : ["lld", "release"],
    'workernames' : ["as-worker-93"],
    'builddir': "lld-x86_64-win-rel",
    'factory' : UnifiedTreeBuilder.getCmakeWithNinjaWithMSVCBuildFactory(
                    depends_on_projects=['llvm', 'lld'],
                    vs="autodetect",
                    extra_configure_args = [
                        '-DLLVM_ENABLE_WERROR=OFF'])},

    {'name' : "lld-x86_64-ubuntu-release",
    'tags'  : ["lld", "release"],
    'workernames' : ["as-builder-4"],
    'builddir' : "lld-x86_64-ubuntu-rel",
    'factory': UnifiedTreeBuilder.getCmakeWithNinjaBuildFactory(
                            clean=True,
                            extra_configure_args=[
                                '-DLLVM_ENABLE_WERROR=OFF'],
                            depends_on_projects=['llvm', 'lld'])},

# LTO and ThinLTO builders.

    {'name' : "clang-with-thin-lto-ubuntu-release",
    'tags'  : ["clang", "lld", "LTO", "release"],
    'workernames' : ["as-worker-92"],
    'builddir': "clang-with-thin-lto-ubuntu-rel",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(jobs=72, lto='thin')},

    {'name' : "clang-with-lto-ubuntu-release",
    'tags'  : ["clang", "lld", "LTO", "release"],
    'workernames' : ["as-worker-91"],
    'builddir': "clang-with-lto-ubuntu-rel",
    'factory' : ClangLTOBuilder.getClangWithLTOBuildFactory(
                    jobs=72,
                    extra_configure_args_lto_stage=[
                        '-DLLVM_PARALLEL_LINK_JOBS=14',
                    ])},

# OpenMP builders.

    {'name' : "openmp-clang-x86_64-linux-debian-release",
    'tags'  : ["openmp", "release"],
    'workernames' : ["gribozavr4"],
    'builddir': "openmp-clang-x86_64-linux-debian-rel",
    'factory' : OpenMPBuilder.getOpenMPCMakeBuildFactory(
                    env={
                        'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                        'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes',
                    })},

]
