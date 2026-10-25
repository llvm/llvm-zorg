#!/usr/bin/env bash

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh
. ${HERE}/buildbot_android_functions.sh

LOCAL_IPS=`hostname -I`

# TODO: Separate clobber from Force Build UI ("Clean source code and build
# directory" / "Clean build directory") and builder clean=True config.
BUILDBOT_CLOBBER=
clobber

download_android_tools

# Stage 1

build_stage1_clang_at_revison
### From now on we use just-built Clang as a host compiler ###

buildbot_update

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

build_stage2_android

# Testing armv7 instead of plain arm to work around
# https://code.google.com/p/android/issues/detail?id=68779
build_android aarch64 aarch64-linux-android
build_android arm armv7-linux-androideabi
build_android i686 i686-linux-android
build_android x86_64 x86_64-linux-android

# Temporarily disable testing on arm arches because software emulation is too
# slow; we will figure out how to run them later.
test_android i686 x86_64 # arm aarch64

cleanup tested_arch_* emulator.log


