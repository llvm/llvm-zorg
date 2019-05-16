#!/usr/bin/env bash

set -exu

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

CHECK_LIBCXX=${CHECK_LIBCXX:-0}
CHECK_LLD=${CHECK_LLD:-0}
LLVM=$ROOT/llvm

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
fi

echo @@@BUILD_STEP update@@@
buildbot_update

