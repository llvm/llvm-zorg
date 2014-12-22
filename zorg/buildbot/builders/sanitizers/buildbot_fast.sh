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
STAGE2_MSAN_DIR=llvm_build_msan
STAGE2_LIBCXX_MSAN_DIR=libcxx_build_msan
STAGE2_LIBCXX_ASAN_DIR=libcxx_build_asan
HOST_CLANG_REVISION=223108
MAKE_JOBS=${MAX_MAKE_JOBS:-16}
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=3"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# Stage 1

if  [ -r host_clang_revision ] && \
    [ "$(cat host_clang_revision)" == $HOST_CLANG_REVISION ]
then
  # Do nothing.
  echo @@@BUILD_STEP using pre-built stage1 clang at r$HOST_CLANG_REVISION@@@
else
  echo @@@BUILD_STEP sync to r$HOST_CLANG_REVISION@@@
  real_buildbot_revision=$BUILDBOT_REVISION
  BUILDBOT_REVISION=$HOST_CLANG_REVISION
  buildbot_update

  echo @@@BUILD_STEP build stage1 clang at r$HOST_CLANG_REVISION@@@

  rm -rf host_clang_revision

  # CMake does not notice that the compiler itself has changed. Anyway,
  # incremental builds of stage2 don't make sense if stage1 compiler has
  # changed. Clobber the build trees.
  rm -rf ${STAGE2_LIBCXX_MSAN_DIR}
  rm -rf ${STAGE2_LIBCXX_ASAN_DIR}
  rm -rf ${STAGE2_MSAN_DIR}
  rm -rf ${STAGE2_ASAN_DIR}

  build_stage1_clang

  echo $HOST_CLANG_REVISION > host_clang_revision

  BUILDBOT_REVISION=$real_buildbot_revision
fi

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 2 / Memory Sanitizer

build_stage2_msan

check_stage2_msan

# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan
