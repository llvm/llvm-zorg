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
STAGE2_MSAN_DIR=llvm_build_msan
STAGE2_LIBCXX_MSAN_DIR=libcxx_build_msan
STAGE3_MSAN_DIR=llvm_build2_msan
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=20"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 and stage3 compilers don't make sense.
# Clobber the build trees.
rm -rf ${STAGE2_LIBCXX_MSAN_DIR}
rm -rf ${STAGE2_MSAN_DIR}
rm -rf ${STAGE3_MSAN_DIR}

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build stage1 clang@@@

build_stage1_clang

# Stage 2 / Memory Sanitizer

build_stage2_msan

check_stage2_msan

# Stage 3 / MemorySanitizer

echo @@@BUILD_STEP build stage3/msan clang@@@

mkdir -p ${STAGE3_MSAN_DIR}

clang_msan_path=$ROOT/${STAGE2_MSAN_DIR}/bin
cmake_stage3_msan_options="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${clang_msan_path}/clang -DCMAKE_CXX_COMPILER=${clang_msan_path}/clang++"

(cd ${STAGE3_MSAN_DIR} && cmake ${cmake_stage3_msan_options} $LLVM && ninja clang) || \
  echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-llvm check-clang stage3/msan@@@

(cd ${STAGE3_MSAN_DIR} && ninja check-llvm) || echo @@@STEP_FAILURE@@@
(cd ${STAGE3_MSAN_DIR} && ninja check-clang) || echo @@@STEP_FAILURE@@@
