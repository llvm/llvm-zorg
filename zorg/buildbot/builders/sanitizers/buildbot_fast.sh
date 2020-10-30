#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON"

clobber

# Stage 1

build_stage1_clang_at_revison

if ccache -s ; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_CCACHE_BUILD=ON"
fi

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
