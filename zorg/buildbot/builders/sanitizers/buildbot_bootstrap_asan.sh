#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
export PATH="/usr/local/bin:$PATH"

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF"

clobber

buildbot_update

# Stage 1

build_stage1_clang

check_stage1_asan


# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan

# Stage 3 / AddressSanitizer

export ASAN_OPTIONS="check_initialization_order=true:detect_stack_use_after_return=1:detect_leaks=1"
build_stage3_asan

check_stage3_asan

cleanup $STAGE1_DIR
