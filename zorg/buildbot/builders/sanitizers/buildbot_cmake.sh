#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

ARCH=`uname -m`
ninja --version || export PATH="/usr/local/bin:$PATH"

CMAKE_ARGS=""
for arg in "$@"
do
    case $arg in
        --CMAKE_ARGS=*)
        CMAKE_ARGS="${arg#*=}"
    esac
done

# Always clobber bootstrap build trees.
clobber

SUPPORTS_32_BITS=${SUPPORTS_32_BITS:-1}
ZLIB=$ROOT/zlib

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=10 -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF ${CMAKE_ARGS}"
ENABLE_LIBCXX_FLAG=

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_BINUTILS_INCDIR=/usr/include"
fi

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_PROJECTS='clang;compiler-rt'"

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_SYMBOLIZER=${CHECK_SYMBOLIZER:-$CHECK_LIBCXX}
# FIXME: Something broken with LLD switch 19cb7a33e82.
CHECK_SYMBOLIZER=0
CHECK_LLD=${CHECK_LLD:-1}
CHECK_ASAN=0
CHECK_HWASAN=0
CHECK_UBSAN=0
CHECK_MSAN=0
CHECK_TSAN=0
CHECK_LSAN=0
CHECK_DFSAN=0
CHECK_SCUDO_STANDALONE=0
CHECK_CFI=0
case "$ARCH" in
  x86_64)
    CHECK_ASAN=1
    CHECK_HWASAN=1
    CHECK_UBSAN=1
    CHECK_MSAN=1
    CHECK_TSAN=1
    CHECK_LSAN=1
    CHECK_DFSAN=1
    CHECK_SCUDO_STANDALONE=1
    CHECK_CFI=1
  ;;
  aarch64)
    CHECK_ASAN=1
    CHECK_UBSAN=1
    CHECK_MSAN=1
    CHECK_TSAN=1
    CHECK_LSAN=1
    CHECK_DFSAN=1
  ;;
  mips64*)
    CHECK_ASAN=1
    CHECK_UBSAN=1
    CHECK_MSAN=1
    CHECK_TSAN=1
    CHECK_LSAN=1
    CHECK_DFSAN=1
  ;;
  ppc64*)
    CHECK_ASAN=1
    CHECK_UBSAN=1
    CHECK_MSAN=1
    CHECK_TSAN=1
    CMAKE_COMMON_OPTIONS+=" -DLLVM_TARGETS_TO_BUILD=PowerPC"
    if [[ "$ARCH" == "ppc64le" ]]; then
      CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-vj256"
    else
      CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-vj80"
    fi
  ;;
  i*86)
    CHECK_UBSAN=1
    CHECK_ASAN=1
  ;;
  mips*)
    CHECK_UBSAN=1
    CHECK_ASAN=1
  ;;
  arm*)
    CHECK_UBSAN=1
    CHECK_ASAN=1
  ;;
  s390x)
    CHECK_UBSAN=1
  ;;
esac

PROJECTS="clang;compiler-rt"
if [[ "$CHECK_LLD" != "0" ]]; then
  PROJECTS+=";lld"
fi
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_PROJECTS='${PROJECTS}' -DLLVM_ENABLE_RUNTIMES=libcxx;libcxxabi"

if [[ "$CHECK_CFI" == "1" ]]; then
  # We need this after https://reviews.llvm.org/D62050
  CMAKE_COMMON_OPTIONS+=" -DLLVM_BUILD_LLVM_DYLIB=ON"
fi

CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-v"

buildbot_update

COMPILER_RT=$LLVM/../compiler-rt
LIBCXX=$LLVM/../libcxx

# Use both gcc and just-built Clang/LLD as a host compiler/linker for sanitizer
# tests. Assume that self-hosted build tree should compile with -Werror.
echo @@@BUILD_STEP build fresh toolchain@@@
mkdir -p clang_build
(cd clang_build && cmake ${CMAKE_COMMON_OPTIONS} $LLVM ) || (rm -rf clang_build ; build_failure)

BOOTSTRAP_BUILD_TARGETS="clang"
if [[ "$CHECK_LLD" != "0" ]]; then
  BOOTSTRAP_BUILD_TARGETS="$BOOTSTRAP_BUILD_TARGETS lld"
fi
(cd clang_build && ninja $BOOTSTRAP_BUILD_TARGETS) || build_failure

# If we're building with libcxx, install the headers to clang_build/include.
if [ ! -z ${ENABLE_LIBCXX_FLAG} ]; then
(cd clang_build && ninja -C ${LIBCXX} installheaders \
  HEADER_DIR=${PWD}/include) || build_failure
fi

# Check on Linux: build and test sanitizers using gcc as a host
# compiler.
check_in_gcc() {
  CONDITION=$1
  SANITIZER=$2
  if [ "$CONDITION" == "1" ]; then
    echo @@@BUILD_STEP check-$SANITIZER in gcc build@@@
    (cd clang_build && ninja check-$SANITIZER) || build_failure
  fi
}
check_in_gcc 1 sanitizer
check_in_gcc $CHECK_ASAN asan
check_in_gcc $CHECK_HWASAN hwasan
check_in_gcc $CHECK_CFI cfi-and-supported
check_in_gcc $CHECK_DFSAN dfsan
check_in_gcc $CHECK_LSAN lsan
check_in_gcc $CHECK_MSAN msan
check_in_gcc $CHECK_SCUDO_STANDALONE scudo_standalone
LDFLAGS=-no-pie check_in_gcc $CHECK_TSAN tsan
check_in_gcc $CHECK_UBSAN ubsan
check_in_gcc $CHECK_UBSAN ubsan-minimal

### From now on we use just-built Clang as a host compiler ###
CLANG_PATH=${ROOT}/clang_build/bin
# Build self-hosted tree with fresh Clang and -Werror.
CMAKE_CLANG_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON -DCMAKE_C_COMPILER=${CLANG_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_PATH}/clang++ -DCMAKE_C_FLAGS=-gmlt -DCMAKE_CXX_FLAGS=-gmlt"

echo @@@BUILD_STEP bootstrap clang@@@
mkdir -p llvm_build64
(cd llvm_build64 && cmake ${CMAKE_CLANG_OPTIONS} \
                          -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON \
                          ${ENABLE_LIBCXX_FLAG} \
                          $LLVM) || build_failure

# First, build only Clang.
(cd llvm_build64 && ninja clang) || build_failure

# If needed, install the headers to clang_build/include.
if [ ! -z ${ENABLE_LIBCXX_FLAG} ]; then
  (cd llvm_build64 && ninja -C ${LIBCXX} installheaders \
    HEADER_DIR=${PWD}/include) || build_failure
fi

# Now build everything else.
(cd llvm_build64 && ninja) || build_failure
# Symbolizer dependencies.
(cd llvm_build64 && ninja llvm-ar llvm-link llvm-tblgen opt) || build_failure


if [ "$CHECK_CFI" == "1" ]; then
  # FIXME: Make these true dependencies of check-cfi-and-supported when
  # compiler-rt is configured as an external project.
  (cd llvm_build64 && ninja LLVMgold opt sanstats) || build_failure
fi

check_64bit() {
  CONDITION=$1
  SANITIZER=$2
  if [ "$CONDITION" == "1" ]; then
    echo @@@BUILD_STEP 64-bit check-$SANITIZER@@@
    (cd llvm_build64 && ninja check-$SANITIZER) || build_failure
  fi
}

check_64bit 1 sanitizer
check_64bit $CHECK_ASAN asan
check_64bit $CHECK_ASAN asan-dynamic
check_64bit $CHECK_HWASAN hwasan
check_64bit $CHECK_CFI cfi-and-supported
check_64bit $CHECK_DFSAN dfsan
check_64bit $CHECK_LSAN lsan
check_64bit $CHECK_MSAN msan
check_64bit $CHECK_TSAN tsan
check_64bit $CHECK_UBSAN ubsan
check_64bit $CHECK_UBSAN ubsan-minimal

echo @@@BUILD_STEP 64-bit check-compiler-rt@@@
(cd llvm_build64 && ninja check-compiler-rt) || build_failure

FRESH_CLANG_PATH=${ROOT}/llvm_build64/bin

echo @@@BUILD_STEP build standalone compiler-rt@@@
if [ ! -d compiler_rt_build ]; then
  mkdir compiler_rt_build
fi
(cd compiler_rt_build && cmake -GNinja \
  -DCMAKE_C_COMPILER=${FRESH_CLANG_PATH}/clang \
  -DCMAKE_CXX_COMPILER=${FRESH_CLANG_PATH}/clang++ \
  -DCOMPILER_RT_INCLUDE_TESTS=ON \
  -DCOMPILER_RT_ENABLE_WERROR=ON \
  -DLLVM_CMAKE_DIR=${ROOT}/llvm_build64 \
  $COMPILER_RT) || build_failure
(cd compiler_rt_build && ninja) || build_failure

echo @@@BUILD_STEP test standalone compiler-rt@@@
(cd compiler_rt_build && ninja check-all) || build_failure

echo @@@BUILD_STEP build with ninja@@@
if [ ! -d llvm_build_ninja ]; then
  mkdir llvm_build_ninja
fi
CMAKE_NINJA_OPTIONS="${CMAKE_CLANG_OPTIONS} -GNinja"
(cd llvm_build_ninja && cmake \
    ${CMAKE_NINJA_OPTIONS} $LLVM) || build_failure
ln -sf llvm_build_ninja/compile_commands.json $LLVM
(cd llvm_build_ninja && ninja) || build_failure

check_ninja() {
  CONDITION=$1
  SANITIZER=$2
  if [ "$CONDITION" == "1" ]; then
    echo @@@BUILD_STEP ninja check-$SANITIZER@@@
    (cd llvm_build_ninja && ninja check-$SANITIZER) || build_failure
  fi
}

check_ninja 1 sanitizer
check_ninja $CHECK_ASAN asan
check_ninja $CHECK_HWASAN hwasan
check_ninja $CHECK_CFI cfi-and-supported
check_ninja $CHECK_DFSAN dfsan
check_ninja $CHECK_LSAN lsan
check_ninja $CHECK_MSAN msan
check_ninja $CHECK_SCUDO_STANDALONE scudo_standalone
check_ninja $CHECK_TSAN tsan
check_ninja $CHECK_UBSAN ubsan
check_ninja $CHECK_UBSAN ubsan-minimal

echo @@@BUILD_STEP ninja check-compiler-rt@@@
(cd llvm_build_ninja && ninja check-compiler-rt) || true

if [ "$CHECK_SYMBOLIZER" == "1" ]; then
  build_symbolizer() {
    echo @@@BUILD_STEP build $1-bit symbolizer for $2@@@
    if [ ! -d symbolizer_build$1 ]; then
      mkdir symbolizer_build$1
    fi
    (cd symbolizer_build$1 && ZLIB_SRC=$ZLIB FLAGS=-m$1 \
      CLANG=${FRESH_CLANG_PATH}/clang \
      bash -eux $COMPILER_RT/lib/sanitizer_common/symbolizer/scripts/build_symbolizer.sh \
        $(dirname $(find ../$2/ -name libclang_rt.*.a | head -n1)) || build_failure)
  }

  echo @@@BUILD_STEP update zlib@@@
  (cd $ZLIB && git pull --rebase) || \
      git clone https://github.com/madler/zlib.git $ZLIB || build_failure

  build_symbolizer 32 llvm_build_ninja
  build_symbolizer 64 llvm_build_ninja

  check_ninja_with_symbolizer() {
    CONDITION=$1
    SANITIZER=$2
    if [ "$CONDITION" == "1" ]; then
      echo @@@BUILD_STEP ninja check-$SANITIZER with internal symbolizer@@@
      (cd llvm_build_ninja && ninja check-$SANITIZER) || build_failure
    fi
  }

  # TODO: Replace LIT_FILTER_OUT with lit features.
  LIT_FILTER_OUT=":: (max_allocation_size.cpp|Linux/soft_rss_limit_mb_test.cpp)$" check_ninja_with_symbolizer 1 sanitizer
  LIT_FILTER_OUT=":: TestCases/Linux/check_memcpy.c$" check_ninja_with_symbolizer $CHECK_ASAN asan
  # check_ninja_with_symbolizer $CHECK_HWASAN hwasan
  # check_ninja_with_symbolizer $CHECK_CFI cfi-and-supported
  check_ninja_with_symbolizer $CHECK_DFSAN dfsan
  LIT_FILTER_OUT=":: TestCases/(realloc_too_big.c|recoverable_leak_check.cpp|suppressions_file.cpp)$" check_ninja_with_symbolizer $CHECK_LSAN lsan
  LIT_FILTER_OUT=":: Linux/check_memcpy.c$" check_ninja_with_symbolizer $CHECK_MSAN msan
  check_ninja_with_symbolizer $CHECK_SCUDO_STANDALONE scudo_standalone
  LIT_FILTER_OUT=":: Linux/check_memcpy.c$" check_ninja_with_symbolizer $CHECK_TSAN tsan
  LIT_FILTER_OUT=":: TestCases/TypeCheck/(vptr-virtual-base.cpp|vptr.cpp)$" check_ninja_with_symbolizer $CHECK_UBSAN ubsan
fi

cleanup
