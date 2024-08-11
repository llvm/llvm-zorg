#!/usr/bin/env bash

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

# TODO: find a better way to disable cleanup.
function cleanup() {
  # Workaround the case when a new unittest was reverted, but incremental build continues to execute the leftover binary.
  find -executable -type f -wholename *unittests* -delete
  du -hs * | sort -h
}

clobber

# Stage 1

build_stage1_clang_at_revison

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

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
