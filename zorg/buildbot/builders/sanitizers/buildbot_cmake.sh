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

if [ -e /usr/include/plugin-api.h ]; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_BINUTILS_INCDIR=/usr/include"
fi

CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_PROJECTS='clang;compiler-rt'"

# FIXME: Something broken with LLD switch 19cb7a33e82.
CHECK_SYMBOLIZER=0
case "$ARCH" in
  ppc64*)
    CHECK_SYMBOLIZER=0
    CMAKE_COMMON_OPTIONS+=" -DLLVM_TARGETS_TO_BUILD=PowerPC"
    if [[ "$ARCH" == "ppc64le" ]]; then
      CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-vj256"
    else
      CMAKE_COMMON_OPTIONS+=" -DLLVM_LIT_ARGS=-vj80"
    fi
  ;;
esac

PROJECTS="clang;compiler-rt;lld"
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_PROJECTS='${PROJECTS}' -DLLVM_ENABLE_RUNTIMES=libcxx;libcxxabi"
CMAKE_COMMON_OPTIONS+=" -DLLVM_BUILD_LLVM_DYLIB=ON"

buildbot_update

COMPILER_RT=$LLVM/../compiler-rt
LIBCXX=$LLVM/../libcxx

# Use both gcc and just-built Clang/LLD as a host compiler/linker for sanitizer
# tests. Assume that self-hosted build tree should compile with -Werror.
echo @@@BUILD_STEP build fresh toolchain@@@
mkdir -p clang_build
(cd clang_build && cmake ${CMAKE_COMMON_OPTIONS} $LLVM ) || (rm -rf clang_build ; build_failure)

(cd clang_build && ninja clang lld) || build_failure

# Check on Linux: build and test sanitizers using gcc as a host
# compiler.
echo @@@BUILD_STEP check-compiler-rt in gcc build@@@
(cd clang_build && ninja check-compiler-rt) || build_failure

### From now on we use just-built Clang as a host compiler ###
CLANG_PATH=${ROOT}/clang_build/bin
# Build self-hosted tree with fresh Clang and -Werror.
CMAKE_CLANG_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON -DCMAKE_C_COMPILER=${CLANG_PATH}/clang -DCMAKE_CXX_COMPILER=${CLANG_PATH}/clang++ -DCMAKE_C_FLAGS=-gmlt -DCMAKE_CXX_FLAGS=-gmlt"

echo @@@BUILD_STEP bootstrap clang@@@
mkdir -p llvm_build64
(cd llvm_build64 && cmake ${CMAKE_CLANG_OPTIONS} \
                          -DLLVM_BUILD_EXTERNAL_COMPILER_RT=ON \
                          $LLVM) || build_failure

# Now build everything else.
(cd llvm_build64 && ninja) || build_failure


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

echo @@@BUILD_STEP ninja check-compiler-rt@@@
(cd llvm_build_ninja && ninja check-compiler-rt) || build_failure

if [ "$CHECK_SYMBOLIZER" == "1" ]; then
  if [ ! -d llvm_build_symbolizer ]; then
     mkdir llvm_build_symbolizer
  fi

  echo @@@BUILD_STEP build with internal symbolizer@@@
  CMAKE_NINJA_OPTIONS+=" -DCOMPILER_RT_ENABLE_INTERNAL_SYMBOLIZER=ON"
  (cd llvm_build_symbolizer && cmake \
      ${CMAKE_NINJA_OPTIONS} $LLVM) || build_failure
  ninja -C llvm_build_symbolizer compiler-rt || build_failure

  echo @@@BUILD_STEP ninja check-compiler-rt with internal symbolizer@@@
  ninja -C llvm_build_symbolizer check-compiler-rt || build_failure
fi

cleanup
