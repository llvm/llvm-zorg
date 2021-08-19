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

clobber

buildbot_update

build_stage1_clang

COMPILER_BIN_DIR=$(readlink -f ${STAGE1_DIR})/bin

function git_clone_at_revision {
  local src_dir_name="${1}"
  local git_url="${2}"
  local revision="${3}"
  local build_dir="${4}"
  (
    cd ${ROOT}
    [[ -d ${src_dir_name} ]] || git clone ${git_url} ${src_dir_name} || exit 1
    cd ${ROOT}/${src_dir_name}
    git remote set-url origin ${git_url}
    git fetch origin

    # Short circuit if we already have a build at the correct revision.
    [[ "$(git rev-parse HEAD)" == "$(git rev-parse ${revision})" ]] && exit 0

    # Delete the build dir to ensure a rebuild happens at the new revision.
    rm -rf ${build_dir}

    git reset --hard ${revision}
    git submodule update --init --recursive
  )
}

function build_qemu {
  local qemu_name="${1}"
  local qemu_url="${2}"
  local qemu_revision="${3}"

  local build_dir="${ROOT}/${qemu_name}_build"

  echo "@@@BUILD_STEP build ${qemu_name}@@@"
  (
    git_clone_at_revision ${qemu_name} ${qemu_url} ${qemu_revision} \
      ${build_dir} || exit 1

    ${build_dir}/qemu-x86_64 --version &&
      ${build_dir}/qemu-system-x86_64 --version &&
      ${build_dir}/qemu-img --version &&
      exit 0

    rm -rf ${build_dir} &&
    mkdir -p ${build_dir} &&
    cd ${build_dir} &&
    ${ROOT}/${qemu_name}/configure --enable-linux-user &&
    ninja &&
    ${build_dir}/qemu-x86_64 --version &&
    ${build_dir}/qemu-system-x86_64 --version &&
    ${build_dir}/qemu-img --version
  ) || (
    echo "@@@STEP_EXCEPTION@@@"
    exit 2
  )
}

SCUDO_BUILDS=

function configure_scudo_compiler_rt {
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

  local linker_flags=
  [[ "${arch}" =~ "mips*" ]] && linker_flags="-latomic -Wl,-z,notext -Wno-unused-command-line-argument"

  local out_dir=llvm_build2_${name}
  rm -rf ${out_dir}
  mkdir -p ${out_dir}

  SCUDO_BUILDS+=" ${name}"

  (
    cd ${out_dir}

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
        -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=lld ${linker_flags}" \
        -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=lld ${linker_flags}" \
        -DCOMPILER_RT_TEST_COMPILER_CFLAGS="--target=${target} ${linker_flags}" \
        -DCMAKE_C_COMPILER_TARGET=${target} \
        -DCMAKE_CXX_COMPILER_TARGET=${target} \
        -DCOMPILER_RT_EMULATOR="${qemu_cmd:-}" \
        $LLVM/../compiler-rt
     ) >& configure.log
  ) &
}

readonly LLVM_SYMBOLIZER_DIR="${ROOT}/llvm_build2_x86_64_symbolizer"

function configure_llvm_symbolizer {
  rm -rf ${LLVM_SYMBOLIZER_DIR}
  mkdir -p ${LLVM_SYMBOLIZER_DIR}

  (
    cd ${LLVM_SYMBOLIZER_DIR}

    (
      cmake \
        ${CMAKE_COMMON_OPTIONS} \
        -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
        -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++ \
        -DLLVM_BUILD_RUNTIME=OFF \
        -DLLVM_STATIC_LINK_CXX_STDLIB=ON \
        $LLVM
     ) >& configure.log
  ) &
}

function run_scudo_tests {
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

function build_llvm_symbolizer {
  echo "@@@BUILD_STEP llvm-symbolizer x86_64@@@"

  (
    cd ${LLVM_SYMBOLIZER_DIR}

    cat configure.log

    ninja llvm-symbolizer || exit 3
  ) || echo "@@@STEP_FAILURE@@@"
}

echo "@@@BUILD_STEP configure@@@"

for DBG in OFF ON ; do
  QEMU=0 configure_scudo_compiler_rt x86_64
  configure_scudo_compiler_rt x86_64
  configure_scudo_compiler_rt arm eabihf
  configure_scudo_compiler_rt aarch64
  QEMU_CPU="cortex-a72" configure_scudo_compiler_rt aarch64
  #configure_scudo_compiler_rt mips
  #configure_scudo_compiler_rt mipsel
  configure_scudo_compiler_rt mips64 abi64
  configure_scudo_compiler_rt mips64el abi64
  configure_scudo_compiler_rt powerpc64le
done
configure_llvm_symbolizer

wait

for B in $SCUDO_BUILDS ; do
  run_scudo_tests $B
done

set +x # Avoid echoing STEP_FAILURE because of the command trace.
MISSING_QEMU_IMAGE_MESSAGE=$(cat << 'EOF'
=====================================================================
Looks like you're missing the QEMU system images for x86_64 LAM
HWASan testing. These system images aren't automatically generated
as part of the buildbot script because they require root (sorry!).

If you have the system images already built, you can run
buildbot_qemu.sh with QEMU_IMAGE_DIR=path/to/qemu/images. Otherwise,
you can build the images (only necessary once-per-clobber) by:
 1. WARNING: Read the script at https://github.com/google/sanitizers/blob/master/hwaddress-sanitizer/create_qemu_image.sh
    You're running this as ROOT, so make sure you're comfortable with
    that.
 2. In your terminal, run:
      $ sudo su -c "bash <(wget -qO- https://raw.githubusercontent.com/google/sanitizers/master/hwaddress-sanitizer/create_qemu_image.sh)" root && \
        sudo chown $(whoami) debian.*

You can also choose to skip the x86_64 HWASan LAM testing by supplying
SKIP_HWASAN_LAM=true in your invocation of this script.
=====================================================================
@@@STEP_EXCEPTION@@@
EOF
)
set -x

SKIP_HWASAN_LAM=${SKIP_HWASAN_LAM:-}

function setup_lam_qemu_image {
  # Full system emulation is required for x86_64 testing with LAM, as some
  # sanitizers aren't friendly with usermode emulation under x86_64 LAM.
  echo @@@BUILD_STEP Check x86_64 LAM Prerequisites@@@

  # Allow specifying the QEMU image dir, otherwise assume in the local dir.
  QEMU_IMAGE_DIR=${QEMU_IMAGE_DIR:=${ROOT}}

  # Ensure the buildbot start script created a QEMU image for us.
  (
    ls ${QEMU_IMAGE_DIR}/debian.img
    ls ${QEMU_IMAGE_DIR}/debian.id_rsa
  ) ||
  (
    # Make the "missing file" error clearer by not effectively echoing twice.
    set +x
    echo "$MISSING_QEMU_IMAGE_MESSAGE"
    exit 1
  )
}

function build_lam_linux {
  local build_dir="${ROOT}/lam_linux_build"

  echo "@@@BUILD_STEP build lam linux@@@"
  (
    git_clone_at_revision lam_linux https://github.com/morehouse/linux.git \
      origin/lam ${build_dir} || exit 1

    ls ${build_dir}/arch/x86_64/boot/bzImage && exit 0

    rm -rf ${build_dir} &&
    mkdir -p ${build_dir} &&
    cd ${ROOT}/lam_linux &&
    make O=${build_dir} LD=ld.bfd defconfig &&
    make O=${build_dir} LD=ld.bfd -j $(nproc) &&
    ls ${build_dir}/arch/x86_64/boot/bzImage
  ) || (
    echo "@@@STEP_EXCEPTION@@@"
    exit 2
  )
}

function configure_hwasan_lam {
  echo "@@@BUILD_STEP configure hwasan@@@"

  git_clone_at_revision sanitizers https://github.com/google/sanitizers.git \
    origin/master ""
  local script="${ROOT}/sanitizers/hwaddress-sanitizer/run_in_qemu_with_lam.sh"
  ls ${script}

  local out_dir=llvm_build2_x86_64_lam_qemu
  rm -rf ${out_dir}
  mkdir -p ${out_dir}

  (
    cd ${out_dir}
    cmake \
      ${CMAKE_COMMON_OPTIONS} \
      -DLLVM_ENABLE_PROJECTS="clang;compiler-rt;lld;libcxx;libcxxabi" \
      -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
      -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++ \
      -DLLVM_ENABLE_LLD=ON \
      -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
      -DLLVM_LIT_ARGS="-v --time-tests" \
      -DCOMPILER_RT_EMULATOR="env ROOT=${ROOT} QEMU_IMAGE_DIR=${QEMU_IMAGE_DIR} ${script}" \
      $LLVM
  ) || echo "@@@STEP_FAILURE@@@"
}

function run_hwasan_lam_tests {
  local name="x86_64_lam_qemu"
  local out_dir=llvm_build2_${name}

  echo "@@@BUILD_STEP hwasan ${name}@@@"

  (
    cd ${out_dir}

    # LLD must be built first since HWASan tests use -fuse-ld=lld and the
    # buildbots don't have LLD preinstalled.
    ninja lld || exit 3

    ninja check-hwasan-lam || exit 3
  ) || echo "@@@STEP_FAILURE@@@"
}

([[ -z "$SKIP_HWASAN_LAM" ]] && setup_lam_qemu_image) || SKIP_HWASAN_LAM=1

build_qemu qemu https://github.com/vitalybuka/qemu.git origin/sanitizer_bot
[[ -z "$SKIP_HWASAN_LAM" ]] && (
  build_qemu lam_qemu https://github.com/morehouse/qemu.git origin/lam
  build_lam_linux
  configure_hwasan_lam
  build_llvm_symbolizer
  run_hwasan_lam_tests
)

cleanup $STAGE1_DIR
