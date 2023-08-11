#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

function cleanup() {
  ls
}

clobber

# Stage 1

build_stage1_clang_at_revison

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF"

# Some of them are slow.
STAGE2_SKIP_TEST_CXX=1

buildbot_update

# Stage 2 / Address and Undefined Sanitizer

build_stage2_asan_ubsan

check_stage2_asan_ubsan

# Stage 2 / Memory Sanitizer

CMAKE_COMMON_OPTIONS+=" -DCMAKE_C_FLAGS=-fno-inline"
CMAKE_COMMON_OPTIONS+=" -DCMAKE_CXX_FLAGS=-fno-inline"
CMAKE_COMMON_OPTIONS+=" -DCMAKE_C_FLAGS_RELEASE=-Oz"
CMAKE_COMMON_OPTIONS+=" -DCMAKE_CXX_FLAGS_RELEASE=-Oz"
build_stage2_msan

check_stage2_msan

cleanup
