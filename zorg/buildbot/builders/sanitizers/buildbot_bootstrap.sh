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
STAGE2_LIBCXX_UBSAN_DIR=libcxx_build_ubsan
STAGE2_UBSAN_DIR=llvm_build_ubsan
STAGE3_ASAN_DIR=llvm_build2_asan
STAGE3_MSAN_DIR=llvm_build2_msan
MAKE_JOBS=${MAX_MAKE_JOBS:-16}
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=3"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 and stage3 compilers don't make sense.
# Clobber the build trees.
rm -rf ${STAGE2_LIBCXX_MSAN_DIR}
rm -rf ${STAGE2_LIBCXX_ASAN_DIR}
rm -rf ${STAGE2_MSAN_DIR}
rm -rf ${STAGE3_MSAN_DIR}
rm -rf ${STAGE2_ASAN_DIR}
rm -rf ${STAGE3_ASAN_DIR}
rm -rf ${STAGE2_UBSAN_DIR}

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
cmake_stage3_msan_options="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${clang_msan_path}/clang -DCMAKE_CXX_COMPILER=${clang_msan_path}/clang++ -DLLVM_PARALLEL_COMPILE_JOBS=15"

(cd ${STAGE3_MSAN_DIR} && cmake ${cmake_stage3_msan_options} $LLVM && ninja clang) || \
  echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-llvm check-clang stage3/msan@@@

(cd ${STAGE3_MSAN_DIR} && ninja check-llvm) || echo @@@STEP_FAILURE@@@
(cd ${STAGE3_MSAN_DIR} && ninja check-clang) || echo @@@STEP_FAILURE@@@


# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan

# Stage 3 / AddressSanitizer

echo @@@BUILD_STEP build stage3/asan clang@@@

mkdir -p ${STAGE3_ASAN_DIR}

clang_asan_path=$ROOT/${STAGE2_ASAN_DIR}/bin
cmake_stage3_asan_options="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${clang_asan_path}/clang -DCMAKE_CXX_COMPILER=${clang_asan_path}/clang++ -DLLVM_PARALLEL_COMPILE_JOBS=10"

(cd ${STAGE3_ASAN_DIR} && cmake ${cmake_stage3_asan_options} $LLVM && ninja clang) || \
  echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-llvm check-clang stage3/asan@@@

export ASAN_OPTIONS="check_initialization_order=true:detect_leaks=1"

(cd ${STAGE3_ASAN_DIR} && ninja check-llvm) || echo @@@STEP_FAILURE@@@
(cd ${STAGE3_ASAN_DIR} && ninja check-clang) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP check-llvm check-clang stage3/asan-uar@@@

export ASAN_OPTIONS="check_initialization_order=true:detect_stack_use_after_return=1:detect_leaks=1"

(cd ${STAGE3_ASAN_DIR} && ninja check-llvm) || echo @@@STEP_FAILURE@@@
(cd ${STAGE3_ASAN_DIR} && ninja check-clang) || echo @@@STEP_FAILURE@@@

# Stage 2 / UndefinedBehaviorSanitizer

build_stage2_ubsan

check_stage2_ubsan
