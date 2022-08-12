#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

# FIXME: One test timeouts, the rest is good. Enable after moving to buildbot.
# Slow: 811.35s: llvm-libc++-shared.cfg.in :: libcxx/modules_include.sh.cpp
# Timeouts: llvm-libc++-shared.cfg.in :: std/input.output/stream.buffers/streambuf/streambuf.protected/streambuf.put.area/pbump2gig.pass.cpp
[[ "$(arch)" != "aarch64" ]] || exit 0

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS+=" -GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF"

clobber

buildbot_update

# Stage 1

build_stage1_clang

check_stage1_msan

# Stage 2 / Memory Sanitizer

build_stage2_msan

check_stage2_msan |& tee stage2_msan.log

if grep "WARNING: MemorySanitizer" stage2_msan.log ; then
  # Stage 2 / MemoryWithOriginsSanitizer
  (
    build_stage2_msan_track_origins

    check_stage2_msan_track_origins
  )
fi

# Stage 3 / MemorySanitizer
{
  build_stage3_msan

  check_stage3_msan
} |& tee stage3_msan.log

if grep "WARNING: MemorySanitizer" stage3_msan.log ; then
  # Stage 3 / MemoryWithOriginsSanitizer
  (
    build_stage2_msan_track_origins
    
    build_stage3_msan_track_origins

    check_stage3_msan_track_origins
  )
fi

cleanup $STAGE1_DIR
