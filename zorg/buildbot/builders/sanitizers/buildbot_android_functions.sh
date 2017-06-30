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

function build_llvm_symbolizer { # ARCH triple
  local _arch=$1
  local _triple=$2

  echo @@@BUILD_STEP build llvm-symbolizer android/$_arch@@@
  
  rm -rf llvm_build_android_$_arch
  mkdir llvm_build_android_$_arch
  cd llvm_build_android_$_arch

  local ANDROID_TOOLCHAIN=$ROOT/android_ndk/standalone-$_arch
  local ANDROID_FLAGS="--target=$_triple --sysroot=$ANDROID_TOOLCHAIN/sysroot -B$ANDROID_TOOLCHAIN"
  cmake -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
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
    $LLVM || echo @@@STEP_FAILURE@@@
  ninja llvm-symbolizer || echo @@@STEP_FAILURE@@@

  cd ..
}

function build_compiler_rt { # ARCH triple
  local _arch=$1
  local _triple=$2

  echo @@@BUILD_STEP build compiler-rt android/$_arch@@@

  local ANDROID_TOOLCHAIN=$ROOT/android_ndk/standalone-$_arch
  local ANDROID_LIBRARY_OUTPUT_DIR=$(ls -d $ROOT/llvm_build64/lib/clang/* | tail -1)
  local ANDROID_EXEC_OUTPUT_DIR=$ROOT/llvm_build64/bin
  local ANDROID_FLAGS="--target=$_triple --sysroot=$ANDROID_TOOLCHAIN/sysroot -B$ANDROID_TOOLCHAIN"

  # Always clobber android build tree.
  # It has a hidden dependency on clang (through CXX) which is not known to
  # the build system.
  rm -rf compiler_rt_build_android_$_arch
  mkdir compiler_rt_build_android_$_arch
  cd compiler_rt_build_android_$_arch

  cmake -GNinja -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
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
    $LLVM/projects/compiler-rt || echo @@@STEP_FAILURE@@@
  ninja asan || echo @@@STEP_FAILURE@@@
  ls "$ANDROID_LIBRARY_OUTPUT_DIR"
  ninja AsanUnitTests SanitizerUnitTests || echo @@@STEP_FAILURE@@@

  cd ..
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

function test_android { # ARCH ABI STEP_FAILURE
  local _arch=$1
  local _abi=$2
  local _step_failure=$3
  ADB=adb
  $ADB kill-server
  ANDROID_DEVICES=$(${ADB} devices | grep 'device$' | awk '{print $1}')
  local FOUND=0
  for SERIAL in $ANDROID_DEVICES; do
    ABILIST=$(${ADB} -s $SERIAL shell getprop ro.product.cpu.abilist)
    patch_abilist $ABILIST ABILIST
    if [[ $ABILIST == *"$_abi"* ]]; then
      BUILD_ID=$(${ADB} -s $SERIAL shell getprop ro.build.id | tr -d '\r')
      BUILD_FLAVOR=$(${ADB} -s $SERIAL shell getprop ro.build.flavor | tr -d '\r')
      test_android_on_device "$_arch" "$SERIAL" "$BUILD_ID" "$BUILD_FLAVOR" "$_step_failure"
      FOUND=1
    fi
  done

  if [[ $FOUND != "1" ]]; then
    echo @@@BUILD_STEP unavailable device android/$_arch@@@
    echo @@@STEP_WARNINGS@@@
  fi
}

function test_android_on_device { # ARCH SERIAL BUILD_ID BUILD_FLAVOR STEP_FAILURE
  local _arch=$1
  local _serial=$2
  local _build_id=$3
  local _build_flavor=$4
  local _step_failure=$5 # @@@STEP_FAILURE@@@ or @@@STEP_WARNINGS@@@

  DEVICE_DESCRIPTION=$_arch/$_build_flavor/$_build_id

  SYMBOLIZER_BIN=$ROOT/llvm_build_android_$_arch/bin/llvm-symbolizer
  ASAN_RT=$(find $ROOT/llvm_build64/lib/ -name libclang_rt.asan-$_arch-android.so)
  COMPILER_RT_BUILD_DIR=$ROOT/compiler_rt_build_android_$_arch
  ADB=adb
  DEVICE_ROOT=/data/local/tmp/Output

  export ANDROID_SERIAL=$_serial
  echo "Serial $_serial"

  echo @@@BUILD_STEP device setup [$DEVICE_DESCRIPTION]@@@
  $ADB wait-for-device
  $ADB devices

  # Nexus Player does not have enough RAM to run ASan tests reliably.
  # Luckily, none of our tests need the application runtime, and killing
  # that can free several hundred megs of RAM.
  if [[ $_build_flavor == fugu* || $_build_flavor == volantis* ]]; then
    $ADB root
    $ADB shell stop
    $ADB unroot
    $ADB wait-for-device
  fi

  # Kill leftover symbolizers. TODO: figure out what's going on.
  $ADB shell pkill llvm-symbolizer || true

  $ADB shell rm -rf $DEVICE_ROOT
  $ADB shell mkdir $DEVICE_ROOT
  $ADB push $SYMBOLIZER_BIN $DEVICE_ROOT/
  $ADB push $ASAN_RT $DEVICE_ROOT/
  $ADB push $COMPILER_RT_BUILD_DIR/lib/sanitizer_common/tests/SanitizerTest $DEVICE_ROOT/
  $ADB push $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanTest $DEVICE_ROOT/
  $ADB push $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanNoinstTest $DEVICE_ROOT/

  echo @@@BUILD_STEP run asan lit tests [$DEVICE_DESCRIPTION]@@@
  (cd $COMPILER_RT_BUILD_DIR && ninja check-asan) || echo $_step_failure

  echo @@@BUILD_STEP run sanitizer_common tests [$DEVICE_DESCRIPTION]@@@
  $ADB shell "$DEVICE_ROOT/SanitizerTest; \
    echo \$? >$DEVICE_ROOT/error_code"
  $ADB pull $DEVICE_ROOT/error_code error_code && (exit `cat error_code`) || echo $_step_failure

  echo @@@BUILD_STEP run asan tests [$DEVICE_DESCRIPTION]@@@
  if [[ $_arch == aarch64 || $_arch == x86_64 ]]; then
    ASANWRAPPER=
  else
    ASANWRAPPER=asanwrapper
  fi
  NUM_SHARDS=7
  for ((SHARD=0; SHARD < $NUM_SHARDS; SHARD++)); do
    $ADB shell "ASAN_OPTIONS=start_deactivated=1 \
      GTEST_TOTAL_SHARDS=$NUM_SHARDS \
      GTEST_SHARD_INDEX=$SHARD \
      $ASANWRAPPER $DEVICE_ROOT/AsanTest; \
      echo \$? >$DEVICE_ROOT/error_code"
    $ADB pull $DEVICE_ROOT/error_code error_code && echo && (exit `cat error_code`) || echo $_step_failure
    $ADB shell " \
      GTEST_TOTAL_SHARDS=$NUM_SHARDS \
      GTEST_SHARD_INDEX=$SHARD \
      $DEVICE_ROOT/AsanNoinstTest; \
      echo \$? >$DEVICE_ROOT/error_code"
    $ADB pull $DEVICE_ROOT/error_code error_code && echo && (exit `cat error_code`) || echo $_step_failure
  done
}
