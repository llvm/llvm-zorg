#!/usr/bin/env bash

set -x
set -e
set -u

# Set HOME for gsutil to work
export HOME=/var/lib/buildbot

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
STAGE2_ASAN_DIR=llvm_build_asan
STAGE2_ASAN_ASSERTIONS_DIR=llvm_build_asan_assertions
MAKE_JOBS=${MAX_MAKE_JOBS:-8}
LLVM=$ROOT/llvm
# No assertions. Need to clean up the existing assertion failures first.
# Also, the Fuzzer does not provide reproducers on assertion failures yet.
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_PARALLEL_LINK_JOBS=8"
CORPUS_ROOT=$ROOT/CORPORA/llvm
CLANG_FORMAT_CORPUS=$CORPUS_ROOT/clang-format/C1
CLANG_CORPUS=$CORPUS_ROOT/clang/C2
LLVM_AS_CORPUS=$CORPUS_ROOT/llvm-as/C1
LLVM_PDBDUMP_CORPUS=$CORPUS_ROOT/llvm-pdbdump/C1

GS_ROOT=gs://fuzzing-with-sanitizers/llvm

syncFromGs() {
  mkdir -p $CORPUS_ROOT/$1
  gsutil -m rsync $GS_ROOT/$1 $CORPUS_ROOT/$1
}

syncToGs() {
  gsutil -m rsync $CORPUS_ROOT/$1 $GS_ROOT/$1
}

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 compilers don't make sense.
# Clobber the build trees.
rm -rf ${STAGE2_ASAN_DIR}
rm -rf ${STAGE2_ASAN_ASSERTIONS_DIR}

# Make sure asan intercepts SIGABRT so that the fuzzer can print the test cases
# for assertion failures.
export ASAN_OPTIONS=handle_abort=1:strip_path_prefix=build/llvm/

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build clang@@@

build_stage1_clang

echo @@@BUILD_STEP pull test corpuses @@@
syncFromGs clang/C2
syncFromGs clang-format/C1
syncFromGs llvm-pdbdump/C1
#syncFromGs llvm-as/C1

# TODO(smatveev): merge this with build_stage2()
clang_path=$ROOT/${STAGE1_DIR}/bin
cmake_stage2_asan_options=" \
  ${CMAKE_COMMON_OPTIONS} \
  -DCMAKE_C_COMPILER=${clang_path}/clang \
  -DCMAKE_CXX_COMPILER=${clang_path}/clang++ \
  -DLLVM_USE_SANITIZER=Address \
  -DLLVM_USE_SANITIZE_COVERAGE=YES \
"
common_stage2_variables
export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"

# Stage 2 / AddressSanitizer + assertions
mkdir -p ${STAGE2_ASAN_ASSERTIONS_DIR}
echo @@@BUILD_STEP stage2/asan+assertions check-fuzzer@@@
cmake_stage2_asan_assertions_options="$cmake_stage2_asan_options -DLLVM_ENABLE_ASSERTIONS=ON"

(cd ${STAGE2_ASAN_ASSERTIONS_DIR} && cmake ${cmake_stage2_asan_assertions_options} $LLVM) || \
  echo @@@STEP_FAILURE@@@

(cd ${STAGE2_ASAN_ASSERTIONS_DIR} && ninja check-fuzzer) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP stage2/asan+assertions build clang-format-fuzzer and clang-fuzzer@@@

(cd ${STAGE2_ASAN_ASSERTIONS_DIR} && ninja clang-format-fuzzer clang-fuzzer llvm-as-fuzzer llvm-pdbdump-fuzzer) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP stage2/asan+assertions run clang-format-fuzzer@@@

(${STAGE2_ASAN_ASSERTIONS_DIR}/bin/clang-format-fuzzer -max_len=64 -jobs=8 -workers=8 -max_total_time=600 $CLANG_FORMAT_CORPUS) || \
  echo @@@STEP_WARNINGS@@@

echo @@@BUILD_STEP stage2/asan+assertions run llvm-pdbdump-fuzzer@@@

(${STAGE2_ASAN_ASSERTIONS_DIR}/bin/llvm-pdbdump-fuzzer -max_len=50000 -rss_limit_mb=3000 -jobs=8 -workers=8 -max_total_time=600 $LLVM_PDBDUMP_CORPUS $LLVM/test/DebugInfo/PDB/Inputs/) || \
  echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP stage2/asan+assertions run clang-fuzzer@@@
(${STAGE2_ASAN_ASSERTIONS_DIR}/bin/clang-fuzzer -max_len=64 -detect_leaks=0 -jobs=8 -workers=8 -only_ascii=1 -max_total_time=1200 $CLANG_CORPUS) || \
  echo @@@STEP_WARNINGS@@@

# No leak detection due to https://llvm.org/bugs/show_bug.cgi?id=24639#c5
# Too many known failures in llvm-as, disabling this until they are fixed.
#echo @@@BUILD_STEP stage2/asan+assertions run llvm-as-fuzzer@@@
#(ASAN_OPTIONS=$ASAN_OPTIONS:detect_leaks=0 ${STAGE2_ASAN_ASSERTIONS_DIR}/bin/llvm-as-fuzzer -jobs=8 -workers=8 -runs=0 -only_ascii=1 $LLVM_AS_CORPUS) || \
#  echo @@@STEP_WARNINGS@@@

echo @@@BUILD_STEP push corpus updates@@@
syncToGs clang/C2
syncToGs clang-format/C1
syncToGs llvm-pdbdump/C1
#syncToGs llvm-as/C1

