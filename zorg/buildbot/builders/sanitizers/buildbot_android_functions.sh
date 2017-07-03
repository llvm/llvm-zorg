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
    $NDK_DIR/build/tools/make_standalone_toolchain.py --api 24 --force --arch $_ndk_arch --install-dir $NDK_DIR/standalone-$_arch
  fi
}

function configure_android { # ARCH triple
  local _arch=$1
  local _triple=$2

  local ANDROID_TOOLCHAIN=$ROOT/android_ndk/standalone-$_arch
  local ANDROID_LIBRARY_OUTPUT_DIR=$(ls -d $ROOT/llvm_build64/lib/clang/* | tail -1)
  local ANDROID_EXEC_OUTPUT_DIR=$ROOT/llvm_build64/bin
  local ANDROID_FLAGS="--target=$_triple --sysroot=$ANDROID_TOOLCHAIN/sysroot -B$ANDROID_TOOLCHAIN"

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
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS" \
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
    -DCOMPILER_RT_INCLUDE_TESTS=ON \
    -DCOMPILER_RT_ENABLE_WERROR=ON \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS" \
    -DANDROID=1 \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="$ANDROID_FLAGS" \
    -DCOMPILER_RT_TEST_TARGET_TRIPLE=$_triple \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    -DCOMPILER_RT_EXEC_OUTPUT_DIR="$ANDROID_EXEC_OUTPUT_DIR" \
    ${CMAKE_COMMON_OPTIONS} \
    $LLVM/projects/compiler-rt || echo @@@STEP_FAILURE@@@) &
}

function build_android {
  local _arch=$1
  wait
  echo @@@BUILD_STEP build android/$_arch@@@
  ninja -C llvm_build_android_$_arch llvm-symbolizer || echo @@@STEP_FAILURE@@@
  ninja -C compiler_rt_build_android_$_arch asan AsanUnitTests SanitizerUnitTests || echo @@@STEP_FAILURE@@@
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
  local _out=$1
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
      eval $_out["$_arg"]=1
    fi
  done
}

function test_android {
  restart_adb_server

  declare -A _tested
  for _arg in "$@"; do
    _tested["$_arg"]=0
  done

  ADB=adb
  echo @@@BUILD_STEP run tests@@@
  ANDROID_DEVICES=$(${ADB} devices | grep 'device$' | awk '{print $1}')

  rm -rf test_android_*.log
  for SERIAL in $ANDROID_DEVICES; do
    (test_on_device "$SERIAL" _tested $@ >$(mktemp test_android_XXXX.log) 2>&1) &
  done

  wait
  find -name test_android_*.log | xargs cat

  for _arg in "$@"; do
    if [[ ${_tested["$_arg"]} != 1 ]]; then
      echo @@@BUILD_STEP unavailable device android/$_arg@@@
      echo @@@STEP_WARNINGS@@@
    fi
  done
}

function run_command_on_device {
  local _cmd=$1
  local EXIT_CODE=$($ADB shell "mktemp $DEVICE_ROOT/exit_code.XXXXXX") 
  $ADB shell "$_cmd ; echo \$? >$EXIT_CODE"
  return $($ADB shell "cat $EXIT_CODE")
}

function test_arch_on_device {
  local _arch=$1
  local _serial=$2
  local _build_id=$3
  local _build_flavor=$4

  DEVICE_DESCRIPTION=$_arch/$_build_flavor/$_build_id

  SYMBOLIZER_BIN=$ROOT/llvm_build_android_$_arch/bin/llvm-symbolizer
  ASAN_RT=$(find $ROOT/llvm_build64/lib/ -name libclang_rt.asan-$_arch-android.so)
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
  $ADB push $SYMBOLIZER_BIN $DEVICE_ROOT/ &
  $ADB push $ASAN_RT $DEVICE_ROOT/ &
  $ADB push $COMPILER_RT_BUILD_DIR/lib/sanitizer_common/tests/SanitizerTest $DEVICE_ROOT/ &
  $ADB push $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanTest $DEVICE_ROOT/ &
  $ADB push $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanNoinstTest $DEVICE_ROOT/ &
  wait

  echo @@@BUILD_STEP run asan lit tests [$DEVICE_DESCRIPTION]@@@
  (cd $COMPILER_RT_BUILD_DIR && ninja check-asan) || echo @@@STEP_FAILURE@@@

  echo @@@BUILD_STEP run sanitizer_common tests [$DEVICE_DESCRIPTION]@@@
  run_command_on_device $DEVICE_ROOT/SanitizerTest || echo @@@STEP_FAILURE@@@

  echo @@@BUILD_STEP run asan tests [$DEVICE_DESCRIPTION]@@@
  NUM_SHARDS=7
  for ((SHARD=0; SHARD < $NUM_SHARDS; SHARD++)); do
    local ENV="GTEST_TOTAL_SHARDS=$NUM_SHARDS GTEST_SHARD_INDEX=$SHARD LD_LIBRARY_PATH=$DEVICE_ROOT"
    run_command_on_device "ASAN_OPTIONS=start_deactivated=1 $ENV $DEVICE_ROOT/AsanTest" || echo @@@STEP_FAILURE@@@
    run_command_on_device "$ENV $DEVICE_ROOT/AsanNoinstTest" || echo @@@STEP_FAILURE@@@
  done
}
