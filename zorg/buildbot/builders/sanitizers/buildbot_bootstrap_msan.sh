#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF"

clobber

buildbot_update

# Stage 1

build_stage1_clang

check_stage1_msan

for I in 1 2 ; do
  # Stage 2 / Memory Sanitizer

  build_stage2_msan

  (
    check_stage2_msan |& tee stage2_msan.log
    exit ${PIPESTATUS[0]}
  )

  if grep "WARNING: MemorySanitizer" stage2_msan.log ; then
    # Stage 2 / MemoryWithOriginsSanitizer
    (
      build_stage2_msan_track_origins

      check_stage2_msan_track_origins
    )
  fi

  # Stage 3 / MemorySanitizer
  (
    {
      build_stage3_msan

      check_stage3_msan
    } |& tee stage3_msan.log
    exit ${PIPESTATUS[0]}
  )

  if grep "WARNING: MemorySanitizer" stage3_msan.log ; then
    # Stage 3 / MemoryWithOriginsSanitizer
    (
      build_stage2_msan_track_origins
      
      build_stage3_msan_track_origins

      check_stage3_msan_track_origins
    )
  fi

  # FIXME: stage3/msan check_1 crashes.
  break

  cleanup

  # Repeat with strict settings.
  CMAKE_COMMON_OPTIONS+=" -DCMAKE_C_FLAGS=-fno-inline"
  CMAKE_COMMON_OPTIONS+=" -DCMAKE_CXX_FLAGS=-fno-inline"
  CMAKE_COMMON_OPTIONS+=" -DCMAKE_C_FLAGS_RELEASE=-Oz"
  CMAKE_COMMON_OPTIONS+=" -DCMAKE_CXX_FLAGS_RELEASE=-Oz"
done

cleanup $STAGE1_DIR