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

USE_GIT=0

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_PARALLEL_LINK_JOBS=20"

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_BINUTILS_INCDIR=/usr/include"
fi

clobber

download_android_tools r16

# Stage 1

build_stage1_clang_at_revison
### From now on we use just-built Clang as a host compiler ###

buildbot_update

CMAKE_COMMON_OPTIONS="$CMAKE_COMMON_OPTIONS -DLLVM_ENABLE_ASSERTIONS=ON"

build_clang64

# Android NDK has no iconv.h which is requred by LIBXML2.
CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_LIBXML2_ENABLED=OFF"

build_android_ndk aarch64 arm64
build_android_ndk arm arm
build_android_ndk i686 x86

echo @@@BUILD_STEP run cmake@@@
configure_android aarch64 aarch64-linux-android
# Testing armv7 instead of plain arm to work around
# https://code.google.com/p/android/issues/detail?id=68779
configure_android arm armv7-linux-androideabi
configure_android i686 i686-linux-android

build_android aarch64
build_android arm
build_android i686

test_android i686:x86 aarch64:arm64-v8a arm:armeabi-v7a
