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
  rm -rf llvm-build
fi

ROOT=`pwd`
PLATFORM=`uname`
MAKE_JOBS=${MAX_MAKE_JOBS:-8}
BUILD_ASAN_ANDROID=${BUILD_ASAN_ANDROID:-0}
CHECK_TSAN=${CHECK_TSAN:-0}

echo @@@BUILD_STEP update@@@
buildbot_update

echo @@@BUILD_STEP build clang@@@
if [ ! -d llvm-build ]; then
  mkdir llvm-build
fi
cd llvm-build
CC=gcc CXX=g++ ../llvm/configure --enable-optimized
make -j$MAKE_JOBS ONLY_TOOLS=clang
cd ..
CLANG_BUILD=$ROOT/llvm-build/Release+Asserts

if [ $CHECK_TSAN == 1 ] ; then
  echo @@@BUILD_STEP prepare for testing tsan@@@

  TSAN_PATH=$ROOT/llvm/projects/compiler-rt/lib/tsan/
  (cd $TSAN_PATH && make -f Makefile.old install_deps)

  export PATH=$CLANG_BUILD/bin:$PATH
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
