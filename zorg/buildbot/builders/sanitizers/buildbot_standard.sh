#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

TSAN_DEBUG_BUILD_DIR=tsan_debug_build
TSAN_FULL_DEBUG_BUILD_DIR=tsan_full_debug_build
TSAN_RELEASE_BUILD_DIR=tsan_release_build

CLEANUP="$TSAN_DEBUG_BUILD_DIR $TSAN_FULL_DEBUG_BUILD_DIR $TSAN_RELEASE_BUILD_DIR"
clobber $CLEANUP

function build_tsan {
  local build_dir=$1
  local extra_cmake_args="$2 -DLLVM_ENABLE_PROJECTS='clang' -DLLVM_ENABLE_RUNTIMES='compiler-rt'"
  local targets="clang llvm-symbolizer llvm-config FileCheck not"
  if [ ! -d $build_dir ]; then
    mkdir $build_dir
  fi
  (cd $build_dir && CC="$3" CXX="$4" cmake \
    ${CMAKE_COMMON_OPTIONS} ${extra_cmake_args} \
    ${LLVM})
  ninja -C ${build_dir} compiler-rt || build_failure
}

buildbot_update

echo @@@BUILD_STEP build fresh clang + debug compiler-rt@@@
build_tsan "${TSAN_DEBUG_BUILD_DIR}" "-DCOMPILER_RT_DEBUG=ON" gcc g++
echo @@@BUILD_STEP test tsan in debug compiler-rt build@@@
ninja -C ${TSAN_DEBUG_BUILD_DIR}/runtimes/runtimes-bins check-tsan || build_failure

echo @@@BUILD_STEP build tsan with stats and debug output@@@
build_tsan "${TSAN_FULL_DEBUG_BUILD_DIR}" "-DCOMPILER_RT_DEBUG=ON -DCOMPILER_RT_TSAN_DEBUG_OUTPUT=ON -DLLVM_INCLUDE_TESTS=OFF" gcc g++

echo @@@BUILD_STEP build release tsan with clang@@@
build_tsan "${TSAN_RELEASE_BUILD_DIR}" "-DCOMPILER_RT_DEBUG=OFF" "$ROOT/$TSAN_DEBUG_BUILD_DIR/bin/clang" "$ROOT/$TSAN_DEBUG_BUILD_DIR/bin/clang++"

echo @@@BUILD_STEP tsan analyze@@@
BIN=$(mktemp -t tsan_exe.XXXXXXXX)
echo "int main() {return 0;}" | $TSAN_RELEASE_BUILD_DIR/bin/clang -x c++ - -fsanitize=thread -O2 -o ${BIN}
COMPILER_RT=$LLVM/../compiler-rt
$COMPILER_RT/lib/tsan/check_analyze.sh ${BIN} || build_failure

cleanup $CLEANUP
