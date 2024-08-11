#!/usr/bin/env bash

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

clobber

buildbot_update

# Stage 1

build_stage1_clang

check_stage1_ubsan

# Stage 2 / UndefinedBehaviorSanitizer

build_stage2_ubsan

check_stage2_ubsan

# Stage 3 / UndefinedBehaviorSanitizer

build_stage3_ubsan

check_stage3_ubsan

cleanup
