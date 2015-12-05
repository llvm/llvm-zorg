#!/usr/bin/env bash

set -x
set -e
set -u

# dump buildbot env
env

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

TSAN_FULL_DEBUG_BUILD_DIR=tsan_full_debug_build

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf clang_build
  rm -rf $TSAN_FULL_DEBUG_BUILD_DIR
fi

ROOT=`pwd`
PLATFORM=`uname`
MAKE_JOBS=${MAX_MAKE_JOBS:-8}
CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}

LLVM_CHECKOUT=${ROOT}/llvm
CMAKE_COMMON_OPTIONS="-DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON"

echo @@@BUILD_STEP update@@@
buildbot_update

echo @@@BUILD_STEP build fresh clang + debug compiler-rt@@@
if [ ! -d clang_build ]; then
  mkdir clang_build
fi
TARGETS="clang llvm-symbolizer llvm-config FileCheck not"
(cd clang_build && CC=gcc CXX=g++ cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  ${CMAKE_COMMON_OPTIONS} -DCOMPILER_RT_DEBUG=ON ${LLVM_CHECKOUT})

(cd clang_build && make -j$MAKE_JOBS ${TARGETS}) || echo @@@STEP_FAILURE@@@
CLANG_PATH=$ROOT/clang_build/bin

echo @@@BUILD_STEP test tsan in debug compiler-rt build@@@
(cd clang_build && make compiler-rt-clear) || echo @@@STEP_FAILURE@@@
(cd clang_build && make -j$MAKE_JOBS check-tsan) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP build tsan with stats and debug output@@@
if [ ! -d $TSAN_FULL_DEBUG_BUILD_DIR ]; then
  mkdir $TSAN_FULL_DEBUG_BUILD_DIR
fi
(cd $TSAN_FULL_DEBUG_BUILD_DIR && CC=gcc CXX=g++ cmake -DCMAKE_BUILD_TYPE=Release \
  ${CMAKE_COMMON_OPTIONS} -DCOMPILER_RT_DEBUG=ON \
  -DCOMPILER_RT_TSAN_DEBUG_OUTPUT=ON -DLLVM_INCLUDE_TESTS=OFF \
  ${LLVM_CHECKOUT})
(cd $TSAN_FULL_DEBUG_BUILD_DIR && make -j$MAKE_JOBS ${TARGETS}) || echo @@@STEP_FAILURE@@@
(cd $TSAN_FULL_DEBUG_BUILD_DIR && make compiler-rt-clear) || echo @@@STEP_FAILURE@@@
(cd $TSAN_FULL_DEBUG_BUILD_DIR && make -j$MAKE_JOBS tsan) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP prepare for testing tsan@@@

TSAN_PATH=$ROOT/llvm/projects/compiler-rt/lib/tsan/
(cd $TSAN_PATH && make -f Makefile.old install_deps)

export PATH=$CLANG_PATH:$PATH
export MAKEFLAGS=-j$MAKE_JOBS
gcc -v 2>tmp && grep "version" tmp
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
