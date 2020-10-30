#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

MAKE_JOBS=${MAX_MAKE_JOBS:-$(nproc)}
LLVM=$ROOT/llvm
LIBFUZZER=$LLVM/lib/Fuzzer
# No assertions. Need to clean up the existing assertion failures first.
# Also, the Fuzzer does not provide reproducers on assertion failures yet.
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_PARALLEL_LINK_JOBS=8 -DLIBFUZZER_ENABLE_TESTS=ON"

CLOBBER=fuzzer-test-suite
STAGE1_CLOBBER="RUNDIR-* $LIBFUZZER"
clobber

# Make sure asan intercepts SIGABRT so that the fuzzer can print the test cases
# for assertion failures.
# export ASAN_OPTIONS=handle_abort=1:strip_path_prefix=build/llvm/

buildbot_update

# Stage 1

build_stage1_clang

# export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
export PATH="$(readlink -f ${STAGE1_DIR}/bin):$PATH"

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
  echo
}

ulimit -t 3600

export JOBS=${MAKE_JOBS}

RunFuzzerTest libxml2-v2.9.2       || echo @@@STEP_FAILURE@@@
RunFuzzerTest libpng-1.2.56        || echo @@@STEP_FAILURE@@@
RunFuzzerTest libssh-2017-1272     || echo @@@STEP_FAILURE@@@
RunFuzzerTest re2-2014-12-09       || echo @@@STEP_FAILURE@@@
RunFuzzerTest c-ares-CVE-2016-5180 || echo @@@STEP_FAILURE@@@
RunFuzzerTest openssl-1.0.1f       || echo @@@STEP_FAILURE@@@
RunFuzzerTest openssl-1.0.2d       || echo @@@STEP_FAILURE@@@
RunFuzzerTest proj4-2017-08-14     || echo @@@STEP_FAILURE@@@
#RunFuzzerTest woff2-2016-05-06     || echo @@@STEP_WARNINGS@@@  # Often can't find the bug in the given time.
