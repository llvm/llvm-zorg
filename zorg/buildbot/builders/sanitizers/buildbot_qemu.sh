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
CMAKE_COMMON_OPTIONS+=" -GNinja -DCMAKE_BUILD_TYPE=Release"

clobber

build_stage1_clang_at_revison
CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_ASSERTIONS=ON"

buildbot_update

readonly STAGE2_DIR=llvm_build2_host
(
  echo @@@BUILD_STEP build host clang@@@
  COMPILER_BIN_DIR="$(readlink -f ${STAGE1_DIR})/bin"
  if ccache -s >/dev/null ; then
    CMAKE_COMMON_OPTIONS+=" -DLLVM_CCACHE_BUILD=ON"
  fi

  rm -rf ${STAGE2_DIR}
  mkdir -p ${STAGE2_DIR}
  cd ${STAGE2_DIR}

  cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DLLVM_ENABLE_PROJECTS="clang;compiler-rt;lld" \
    -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
    -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++ \
    -DLLVM_ENABLE_LLD=ON \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    $LLVM && ninja
) || build_failure

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
  {
    QEMU_IMAGE="${QEMU_IMAGE_DIR}/debian.img"
    QEMU_SSH_KEY="${QEMU_IMAGE_DIR}/debian.id_rsa"
    ls ${QEMU_IMAGE}
    ls ${QEMU_SSH_KEY}
  } || {
    # Make the "missing file" error clearer by not effectively echoing twice.
    set +x
    echo "$MISSING_QEMU_IMAGE_MESSAGE"
    build_exception
    exit 2
  }
}

[[ -z "$SKIP_HWASAN_LAM" ]] && setup_lam_qemu_image || SKIP_HWASAN_LAM=1

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
    build_exception
    exit 2
  )
}

function build_lam_linux {
  echo "@@@BUILD_STEP build lam linux@@@"
  local build_dir="${ROOT}/lam_linux_build"
  LAM_KERNEL="${build_dir}/arch/x86_64/boot/bzImage"
  (
    git_clone_at_revision lam_linux https://github.com/vitalybuka/linux.git \
      origin/lam ${build_dir} || exit 1

    ls "${LAM_KERNEL}" && exit 0

    rm -rf ${build_dir} &&
    mkdir -p ${build_dir} &&
    cd ${ROOT}/lam_linux &&
    make O=${build_dir} LD=ld.bfd defconfig &&
    make O=${build_dir} LD=ld.bfd -j $(nproc) &&
    ls "${LAM_KERNEL}"
  ) || (
    build_exception
    exit 2
  )
}

build_qemu qemu https://github.com/vitalybuka/qemu.git origin/sanitizer_bot
[[ -z "$SKIP_HWASAN_LAM" ]] && build_lam_linux

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
    # We need a fresh base compiler to test standalone build, as this config
    # does not build own clang.
    local COMPILER_BIN_DIR="$(readlink -f ${STAGE2_DIR})/bin"
    cd ${out_dir}

    (
      cmake \
        ${CMAKE_COMMON_OPTIONS} \
        -DCOMPILER_RT_DEBUG=$DBG \
        -DLLVM_CMAKE_DIR="${COMPILER_BIN_DIR}/.." \
        -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
        -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++ \
        -DCOMPILER_RT_HAS_LLD=ON \
        -DCOMPILER_RT_TEST_USE_LLD=ON \
        -DCMAKE_INSTALL_PREFIX=$(${COMPILER_BIN_DIR}/clang -print-resource-dir) \
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

function configure_hwasan_lam {
  local out_dir=llvm_build2_x86_64_lam_qemu
  rm -rf ${out_dir}
  mkdir -p ${out_dir}

  (
    # We don't need fresh base compiler, as this config will build own clang.
    local COMPILER_BIN_DIR="$(readlink -f ${STAGE1_DIR})/bin"
    cd ${out_dir}

    (
      # STAGE1_DIR is build once, so we can use CCACHE.
      if ccache -s >/dev/null ; then
        CMAKE_COMMON_OPTIONS+=" -DLLVM_CCACHE_BUILD=ON"
      fi
      cmake \
        ${CMAKE_COMMON_OPTIONS} \
        -DLLVM_ENABLE_PROJECTS="clang;compiler-rt;lld" \
        -DCMAKE_C_COMPILER=${COMPILER_BIN_DIR}/clang \
        -DCMAKE_CXX_COMPILER=${COMPILER_BIN_DIR}/clang++ \
        -DLLVM_ENABLE_LLD=ON \
        -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        -DCOMPILER_RT_EMULATOR="env SSH_CONTROL_SOCKET=${SSH_CONTROL_SOCKET} ${HERE}/ssh_run.sh" \
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
  ) || build_failure
}

QEMU_PID=""
readonly QEMU_TMPDIR="$ROOT/qemu_tmp"
readonly SSH_CONTROL_SOCKET="${QEMU_TMPDIR}/ssh-control-socket"

function kill_qemu {
  if kill "${QEMU_PID}"; then
    echo "Waiting for QEMU to shutdown..." >&2
    {
      timeout -k 5s 5s wait "${QEMU_PID}" && return
      kill -9 "${QEMU_PID}" && wait "${QEMU_PID}" || true
    } &>/dev/null
  fi
}

function boot_qemu {
  trap kill_qemu EXIT

  # Path to a qemu-system-x86_64 binary built with LAM support.
  local QEMU="${ROOT}/qemu_build/qemu-system-x86_64"
  # Path to a qemu-img binary.
  local QEMU_IMG="${ROOT}/qemu_build/qemu-img"
  
  echo "Booting QEMU..." >&2

  # Try up to 10 random port numbers until one succeeds.
  for i in {0..10}; do
    rm -rf ${QEMU_TMPDIR}
    mkdir -p ${QEMU_TMPDIR}
    # Create a delta image to boot from.
    local DELTA_IMAGE="${QEMU_TMPDIR}/delta.qcow2"
    "${QEMU_IMG}" create -F raw -b "${QEMU_IMAGE}" -f qcow2 "${DELTA_IMAGE}"

    local SSH_PORT="$(shuf -i 1000-65535 -n 1)"

    "${QEMU}" -hda "${DELTA_IMAGE}" -nographic \
      -net "user,host=10.0.2.10,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22" \
      -net "nic,model=e1000" -machine "type=q35,accel=tcg" \
      -smp $(($(nproc) / 2)) -cpu "qemu64,+la57,+lam" -kernel "${LAM_KERNEL}" \
      -append "root=/dev/sda net.ifnames=0 console=ttyS0" -m "16G" &
    QEMU_PID=$!

    # If QEMU is running, the port number worked.
    sleep 1
    ps -p "${QEMU_PID}" &>/dev/null || continue

    echo "Waiting for QEMU ssh daemon..." >&2
    for i in {0..10}; do
      echo "SSH into VM, try ${i}" >&2
      sleep 15

      # Set up persistent SSH connection for faster command execution inside QEMU.
      ssh -p "${SSH_PORT}" -o "StrictHostKeyChecking=no" \
          -o "UserKnownHostsFile=/dev/null" -o "ControlPersist=30m" \
          -M -S "${SSH_CONTROL_SOCKET}" -i "${QEMU_SSH_KEY}" root@localhost "uname -a" 1>&2 &&
        return
    done

    kill_qemu
  done

  # Fail fast if QEMU is not running.
  ps -p "${QEMU_PID}" &>/dev/null
}

function run_hwasan_lam_tests {
  local name="x86_64_lam_qemu"
  local out_dir=llvm_build2_${name}

  echo "@@@BUILD_STEP configure hwasan ${name}@@@"

  (
    cd ${out_dir}
    cat configure.log

    # Build most stuff before starting VM.
    echo "@@@BUILD_STEP build tools ${name}@@@"
    ninja clang lld llvm-symbolizer || exit 3

    echo "@@@BUILD_STEP start LAM QEMU@@@"
    boot_qemu || build_exception

    ssh -S "${SSH_CONTROL_SOCKET}" root@localhost \
        "mkdir -p /b && mount -t nfs 10.0.2.10:/b /b"

    echo
    echo "@@@BUILD_STEP test hwasan ${name}@@@"
    ninja check-hwasan-lam || exit 3
  ) || build_failure
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
[[ -z "$SKIP_HWASAN_LAM" ]] && configure_hwasan_lam

wait

for B in $SCUDO_BUILDS ; do
  run_scudo_tests $B
done

[[ -z "$SKIP_HWASAN_LAM" ]] && (
  run_hwasan_lam_tests
)

cleanup $STAGE2_DIR
