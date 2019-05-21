#!/usr/bin/env bash

set -exu

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`

CHECK_LIBCXX=${CHECK_LIBCXX:-0}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE1_CLOBBER=
STAGE2_DIR=llvm_build

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf llvm-project
  rm -rf gn
  rm -rf ${STAGE1_DIR}
  rm -rf ${STAGE2_DIR}
fi

(
  LLVM=$ROOT/llvm
  CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_PARALLEL_LINK_JOBS=20"
  build_stage1_clang_at_revison
)

echo @@@BUILD_STEP build GN@@@
[[ -d gn ]] || git clone https://gn.googlesource.com/gn
(
  export PATH="$PATH:$(readlink -f $STAGE1_DIR)/bin"
  cd gn
  # Does not work with 0d038c2e0a32a528713d3dfaf1f1e0cdfe87fd46
  git checkout 0d038c2e0a32a528713d3dfaf1f1e0cdfe87fd46^
  python build/gen.py
  ninja -C out
) || { echo @@@STEP_EXCEPTION@@@ ; exit 1 ; }

echo @@@BUILD_STEP update@@@
buildbot_update_git

(
  echo @@@BUILD_STEP configure@@@
  export PATH=$(readlink -f gn/out/):$PATH
  $LLVM/utils/gn/gn.py gen ${STAGE2_DIR} \
    --list --short --overrides-only \
    --args="clang_base_path=\"$(readlink -f $STAGE1_DIR)\""
) || echo @@@STEP_FAILURE@@@

(
  cd $STAGE2_DIR
  for TARGET in "" $(ninja -t targets | grep -o "^check-[^:]*") ; do
    echo @@@BUILD_STEP ninja $TARGET@@@
    ninja $TARGET || echo @@@STEP_FAILURE@@@
  done
)
