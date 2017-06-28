#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh
. ${HERE}/buildbot_android_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE1_CLOBBER="llvm_build64 compiler_rt_build_android_* llvm_build_android_*"
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_PARALLEL_LINK_JOBS=20"
BUILD_TYPE=Release

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
  rm -rf android_ndk
  rm -rf platform-tools
fi

download_android_tools r15

# Stage 1

build_stage1_clang_at_revison 305968
### From now on we use just-built Clang as a host compiler ###
CLANG_PATH=${ROOT}/${STAGE1_DIR}/bin

echo @@@BUILD_STEP update@@@
buildbot_update

CMAKE_COMMON_OPTIONS="$CMAKE_COMMON_OPTIONS -DLLVM_ENABLE_ASSERTIONS=ON"

# Build self-hosted tree with fresh Clang and -Werror.
CMAKE_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON -DCMAKE_C_COMPILER=${CLANG_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_PATH}/clang++ -DCMAKE_C_FLAGS=-gmlt -DCMAKE_CXX_FLAGS=-gmlt"

echo @@@BUILD_STEP bootstrap clang@@@
if [ ! -d llvm_build64 ]; then
  mkdir llvm_build64
fi
(cd llvm_build64 && cmake ${CMAKE_OPTIONS} -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON $LLVM && ninja) || echo @@@STEP_FAILURE@@

CMAKE_COMMON_OPTIONS=-DLLVM_ENABLE_ASSERTIONS=ON

build_android() {
  CPU=$1
  TRIPLE=$2
  build_android_ndk $CPU
  build_compiler_rt $CPU $TRIPLE
  build_llvm_symbolizer $CPU $TRIPLE
}

# Testing armv7 instead of plain arm to work around
# https://code.google.com/p/android/issues/detail?id=68779
build_android arm armv7-linux-androideabi armeabi-v7a
build_android x86 i686-linux-android x86
build_android arm64 aarch64-linux-android arm64-v8a

echo @@@BUILD_STEP restart adb@@@
export USER=$( id -un )
export HOME=$( getent passwd "$USER" | cut -d: -f6 )
ADB_TRACE=all adb kill-server || true
ADB_TRACE=all adb devices || true

test_android arm armeabi-v7a @@@STEP_FAILURE@@@
test_android x86 x86 @@@STEP_FAILURE@@@
test_android arm64 arm64-v8a @@@STEP_FAILURE@@@
