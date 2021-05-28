#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

ROOT=`pwd`
PLATFORM=`uname`
export PATH="/usr/local/bin:$PATH"

LLVM=$ROOT/llvm
CMAKE_COMMON_OPTIONS="-GNinja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=OFF"
CLOBBER="qemu qemu_build"

clobber

buildbot_update

build_stage1_clang

COMPILER_BIN_DIR=$(readlink -f ${STAGE1_DIR})/bin

function build_qemu {
  echo "@@@BUILD_STEP build qemu@@@"
  (
    local qemu_url=https://github.com/vitalybuka/qemu.git
    cd $ROOT
    [[ -d qemu ]] || git clone $qemu_url || exit 1
    cd $ROOT/qemu
    git remote set-url origin $qemu_url
    git fetch origin
    [[ "$(git rev-parse HEAD)" == "$(git rev-parse $1)" ]] && $ROOT/qemu_build/qemu-x86_64 --version && exit 0

    rm -rf $ROOT/qemu_build &&
    mkdir -p $ROOT/qemu_build &&
    git reset --hard $1 &&
    git submodule update --init --recursive &&
    cd $ROOT/qemu_build &&
    ../qemu/configure --disable-system --enable-linux-user --static &&
    ninja &&
    $ROOT/qemu_build/qemu-x86_64 --version
  ) || (
    echo "@@@STEP_EXCEPTION@@@"
    exit 2
  )
}

build_qemu origin/sanitizer_bot

BUILDS=

function configure_compiler_rt {
  local arch=$1
  local target="${arch}-linux-gnu${2:-}"

  local name=""
  if [[ "$DBG" == "ON" ]] ; then
    name=debug_
  fi
  name+="${arch}"
  
  local qemu_cmd=""
  if [[ "${QEMU:-}" != "0" ]] ; then
    name+="_qemu"
    local qemu_arch=${arch}
    [[ "${arch}" == "powerpc64le" ]] && qemu_arch="ppc64le"
    qemu_cmd="$ROOT/qemu_build/qemu-${qemu_arch} -L /usr/${target}"
    if [[ ! -z "${QEMU_CPU:-}" ]] ; then
      qemu_cmd+=" -cpu ${QEMU_CPU}"
      name+="_${QEMU_CPU}"
    fi
  fi

  local out_dir=llvm_build2_${name}
  rm -rf ${out_dir}
  mkdir -p ${out_dir}

  BUILDS+=" ${name}"

  (
    cd ${out_dir}

    LINKER_FLAGS=${LINKER_FLAGS:-}

    (
      cmake \
        ${CMAKE_COMMON_OPTIONS} \
        -DCOMPILER_RT_DEBUG=$DBG \
        -DLLVM_CONFIG_PATH=${COMPILER_BIN_DIR}/llvm-config \
        -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
        -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++ \
        -DCOMPILER_RT_HAS_LLD=ON \
        -DCOMPILER_RT_TEST_USE_LLD=ON \
        -DCMAKE_INSTALL_PREFIX=$(${COMPILER_BIN_DIR}/clang -print-resource-dir) \
        -DLLVM_LIT_ARGS="-v --time-tests" \
        -DCOMPILER_RT_BUILD_BUILTINS=OFF \
        -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON \
        -DCMAKE_CROSSCOMPILING=True \
        -DCOMPILER_RT_INCLUDE_TESTS=ON \
        -DCOMPILER_RT_BUILD_LIBFUZZER=OFF \
        -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        -DCMAKE_CXX_FLAGS=-fPIC \
        -DCMAKE_C_FLAGS=-fPIC \
        -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=lld ${LINKER_FLAGS}" \
        -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld \
        -DCOMPILER_RT_TEST_COMPILER_CFLAGS="--target=${target} ${LINKER_FLAGS}" \
        -DCMAKE_C_COMPILER_TARGET=${target} \
        -DCMAKE_CXX_COMPILER_TARGET=${target} \
        -DCOMPILER_RT_EMULATOR="${qemu_cmd:-}" \
        $LLVM/../compiler-rt
     ) >& configure.log
  ) &
}

function run_tests {
  local name="${1}"
  local out_dir=llvm_build2_${name}

  echo "@@@BUILD_STEP scudo $name@@@"

  (
    cd ${out_dir}

    cat configure.log

    # Copy into clang resource dir to make -fsanitize= work in lit tests.
    ninja install-scudo_standalone

    ninja check-scudo_standalone || exit 3
  ) || echo "@@@STEP_FAILURE@@@"
}

echo "@@@BUILD_STEP configure@@@"

for DBG in OFF ON ; do
  QEMU=0 configure_compiler_rt x86_64
  configure_compiler_rt x86_64
  configure_compiler_rt arm eabihf
  configure_compiler_rt aarch64
  QEMU_CPU="cortex-a72" configure_compiler_rt aarch64
  (
    LINKER_FLAGS="-latomic -Wl,-z,notext -Wno-unused-command-line-argument"
    configure_compiler_rt mips
    configure_compiler_rt mipsel
    configure_compiler_rt mips64 abi64
    configure_compiler_rt mips64el abi64
  )
  
  configure_compiler_rt powerpc64le
done

wait

for B in $BUILDS ; do
  run_tests $B
done 

