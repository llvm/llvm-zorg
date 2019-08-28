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
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=20"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf llvm-project
  rm -rf llvm_build0
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 and stage3 compilers don't make sense.
# Clobber the build trees.
rm -rf llvm_build_* libcxx_build_* llvm_build2_*

buildbot_update

# Stage 1

build_stage1_clang

# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan

# Stage 3 / AddressSanitizer

export ASAN_OPTIONS="check_initialization_order=true:detect_stack_use_after_return=1:detect_leaks=1"
build_stage3_asan

check_stage3_asan

