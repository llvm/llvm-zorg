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
CHECK_TSAN=${CHECK_TSAN:-0}

LLVM_CHECKOUT=${ROOT}/llvm
CMAKE_COMMON_OPTIONS="-DLLVM_ENABLE_ASSERTIONS=ON"

echo @@@BUILD_STEP update@@@
buildbot_update

echo @@@BUILD_STEP build fresh clang@@@
if [ ! -d clang_build ]; then
  mkdir clang_build
fi
(cd clang_build && CC=gcc CXX=g++ cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  ${CMAKE_COMMON_OPTIONS} ${LLVM_CHECKOUT})
(cd clang_build && make -j$MAKE_JOBS) || echo @@@STEP_FAILURE@@@
CLANG_PATH=$ROOT/clang_build/bin

if [ $CHECK_TSAN == 1 ] ; then
  echo @@@BUILD_STEP prepare for testing tsan@@@

  TSAN_PATH=$ROOT/llvm/projects/compiler-rt/lib/tsan/
  (cd $TSAN_PATH && make -f Makefile.old install_deps)

  export PATH=$CLANG_PATH:$PATH
  export MAKEFLAGS=-j$MAKE_JOBS
  gcc -v 2>tmp && grep "version" tmp
  clang -v 2>tmp && grep "version" tmp

  cd $ROOT
  if [ -d tsanv2 ]; then
    (cd tsanv2 && svn up --ignore-externals)
  else
    svn co http://data-race-test.googlecode.com/svn/trunk/ tsanv2
  fi
  export RACECHECK_UNITTEST_PATH=$ROOT/tsanv2/unittest

  cp $ROOT/../sanitizer_buildbot/sanitizers/test_tsan.sh $TSAN_PATH
  (cd $TSAN_PATH && ./test_tsan.sh)
fi
