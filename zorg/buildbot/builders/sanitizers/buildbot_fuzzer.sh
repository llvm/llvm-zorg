#!/usr/bin/env bash

set -x
set -e
set -u

# Set HOME for gsutil to work
export HOME=/var/lib/buildbot

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

CHECK_LIBCXX=${CHECK_LIBCXX:-0}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE2_ASAN_DIR=llvm_build_asan
STAGE2_ASAN_ASSERTIONS_DIR=llvm_build_asan_assertions
MAKE_JOBS=${MAX_MAKE_JOBS:-8}
LLVM=$ROOT/llvm
LIBFUZZER=$LLVM/lib/Fuzzer
# No assertions. Need to clean up the existing assertion failures first.
# Also, the Fuzzer does not provide reproducers on assertion failures yet.
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_PARALLEL_LINK_JOBS=8 -DLLVM_APPEND_VC_REV=OFF"
CORPUS_ROOT=$ROOT/CORPORA/llvm
CLANG_FORMAT_CORPUS=$CORPUS_ROOT/clang-format/C1
CLANG_CORPUS=$CORPUS_ROOT/clang/C2
LLVM_AS_CORPUS=$CORPUS_ROOT/llvm-as/C1
LLVM_PDBDUMP_CORPUS=$CORPUS_ROOT/llvm-pdbdump/C1

GS_ROOT=gs://fuzzing-with-sanitizers/llvm

syncFromGs() {
  mkdir -p $CORPUS_ROOT/$1
  gsutil -m rsync $GS_ROOT/$1 $CORPUS_ROOT/$1
}

syncToGs() {
  gsutil -m rsync $CORPUS_ROOT/$1 $GS_ROOT/$1
}

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 compilers don't make sense.
# Clobber the build trees.
rm -rf ${STAGE2_ASAN_DIR}
rm -rf ${STAGE2_ASAN_ASSERTIONS_DIR}

# Make sure asan intercepts SIGABRT so that the fuzzer can print the test cases
# for assertion failures.
export ASAN_OPTIONS=handle_abort=1:strip_path_prefix=build/llvm/

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build clang@@@

build_stage1_clang


# TODO(smatveev): merge this with build_stage2()
clang_path=$ROOT/${STAGE1_DIR}/bin
cmake_stage2_asan_options=" \
  ${CMAKE_COMMON_OPTIONS} \
  -DCMAKE_C_COMPILER=${clang_path}/clang \
  -DCMAKE_CXX_COMPILER=${clang_path}/clang++ \
  -DLLVM_USE_SANITIZER=Address \
  -DLLVM_USE_SANITIZE_COVERAGE=YES \
"
common_stage2_variables
export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
export PATH="${clang_path}:$PATH"

# Stage 2 / AddressSanitizer + assertions
mkdir -p ${STAGE2_ASAN_ASSERTIONS_DIR}
echo @@@BUILD_STEP stage2/asan+assertions check-fuzzer@@@
cmake_stage2_asan_assertions_options="$cmake_stage2_asan_options -DLLVM_ENABLE_ASSERTIONS=ON"

(cd ${STAGE2_ASAN_ASSERTIONS_DIR} && cmake ${cmake_stage2_asan_assertions_options} $LLVM) || \
  echo @@@STEP_FAILURE@@@

(cd ${STAGE2_ASAN_ASSERTIONS_DIR} && ninja check-fuzzer) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP get fuzzer-test-suite @@@
[ ! -e fuzzer-test-suite ] && git clone https://github.com/google/fuzzer-test-suite.git
(cd fuzzer-test-suite && git pull)

RunFuzzerTest() {
  echo @@@BUILD_STEP test "$1" fuzzer@@@
  ln -sf $LIBFUZZER .
  `pwd`/fuzzer-test-suite/build-and-test.sh "$1"
}

RunFuzzerTest re2-2014-12-09       || echo @@@STEP_FAILURE@@@
RunFuzzerTest c-ares-CVE-2016-5180 || echo @@@STEP_FAILURE@@@
RunFuzzerTest openssl-1.0.1f       || echo @@@STEP_FAILURE@@@
RunFuzzerTest openssl-1.0.2d       || echo @@@STEP_FAILURE@@@
RunFuzzerTest libxml2-v2.9.2       || echo @@@STEP_FAILURE@@@
RunFuzzerTest libpng-1.2.56        || echo @@@STEP_FAILURE@@@
RunFuzzerTest woff2-2016-05-06     || echo @@@STEP_WARNINGS@@@  # Often can't find the bug in the given time.
