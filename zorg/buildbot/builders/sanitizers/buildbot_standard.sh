#!/usr/bin/env bash

set -x
set -e
set -u

# dump buildbot env
env

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

TSAN_DEBUG_BUILD_DIR=tsan_debug_build
TSAN_FULL_DEBUG_BUILD_DIR=tsan_full_debug_build
TSAN_RELEASE_BUILD_DIR=tsan_release_build

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf $TSAN_DEBUG_BUILD_DIR
  rm -rf $TSAN_FULL_DEBUG_BUILD_DIR
  rm -rf $TSAN_RELEASE_BUILD_DIR
fi

ROOT=`pwd`
PLATFORM=`uname`
MAKE_JOBS=${MAX_MAKE_JOBS:-8}
CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}

LLVM_CHECKOUT=${ROOT}/llvm
CMAKE_COMMON_OPTIONS="-DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON"

function build_tsan {
  local build_dir=$1
  local extra_cmake_args=$2
  local targets="clang llvm-symbolizer llvm-config FileCheck not"
  if [ ! -d $build_dir ]; then
    mkdir $build_dir
  fi
  (cd $build_dir && CC=gcc CXX=g++ cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    ${CMAKE_COMMON_OPTIONS} ${extra_cmake_args} \
    ${LLVM_CHECKOUT})
  (cd $build_dir && make -j$MAKE_JOBS ${targets}) || echo @@@STEP_FAILURE@@@
  (cd $build_dir && make compiler-rt-clear) || echo @@@STEP_FAILURE@@@
  (cd $build_dir && make -j$MAKE_JOBS tsan) || echo @@@STEP_FAILURE@@@
}

echo @@@BUILD_STEP update@@@
buildbot_update

echo @@@BUILD_STEP build fresh clang + debug compiler-rt@@@
build_tsan "${TSAN_DEBUG_BUILD_DIR}" "-DCOMPILER_RT_DEBUG=ON"

echo @@@BUILD_STEP test tsan in debug compiler-rt build@@@
(cd $TSAN_DEBUG_BUILD_DIR && make -j$MAKE_JOBS check-tsan) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP build tsan with stats and debug output@@@
build_tsan "${TSAN_FULL_DEBUG_BUILD_DIR}" "-DCOMPILER_RT_DEBUG=ON -DCOMPILER_RT_TSAN_DEBUG_OUTPUT=ON -DLLVM_INCLUDE_TESTS=OFF"

echo @@@BUILD_STEP build release tsan with clang@@@
build_tsan "${TSAN_RELEASE_BUILD_DIR}" "-DCOMPILER_RT_DEBUG=OFF"

echo @@@BUILD_STEP prepare for testing tsan@@@
TSAN_PATH=$ROOT/llvm/projects/compiler-rt/lib/tsan/

CLANG_PATH=$ROOT/$TSAN_RELEASE_BUILD_DIR/bin
export PATH=$CLANG_PATH:$PATH
export MAKEFLAGS=-j$MAKE_JOBS
clang -v 2>tmp && grep "version" tmp

cd $ROOT
if [ -d tsanv2 ]; then
  (cd tsanv2 && svn cleanup && svn up --ignore-externals)
else
  svn co http://data-race-test.googlecode.com/svn/trunk/ tsanv2
fi
export RACECHECK_UNITTEST_PATH=$ROOT/tsanv2/unittest

cp $ROOT/../sanitizer_buildbot/sanitizers/test_tsan.sh $TSAN_PATH
(cd $TSAN_PATH && ./test_tsan.sh)
