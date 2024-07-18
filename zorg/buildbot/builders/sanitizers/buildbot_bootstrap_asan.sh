#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

clobber

buildbot_update

# Stage 1

build_stage1_clang

check_stage1_asan


# Stage 2 / AddressSanitizer

build_stage2_asan

check_stage2_asan

# Stage 3 / AddressSanitizer

export ASAN_OPTIONS="check_initialization_order=true"
build_stage3_asan

check_stage3_asan

cleanup
