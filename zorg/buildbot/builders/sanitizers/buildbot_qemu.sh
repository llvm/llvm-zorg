#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF"
CLOBBER="qemu qemu_build"

clobber

buildbot_update

build_stage1_clang
#build_stage1_clang_at_revison

COMPILER_BIN_DIR=$(readlink -f ${STAGE1_DIR})/bin

function build_qemu {
  echo "@@@BUILD_STEP build qemu@@@"
  $ROOT/qemu_build/qemu-x86_64 --version || (
    cd $ROOT
    git clone https://gitlab.com/qemu-project/qemu.git
    cd $ROOT/qemu
    git reset --hard $1
    git submodule update --init --recursive
    rm -rf $ROOT/qemu_build
    mkdir $ROOT/qemu_build
    cd $ROOT/qemu_build
    ../qemu/configure --disable-system --enable-linux-user --static
    ninja
    $ROOT/qemu_build/qemu-x86_64 --version
  ) || echo "@@@STEP_WARNINGS@@@"
}

build_qemu ffa090bc56e73e287a63261e70ac02c0970be61a

function build_compiler_rt {
  local name="$1"
  shift
  local cmake_opions=$@
  
  OUT_DIR=llvm_build2_${name}
  rm -rf ${OUT_DIR}
  mkdir -p ${OUT_DIR}
  cd ${OUT_DIR}

  (
    echo "@@@BUILD_STEP cmake for $name@@@"
    cmake ${CMAKE_COMMON_OPTIONS} "$@" $LLVM/../compiler-rt

    echo "@@@BUILD_STEP test scudo $name@@@"
    ninja check-scudo_standalone
  ) || echo "@@@STEP_WARNINGS@@@"
}

CMAKE_COMMON_OPTIONS+=" \
  -DLLVM_CONFIG_PATH=${COMPILER_BIN_DIR}//llvm-config \
  -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
  -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++"

CMAKE_COMMON_OPTIONS+=" \
-DCOMPILER_RT_BUILD_BUILTINS=OFF \
-DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON \
-DCMAKE_CROSSCOMPILING=True \
-DCOMPILER_RT_INCLUDE_TESTS=ON \
-DCOMPILER_RT_BUILD_LIBFUZZER=OFF \
-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
"

for DBG in OFF ON ; do
  CMAKE_COMMON_OPTIONS+=" -DCOMPILER_RT_DEBUG=$DBG"
  NAME_PREFIX=""
  if [[ "$DBG" == "ON" ]] ; then
    NAME_PREFIX="debug_"
  fi

  build_compiler_rt ${NAME_PREFIX}x86_64$ \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS=--target=x86_64-linux-gnu \
    -DCMAKE_C_COMPILER_TARGET=x86_64-linux-gnu \
    -DCMAKE_CXX_COMPILER_TARGET=x86_64-linux-gnu

  build_compiler_rt ${NAME_PREFIX}x86_64_qemu \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS=--target=x86_64-linux-gnu \
    -DCOMPILER_RT_EMULATOR=$ROOT/qemu_build/qemu-x86_64 \
    -DCMAKE_C_COMPILER_TARGET=x86_64-linux-gnu \
    -DCMAKE_CXX_COMPILER_TARGET=x86_64-linux-gnu

  build_compiler_rt ${NAME_PREFIX}aarch64_qemu \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS=--target=aarch64-linux-gnu \
    -DCMAKE_C_COMPILER_TARGET=aarch64-linux-gnu \
    -DCMAKE_CXX_COMPILER_TARGET=aarch64-linux-gnu \
    -DCOMPILER_RT_EMULATOR="$ROOT/qemu_build/qemu-aarch64 -L /usr/aarch64-linux-gnu" \
    -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld

  # DHWCAP2_MTE=1 is workaround for https://bugs.launchpad.net/qemu/+bug/1926044
  build_compiler_rt ${NAME_PREFIX}aarch64_mte_qemu \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="--target=aarch64-linux-gnu" \
    -DCMAKE_C_FLAGS=-DHWCAP2_MTE=1 \
    -DCMAKE_CXX_FLAGS=-DHWCAP2_MTE=1 \
    -DCMAKE_C_COMPILER_TARGET=aarch64-linux-gnu \
    -DCMAKE_CXX_COMPILER_TARGET=aarch64-linux-gnu \
    -DCOMPILER_RT_EMULATOR="$ROOT/qemu_build/qemu-aarch64 -L /usr/aarch64-linux-gnu -cpu max" \
    -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld
done
