#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

USE_GIT=0

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE3_DIR=llvm_build2_asan
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=20"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf llvm-project
  rm -rf ${STAGE1_DIR}
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 and stage3 compilers don't make sense.
# Clobber the build trees.
rm -rf llvm_build_* libcxx_build_*
rm -rf ${STAGE3_DIR}

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build stage1 clang@@@

build_stage1_clang

# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan

# Stage 3 / AddressSanitizer

echo @@@BUILD_STEP build stage3/asan clang@@@

mkdir -p ${STAGE3_DIR}

clang_asan_path=$ROOT/${STAGE2_DIR}/bin
cmake_stage3_asan_options="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${clang_asan_path}/clang -DCMAKE_CXX_COMPILER=${clang_asan_path}/clang++"

export ASAN_OPTIONS="check_initialization_order=true:detect_stack_use_after_return=1:detect_leaks=1"

(cd ${STAGE3_DIR} && cmake ${cmake_stage3_asan_options} $LLVM && ninja clang) || \
  echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP check-llvm check-clang stage3/asan@@@

(cd ${STAGE3_DIR} && ninja check-llvm) || echo @@@STEP_FAILURE@@@
(cd ${STAGE3_DIR} && ninja check-clang) || echo @@@STEP_FAILURE@@@

