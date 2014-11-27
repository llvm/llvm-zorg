#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

if [ "$BUILDBOT_CLOBBER" != "" ]; then
  echo @@@BUILD_STEP clobber@@@
  rm -rf llvm
  rm -rf llvm_build0
fi

MEMORY_SANITIZER_KIND="Memory"
BUILDBOT_MSAN_ORIGINS=${BUILDBOT_MSAN_ORIGINS:-}
if [ "$BUILDBOT_MSAN_ORIGINS" != "" ]; then
    MEMORY_SANITIZER_KIND="MemoryWithOrigins"
fi

# CMake does not notice that the compiler itself has changed.
# Anyway, incremental builds of stage2 and stage3 compilers don't make sense.
# Clobber the build trees.
rm -rf libcxx_build_msan
rm -rf llvm_build_msan
rm -rf llvm_build2_msan
rm -rf llvm_build_asan
rm -rf llvm_build2_asan
rm -rf llvm_build_ubsan

MAKE_JOBS=${MAX_MAKE_JOBS:-16}
LLVM=$ROOT/llvm

type -a gcc
type -a g++
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_PARALLEL_LINK_JOBS=3"
CMAKE_STAGE1_OPTIONS="${CMAKE_COMMON_OPTIONS}"

echo @@@BUILD_STEP update@@@
buildbot_update

# Stage 1

echo @@@BUILD_STEP build stage1 clang@@@
if [ ! -d llvm_build0 ]; then
  mkdir llvm_build0
fi
# Build cxx/cxxabi to fool the compiler check in MSan stage 2.
(cd llvm_build0 && cmake ${CMAKE_STAGE1_OPTIONS} $LLVM && \
  ninja clang compiler-rt llvm-symbolizer) || \
  echo @@@STEP_FAILURE@@@

CLANG_PATH=$ROOT/llvm_build0/bin
CMAKE_STAGE2_COMMON_OPTIONS="\
  ${CMAKE_COMMON_OPTIONS} \
  -DCMAKE_C_COMPILER=${CLANG_PATH}/clang \
  -DCMAKE_CXX_COMPILER=${CLANG_PATH}/clang++ \
  "
LLVM_SYMBOLIZER_PATH=${CLANG_PATH}/llvm-symbolizer
export ASAN_SYMBOLIZER_PATH=${LLVM_SYMBOLIZER_PATH}
export MSAN_SYMBOLIZER_PATH=${LLVM_SYMBOLIZER_PATH}

# Stage 2 / Memory Sanitizer

echo @@@BUILD_STEP build libcxx/msan@@@
if [ ! -d libcxx_build_msan ]; then
  mkdir libcxx_build_msan
fi

(cd libcxx_build_msan && \
  cmake \
    ${CMAKE_STAGE2_COMMON_OPTIONS} \
    -DLLVM_USE_SANITIZER=${MEMORY_SANITIZER_KIND} \
    $LLVM && \
  ninja cxx cxxabi) || echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP build clang/msan@@@
if [ ! -d llvm_build_msan ]; then
  mkdir llvm_build_msan
fi

MSAN_LDFLAGS="-lc++abi -Wl,--rpath=${ROOT}/libcxx_build_msan/lib -L${ROOT}/libcxx_build_msan/lib"
# See http://llvm.org/bugs/show_bug.cgi?id=19071, http://www.cmake.org/Bug/view.php?id=15264
CMAKE_BUG_WORKAROUND_CFLAGS="$MSAN_LDFLAGS -fsanitize=memory -w"
MSAN_CFLAGS="-I${ROOT}/libcxx_build_msan/include -I${ROOT}/libcxx_build_msan/include/c++/v1 $CMAKE_BUG_WORKAROUND_CFLAGS"

(cd llvm_build_msan && \
 cmake ${CMAKE_STAGE2_COMMON_OPTIONS} \
   -DLLVM_USE_SANITIZER=${MEMORY_SANITIZER_KIND} \
   -DLLVM_ENABLE_LIBCXX=ON \
   -DCMAKE_C_FLAGS="${MSAN_CFLAGS}" \
   -DCMAKE_CXX_FLAGS="${MSAN_CFLAGS}" \
   -DCMAKE_EXE_LINKER_FLAGS="${MSAN_LDFLAGS}" \
   $LLVM && \
 ninja clang) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP check-llvm msan@@@

(cd llvm_build_msan && ninja check-llvm) || echo @@@STEP_WARNINGS@@@

echo @@@BUILD_STEP check-clang msan@@@

(cd llvm_build_msan && ninja check-clang) || echo @@@STEP_FAILURE@@@


# Stage 3 / MemorySanitizer

echo @@@BUILD_STEP build stage3/msan clang@@@

if [ ! -d llvm_build2_msan ]; then
  mkdir llvm_build2_msan
fi

CLANG_MSAN_PATH=$ROOT/llvm_build_msan/bin
CMAKE_STAGE3_MSAN_OPTIONS="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${CLANG_MSAN_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_MSAN_PATH}/clang++ -DLLVM_PARALLEL_COMPILE_JOBS=15"

(cd llvm_build2_msan && cmake ${CMAKE_STAGE3_MSAN_OPTIONS} $LLVM && ninja) || \
  echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-all stage3/msan@@@

(cd llvm_build2_msan && ninja check-all) || echo @@@STEP_FAILURE@@@


# Stage 2 / AddressSanitizer

echo @@@BUILD_STEP build clang/asan@@@

# Turn on init-order checker as ASan runtime option.
export ASAN_OPTIONS="check_initialization_order=true:detect_stack_use_after_return=1:detect_leaks=1"
CMAKE_ASAN_OPTIONS=" \
  ${CMAKE_STAGE2_COMMON_OPTIONS} \
  -DLLVM_USE_SANITIZER=Address \
  "

if [ ! -d llvm_build_asan ]; then
  mkdir llvm_build_asan
fi

(cd llvm_build_asan && \
 cmake ${CMAKE_ASAN_OPTIONS} $LLVM && \
 ninja clang) || echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-llvm asan@@@

(cd llvm_build_asan && ninja check-llvm) || echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-clang asan@@@

(cd llvm_build_asan && ninja check-clang) || echo @@@STEP_FAILURE@@@


# Stage 3 / AddressSanitizer

echo @@@BUILD_STEP build stage3/asan clang@@@

if [ ! -d llvm_build2_asan ]; then
  mkdir llvm_build2_asan
fi

CLANG_ASAN_PATH=$ROOT/llvm_build_asan/bin
CMAKE_STAGE3_ASAN_OPTIONS="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${CLANG_ASAN_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_ASAN_PATH}/clang++ -DLLVM_PARALLEL_COMPILE_JOBS=10"

(cd llvm_build2_asan && cmake ${CMAKE_STAGE3_ASAN_OPTIONS} $LLVM && ninja) || \
  echo @@@STEP_FAILURE@@@


echo @@@BUILD_STEP check-all stage3/asan@@@

export ASAN_OPTIONS="check_initialization_order=true:detect_leaks=1"

(cd llvm_build2_asan && ninja check-all) || echo @@@STEP_FAILURE@@@

# Stage 2 / UndefinedBehaviorSanitizer
echo @@@BUILD_STEP build clang/ubsan@@@

export UBSAN_OPTIONS="external_symbolizer_path=${LLVM_SYMBOLIZER_PATH}:print_stacktrace=1"
CMAKE_UBSAN_OPTIONS=" \
  ${CMAKE_STAGE2_COMMON_OPTIONS} \
  -DCMAKE_BUILD_TYPE=Debug \
  -DLLVM_USE_SANITIZER=Undefined \
  "

if [ ! -d llvm_build_ubsan ]; then
  mkdir llvm_build_ubsan
fi

(cd llvm_build_ubsan &&
  cmake ${CMAKE_UBSAN_OPTIONS} $LLVM && \
  ninja clang) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP check-llvm ubsan@@@
(cd llvm_build_ubsan && ninja check-llvm) || echo @@@STEP_FAILURE@@@

echo @@@BUILD_STEP check-clang ubsan@@@
(cd llvm_build_ubsan && ninja check-clang) || echo @@@STEP_FAILURE@@@
