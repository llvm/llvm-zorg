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
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=20"

clobber

buildbot_update

# Stage 1

build_stage1_clang

# Stage 2 / Memory Sanitizer

build_stage2_msan

check_stage2_msan

# Stage 3 / MemorySanitizer

build_stage3_msan

check_stage3_msan
