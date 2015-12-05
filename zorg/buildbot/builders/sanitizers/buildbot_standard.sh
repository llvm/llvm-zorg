#!/usr/bin/env bash

set -x
set -e
set -u

# dump buildbot env
env

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf clang_build
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
TARGETS="clang llvm-symbolizer compiler-rt FileCheck not"
(cd clang_build && CC=gcc CXX=g++ cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  ${CMAKE_COMMON_OPTIONS} -DCOMPILER_RT_DEBUG=ON ${LLVM_CHECKOUT})

(cd clang_build && make -j$MAKE_JOBS ${TARGETS}) || echo @@@STEP_FAILURE@@@
CLANG_PATH=$ROOT/clang_build/bin

echo @@@BUILD_STEP test tsan in debug compiler-rt build@@@
(cd clang_build && make -j$MAKE_JOBS check-tsan) || echo @@@STEP_FAILURE@@@

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
