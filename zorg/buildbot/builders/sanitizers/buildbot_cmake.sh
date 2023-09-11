#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

ARCH=`uname -m`
ninja --version || export PATH="/usr/local/bin:$PATH"

CMAKE_ARGS=""
for arg in "$@"
do
    case $arg in
        --CMAKE_ARGS=*)
        CMAKE_ARGS="${arg#*=}"
    esac
done

# Always clobber bootstrap build trees.
clobber

build_stage1_clang_at_revison

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_BINUTILS_INCDIR=/usr/include"
fi

CHECK_SYMBOLIZER=1
CHECK_TSAN=1


case "$ARCH" in
  ppc64*)
    CHECK_SYMBOLIZER=0
    # The test is x86_64 specific.
    CHECK_TSAN=0
    CMAKE_COMMON_OPTIONS+=" -DLLVM_TARGETS_TO_BUILD=PowerPC"
    if [[ "$ARCH" == "ppc64le" ]]; then
      CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-vj256"
    else
      CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-vj80"
    fi
  ;;
esac

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_PROJECTS=clang;lld"
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_RUNTIMES=libcxx;libcxxabi;compiler-rt"
CMAKE_COMMON_OPTIONS+=" -DLLVM_BUILD_LLVM_DYLIB=ON"
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF" # for "standalone compiler-rt"
CMAKE_COMMON_OPTIONS+=" ${CMAKE_ARGS}"

buildbot_update

function build {
  local build_dir=llvm_build64
  echo "@@@BUILD_STEP build compiler-rt ${1}${2}@@@"
  rm -rf ${build_dir}
  mkdir -p ${build_dir}

  cmake -B ${build_dir} ${CMAKE_COMMON_OPTIONS} ${2} $LLVM || build_failure
  ninja -C ${build_dir} || build_failure
}

function build_and_test {
  build "${1}" "${2}"

  local build_dir=llvm_build64
  echo "@@@BUILD_STEP test compiler-rt ${1}@@@"
  ninja -C ${build_dir} check-compiler-rt || build_failure
}

build_and_test "with gcc" ""

CMAKE_COMMON_OPTIONS+=" ${STAGE1_AS_COMPILER}"
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_WERROR=ON"

if [ "$CHECK_SYMBOLIZER" == "1" ]; then
  build_and_test "" "-DCOMPILER_RT_ENABLE_INTERNAL_SYMBOLIZER=ON"
fi

# FIXME: all tests should pass with DCOMPILER_RT_DEBUG=ON
LIT_FILTER_OUT='(AddressSanitizer|asan|ubsan)' \
  build_and_test "" "-DCOMPILER_RT_DEBUG=ON"

# Copied from buildbot_standard.sh, where it was not tested as well.
build "" "-DCOMPILER_RT_DEBUG=ON -DCOMPILER_RT_TSAN_DEBUG_OUTPUT=ON -DLLVM_INCLUDE_TESTS=OFF"

build_and_test "" ""

FRESH_CLANG_PATH=${ROOT}/llvm_build64/bin

echo @@@BUILD_STEP build standalone compiler-rt@@@
mkdir -p compiler_rt_build
cmake -B compiler_rt_build -GNinja \
  -DCMAKE_C_COMPILER=${FRESH_CLANG_PATH}/clang \
  -DCMAKE_CXX_COMPILER=${FRESH_CLANG_PATH}/clang++ \
  -DCOMPILER_RT_INCLUDE_TESTS=ON \
  -DCOMPILER_RT_ENABLE_WERROR=ON \
  -DLLVM_CMAKE_DIR=${ROOT}/llvm_build64 \
  $LLVM/../compiler-rt || build_failure
ninja -C compiler_rt_build || build_failure

echo @@@BUILD_STEP test standalone compiler-rt@@@
ninja -C compiler_rt_build check-all || build_failure

if [ "$CHECK_TSAN" == "1" ]; then
  # FIXME: Convert to a LIT test.
  echo @@@BUILD_STEP tsan analyze@@@
  BIN=tsan_bin
  echo "int main() {return 0;}" | ${FRESH_CLANG_PATH}/clang -x c++ - -fsanitize=thread -O2 -o ${BIN}
  $LLVM/../compiler-rt/lib/tsan/check_analyze.sh ${BIN} || build_failure
fi

cleanup
