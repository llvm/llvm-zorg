#!/usr/bin/env bash

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

clobber

buildbot_update

# Stage 1

build_stage1_clang

check_stage1_cfi

# Stage 2 / CFI

build_stage2_cfi

check_stage2_cfi

# Stage 3 / CFI

build_stage3_cfi

check_stage3_cfi

cleanup
