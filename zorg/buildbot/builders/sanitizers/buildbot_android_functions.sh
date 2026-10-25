#!/usr/bin/env bash

ANDROID_NDK_VERSION=30
ANDROID_API=24
NDK_DIR=android_ndk
SDK_DIR=android_sdk

function download_android_tools {
  local VERSION=android-ndk-r${ANDROID_NDK_VERSION}
  local FILE_NAME=${VERSION}-linux.zip
  local NDK_URL=https://dl.google.com/android/repository/${FILE_NAME}
  if  [[ "$(cat ${NDK_DIR}/android_ndk_url 2>/dev/null)" != ${NDK_URL} ]] ; then
    build_step "downloading Android NDK"
    [[ -d ${NDK_DIR} ]] && rm -rf ${NDK_DIR}
    [[ -d ${VERSION} ]] && rm -rf ${VERSION}
    [[ -f ${FILE_NAME} ]] && rm -f ${FILE_NAME}
    wget -e dotbytes=10m ${NDK_URL}
    unzip ${FILE_NAME} > /dev/null
    mv ${VERSION} ${NDK_DIR}
    rm -f ${FILE_NAME}
    echo ${NDK_URL} > ${NDK_DIR}/android_ndk_url
  fi

  export ANDROID_HOME=$ROOT/$SDK_DIR
  export ANDROID_SDK_ROOT=$ANDROID_HOME
  export ANDROID_USER_HOME=$ANDROID_HOME/.android
  export ANDROID_AVD_HOME=$ANDROID_USER_HOME/avd

  local CMDLINE_FILE=commandlinetools-linux-11076708_latest.zip
  local CMDLINE_URL=https://dl.google.com/android/repository/${CMDLINE_FILE}
  local SYS_IMAGE="system-images;android-29;default;x86_64"
  if [[ "$(cat ${SDK_DIR}/android_sdk_url 2>/dev/null)" != "${CMDLINE_URL}|${SYS_IMAGE}" ]] ; then
    build_step "downloading Android SDK"
    rm -rf ${SDK_DIR}
    mkdir -p ${SDK_DIR}/cmdline-tools ${ANDROID_AVD_HOME}
    [[ -f ${CMDLINE_FILE} ]] && rm -f ${CMDLINE_FILE}
    wget -e dotbytes=10m ${CMDLINE_URL}
    unzip ${CMDLINE_FILE} -d ${SDK_DIR}/cmdline-tools > /dev/null
    mv ${SDK_DIR}/cmdline-tools/cmdline-tools ${SDK_DIR}/cmdline-tools/latest
    rm -f ${CMDLINE_FILE}
    yes | HOME=$ANDROID_HOME ${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager --sdk_root=${ANDROID_HOME} \
      "platform-tools" "emulator" "${SYS_IMAGE}" > /dev/null && \
    echo no | HOME=$ANDROID_HOME ${ANDROID_HOME}/cmdline-tools/latest/bin/avdmanager create avd \
      -n san_x86_64 -k "${SYS_IMAGE}" --force && \
    echo "${CMDLINE_URL}|${SYS_IMAGE}" > ${SDK_DIR}/android_sdk_url
  fi
  export PATH=$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH
}

function build_stage2_android() {
  # Build self-hosted tree with fresh Clang and -Werror.
  local CMAKE_OPTIONS="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_WERROR=ON ${STAGE1_AS_COMPILER}"
  CMAKE_OPTIONS="${CMAKE_OPTIONS} -DLLVM_ENABLE_PROJECTS='clang;lld'"

  build_step "bootstrap clang"
  if [[ "$(cat llvm_build64/CMAKE_OPTIONS 2>/dev/null)" != "${CMAKE_OPTIONS}" ]] ; then
    rm -rf llvm_build64
    mkdir -p llvm_build64
    (cd llvm_build64 && cmake ${CMAKE_OPTIONS} $LLVM && \
       echo ${CMAKE_OPTIONS} > CMAKE_OPTIONS) || build_failure
  fi
  ninja -C llvm_build64 || (build_failure && exit 2)
  rm -rf llvm_build64/lib/clang/*/lib/linux
}

BUILD_RT_ERR=""
function build_android { # ARCH triple
  local _arch=$1
  local _triple=$2

  ANDROID_TOOLCHAIN=$ROOT/$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64
  echo "Building for Android API level $ANDROID_API"

  local ANDROID_LIBRARY_OUTPUT_DIR=$(ls -d $ROOT/llvm_build64/lib/clang/* | tail -1)
  local ANDROID_UNWIND_DIR="$ANDROID_LIBRARY_OUTPUT_DIR/lib/linux/${_arch/i686/i386}"
  local ANDROID_FLAGS="--target=${_triple}${ANDROID_API} --sysroot=$ANDROID_TOOLCHAIN/sysroot -ffunction-sections -fdata-sections"

  local CLANG_PATH=$ROOT/llvm_build64/bin/clang
  local CLANGXX_PATH=$ROOT/llvm_build64/bin/clang++

  # Always clobber android build tree.
  # It has a hidden dependency on clang (through CXX) which is not known to
  # the build system.
  rm_dirs builtins_build_android_$_arch libunwind_build_android_$_arch llvm_build_android_$_arch compiler_rt_build_android_$_arch
  mkdir -p builtins_build_android_$_arch
  mkdir -p libunwind_build_android_$_arch
  mkdir -p llvm_build_android_$_arch
  mkdir -p compiler_rt_build_android_$_arch

  mkdir -p "$ANDROID_UNWIND_DIR"
  rm -f "$ANDROID_LIBRARY_OUTPUT_DIR/lib/linux/libclang_rt.builtins-$_arch-android.a" "$ANDROID_UNWIND_DIR/libunwind.a"
  ln -s "$ANDROID_UNWIND_DIR" libunwind_build_android_$_arch/lib

  # Based on BuiltinsBuilder in
  # https://android.googlesource.com/toolchain/llvm_android/+/refs/heads/main/src/llvm_android/builders.py
  build_step "cmake builtins android/$_arch"
  if ! (cd builtins_build_android_$_arch && cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DCMAKE_C_COMPILER=$CLANG_PATH \
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH \
    -DLLVM_CMAKE_DIR=$ROOT/llvm_build64 \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS" \
    -DANDROID=1 \
    -DCOMPILER_RT_BUILTINS_HIDE_SYMBOLS=OFF \
    -DCOMPILER_RT_EXCLUDE_ATOMIC_BUILTIN=OFF \
    -DCOMPILER_RT_DEFAULT_TARGET_TRIPLE=${_triple}${ANDROID_API} \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    $LLVM/../compiler-rt/lib/builtins) ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  build_step "build builtins android/$_arch"
  if ! ninja -C builtins_build_android_$_arch ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  # Based on LibUnwindBuilder in
  # https://android.googlesource.com/toolchain/llvm_android/+/refs/heads/main/src/llvm_android/builders.py
  build_step "cmake libunwind android/$_arch"
  if ! (cd libunwind_build_android_$_arch && cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DLLVM_ENABLE_RUNTIMES=libunwind \
    -DCMAKE_C_COMPILER=$CLANG_PATH \
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS -D_LIBUNWIND_USE_DLADDR=0" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS -D_LIBUNWIND_USE_DLADDR=0" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS -D_LIBUNWIND_USE_DLADDR=0" \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs -unwindlib=none -nostdlib++" \
    -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs -unwindlib=none -nostdlib++" \
    -DANDROID=1 \
    -DLIBUNWIND_ENABLE_SHARED=OFF \
    -DLIBUNWIND_ENABLE_STATIC=ON \
    -DLIBUNWIND_HIDE_SYMBOLS=ON \
    -DLIBUNWIND_USE_FRAME_HEADER_CACHE=OFF \
    -DLIBUNWIND_TARGET_TRIPLE=${_triple}${ANDROID_API} \
    $LLVM/../runtimes) ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  build_step "build libunwind android/$_arch"
  if ! ninja -C libunwind_build_android_$_arch unwind ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  build_step "cmake llvm-symbolizer android/$_arch"
  if ! (cd llvm_build_android_$_arch && cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DLLVM_ENABLE_WERROR=OFF \
    -DCMAKE_C_COMPILER=$CLANG_PATH \
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS" \
    -DLLVM_BINUTILS_INCDIR=/usr/include \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs -pie" \
    -DCMAKE_SKIP_RPATH=ON \
    -DLLVM_BUILD_RUNTIME=OFF \
    -DLLVM_TABLEGEN=$ROOT/llvm_build64/bin/llvm-tblgen \
    $LLVM) ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  build_step "build llvm-symbolizer android/$_arch"
  if ! ninja -C llvm_build_android_$_arch llvm-symbolizer ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  # Based on CompilerRTBuilder in
  # https://android.googlesource.com/toolchain/llvm_android/+/refs/heads/main/src/llvm_android/builders.py
  build_step "cmake compiler-rt android/$_arch"
  if ! (cd compiler_rt_build_android_$_arch && cmake \
    ${CMAKE_COMMON_OPTIONS} \
    -DCMAKE_C_COMPILER=$CLANG_PATH \
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH \
    -DLLVM_CMAKE_DIR=$ROOT/llvm_build64 \
    -DANDROID=1 \
    -DCOMPILER_RT_BUILD_BUILTINS=OFF \
    -DCOMPILER_RT_USE_BUILTINS_LIBRARY=ON \
    -DCOMPILER_RT_USE_LIBCXX=ON \
    -DLIBCXX_HAS_PTHREAD_LIB=OFF \
    -DLIBCXX_HAS_RT_LIB=OFF \
    -DLIBCXXABI_HAS_PTHREAD_LIB=OFF \
    -DCOMPILER_RT_INCLUDE_TESTS=ON \
    -DCOMPILER_RT_ENABLE_WERROR=ON \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS -funwind-tables" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS -funwind-tables" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS -funwind-tables" \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs" \
    -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs" \
    -DCMAKE_MODULE_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs" \
    -DSANITIZER_CXX_ABI="libcxxabi" \
    -DSANITIZER_COMMON_LINK_LIBS=-lunwind \
    -DSANITIZER_COMMON_LINK_FLAGS=-Wl,-z,defs \
    -DCOMPILER_RT_ASAN_ENABLE_EXCEPTIONS=OFF \
    -DCOMPILER_RT_HWASAN_WITH_INTERCEPTORS=OFF \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="$ANDROID_FLAGS -funwind-tables" \
    -DCOMPILER_RT_DEFAULT_TARGET_TRIPLE=${_triple}${ANDROID_API} \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    -DLLVM_LIT_ARGS="-vv --show-unsupported --show-xfail" \
    $(readlink -f $LLVM/../compiler-rt)) ; then
    BUILD_RT_ERR="${BUILD_RT_ERR}|${_arch}|"
    build_failure
  fi

  build_step "build compiler-rt android/$_arch"
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
  build_step "restart adb server"
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
      test_arch_on_device "$_arch" "$_serial" "$BUILD_ID" "$BUILD_FLAVOR"
    fi
  done
}

function start_android_emulator {
  build_step "starting Android emulator"
  stop_android_emulator
  local ACCEL_FLAG="-accel off"
  [[ -w /dev/kvm ]] && ACCEL_FLAG="-accel on"
  mkdir -p $ANDROID_HOME/tmp
  HOME=$ANDROID_HOME TMPDIR=$ANDROID_HOME/tmp \
    $ANDROID_HOME/emulator/emulator -avd san_x86_64 \
    -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect \
    -no-snapshot -wipe-data $ACCEL_FLAG >$ROOT/emulator.log 2>&1 &
  EMULATOR_PID=$!
  if ! timeout 300 $ADB -e wait-for-device shell 'while [[ "$(getprop sys.boot_completed | tr -d "\r")" != "1" ]]; do sleep 1; done' ; then
    cat $ROOT/emulator.log
    build_failure
  fi
}

function stop_android_emulator {
  ${ADB:-adb} -e emu kill 2>/dev/null || true
  if [[ -n "${EMULATOR_PID:-}" ]]; then
    kill $EMULATOR_PID 2>/dev/null || true
    wait $EMULATOR_PID 2>/dev/null || true
    EMULATOR_PID=""
  fi
  pkill -f "$ANDROID_HOME/emulator" 2>/dev/null || true
}

function test_android {
  if [[ -v BUILDBOT_BUILDERNAME ]]; then
    restart_adb_server
  fi

  ADB=adb
  start_android_emulator

  build_step "run all tests"
  ANDROID_DEVICES=$(${ADB} devices | grep 'device$' | sort -r | awk '{print $1}')

  rm -rf tested_arch_*
  for SERIAL in $ANDROID_DEVICES; do
    test_on_device "$SERIAL" $@
  done

  stop_android_emulator

  # Return to avoid exception if we already have error.
  [[ $BUILD_RT_ERR == "" ]] || return

  # for _arg in "$@"; do
  #   local _arch=${_arg%:*}
  #   if [[ ! -f tested_arch_$_arch ]]; then
  #     build_step "unavailable device android/$_arch"
  #     echo @@@STEP_EXCEPTION@@@
  #   fi
  # done
}

function run_command_on_device {
  local _cmd=$1
  local EXIT_CODE=$($ADB shell "mktemp $DEVICE_ROOT/exit_code.XXXXXX") 
  $ADB shell "$_cmd ; echo \$? >$EXIT_CODE"
  return $($ADB shell "cat $EXIT_CODE")
}

function run_tests_on_device {
  local _test_name=$1
  local _test=$2
  local _env=$3

  build_step "run $_test_name tests [$DEVICE_DESCRIPTION]"
  # 'adb shell <command>' on Fugu is missing TMPDIR.
  local ENV="$_env LD_LIBRARY_PATH=$DEVICE_ROOT TMPDIR=$DEVICE_TMPDIR"
  run_command_on_device "$ENV $DEVICE_ROOT/$_test" || build_failure
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

  build_step "device setup [$DEVICE_DESCRIPTION]"
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
    $ADB push $F $DEVICE_ROOT/ >/dev/null || build_failure
  done

  build_step "run lit tests [$DEVICE_DESCRIPTION]"
  (cd $COMPILER_RT_BUILD_DIR && ninja check-all) || build_failure

  run_tests_on_device sanitizer_common SanitizerTest ""
  run_tests_on_device asan AsanNoinstTest ""
  run_tests_on_device "instrumented asan" AsanTest "ASAN_OPTIONS=start_deactivated=1"
}
