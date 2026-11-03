#!/usr/bin/env bash

ANDROID_NDK_VERSION=30
NDK_DIR=android_ndk
CVD_DIR=android_cvd

declare -A ANDROID_API=(
  [aarch64]="37"
  [arm]="34"
  [i686]="34"
  [x86_64]="37"
)

declare -A ANDROID_ABI=(
  [aarch64]="arm64-v8a"
  [arm]="armeabi-v7a"
  [i686]="x86"
  [x86_64]="x86_64"
)

declare -A CVD_BUILD=(
  [aarch64]="aosp-android-latest-release/aosp_cf_arm64_only_phone-userdebug"
  [arm]="aosp-android14-gsi/aosp_cf_arm64_phone-userdebug"
  [i686]="aosp-android14-gsi/aosp_cf_x86_64_phone-userdebug"
  [x86_64]="aosp-android-latest-release/aosp_cf_x86_64_only_phone-userdebug"
)

function download_cuttlefish_images {
  for _arch in "${!CVD_BUILD[@]}"; do
    local _dir="$ROOT/$CVD_DIR/$_arch"
    local _build="${CVD_BUILD[$_arch]}"
    local _host_build="${_build/_arm64_/_x86_64_}"
    local _stamp="${_build}|${_host_build}"
    if [[ "$(cat "$_dir/cvd_build_stamp" 2>/dev/null)" != "$_stamp" ]]; then
      build_step "downloading Android Cuttlefish ($_arch)"
      stop_cuttlefish
      rm -rf "$_dir"
      mkdir -p "$_dir"
      if ! cvd fetch \
        --default_build="$_build" \
        --host_package_build="$_host_build" \
        --target_directory="$_dir" \
        --enable_caching=false ; then
        build_failure
        continue
      fi
      if [[ "$_arch" == "arm" ]]; then
        # Android 14 host_tools passes QEMU 8 flags removed in QEMU 9+.
        local _qemu_dir="$ROOT/$CVD_DIR/aarch64"
        mkdir -p "$_dir/qemu_wrap"
        cat > "$_dir/qemu_wrap/qemu-system-aarch64" <<EOF
#!/usr/bin/env bash
args=()
while ((\$#)); do
  if [[ "\$1" == "-device" && "\${2:-}" == "AC97" ]]; then
    shift 2
    continue
  fi
  args+=("\${1//,scsi=off/}")
  shift
done
exec "$_qemu_dir/bin/x86_64-linux-gnu/qemu/qemu-system-aarch64" -L "$_qemu_dir/usr/share/qemu/x86_64-linux-gnu" "\${args[@]}"
EOF
        chmod +x "$_dir/qemu_wrap/qemu-system-aarch64"
      fi
      echo "$_stamp" > "$_dir/cvd_build_stamp"
    fi
  done
}

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

  download_cuttlefish_images
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

function build_and_test_android { # ARCH triple
  local _arch=$1
  local _triple=$2
  local _api=${ANDROID_API[$_arch]}

  ANDROID_TOOLCHAIN=$ROOT/$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64
  echo "Building for Android API level $_api"

  local ANDROID_LIBRARY_OUTPUT_DIR=$(ls -d $ROOT/llvm_build64/lib/clang/* | tail -1)
  local ANDROID_UNWIND_DIR="$ANDROID_LIBRARY_OUTPUT_DIR/lib/linux/${_arch/i686/i386}"
  local ANDROID_FLAGS="--target=${_triple}${_api} --sysroot=$ANDROID_TOOLCHAIN/sysroot -ffunction-sections -fdata-sections"
  local ANDROID_LINKER_FLAGS="-Wl,--gc-sections -Wl,-z,defs -Wl,--build-id=sha1"

  local CLANG_PATH=$ROOT/llvm_build64/bin/clang
  local CLANGXX_PATH=$ROOT/llvm_build64/bin/clang++

  local ANDROID_CMAKE_ARGS=(
    ${CMAKE_COMMON_OPTIONS}
    -DCMAKE_C_COMPILER=$CLANG_PATH
    -DCMAKE_CXX_COMPILER=$CLANGXX_PATH
    -DLLVM_CMAKE_DIR=$ROOT/llvm_build64
    -DANDROID=1
    -DANDROID_PLATFORM_LEVEL=${_api}
    -DANDROID_NATIVE_API_LEVEL=${_api}
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS"
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS"
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS"
    -DCMAKE_EXE_LINKER_FLAGS="$ANDROID_LINKER_FLAGS"
    -DCMAKE_SHARED_LINKER_FLAGS="$ANDROID_LINKER_FLAGS"
    -DCMAKE_MODULE_LINKER_FLAGS="$ANDROID_LINKER_FLAGS"
  )

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
    "${ANDROID_CMAKE_ARGS[@]}" \
    -DCOMPILER_RT_BUILTINS_HIDE_SYMBOLS=OFF \
    -DCOMPILER_RT_EXCLUDE_ATOMIC_BUILTIN=OFF \
    -DCOMPILER_RT_DEFAULT_TARGET_TRIPLE=${_triple}${_api} \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    $LLVM/../compiler-rt/lib/builtins) ; then
    build_failure
    return 0
  fi

  build_step "build builtins android/$_arch"
  if ! ninja -C builtins_build_android_$_arch ; then
    build_failure
    return 0
  fi

  # Based on LibUnwindBuilder in
  # https://android.googlesource.com/toolchain/llvm_android/+/refs/heads/main/src/llvm_android/builders.py
  build_step "cmake libunwind android/$_arch"
  if ! (cd libunwind_build_android_$_arch && cmake \
    "${ANDROID_CMAKE_ARGS[@]}" \
    -DLLVM_ENABLE_RUNTIMES=libunwind \
    -DCMAKE_ASM_FLAGS="$ANDROID_FLAGS -D_LIBUNWIND_USE_DLADDR=0" \
    -DCMAKE_C_FLAGS="$ANDROID_FLAGS -D_LIBUNWIND_USE_DLADDR=0" \
    -DCMAKE_CXX_FLAGS="$ANDROID_FLAGS -D_LIBUNWIND_USE_DLADDR=0" \
    -DCMAKE_EXE_LINKER_FLAGS="$ANDROID_LINKER_FLAGS -unwindlib=none -nostdlib++" \
    -DCMAKE_SHARED_LINKER_FLAGS="$ANDROID_LINKER_FLAGS -unwindlib=none -nostdlib++" \
    -DLIBUNWIND_ENABLE_SHARED=OFF \
    -DLIBUNWIND_ENABLE_STATIC=ON \
    -DLIBUNWIND_HIDE_SYMBOLS=ON \
    -DLIBUNWIND_USE_FRAME_HEADER_CACHE=OFF \
    -DLIBUNWIND_TARGET_TRIPLE=${_triple}${_api} \
    $LLVM/../runtimes) ; then
    build_failure
    return 0
  fi

  build_step "build libunwind android/$_arch"
  if ! ninja -C libunwind_build_android_$_arch unwind ; then
    build_failure
    return 0
  fi

  build_step "cmake llvm-symbolizer android/$_arch"
  if ! (cd llvm_build_android_$_arch && cmake \
    "${ANDROID_CMAKE_ARGS[@]}" \
    -DLLVM_ENABLE_WERROR=OFF \
    -DLLVM_BINUTILS_INCDIR=/usr/include \
    -DCMAKE_EXE_LINKER_FLAGS="$ANDROID_LINKER_FLAGS -pie" \
    -DCMAKE_SKIP_RPATH=ON \
    -DLLVM_BUILD_RUNTIME=OFF \
    -DLLVM_TABLEGEN=$ROOT/llvm_build64/bin/llvm-tblgen \
    $LLVM) ; then
    build_failure
    return 0
  fi

  build_step "build llvm-symbolizer android/$_arch"
  if ! ninja -C llvm_build_android_$_arch llvm-symbolizer ; then
    build_failure
    return 0
  fi

  # Based on CompilerRTBuilder in
  # https://android.googlesource.com/toolchain/llvm_android/+/refs/heads/main/src/llvm_android/builders.py
  build_step "cmake compiler-rt android/$_arch"
  if ! (cd compiler_rt_build_android_$_arch && cmake \
    "${ANDROID_CMAKE_ARGS[@]}" \
    -DCOMPILER_RT_BUILD_BUILTINS=OFF \
    -DCOMPILER_RT_BUILD_ORC=OFF \
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
    -DSANITIZER_CXX_ABI="libcxxabi" \
    -DSANITIZER_COMMON_LINK_LIBS=-lunwind \
    -DSANITIZER_COMMON_LINK_FLAGS=-Wl,-z,defs \
    -DCOMPILER_RT_HWASAN_WITH_INTERCEPTORS=ON \
    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="$ANDROID_FLAGS -funwind-tables" \
    -DCOMPILER_RT_DEFAULT_TARGET_TRIPLE=${_triple}${_api} \
    -DCOMPILER_RT_OUTPUT_DIR="$ANDROID_LIBRARY_OUTPUT_DIR" \
    -DLLVM_LIT_ARGS="-vv --show-unsupported --show-xfail" \
    $(readlink -f $LLVM/../compiler-rt)) ; then
    build_failure
    return 0
  fi

  build_step "build compiler-rt android/$_arch"
  if ! ninja -C compiler_rt_build_android_$_arch ; then
    build_failure
    return 0
  fi

  test_android "$_arch"
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

  ABILIST=$(${ADB} -s $_serial shell getprop ro.product.cpu.abilist | tr -d '\r')
  patch_abilist "$ABILIST" ABILIST
  for _arch in "$@"; do
    local _abi=${ANDROID_ABI[$_arch]}
    if [[ ",$ABILIST," == *,"$_abi",* ]]; then
      echo "$_serial" >> tested_arch_$_arch
      BUILD_ID=$(${ADB} -s $_serial shell getprop ro.build.id | tr -d '\r')
      BUILD_FLAVOR=$(${ADB} -s $_serial shell getprop ro.build.flavor | tr -d '\r')
      test_arch_on_device "$_arch" "$_serial" "$BUILD_ID" "$BUILD_FLAVOR"
    fi
  done
}

function wait_for_cuttlefish_boot {
  local _adb="${ADB:-adb}"
  for ((i = 0; i < 300; i++)); do
    local _serial
    _serial=$($_adb devices | awk '/:(652[0-9])[[:space:]]+device$/ {print $1; exit}')
    if [[ -n "$_serial" ]] && [[ "$(timeout 10 $_adb -s "$_serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

function start_cuttlefish {
  local _arch=$1
  local _dir="$ROOT/$CVD_DIR/$_arch"
  build_step "starting Android Cuttlefish ($_arch)"
  stop_cuttlefish
  local _cpus=8
  local _mem=16384
  local _extra_args=()
  EXTRA_LIT_OPTS="-j 8"
  if [[ "$_arch" == "x86_64" || "$_arch" == "i686" ]] && [[ -w /dev/kvm ]]; then
    _cpus=$(( $(nproc) / 4 ))
    _mem=32768
    EXTRA_LIT_OPTS=""
  else
    _extra_args+=(--vm_manager=qemu_cli)
    [[ -d "$_dir/qemu_wrap" ]] && _extra_args+=(--qemu_binary_dir="$_dir/qemu_wrap")
  fi
  if ! cvd create \
    --product_path="$_dir" \
    --host_path="$_dir" \
    --cpus="$_cpus" \
    --memory_mb="$_mem" \
    --gpu_mode=guest_swiftshader \
    --enable_sandbox=false \
    --data_policy=always_create \
    --blank_data_image_mb=16384 \
    --report_anonymous_usage_stats=n \
    ${_extra_args[@]+"${_extra_args[@]}"} >"$ROOT/emulator.log" 2>&1 || ! wait_for_cuttlefish_boot ; then
    cat "$ROOT/emulator.log" || true
    tail -n 200 /var/tmp/cvd/"$(id -u)"/*/home/cuttlefish/instances/cvd-1/logs/launcher.log 2>/dev/null || true
    build_failure
  fi
}

function stop_cuttlefish {
  cvd reset -y >/dev/null 2>&1 || true
  ${ADB:-adb} disconnect >/dev/null 2>&1 || true
}

function test_android {
  ADB=adb
  rm -rf tested_arch_*

  for _arch in "$@"; do
    start_cuttlefish "$_arch"

    build_step "run all tests ($_arch)"
    ANDROID_DEVICES=$(${ADB} devices | grep 'device$' | sort -r | awk '{print $1}')

    for SERIAL in $ANDROID_DEVICES; do
      test_on_device "$SERIAL" "$_arch"
    done

    stop_cuttlefish
  done

  for _arch in "$@"; do
    if [[ ! -f tested_arch_$_arch ]]; then
      build_step "unavailable device android/$_arch"
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

  local _sdk=$($ADB shell getprop ro.build.version.sdk | tr -d '\r')
  local _api=${ANDROID_API[$_arch]}
  if [[ "$_sdk" != "$_api" ]]; then
    echo "Unexpected android/$_arch API: $_api vs $_sdk"
    build_warning
  fi

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
  (cd $COMPILER_RT_BUILD_DIR && LIT_OPTS="$LIT_OPTS ${EXTRA_LIT_OPTS:-}" ninja check-all) || build_failure

  run_tests_on_device sanitizer_common SanitizerTest ""
  run_tests_on_device asan AsanNoinstTest ""
  run_tests_on_device "instrumented asan" AsanTest "ASAN_OPTIONS=start_deactivated=1"
}
