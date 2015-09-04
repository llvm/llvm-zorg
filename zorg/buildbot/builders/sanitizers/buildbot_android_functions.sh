#!/usr/bin/env bash

function build_llvm_symbolizer { # ARCH triple
    local _arch=$1
    local _triple=$2
    
    rm -rf llvm_build_android_$_arch
    mkdir llvm_build_android_$_arch
    cd llvm_build_android_$_arch

    local ANDROID_TOOLCHAIN=$ROOT/../../../android-ndk/standalone-$_arch
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
        -DANDROID=1 \
        -DLLVM_BUILD_RUNTIME=OFF \
        -DLLVM_TABLEGEN=$ROOT/llvm_build64/bin/llvm-tblgen \
        ${CMAKE_COMMON_OPTIONS} \
        $LLVM_CHECKOUT || echo @@@STEP_FAILURE@@@
    ninja llvm-symbolizer || echo @@@STEP_FAILURE@@@

    cd ..
}

function build_compiler_rt { # ARCH triple
    local _arch=$1
    local _triple=$2

    local ANDROID_TOOLCHAIN=$ROOT/../../../android-ndk/standalone-$_arch
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
        $LLVM_CHECKOUT/projects/compiler-rt || echo @@@STEP_FAILURE@@@
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
    ANDROID_DEVICES=$(adb devices | grep 'device$' | awk '{print $1}')
    for SERIAL in $ANDROID_DEVICES; do
      ABILIST=$(adb -s $SERIAL shell getprop ro.product.cpu.abilist)
      patch_abilist $ABILIST ABILIST
      if [[ $ABILIST == *"$_abi"* ]]; then
        BUILD_ID=$(adb -s $SERIAL shell getprop ro.build.id | tr -d '\r')
        BUILD_FLAVOR=$(adb -s $SERIAL shell getprop ro.build.flavor | tr -d '\r')
        test_android_on_device "$_arch" "$SERIAL" "$BUILD_ID" "$BUILD_FLAVOR" "$_step_failure"
      fi
    done
}

function test_android_on_device { # ARCH SERIAL BUILD_ID BUILD_FLAVOR STEP_FAILURE
    local _arch=$1
    local _serial=$2
    local _build_id=$3
    local _build_flavor=$4
    local _step_failure=$5 # @@@STEP_FAILURE@@@ or @@@STEP_WARNINGS@@@

    DEVICE_DESCRIPTION=$_arch/$_build_flavor/$_build_id

    ANDROID_SDK=$ROOT/../../../android-sdk-linux/
    SYMBOLIZER_BIN=$ROOT/llvm_build_android_$_arch/bin/llvm-symbolizer
    COMPILER_RT_BUILD_DIR=$ROOT/compiler_rt_build_android_$_arch
    ADB=$ROOT/../../../bin/adb
    DEVICE_ROOT=/data/local/asan_test

    export ANDROID_SERIAL=$_serial
    echo "Serial $_serial"

    echo @@@BUILD_STEP device setup [$DEVICE_DESCRIPTION]@@@

    $ADB wait-for-device

    echo "Device is up"
    $ADB devices

    sleep 2

    ADB=$ADB $ROOT/llvm_build64/bin/asan_device_setup
    sleep 2

    $ADB push $SYMBOLIZER_BIN /system/bin/
    $ADB shell rm -rf $DEVICE_ROOT
    $ADB shell mkdir $DEVICE_ROOT

    echo @@@BUILD_STEP run asan lit tests [$DEVICE_DESCRIPTION]@@@

    (cd $COMPILER_RT_BUILD_DIR && ninja check-asan) || echo $_step_failure

    echo @@@BUILD_STEP run sanitizer_common tests [$DEVICE_DESCRIPTION]@@@

    $ADB push $COMPILER_RT_BUILD_DIR/lib/sanitizer_common/tests/SanitizerTest $DEVICE_ROOT/

    $ADB shell "$DEVICE_ROOT/SanitizerTest; \
        echo \$? >$DEVICE_ROOT/error_code"
    $ADB pull $DEVICE_ROOT/error_code error_code && (exit `cat error_code`) || echo $_step_failure

    echo @@@BUILD_STEP run asan tests [$DEVICE_DESCRIPTION]@@@

    $ADB push $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanTest $DEVICE_ROOT/
    $ADB push $COMPILER_RT_BUILD_DIR/lib/asan/tests/AsanNoinstTest $DEVICE_ROOT/

    NUM_SHARDS=7
    for ((SHARD=0; SHARD < $NUM_SHARDS; SHARD++)); do
        $ADB shell "ASAN_OPTIONS=start_deactivated=1 \
          GTEST_TOTAL_SHARDS=$NUM_SHARDS \
          GTEST_SHARD_INDEX=$SHARD \
          asanwrapper $DEVICE_ROOT/AsanTest; \
          echo \$? >$DEVICE_ROOT/error_code"
        $ADB pull $DEVICE_ROOT/error_code error_code && echo && (exit `cat error_code`) || echo $_step_failure
        $ADB shell " \
          GTEST_TOTAL_SHARDS=$NUM_SHARDS \
          GTEST_SHARD_INDEX=$SHARD \
          $DEVICE_ROOT/AsanNoinstTest; \
          echo \$? >$DEVICE_ROOT/error_code"
        $ADB pull $DEVICE_ROOT/error_code error_code && echo && (exit `cat error_code`) || echo $_step_failure
    done

    sleep 2

    $ADB devices
}
