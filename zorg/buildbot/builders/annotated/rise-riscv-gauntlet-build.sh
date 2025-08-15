#!/bin/sh

# We don't want to build within 'build' (where we start by default).
cd ..
rm -rf build

LLVM_REVISION="${BUILDBOT_REVISION:-origin/main}"

die() {
  printf "%s\n" "$*" >&2
  exit 1
}

build_step() {
  printf "@@@BUILD_STEP %s@@@\n" "$*" >&2
}
step_text() {
  printf "@@@STEP_TEXT@%s@@@\n" "$*" >&2
}
HAD_FAILURE=0
step_failure() {
  HAD_FAILURE=1
  # Use same workaround as the sanitizers - the server fails to pick up step
  # failures unless repeated multiple times with a delay.
  for _ in 0 1 2 ; do
    echo "@@@STEP_FAILURE@@@" >&2
    sleep 5
  done
}

set -u # Exit on referencing an unset variable.
set -x # Trace all commands.

set -e # Exit upon command failure. Will be disabled later.

if [ ! -d llvm-project ]; then
  build_step "Cloning llvm-project repo"
  git clone --progress https://github.com/llvm/llvm-project.git
fi

build_step "Updating llvm-project repo"
git -C llvm-project fetch --prune origin
git -C llvm-project reset --hard "${LLVM_REVISION}"

if [ ! -d llvm-test-suite ]; then
  build_step "Cloning llvm-test-suite repo"
  git clone --progress https://github.com/llvm/llvm-test-suite.git
fi

build_step "Updating llvm-test-suite repo"
git -C llvm-test-suite fetch --prune origin
git -C llvm-test-suite reset --hard origin/main

# We unconditionally clean (i.e. don't check BUILDBOT_CLOBBER=1) as the script
# hasn't been tested without cleaning after each build.
build_step "Cleaning last build"
rm -rf llvm-project/build llvm-test-suite/build.* *-toolchain.cmake

build_step "llvm-project configure stage 1"
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_ASSERTIONS=True \
  -DLLVM_LIT_ARGS="-v" \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DLLVM_ENABLE_LLD=True \
  -DLLVM_TARGETS_TO_BUILD="RISCV;X86" \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DLLVM_ENABLE_PROJECTS="lld;clang;llvm" \
  -B llvm-project/build/stage1 \
  -S llvm-project/llvm

build_step "llvm-project build stage 1"
cmake --build llvm-project/build/stage1

STAGE1_BINDIR=$(pwd)/llvm-project/build/stage1/bin

# Don't exit immediately upon failure from here on.
set +e

# Skip a few tests that have excessive runtimes relative to the others.
export LIT_FILTER_OUT='(SingleSource/Benchmarks/Polybench/linear-algebra/solvers/(ludcmp|lu)|MicroBenchmarks/LoopVectorization/LoopInterleavingBenchmarks)'
for CONF in rva20 rva22 rva23 rva23-zvl1024b rva23-mrvv-vec-bits; do
  RVA23_QEMU_CPU="rv64,zba=true,zbb=true,zbc=false,zbs=true,zfhmin=true,v=true,vext_spec=v1.0,zkt=true,zvfhmin=true,zvbb=true,zvkt=true,zihintntl=true,zicond=true,zimop=true,zcmop=true,zcb=true,zfa=true,zawrs=true,rvv_ta_all_1s=true,rvv_ma_all_1s=true,rvv_vl_half_avl=true"
  case "$CONF" in
    rva20)
      CFLAGS="-march=rva20u64"
      QEMU_CPU="rv64,zfa=false,zba=false,zbb=false,zbc=false,zbs=false"
      ;;
    rva22)
      CFLAGS="-march=rva22u64"
      QEMU_CPU="rv64,zba=true,zbb=true,zbc=false,zbs=true,zfhmin=true,v=false,zkt=true,zihintntl=true"
      ;;
    rva23)
      CFLAGS="-march=rva23u64"
      QEMU_CPU=$RVA23_QEMU_CPU
      ;;
    rva23-zvl1024b)
      CFLAGS="-march=rva23u64_zvl1024b"
      QEMU_CPU=$RVA23_QEMU_CPU
      ;;
    rva23-mrvv-vec-bits)
      CFLAGS="-march=rva23u64 -mrvv-vector-bits=zvl"
      QEMU_CPU=$RVA23_QEMU_CPU
      ;;
    *)
      echo "Unrecognised config name"
      exit 1
  esac
  export QEMU_LD_PREFIX="$(pwd)/../rvsysroot"
  export QEMU_CPU=$QEMU_CPU
  cat - <<EOF > $CONF-toolchain.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSROOT $(pwd)/../rvsysroot)
set(CMAKE_C_COMPILER_TARGET riscv64-linux-gnu)
set(CMAKE_CXX_COMPILER_TARGET riscv64-linux-gnu)
set(CMAKE_C_FLAGS_INIT "$CFLAGS -DSMALL_PROBLEM_SIZE")
set(CMAKE_CXX_FLAGS_INIT "$CFLAGS -DSMALL_PROBLEM_SIZE")
set(CMAKE_LINKER_TYPE LLD)
set(CMAKE_C_COMPILER $STAGE1_BINDIR/clang)
set(CMAKE_CXX_COMPILER $STAGE1_BINDIR/clang++)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
  build_step "$CONF: llvm-test-suite configure"
  cmake -G Ninja \
    --toolchain=$(pwd)/$CONF-toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DTEST_SUITE_LIT=$STAGE1_BINDIR/llvm-lit \
    -DTEST_SUITE_LIT_FLAGS=-v \
    -DTEST_SUITE_COLLECT_CODE_SIZE=OFF \
    -DTEST_SUITE_COLLECT_COMPILE_TIME=OFF \
    -DTEST_SUITE_USER_MODE_EMULATION=ON \
    -DSMALL_PROBLEM_SIZE=ON \
    -S llvm-test-suite \
    -B llvm-test-suite/build.$CONF
  if [ $? -ne 0 ]; then
    step_failure
    continue
  fi
  build_step "$CONF: llvm-test-suite build"
  cmake --build llvm-test-suite/build.$CONF
  if [ $? -ne 0 ]; then
    step_failure
    continue
  fi
  build_step "$CONF: llvm-test-suite check"
  cmake --build llvm-test-suite/build.$CONF --target check
  if [ $? -ne 0 ]; then
    step_failure
    continue
  fi
done
export -n LIT_FILTER_OUT

if [ $HAD_FAILURE -ne 0 ]; then
  build_step "llvm-project check-all"
  cmake --build llvm-project/build/stage1 --target check-all
  if [ $? -ne 0 ]; then
    die "check-all on X86_64 host failed. This indicates there is most likely an issue that is not RISC-V specific."
  fi
else
  build_step "SKIPPED llvm-project check-all"
fi
