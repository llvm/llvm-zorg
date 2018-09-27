#!/usr/bin/env bash

uptime

function update_or_checkout {
  local rev_arg=$1
  local repo=$2
  local tree=$3
  if [ -d ${tree} ]; then
    svn cleanup "${tree}"
    svn revert -R "${tree}"
    svn up "${tree}" $rev_arg
  else
    mkdir -p svn_checkout
    DIR=$(mktemp -d -p `pwd`/svn_checkout XXXXXX)
    svn co "${repo}" $DIR/${tree} $rev_arg
  fi
}

function buildbot_update {
    local rev_arg=
    if [ "$BUILDBOT_REVISION" != "" ]; then
        rev_arg="-r$BUILDBOT_REVISION"
    fi

    if [ "$rev_arg" == "" ]; then
        rev_arg="-r"$(svn info http://llvm.org/svn/llvm-project/llvm/trunk | grep '^Revision:' | awk '{print $2}')
    fi

    rm -rf svn_checkout

    update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/llvm/trunk llvm &

    # XXX: Keep this list in sync with the change filter in buildbot/osuosl/master/master.cfg.
    update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/cfe/trunk llvm/tools/clang &
    update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/compiler-rt/trunk llvm/projects/compiler-rt &
    if [ "$CHECK_LIBCXX" != "0" ]; then
      update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/libcxx/trunk llvm/projects/libcxx &
      update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/libcxxabi/trunk llvm/projects/libcxxabi &
      update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/libunwind/trunk llvm/projects/libunwind &
    fi
    if [ "$CHECK_LLD" != "0" ]; then
      update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/lld/trunk llvm/tools/lld &
    fi
    wait

    # Merge checked out temporarily directories.
    if [ -d svn_checkout ]; then
      for D in svn_checkout/*; do
        cp -rflP $D/* .
      done
      rm -rf svn_checkout
    fi
}

function set_chrome_suid_sandbox {
  export CHROME_DEVEL_SANDBOX=/usr/local/sbin/chrome-devel-sandbox
}

function fetch_depot_tools {
  ROOT=$1
  (
    cd $ROOT
    if [ ! -d depot_tools ]; then
      git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
    fi
  )
  export PATH="$ROOT/depot_tools:$PATH"
}

function check_out_chromium {
  CHROME=$1
  (
  if [ ! -d $CHROME ]; then
    mkdir $CHROME
    pushd $CHROME
    fetch --nohooks chromium --nosvn=True 

    # Sync to LKGR, see http://crbug.com/109191
    mv .gclient .gclient-tmp
    cat .gclient-tmp  | \
        sed 's/"safesync_url": ""/"safesync_url": "https:\/\/chromium-status.appspot.com\/git-lkgr"/' > .gclient
    rm .gclient-tmp
    popd
  fi
  cd $CHROME/src
  git checkout master
  git pull
  gclient sync --nohooks --jobs=16
  )
}

function gclient_runhooks {
  CHROME=$1
  CLANG_BUILD=$2
  CUSTOM_GYP_DEFINES=$3
  (
  cd $CHROME/src
  
  # Clobber Chromium to catch possible LLVM regressions early.
  rm -rf out/Release
  
  export COMMON_GYP_DEFINES="use_allocator=none use_aura=1 clang_use_chrome_plugins=0 component=static_library"
  export GYP_DEFINES="$CUSTOM_GYP_DEFINES $COMMON_GYP_DEFINES"
  export GYP_GENERATORS=ninja
  export CLANG_BIN=$CLANG_BUILD/bin
  export CC="$CLANG_BIN/clang"
  export CXX="$CLANG_BIN/clang++"
  
  gclient runhooks
  )
}

function build_stage1_clang {
  mkdir -p ${STAGE1_DIR}
  cmake_stage1_options="${CMAKE_COMMON_OPTIONS}"
  (cd ${STAGE1_DIR} && cmake ${cmake_stage1_options} $LLVM && \
    ninja clang compiler-rt llvm-symbolizer)
}

function build_stage1_clang_at_revison {
  local HOST_CLANG_REVISION=343264

  if  [ -r ${STAGE1_DIR}/host_clang_revision ] && \
      [ "$(cat ${STAGE1_DIR}/host_clang_revision)" == $HOST_CLANG_REVISION ]
  then
    echo @@@BUILD_STEP using pre-built stage1 clang at r$HOST_CLANG_REVISION@@@
  else
    echo @@@BUILD_STEP sync to r$HOST_CLANG_REVISION@@@
    real_buildbot_revision=$BUILDBOT_REVISION
    BUILDBOT_REVISION=$HOST_CLANG_REVISION
    buildbot_update

    echo @@@BUILD_STEP Clear ${STAGE1_DIR} ${STAGE1_CLOBBER}
    rm -rf ${STAGE1_DIR} ${STAGE1_CLOBBER}

    echo @@@BUILD_STEP build stage1 clang at r$HOST_CLANG_REVISION@@@

    build_stage1_clang

    echo $HOST_CLANG_REVISION > ${STAGE1_DIR}/host_clang_revision

    BUILDBOT_REVISION=$real_buildbot_revision
  fi
}

function common_stage2_variables {
  local stage1_clang_path=$ROOT/${STAGE1_DIR}/bin
  cmake_stage2_common_options="\
    ${CMAKE_COMMON_OPTIONS} \
    -DCMAKE_C_COMPILER=${stage1_clang_path}/clang \
    -DCMAKE_CXX_COMPILER=${stage1_clang_path}/clang++ \
    "
  llvm_symbolizer_path=${stage1_clang_path}/llvm-symbolizer
}

function build_stage2 {
  local sanitizer_name=$1
  local libcxx_build_dir=$2
  local build_dir=$3
  local step_result=$4

  common_stage2_variables

  if [ "$sanitizer_name" == "msan" ]; then
    export MSAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    local llvm_use_sanitizer="Memory"
    local fsanitize_flag="-fsanitize=memory"
    BUILDBOT_MSAN_ORIGINS=${BUILDBOT_MSAN_ORIGINS:-}
    if [ "$BUILDBOT_MSAN_ORIGINS" != "" ]; then
      llvm_use_sanitizer="MemoryWithOrigins"
    fi
    local build_type="Release"
  elif [ "$sanitizer_name" == "asan" ]; then
    export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export ASAN_OPTIONS="check_initialization_order=true:detect_stack_use_after_return=1:detect_leaks=1"
    local llvm_use_sanitizer="Address"
    local fsanitize_flag="-fsanitize=address"
    local build_type="Release"
  elif [ "$sanitizer_name" == "ubsan" ]; then
    export UBSAN_OPTIONS="external_symbolizer_path=${llvm_symbolizer_path}:print_stacktrace=1"
    local llvm_use_sanitizer="Undefined"
    local fsanitize_flag="-fsanitize=undefined"
    local build_type="Release"
  else
    echo "Unknown sanitizer!"
    exit 1
  fi

  local sanitizer_ldflags=""
  local sanitizer_cflags=""
  local cmake_libcxx_flag="-DLLVM_ENABLE_LIBCXX=OFF"

  # Don't use libc++/libc++abi in UBSan builds (due to known bugs).
  if [ "$CHECK_LIBCXX" != "0" -a \
       "$sanitizer_name" != "ubsan" ]; then
    echo @@@BUILD_STEP build libcxx/$sanitizer_name@@@
    mkdir -p ${libcxx_build_dir}
    (cd ${libcxx_build_dir} && \
      cmake \
        ${cmake_stage2_common_options} \
        -DCMAKE_BUILD_TYPE=${build_type} \
        -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
        $LLVM && \
      ninja cxx cxxabi) || echo $step_result
    sanitizer_ldflags="$sanitizer_ldflags -lc++abi -Wl,--rpath=${ROOT}/${libcxx_build_dir}/lib -L${ROOT}/${libcxx_build_dir}/lib"
    sanitizer_cflags="$sanitizer_cflags -nostdinc++ -isystem ${ROOT}/${libcxx_build_dir}/include -isystem ${ROOT}/${libcxx_build_dir}/include/c++/v1"
    cmake_libcxx_flag="-DLLVM_ENABLE_LIBCXX=ON"
  fi

  echo @@@BUILD_STEP build clang/$sanitizer_name@@@

  # See http://llvm.org/bugs/show_bug.cgi?id=19071, http://www.cmake.org/Bug/view.php?id=15264
  local cmake_bug_workaround_cflags="$sanitizer_ldflags $fsanitize_flag -w"
  sanitizer_cflags="$sanitizer_cflags $cmake_bug_workaround_cflags"

  mkdir -p ${build_dir}
  local extra_dir
  if [ "$CHECK_LLD" != "0" ]; then
    extra_dir="lld"
  fi
  (cd ${build_dir} && \
   cmake ${cmake_stage2_common_options} \
     -DCMAKE_BUILD_TYPE=${build_type} \
     -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
     ${cmake_libcxx_flag} \
     -DCMAKE_C_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_CXX_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_EXE_LINKER_FLAGS="${sanitizer_ldflags}" \
     $LLVM && \
   ninja clang ${extra_dir}) || echo $step_result
}

function build_stage2_msan {
  build_stage2 msan "${STAGE2_LIBCXX_MSAN_DIR}" "${STAGE2_MSAN_DIR}" @@@STEP_FAILURE@@@
}

function build_stage2_asan {
  build_stage2 asan "${STAGE2_LIBCXX_ASAN_DIR}" "${STAGE2_ASAN_DIR}" @@@STEP_FAILURE@@@
}

function build_stage2_ubsan {
  build_stage2 ubsan "${STAGE2_LIBCXX_UBSAN_DIR}" "${STAGE2_UBSAN_DIR}" @@@STEP_FAILURE@@@
}

function check_stage2 {
  local sanitizer_name=$1
  local build_dir=$2
  local step_result=$3
  echo @@@BUILD_STEP check-llvm ${sanitizer_name}@@@

  (cd ${build_dir} && ninja check-llvm) || echo $step_result

  echo @@@BUILD_STEP check-clang ${sanitizer_name}@@@

  (cd ${build_dir} && ninja check-clang) || echo $step_result

  if [ "$CHECK_LLD" != "0" ]; then
    echo @@@BUILD_STEP check-lld ${sanitizer_name}@@@
    (cd ${build_dir} && ninja check-lld) || echo $step_result
  fi
}

function check_stage2_msan {
  check_stage2 msan "${STAGE2_MSAN_DIR}" @@@STEP_FAILURE@@@
}

function check_stage2_asan {
  check_stage2 asan "${STAGE2_ASAN_DIR}" @@@STEP_FAILURE@@@
}

function check_stage2_ubsan {
  check_stage2 ubsan "${STAGE2_UBSAN_DIR}" @@@STEP_FAILURE@@@
}
