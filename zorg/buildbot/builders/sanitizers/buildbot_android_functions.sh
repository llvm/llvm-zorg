#!/usr/bin/env bash

function download_android_tools {
  local VERSION=android-ndk-$1
  local FILE_NAME=${VERSION}-linux-x86_64.zip
  local NDK_URL=https://dl.google.com/android/repository/${FILE_NAME}
  local NDK_DIR=android_ndk
  if  [[ "$(cat ${NDK_DIR}/android_ndk_url)" != ${NDK_URL} ]] ; then
    echo @@@BUILD_STEP downloading Android NDK@@@
    [[ -d ${NDK_DIR} ]] && rm -rf ${NDK_DIR}
    [[ -d ${VERSION} ]] && rm -rf ${VERSION}
    [[ -f ${FILE_NAME} ]] && rm -f ${FILE_NAME}
    wget ${NDK_URL}
    unzip ${FILE_NAME} > /dev/null
    mv ${VERSION} ${NDK_DIR}
    echo ${NDK_URL} > ${NDK_DIR}/android_ndk_url
  fi

  if  [[ ! -d platform-tools ]] ; then
    echo @@@BUILD_STEP downloading Android Platform Tools@@@
    local FILE_NAME=platform-tools-latest-linux.zip
    [[ -f ${FILE_NAME} ]] && rm -f ${FILE_NAME}
    wget https://dl.google.com/android/repository/${FILE_NAME}
    unzip ${FILE_NAME} > /dev/null
  fi
  export PATH=$ROOT/platform-tools/:$PATH
}

function build_android_ndk {
  local NDK_DIR=android_ndk
  local _arch=$1
  local _ndk_arch=$2
  if [[ ! -d $NDK_DIR/standalone-$_arch ]] ; then 
    echo @@@BUILD_STEP building Android NDK for $_arch@@@
    $NDK_DIR/build/tools/make_standalone_toolchain.py --api 24 --force --arch $_ndk_arch --stl=libc++ --install-dir $NDK_DIR/standalone-$_arch
  fi
}

function configure_android { # ARCH triple
  local _arch=$1
  local _triple=$2

  local ANDROID_TOOLCHAIN=$ROOT/android_ndk/standalone-$_arch
  local ANDROID_LIBRARY_OUTPUT_DIR=$(ls -d $ROOT/llvm_build64/lib/clang/* | tail -1)
  local ANDROID_EXEC_OUTPUT_DIR=$ROOT/llvm_build64/bin
  local ANDROID_FLAGS="--target=$_triple --sysroot=$ANDROID_TOOLCHAIN/sysroot -B$ANDROID_TOOLCHAIN"
  local ANDROID_CXX_FLAGS="$ANDROID_FLAGS -stdlib=libstdc++"

  # Always clobber android build tree.
  # It has a hidden dependency on clang (through CXX) which is not known to
  # the build system.
  rm -rf compiler_rt_build_android_$_arch
  mkdir -p compiler_rt_build_android_$_arch
  rm -rf llvm_build_android_$_arch
  mkdir -p llvm_build_android_$_arch

  (cd llvm_build_android_$_arch && cmake \
    -DLLVM_ENABLE_WERROR=OFF \
    -DCMAKE_C_COMPILER=$ROOT/llvm_build64/bin/clang \
    -DCMAKE_CXX_COMPILER=$ROOT/llvm_build64/bin/clang++ \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_CXX_FLAGS" \
    -DCMAKE_EXE_LINKER_FLAGS="-pie" \
    -DCMAKE_SKIP_RPATH=ON \
    -DLLVM_BUILD_RUNTIME=OFF \
    -DLLVM_TABLEGEN=$ROOT/llvm_build64/bin/llvm-tblgen \
    ${CMAKE_COMMON_OPTIONS} \
    $LLVM || echo @@@STEP_FAILURE@@@) &
  
  (cd compiler_rt_build_android_$_arch && cmake \
    -DCMAKE_C_COMPILER=$ROOT/llvm_build64/bin/clang \
    -DCMAKE_CXX_COMPILER=$ROOT/llvm_build64/bin/clang++ \
    -DLLVM_CONFIG_PATH=$ROOT/llvm_build64/bin/llvm-config \
    -DCOMPILER_RT_BUILD_BUILTINS=OFF \
    -DCOMPILER_RT_INCLUDE_TESTS=ON \
    -DCOMPILER_RT_ENABLE_WERROR=ON \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_CXX_FLAGS" \
    -DANDROID=1 \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="$ANDROID_FLAGS" \
    -DCOMPILER_RT_TEST_TARGET_TRIPLE=$_triple \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    -DCOMPILER_RT_EXEC_OUTPUT_DIR="$ANDROID_EXEC_OUTPUT_DIR" \
    -DLLVM_LIT_ARGS="-sv --show-unsupported --show-xfail" \
    ${CMAKE_COMMON_OPTIONS} \
    $LLVM/projects/compiler-rt || echo @@@STEP_FAILURE@@@) &
}

function build_android {
  local _arch=$1
  wait
  echo @@@BUILD_STEP build android/$_arch@@@
  ninja -C llvm_build_android_$_arch llvm-symbolizer || echo @@@STEP_FAILURE@@@
  ninja -C compiler_rt_build_android_$_arch || echo @@@STEP_FAILURE@@@
}

# If a multiarch device has x86 as the first arch, remove everything else from
# the list. This captures cases like [x86,armeabi-v7a], where the arm part is
# software emulation and incompatible with ASan.
function patch_abilist { # IN OUT
  local _abilist=$1
  local _out=$2
  if [[ "$_abilist" == "x86,"* ]]; then
    _abilist="x86"
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
  patch_abilist $ABILIST ABILIST
  for _arg in "$@"; do
    local _arch=${_arg%:*}
    local _abi=${_arg#*:}
    if [[ $ABILIST == *"$_abi"* ]]; then
      BUILD_ID=$(${ADB} -s $_serial shell getprop ro.build.id | tr -d '\r')
      BUILD_FLAVOR=$(${ADB} -s $_serial shell getprop ro.build.flavor | tr -d '\r')
      test_arch_on_device "$_arch" "$_serial" "$BUILD_ID" "$BUILD_FLAVOR"
      echo "$_serial" >> tested_arch_$_arch
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
  if [[ "${BUILDBOT_SLAVENAME:-}" != "" ]]; then
    restart_adb_server
  fi

  ADB=adb
  echo @@@BUILD_STEP run all tests@@@
  ANDROID_DEVICES=$(${ADB} devices | grep 'device$' | awk '{print $1}')

  rm -rf test_android_log_*
  rm -rf tested_arch_*
  rm -rf shards_*
  LOGS=
  for SERIAL in $ANDROID_DEVICES; do
    LOG="$(mktemp test_android_log_XXXX)"
    (test_on_device "$SERIAL" $@ 2>&1 >"$LOG") &
    LOGS="$LOGS $LOG,$!"
  done
  tail_pids "$LOGS"

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
    local ENV="$_env GTEST_TOTAL_SHARDS=$NUM_SHARDS GTEST_SHARD_INDEX=$SHARD LD_LIBRARY_PATH=$DEVICE_ROOT"
    ( (run_command_on_device "$ENV $DEVICE_ROOT/$_test" || echo @@@STEP_FAILURE@@@) 2>&1 >${_log_prefix}_$SHARD ) &
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

  ANDROID_TOOLCHAIN=$ROOT/android_ndk/standalone-$_arch
  LIBCXX_SHARED=$(find $ANDROID_TOOLCHAIN/ -name libc++_shared.so | head -1)
  SYMBOLIZER_BIN=$ROOT/llvm_build_android_$_arch/bin/llvm-symbolizer
  RT_DIR=$($ROOT/llvm_build64/bin/clang -print-resource-dir)/lib/linux
  COMPILER_RT_BUILD_DIR=$ROOT/compiler_rt_build_android_$_arch
  export ADB=adb
  export DEVICE_ROOT=/data/local/tmp/Output
  export ANDROID_SERIAL=$_serial
  echo "Serial $_serial"

  echo @@@BUILD_STEP device setup [$DEVICE_DESCRIPTION]@@@
  $ADB wait-for-device
  $ADB devices

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
    ( $ADB push $F $DEVICE_ROOT/ >/dev/null || echo @@@STEP_FAILURE@@@ )&
  done
  wait

  echo @@@BUILD_STEP run lit tests [$DEVICE_DESCRIPTION]@@@
  (cd $COMPILER_RT_BUILD_DIR && ninja check-all) || echo @@@STEP_FAILURE@@@

  run_tests_sharded sanitizer_common SanitizerTest ""
  run_tests_sharded asan AsanNoinstTest ""
  run_tests_sharded "instrumented asan" AsanTest "ASAN_OPTIONS=start_deactivated=1"
}
