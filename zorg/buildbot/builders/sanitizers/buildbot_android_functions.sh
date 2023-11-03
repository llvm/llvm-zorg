#!/usr/bin/env bash

ANDROID_NDK_VERSION=21
ANDROID_API=24
NDK_DIR=android_ndk

function download_android_tools {
  local VERSION=android-ndk-r${ANDROID_NDK_VERSION}d
  local FILE_NAME=${VERSION}-linux-x86_64.zip
  local NDK_URL=https://dl.google.com/android/repository/${FILE_NAME}
  if  [[ "$(cat ${NDK_DIR}/android_ndk_url)" != ${NDK_URL} ]] ; then
    echo @@@BUILD_STEP downloading Android NDK@@@
    [[ -d ${NDK_DIR} ]] && rm -rf ${NDK_DIR}
    [[ -d ${VERSION} ]] && rm -rf ${VERSION}
    [[ -f ${FILE_NAME} ]] && rm -f ${FILE_NAME}
    wget -e dotbytes=10m ${NDK_URL}
    unzip ${FILE_NAME} > /dev/null
    mv ${VERSION} ${NDK_DIR}
    echo ${NDK_URL} > ${NDK_DIR}/android_ndk_url
  fi

  if  [[ ! -d platform-tools ]] ; then
    echo @@@BUILD_STEP downloading Android Platform Tools@@@
    local FILE_NAME=platform-tools-latest-linux.zip
    [[ -f ${FILE_NAME} ]] && rm -f ${FILE_NAME}
    wget -e dotbytes=10m https://dl.google.com/android/repository/${FILE_NAME}
    unzip ${FILE_NAME} > /dev/null
  fi
  export PATH=$ROOT/platform-tools/:$PATH
}

function build_stage2_android() {
  # Build self-hosted tree with fresh Clang and -Werror.
  local CMAKE_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON ${STAGE1_AS_COMPILER}"
  CMAKE_OPTIONS="${CMAKE_OPTIONS} -DLLVM_ENABLE_PROJECTS='clang;lld' -DCLANG_DEFAULT_RTLIB=libgcc"

  echo @@@BUILD_STEP bootstrap clang@@@
  mkdir -p llvm_build64
  if  [[ "$(cat llvm_build64/CMAKE_OPTIONS)" != "${CMAKE_OPTIONS}" ]] ; then
    (cd llvm_build64 && cmake ${CMAKE_OPTIONS} $LLVM && \
       echo ${CMAKE_OPTIONS} > CMAKE_OPTIONS) || build_failure
  fi
  ninja -C llvm_build64 || (build_failure && exit 2)
}

function configure_android { # ARCH triple
  local _arch=$1
  local _triple=$2

  ANDROID_TOOLCHAIN=$ROOT/$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64
  echo "Building for Android API level $ANDROID_API"

  local ANDROID_LIBRARY_OUTPUT_DIR=$(ls -d $ROOT/llvm_build64/lib/clang/* | tail -1)
  local ANDROID_EXEC_OUTPUT_DIR=$ROOT/llvm_build64/bin
  local ANDROID_FLAGS="--target=${_triple}${ANDROID_API} --sysroot=$ANDROID_TOOLCHAIN/sysroot --gcc-toolchain=$ANDROID_TOOLCHAIN  -B$ANDROID_TOOLCHAIN"

  local CLANG_PATH=$ROOT/llvm_build64/bin/clang
  local CLANGXX_PATH=$ROOT/llvm_build64/bin/clang++

  # Always clobber android build tree.
  # It has a hidden dependency on clang (through CXX) which is not known to
  # the build system.
  rm_dirs compiler_rt_build_android_$_arch llvm_build_android_$_arch
  mkdir -p compiler_rt_build_android_$_arch
  mkdir -p llvm_build_android_$_arch

  (cd llvm_build_android_$_arch && cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DLLVM_ENABLE_WERROR=OFF \
    -DCMAKE_C_COMPILER=$CLANG_PATH \
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS" \
    -DLLVM_BINUTILS_INCDIR=/usr/include \
    -DCMAKE_EXE_LINKER_FLAGS="-pie" \
    -DCMAKE_SKIP_RPATH=ON \
    -DLLVM_BUILD_RUNTIME=OFF \
    -DLLVM_TABLEGEN=$ROOT/llvm_build64/bin/llvm-tblgen \
    $LLVM || build_failure) &

  local COMPILER_RT_OPTIONS="$(readlink -f $LLVM/../compiler-rt)"
  
  (cd compiler_rt_build_android_$_arch && cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DCMAKE_C_COMPILER=$CLANG_PATH \
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH \
    -DLLVM_CMAKE_DIR=$ROOT/llvm_build64 \
    -DCOMPILER_RT_BUILD_BUILTINS=OFF \
    -DCOMPILER_RT_INCLUDE_TESTS=ON \
    -DCOMPILER_RT_ENABLE_WERROR=ON \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS" \
    -DSANITIZER_CXX_ABI="libcxxabi" \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="$ANDROID_FLAGS" \
    -DCOMPILER_RT_DEFAULT_TARGET_TRIPLE=$_triple \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    -DCOMPILER_RT_EXEC_OUTPUT_DIR="$ANDROID_EXEC_OUTPUT_DIR" \
    -DLLVM_LIT_ARGS="-vv --show-unsupported --show-xfail" \
    ${COMPILER_RT_OPTIONS} || build_failure) &
}

BUILD_RT_ERR=""
function build_android {
  local _arch=$1
  wait
  echo @@@BUILD_STEP build android/$_arch@@@
  if ! ninja -C llvm_build_android_$_arch llvm-symbolizer ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi
  if ! ninja -C compiler_rt_build_android_$_arch ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi
}

# If a multiarch device's first arch starts with x86, remove archs that don't
# start with x86. Handle cases like:
#  - x86,armeabi-v7a
#  - x86_64,x86,arm64-v8a,armeabi-v7a,armeabi
#  - x86_64,arm64-v8a,x86,armeabi-v7a,armeabi
# The arm part is software emulation and incompatible with ASan.
function patch_abilist { # IN OUT
  local _abilist=$1
  local _out=$2
  if [[ "$_abilist" == "x86"* ]]; then
    _abilist=$(echo $_abilist | tr , '\n' | grep '^x86')
    _abilist=$(echo $_abilist | tr ' ' ,)
  fi
  eval $_out="'$_abilist'"
}

function restart_adb_server {
  ADB=adb
  echo @@@BUILD_STEP restart adb server@@@
  $ADB kill-server
  sleep 2
  $ADB start-server
  sleep 2
}

function test_on_device {
  local _serial=$1
  shift

  ABILIST=$(${ADB} -s $_serial shell getprop ro.product.cpu.abilist)
  patch_abilist "$ABILIST" ABILIST
  for _arg in "$@"; do
    local _arch=${_arg%:*}
    local _abi=${_arg#*:}
    if [[ $BUILD_RT_ERR == *"|${_arch}|"* ]]; then
      echo "skipping tests on ${_arch}"
      build_failure
      continue
    fi
    if [[ $ABILIST == *"$_abi"* ]]; then
      echo "$_serial" >> tested_arch_$_arch
      BUILD_ID=$(${ADB} -s $_serial shell getprop ro.build.id | tr -d '\r')
      BUILD_FLAVOR=$(${ADB} -s $_serial shell getprop ro.build.flavor | tr -d '\r')
      (
        # Test only one arch at a time to avoid simultaneously writes into the
        # same compiler-rt build dir.
        flock -x $lock_fd
        test_arch_on_device "$_arch" "$_serial" "$BUILD_ID" "$BUILD_FLAVOR"
      ) {lock_fd}>$ROOT/${_arch}.lock
    fi
  done
}

function tail_pids {
  for LOG_PID in $1; do
    PID=${LOG_PID#*,}
    LOG=${LOG_PID%,*}
    tail -n +1 -F $LOG --pid=$PID
  done
  wait
}

function test_android {
  if [[ -v BUILDBOT_BUILDERNAME ]]; then
    restart_adb_server
  fi

  ADB=adb
  echo @@@BUILD_STEP run all tests@@@
  ANDROID_DEVICES=$(${ADB} devices | grep 'device$' | sort -r | awk '{print $1}')

  rm -rf test_android_log_*
  rm -rf tested_arch_*
  rm -rf shards_*
  for SERIAL in $ANDROID_DEVICES; do
    test_on_device "$SERIAL" $@
  done

  # Return to avoid exception if we already have error.
  [[ $BUILD_RT_ERR == "" ]] || return

  for _arg in "$@"; do
    local _arch=${_arg%:*}
    if [[ ! -f tested_arch_$_arch ]]; then
      echo @@@BUILD_STEP unavailable device android/$_arch@@@
      echo @@@STEP_EXCEPTION@@@
    fi
  done
}

function run_command_on_device {
  local _cmd=$1
  local EXIT_CODE=$($ADB shell "mktemp $DEVICE_ROOT/exit_code.XXXXXX") 
  $ADB shell "$_cmd ; echo \$? >$EXIT_CODE"
  return $($ADB shell "cat $EXIT_CODE")
}

function run_tests_sharded {
  local _test_name=$1
  local _test=$2
  local _env=$3

  local NUM_SHARDS=4
  local _log_prefix=$(mktemp shards_XXXX_)
  echo @@@BUILD_STEP run $_test_name tests [$DEVICE_DESCRIPTION]@@@
  LOGS=
  for ((SHARD=0; SHARD < $NUM_SHARDS; SHARD++)); do
    LOG=${_log_prefix}_$SHARD
    # 'adb shell <command>' on Fugu is missing TMPDIR.
    local ENV="$_env GTEST_TOTAL_SHARDS=$NUM_SHARDS GTEST_SHARD_INDEX=$SHARD LD_LIBRARY_PATH=$DEVICE_ROOT TMPDIR=$DEVICE_TMPDIR"
    ( (run_command_on_device "$ENV $DEVICE_ROOT/$_test" || build_failure) 2>&1 >${_log_prefix}_$SHARD ) &
    LOGS="$LOGS $LOG,$!"
  done
  tail_pids "$LOGS" || true
}

function test_arch_on_device {
  local _arch=$1
  local _serial=$2
  local _build_id=$3
  local _build_flavor=$4

  export DEVICE_DESCRIPTION=$_arch/$_build_flavor/$_build_id

  local LIBCXX_SHARED=$ANDROID_TOOLCHAIN/sysroot/usr/lib/${_arch}-linux-androideabi/libc++_shared.so
  if [[ ! -f $LIBCXX_SHARED ]] ; then
    local LIBCXX_SHARED=$ANDROID_TOOLCHAIN/sysroot/usr/lib/${_arch}-linux-android/libc++_shared.so
  fi
  local SYMBOLIZER_BIN=$ROOT/llvm_build_android_$_arch/bin/llvm-symbolizer
  local RT_DIR=$($ROOT/llvm_build64/bin/clang -print-resource-dir)/lib/linux
  local COMPILER_RT_BUILD_DIR=$ROOT/compiler_rt_build_android_$_arch
  export ADB=adb
  export DEVICE_TMPDIR=/data/local/tmp
  export DEVICE_ROOT=/data/local/tmp/Output
  export ANDROID_SERIAL=$_serial
  echo "Serial $_serial"

  echo @@@BUILD_STEP device setup [$DEVICE_DESCRIPTION]@@@
  $ADB wait-for-device
  $ADB devices
  $ADB shell getprop ro.build.version.release

  # Kill leftover symbolizers. TODO: figure out what's going on.
  $ADB shell pkill llvm-symbolizer || true

  $ADB shell rm -rf $DEVICE_ROOT
  $ADB shell mkdir $DEVICE_ROOT

  FILES="$SYMBOLIZER_BIN
         $RT_DIR/libclang_rt.*-android.so
         $LIBCXX_SHARED
         $COMPILER_RT_BUILD_DIR/lib/sanitizer_common/tests/SanitizerTest
         $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanTest
         $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanNoinstTest"

  for F in $FILES ; do
    ( $ADB push $F $DEVICE_ROOT/ >/dev/null || build_failure )&
  done
  wait

  echo @@@BUILD_STEP run lit tests [$DEVICE_DESCRIPTION]@@@
  (cd $COMPILER_RT_BUILD_DIR && ninja check-all) || build_failure

  run_tests_sharded sanitizer_common SanitizerTest ""
  run_tests_sharded asan AsanNoinstTest ""
  run_tests_sharded "instrumented asan" AsanTest "ASAN_OPTIONS=start_deactivated=1"
}
