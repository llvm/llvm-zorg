#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

CHECK_LIBCXX=${CHECK_LIBCXX:-0}
CHECK_LLD=${CHECK_LLD:-1}
STAGE1_DIR=llvm_build0
MAKE_JOBS=${MAX_MAKE_JOBS:-$(nproc)}
LLVM=$ROOT/llvm
LIBFUZZER=$LLVM/lib/Fuzzer
# No assertions. Need to clean up the existing assertion failures first.
# Also, the Fuzzer does not provide reproducers on assertion failures yet.
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_PARALLEL_LINK_JOBS=8 -DLIBFUZZER_ENABLE_TESTS=ON"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf ${STAGE1_DIR}
fi

# Make sure asan intercepts SIGABRT so that the fuzzer can print the test cases
# for assertion failures.
# export ASAN_OPTIONS=handle_abort=1:strip_path_prefix=build/llvm/

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build clang@@@

build_stage1_clang

clang_path=$ROOT/${STAGE1_DIR}/bin
# export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
export PATH="${clang_path}:$PATH"

echo @@@BUILD_STEP check-fuzzer@@@

(cd ${STAGE1_DIR} && ninja check-fuzzer) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP get fuzzer-test-suite @@@
[ ! -e fuzzer-test-suite ] && git clone https://github.com/google/fuzzer-test-suite.git
(cd fuzzer-test-suite && git pull)

RunFuzzerTest() {
  echo @@@BUILD_STEP test "$1" fuzzer@@@
  ln -sf $LIBFUZZER .
  export FUZZING_ENGINE=fsanitize_fuzzer
  `pwd`/fuzzer-test-suite/build-and-test.sh "$1"
}

ulimit -t 3600

RunFuzzerTest re2-2014-12-09       || echo @@@STEP_FAILURE@@@
RunFuzzerTest c-ares-CVE-2016-5180 || echo @@@STEP_FAILURE@@@
RunFuzzerTest openssl-1.0.1f       || echo @@@STEP_FAILURE@@@
RunFuzzerTest openssl-1.0.2d       || echo @@@STEP_FAILURE@@@
RunFuzzerTest libxml2-v2.9.2       || echo @@@STEP_FAILURE@@@
RunFuzzerTest libpng-1.2.56        || echo @@@STEP_FAILURE@@@
RunFuzzerTest libssh-2017-1272     || echo @@@STEP_FAILURE@@@
RunFuzzerTest proj4-2017-08-14     || echo @@@STEP_FAILURE@@@
#RunFuzzerTest woff2-2016-05-06     || echo @@@STEP_WARNINGS@@@  # Often can't find the bug in the given time.
