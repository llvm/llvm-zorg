#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`

MAKE_JOBS=${MAX_MAKE_JOBS:-$(nproc)}
LLVM=$ROOT/llvm
LIBFUZZER=$LLVM/lib/Fuzzer
# No assertions. Need to clean up the existing assertion failures first.
# Also, the Fuzzer does not provide reproducers on assertion failures yet.
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=OFF"

clobber RUNDIR-*

# Make sure asan intercepts SIGABRT so that the fuzzer can print the test cases
# for assertion failures.
# export ASAN_OPTIONS=handle_abort=1:strip_path_prefix=build/llvm/

buildbot_update

# Stage 1

build_stage1_clang

# export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
export PATH="$(readlink -f ${STAGE1_DIR}/bin):$PATH"

echo @@@BUILD_STEP check-fuzzer@@@

(cd ${STAGE1_DIR} && ninja check-fuzzer) || build_failure

echo @@@BUILD_STEP get fuzzer-test-suite @@@
[ ! -e fuzzer-test-suite ] && git clone https://github.com/google/fuzzer-test-suite.git
(cd fuzzer-test-suite && git pull)

RunFuzzerTest() {
  echo @@@BUILD_STEP test "$1" fuzzer@@@
  ln -sf $LIBFUZZER .
  export FUZZING_ENGINE=fsanitize_fuzzer
  `pwd`/fuzzer-test-suite/build-and-test.sh "$1"
  echo
}

ulimit -t 3600

# FIXME: Some aarch64 tests are extremly slow, maybe related to

export JOBS=${MAKE_JOBS}

RunFuzzerTest libxml2-v2.9.2       || build_failure
[[ "$(arch)" == "aarch64" ]] || RunFuzzerTest libpng-1.2.56        || build_failure
RunFuzzerTest libssh-2017-1272     || build_failure
RunFuzzerTest re2-2014-12-09       || build_failure
RunFuzzerTest c-ares-CVE-2016-5180 || build_failure
RunFuzzerTest openssl-1.0.1f       || build_failure
[[ "$(arch)" == "aarch64" ]] || RunFuzzerTest openssl-1.0.2d       || build_failure
[[ "$(arch)" == "aarch64" ]] || RunFuzzerTest proj4-2017-08-14     || build_failure
#RunFuzzerTest woff2-2016-05-06     || build_failure  # Often can't find the bug in the given time.

cleanup $STAGE1_DIR RUNDIR-*
