#!/bin/bash

# Enable Error tracing
set -o errtrace

# Print trace for all commands ran before execution
set -x

ANN_SCRIPT_DIR="$(dirname $0)"
. ${ANN_SCRIPT_DIR}/buildbot-helper.sh

# Ensure all commands pass, and no dereferencing of unset variables.
set -eu
halt_on_failure

# We don't want to build within 'build' (where we start by default).
cd ..
rm -rf build

# Set up variables
LLVM_REVISION="${BUILDBOT_REVISION:-origin/main}"

case "$BUILDBOT_BUILDERNAME" in
  "clang-riscv-rva23-evl-vec-2stage")
    TARGET_CFLAGS="-march=rva23u64 -mllvm -force-tail-folding-style=data-with-evl -mllvm -prefer-predicate-over-epilogue=predicate-else-scalar-epilogue"
    export BB_IMG_DIR=$(pwd)/..
     # TODO: Switch to specifying rva23u64 once support is available in a
     # released QEMU.
    export BB_QEMU_CPU="rv64,zba=true,zbb=true,zbc=false,zbs=true,zfhmin=true,v=true,vext_spec=v1.0,zkt=true,zvfhmin=true,zvbb=true,zvkt=true,zihintntl=true,zicond=true,zimop=true,zcmop=true,zcb=true,zfa=true,zawrs=true,rvv_ta_all_1s=true,rvv_ma_all_1s=true,rvv_vl_half_avl=true"
    export BB_QEMU_SMP=32
    export BB_QEMU_MEM="64G"
    ;;
  *)
    echo "Unrecognised builder name"
    exit 1
esac


# Main builder stages start here

if [ ! -d llvm ]; then
  build_step "Cloning llvm-project repo"
  git clone --progress https://github.com/llvm/llvm-project.git llvm
fi

build_step "Updating llvm-project repo"
git -C llvm fetch origin
git -C llvm reset --hard "${LLVM_REVISION}"

# We unconditionally clean (i.e. don't check BUILDBOT_CLOBBER=1) as the script
# hasn't been tested without cleaning after each build.
build_step "Cleaning last build"
rm -rf stage1 stage2

build_step "llvm-project cmake stage 1"
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_ASSERTIONS=True \
  -DLLVM_LIT_ARGS="-v" \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DLLVM_ENABLE_LLD=True \
  -DLLVM_TARGETS_TO_BUILD="RISCV" \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DLLVM_ENABLE_PROJECTS="lld;clang;llvm" \
  -B stage1 \
  -S llvm/llvm

build_step "llvm-project build stage 1"
cmake --build stage1

build_step "llvm-project cmake stage 2"
cat - <<EOF > stage1-toolchain.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSROOT $(pwd)/../rvsysroot)
set(CMAKE_C_COMPILER_TARGET riscv64-linux-gnu)
set(CMAKE_CXX_COMPILER_TARGET riscv64-linux-gnu)
set(CMAKE_C_FLAGS_INIT "$TARGET_CFLAGS")
set(CMAKE_CXX_FLAGS_INIT "$TARGET_CFLAGS")
set(CMAKE_LINKER_TYPE LLD)
set(CMAKE_C_COMPILER $(pwd)/stage1/bin/clang)
set(CMAKE_CXX_COMPILER $(pwd)/stage1/bin/clang++)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_ASSERTIONS=True \
  -DLLVM_LIT_ARGS="-v" \
  -DLLVM_NATIVE_TOOL_DIR=$(pwd)/stage1/bin \
  -DLLVM_BUILD_TESTS=True \
  -DPython3_EXECUTABLE=/usr/bin/python3 \
  -DLLVM_EXTERNAL_LIT="$(pwd)/llvm-zorg/buildbot/riscv-rise/lit-on-qemu" \
  -DLLVM_ENABLE_PROJECTS="lld;clang;clang-tools-extra;llvm" \
  -DCMAKE_TOOLCHAIN_FILE=$(pwd)/stage1-toolchain.cmake \
  -DLLVM_HOST_TRIPLE=riscv64-linux-gnu \
  -S llvm/llvm \
  -B stage2

build_step "llvm-project build stage 2"
cmake --build stage2

build_step "llvm-project check-all"
cmake --build stage2 --target check-all
