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

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE1_CLOBBER="llvm_build64 compiler_rt_build_android_* llvm_build_android_*"
LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_PARALLEL_LINK_JOBS=20"

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_BINUTILS_INCDIR=/usr/include"
fi

export CCACHE_DIR=$ROOT/ccache
export CCACHE_COMPILERCHECK=content
if ccache -sM 20 ; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_CCACHE_BUILD=ON"
fi

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
  rm -rf android_ndk
  rm -rf platform-tools
fi

download_android_tools r16

# Stage 1

build_stage1_clang_at_revison
### From now on we use just-built Clang as a host compiler ###
CLANG_PATH=${ROOT}/${STAGE1_DIR}/bin

echo @@@BUILD_STEP update@@@
buildbot_update

CMAKE_COMMON_OPTIONS="$CMAKE_COMMON_OPTIONS -DLLVM_ENABLE_ASSERTIONS=ON"

# Build self-hosted tree with fresh Clang and -Werror.
CMAKE_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON -DCMAKE_C_COMPILER=${CLANG_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_PATH}/clang++ -DCMAKE_C_FLAGS=-gmlt -DCMAKE_CXX_FLAGS=-gmlt"

echo @@@BUILD_STEP bootstrap clang@@@
mkdir -p llvm_build64
if  [[ "$(cat llvm_build64/CMAKE_OPTIONS)" != "${CMAKE_OPTIONS}" ]] ; then
  (cd llvm_build64 && cmake ${CMAKE_OPTIONS} -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON $LLVM && \
     echo ${CMAKE_OPTIONS} > CMAKE_OPTIONS) || echo @@@STEP_FAILURE@@@
fi
ninja -C llvm_build64 || echo @@@STEP_FAILURE@@@

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
