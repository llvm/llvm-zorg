#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh
. ${HERE}/buildbot_android_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
LOCAL_IPS=`hostname -I`
export PATH="/usr/local/bin:$PATH"

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS:-}"
CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS:-} -GNinja -DCMAKE_BUILD_TYPE=Release"

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS}"
fi

clobber

download_android_tools

# Stage 1

build_stage1_clang_at_revison
### From now on we use just-built Clang as a host compiler ###

buildbot_update

CMAKE_COMMON_OPTIONS="$CMAKE_COMMON_OPTIONS -DLLVM_ENABLE_ASSERTIONS=ON"

build_stage2_android

echo @@@BUILD_STEP run cmake@@@
configure_android aarch64 aarch64-linux-android
# Testing armv7 instead of plain arm to work around
# https://code.google.com/p/android/issues/detail?id=68779
configure_android arm armv7-linux-androideabi
configure_android i686 i686-linux-android

build_android aarch64
build_android arm
build_android i686

# Arm hardware is temporarily offline
test_android i686:x86 arm:armeabi-v7a aarch64:arm64-v8a
