#!/usr/bin/env bash

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh
. ${HERE}/buildbot_android_functions.sh

LOCAL_IPS=`hostname -I`

# TODO: Separate clobber from Force Build UI ("Clean source code and build
# directory" / "Clean build directory") and builder clean=True config.
BUILDBOT_CLOBBER=
clobber clang_rt_android_* tested_arch_* emulator*.log android_log_* android_rc_* cvd.lock

download_android_tools

# Stage 1

build_stage1_clang_at_revison
### From now on we use just-built Clang as a host compiler ###

buildbot_update

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

build_stage2_android

# Testing armv7 instead of plain arm to work around
# https://code.google.com/p/android/issues/detail?id=68779
build_and_test_android \
  aarch64:aarch64-linux-android \
  arm:armv7-linux-androideabi \
  i686:i686-linux-android \
  x86_64:x86_64-linux-android

cleanup clang_rt_android_* tested_arch_* emulator*.log android_log_* android_rc_* cvd.lock


