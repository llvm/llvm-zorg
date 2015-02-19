#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

STAGE1_DIR=llvm_build0
STAGE2_ASAN_DIR=llvm_build_asan
MAKE_JOBS=${MAX_MAKE_JOBS:-16}
LLVM=$ROOT/llvm
# No assertions. Need to clean up the existing assertion failures first.
# Also, the Fuzzer does not provide reproducers on assertion failures yet.
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_PARALLEL_LINK_JOBS=3"
CLANG_FORMAT_CORPUS=$ROOT/clang-format-corpus

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 compilers don't make sense.
# Clobber the build trees.
rm -rf ${STAGE2_ASAN_DIR}

# Create an empty directory for the corpus if it doesn't exist yet.
# It will get populated with examples.
# FIXME: synchronize this directory with some external persistent storage.
mkdir -p $CLANG_FORMAT_CORPUS

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build clang@@@

build_stage1_clang


# Stage 2 / AddressSanitizer

echo @@@BUILD_STEP stage2/asan check-fuzzer@@@

mkdir -p ${STAGE2_ASAN_DIR}

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

(cd ${STAGE2_ASAN_DIR} && cmake ${cmake_stage2_asan_options} $LLVM) || \
  echo @@@STEP_FAILURE@@@

(cd ${STAGE2_ASAN_DIR} && ninja check-fuzzer) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP stage2/asan build clang-format-fuzzer@@@

(cd ${STAGE2_ASAN_DIR} && ninja clang-format-fuzzer) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP stage2/asan run clang-format-fuzzer@@@

(${STAGE2_ASAN_DIR}/bin/clang-format-fuzzer -jobs=32 -workers=8 -runs=1048576 $CLANG_FORMAT_CORPUS) || \
  echo @@@STEP_WARNINGS@@@
