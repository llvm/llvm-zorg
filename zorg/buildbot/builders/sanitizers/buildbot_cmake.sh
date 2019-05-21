#!/usr/bin/env bash

set -x
set -e
set -u

# dump buildbot env
env

HERE="$(dirname $0)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
ARCH=`uname -m`
export PATH="/usr/local/bin:$PATH"
export ANDROID_SDK_HOME=$ROOT/../../..

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm zlib clang_build
fi

# Always clobber bootstrap build trees.
rm -rf compiler_rt_build llvm_build64 llvm_build_ninja symbolizer_build*

SUPPORTS_32_BITS=${SUPPORTS_32_BITS:-1}
MAKE_JOBS=${MAX_MAKE_JOBS:-$(nproc)}
LLVM=$ROOT/llvm
ZLIB=$ROOT/zlib
COMPILER_RT=$LLVM/projects/compiler-rt
CMAKE_COMMON_OPTIONS="-DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=10"
ENABLE_LIBCXX_FLAG=
if [ "$PLATFORM" == "Darwin" ]; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DPYTHON_EXECUTABLE=/usr/bin/python"
  ENABLE_LIBCXX_FLAG="-DLLVM_ENABLE_LIBCXX=ON"
fi

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_BINUTILS_INCDIR=/usr/include"
fi

CHECK_LIBCXX=${CHECK_LIBCXX:-1}
CHECK_SYMBOLIZER=${CHECK_SYMBOLIZER:-$CHECK_LIBCXX}
CHECK_LLD=${CHECK_LLD:-1}
CHECK_ASAN=0
CHECK_HWASAN=0
CHECK_UBSAN=0
CHECK_MSAN=0
CHECK_TSAN=0
CHECK_LSAN=0
CHECK_DFSAN=0
CHECK_SCUDO=0
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
    CHECK_SCUDO=1
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
    CHECK_SCUDO=1
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
    CHECK_SCUDO=1
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

if [[ "$CHECK_CFI" == "1" ]]; then
  # We need this after https://reviews.llvm.org/D62050
  CMAKE_COMMON_OPTIONS="$CMAKE_COMMON_OPTIONS -DLLVM_BUILD_LLVM_DYLIB=ON"
fi

echo @@@BUILD_STEP update@@@
buildbot_update

echo @@@BUILD_STEP lint@@@
CHECK_LINT=${COMPILER_RT}/lib/sanitizer_common/scripts/check_lint.sh
(LLVM=${LLVM} ${CHECK_LINT}) || echo @@@STEP_WARNINGS@@@

# Use both gcc and just-built Clang as a host compiler for sanitizer tests.
# Assume that self-hosted build tree should compile with -Werror.
echo @@@BUILD_STEP build fresh clang@@@
if [ ! -d clang_build ]; then
  mkdir clang_build
fi
(cd clang_build && cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ${CMAKE_COMMON_OPTIONS} $LLVM)
(cd clang_build && make clang -j$MAKE_JOBS) || (echo @@@STEP_FAILURE@@@ ; exit 1)

# If we're building with libcxx, install the headers to clang_build/include.
if [ ! -z ${ENABLE_LIBCXX_FLAG} ]; then
(cd clang_build && make -C ${LLVM}/projects/libcxx installheaders \
  HEADER_DIR=${PWD}/include) || echo @@@STEP_FAILURE@@@
fi

# Do a sanity check on Linux: build and test sanitizers using gcc as a host
# compiler.
if [ "$PLATFORM" == "Linux" ]; then
  check_in_gcc() {
    CONDITION=$1
    SANITIZER=$2
    if [ "$CONDITION" == "1" ]; then
      echo @@@BUILD_STEP check-$SANITIZER in gcc build@@@
      (cd clang_build && make -j$MAKE_JOBS check-$SANITIZER) || echo @@@STEP_FAILURE@@@
    fi
  }
  check_in_gcc 1 sanitizer
  check_in_gcc $CHECK_ASAN asan
  check_in_gcc $CHECK_HWASAN hwasan
  check_in_gcc $CHECK_CFI cfi-and-supported
  check_in_gcc $CHECK_DFSAN dfsan
  check_in_gcc $CHECK_LSAN lsan
  check_in_gcc $CHECK_MSAN msan
  check_in_gcc $CHECK_SCUDO scudo
  check_in_gcc $CHECK_SCUDO_STANDALONE scudo_standalone
  LDFLAGS=-no-pie check_in_gcc $CHECK_TSAN tsan
  check_in_gcc $CHECK_UBSAN ubsan
  check_in_gcc $CHECK_UBSAN ubsan-minimal
fi

### From now on we use just-built Clang as a host compiler ###
CLANG_PATH=${ROOT}/clang_build/bin
# Build self-hosted tree with fresh Clang and -Werror.
CMAKE_CLANG_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON -DCMAKE_C_COMPILER=${CLANG_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_PATH}/clang++ -DCMAKE_C_FLAGS=-gmlt -DCMAKE_CXX_FLAGS=-gmlt"
BUILD_TYPE=Release

echo @@@BUILD_STEP bootstrap clang@@@
if [ ! -d llvm_build64 ]; then
  mkdir llvm_build64
fi
(cd llvm_build64 && cmake -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
    ${CMAKE_CLANG_OPTIONS} -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON \
    ${ENABLE_LIBCXX_FLAG} $LLVM)

# First, build only Clang.
(cd llvm_build64 && make -j$MAKE_JOBS clang) || echo @@@STEP_FAILURE@@@

# If needed, install the headers to clang_build/include.
if [ ! -z ${ENABLE_LIBCXX_FLAG} ]; then
(cd llvm_build64 && make -C ${LLVM}/projects/libcxx installheaders \
  HEADER_DIR=${PWD}/include) || echo @@@STEP_FAILURE@@@
fi

# Now build everything else.
(cd llvm_build64 && make -j$MAKE_JOBS) || echo @@@STEP_FAILURE@@@
# Symbolizer dependencies.
(cd llvm_build64 && make -j$MAKE_JOBS llvm-ar llvm-link llvm-tblgen opt) || echo @@@STEP_FAILURE@@@


if [ "$CHECK_CFI" == "1" ]; then
  # FIXME: Make these true dependencies of check-cfi-and-supported when
  # compiler-rt is configured as an external project.
  (cd llvm_build64 && make -j$MAKE_JOBS LLVMgold opt sanstats) || echo @@@STEP_FAILURE@@@
fi

check_64bit() {
  CONDITION=$1
  SANITIZER=$2
  if [ "$CONDITION" == "1" ]; then
    echo @@@BUILD_STEP 64-bit check-$SANITIZER@@@
    (cd llvm_build64 && make -j$MAKE_JOBS check-$SANITIZER) || echo @@@STEP_FAILURE@@@
  fi
}

check_64bit 1 sanitizer
check_64bit $CHECK_ASAN asan
if [ "$PLATFORM" == "Linux" ]; then
  check_64bit $CHECK_ASAN asan-dynamic
  check_64bit $CHECK_HWASAN hwasan
  check_64bit $CHECK_CFI cfi-and-supported
  check_64bit $CHECK_DFSAN dfsan
  check_64bit $CHECK_LSAN lsan
  check_64bit $CHECK_MSAN msan
  # check_64bit $CHECK_SCUDO scudo, No check-scudo target for this config
  check_64bit $CHECK_TSAN tsan
  check_64bit $CHECK_UBSAN ubsan
  check_64bit $CHECK_UBSAN ubsan-minimal
fi

FRESH_CLANG_PATH=${ROOT}/llvm_build64/bin

echo @@@BUILD_STEP build standalone compiler-rt@@@
if [ ! -d compiler_rt_build ]; then
  mkdir compiler_rt_build
fi
(cd compiler_rt_build && cmake -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
  -DCMAKE_C_COMPILER=${FRESH_CLANG_PATH}/clang \
  -DCMAKE_CXX_COMPILER=${FRESH_CLANG_PATH}/clang++ \
  -DCOMPILER_RT_INCLUDE_TESTS=ON \
  -DCOMPILER_RT_ENABLE_WERROR=ON \
  -DLLVM_CONFIG_PATH=${FRESH_CLANG_PATH}/llvm-config \
  $COMPILER_RT)
(cd compiler_rt_build && make -j$MAKE_JOBS) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP test standalone compiler-rt@@@
(cd compiler_rt_build && make -j$MAKE_JOBS check-all) || echo @@@STEP_FAILURE@@@

build_symbolizer() {
  echo @@@BUILD_STEP build $1-bit symbolizer for $2@@@
  if [ ! -d symbolizer_build$1 ]; then
    mkdir symbolizer_build$1
  fi
  (cd symbolizer_build$1 && ZLIB_SRC=$ZLIB FLAGS=-m$1 \
    CLANG=${FRESH_CLANG_PATH}/clang \
    bash -eux $COMPILER_RT/lib/sanitizer_common/symbolizer/scripts/build_symbolizer.sh \
      $(dirname $(find ../$2/ -name libclang_rt.*.a | head -n1)) || echo @@@STEP_FAILURE@@@)
}

if [ "$CHECK_SYMBOLIZER" == "1" ]; then
  echo @@@BUILD_STEP update zlib@@@
  (cd $ZLIB && git pull --rebase) || \
      git clone https://github.com/madler/zlib.git $ZLIB || echo @@@STEP_FAILURE@@@

  build_symbolizer 32 compiler_rt_build
  build_symbolizer 64 compiler_rt_build

  echo @@@BUILD_STEP test standalone compiler-rt with symbolizer@@@
  (cd compiler_rt_build && make -j$MAKE_JOBS check-all) || echo @@@STEP_FAILURE@@@
fi

HAVE_NINJA=${HAVE_NINJA:-1}
if [ "$PLATFORM" == "Linux" -a $HAVE_NINJA == 1 ]; then
  echo @@@BUILD_STEP build with ninja@@@
  if [ ! -d llvm_build_ninja ]; then
    mkdir llvm_build_ninja
  fi
  CMAKE_NINJA_OPTIONS="${CMAKE_CLANG_OPTIONS} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -G Ninja"
  (cd llvm_build_ninja && cmake -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
      ${CMAKE_NINJA_OPTIONS} $LLVM)
  ln -sf llvm_build_ninja/compile_commands.json $LLVM
  (cd llvm_build_ninja && ninja) || echo @@@STEP_FAILURE@@@

  check_ninja() {
    CONDITION=$1
    SANITIZER=$2
    if [ "$CONDITION" == "1" ]; then
      echo @@@BUILD_STEP ninja check-$SANITIZER@@@
      (cd llvm_build_ninja && ninja check-$SANITIZER) || echo @@@STEP_FAILURE@@@
    fi
  }

  check_ninja 1 sanitizer
  check_ninja $CHECK_ASAN asan
  check_ninja $CHECK_HWASAN hwasan
  check_ninja $CHECK_CFI cfi-and-supported
  check_ninja $CHECK_DFSAN dfsan
  check_ninja $CHECK_LSAN lsan
  check_ninja $CHECK_MSAN msan
  check_ninja $CHECK_SCUDO scudo
  check_ninja $CHECK_SCUDO_STANDALONE scudo_standalone
  check_ninja $CHECK_TSAN tsan
  check_ninja $CHECK_UBSAN ubsan
  check_ninja $CHECK_UBSAN ubsan-minimal

  if [ "$CHECK_SYMBOLIZER" == "1" ]; then
    build_symbolizer 32 llvm_build_ninja
    build_symbolizer 64 llvm_build_ninja

    check_ninja_with_symbolizer() {
      CONDITION=$1
      SANITIZER=$2
      # Disabled, tests are not working yet.
      if [ "$CONDITION" == "-1" ]; then
        echo @@@BUILD_STEP ninja check-$SANITIZER with symbolizer@@@
        (cd llvm_build_ninja && ninja check-$SANITIZER) || echo @@@STEP_FAILURE@@@
      fi
    }

    check_ninja_with_symbolizer 1 sanitizer
    check_ninja_with_symbolizer $CHECK_ASAN asan
    check_ninja_with_symbolizer $CHECK_HWASAN hwasan
    check_ninja_with_symbolizer $CHECK_CFI cfi-and-supported
    check_ninja_with_symbolizer $CHECK_DFSAN dfsan
    check_ninja_with_symbolizer $CHECK_LSAN lsan
    check_ninja_with_symbolizer $CHECK_MSAN msan
    check_ninja_with_symbolizer $CHECK_SCUDO scudo
    check_ninja_with_symbolizer $CHECK_SCUDO_STANDALONE scudo_standalone
    check_ninja_with_symbolizer $CHECK_TSAN tsan
    check_ninja_with_symbolizer $CHECK_UBSAN ubsan
  fi
fi
