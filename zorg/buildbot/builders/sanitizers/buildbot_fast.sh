#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE2_ASAN_DIR=llvm_build_asan
STAGE2_MSAN_DIR=llvm_build_msan
STAGE2_UBSAN_DIR=llvm_build_ubsan
STAGE2_LIBCXX_MSAN_DIR=libcxx_build_msan
STAGE2_LIBCXX_ASAN_DIR=libcxx_build_asan
STAGE2_LIBCXX_UBSAN_DIR=libcxx_build_ubsan
STAGE1_CLOBBER="${STAGE2_LIBCXX_MSAN_DIR} ${STAGE2_LIBCXX_ASAN_DIR} ${STAGE2_LIBCXX_UBSAN_DIR} ${STAGE2_MSAN_DIR} ${STAGE2_ASAN_DIR} ${STAGE2_UBSAN_DIR}"
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_PARALLEL_LINK_JOBS=20"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# Stage 1

build_stage1_clang_at_revison

CMAKE_COMMON_OPTIONS="$CMAKE_COMMON_OPTIONS -DLLVM_ENABLE_ASSERTIONS=ON"

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 2 / Memory Sanitizer

build_stage2_msan

check_stage2_msan

# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan

# Stage 2 / UndefinedBehaviorSanitizer

build_stage2_ubsan

check_stage2_ubsan
