#!/usr/bin/env bash

echo
echo "How to reproduce locally: https://github.com/google/sanitizers/wiki/SanitizerBotReproduceBuild"
echo

uptime

function stage1_clobber {
  rm -rf llvm_build2_* llvm_build_* libcxx_build_* ${STAGE1_CLOBBER:-}
}

function clobber {
  # Clobber if USE_GIT was changed
  local clobber_if_exists=llvm-project
  if [[ "$USE_GIT" != "0" ]]; then
    clobber_if_exists=llvm
  fi
  if [[ -d $clobber_if_exists ]]; then
    BUILDBOT_CLOBBER=1
  fi

  if [ "$BUILDBOT_CLOBBER" != "" ]; then
    echo @@@BUILD_STEP clobber@@@
    rm -rf svn_checkout llvm llvm-project llvm_build0 ${CLOBBER:-}
    stage1_clobber
    ! test "$(ls -A .)" || echo @@@STEP_EXCEPTION@@@
  fi
}

function update_or_checkout {
  local rev_arg=$1
  local repo=$2
  local tree=$3
  
  if [ -d ${tree} ]; then
    (svn cleanup "${tree}" && svn revert -R "${tree}" && svn up "${tree}" $rev_arg) || \
      (rm -rf ${tree} && update_or_checkout $@)
  else
    mkdir -p svn_checkout
    DIR=$(mktemp -d -p `pwd`/svn_checkout XXXXXX)
    svn co "${repo}" $DIR/${tree} $rev_arg || echo @@@STEP_EXCEPTION@@@
  fi
}

BUILDBOT_MONO_REPO_PATH=${BUILDBOT_MONO_REPO_PATH:-}

function get_sources {
  local rev_arg=$1
  local repo_name=$2
  local tree=$3

  if [ -d "$BUILDBOT_MONO_REPO_PATH" ]; then
    # Excludes are needed only for llvm but they should not hurt for the rest.
    rsync -avh --delete \
          --exclude=projects/compiler-rt/ \
          --exclude=projects/libcxx/ \
          --exclude=projects/libcxxabi/ \
          --exclude=projects/libunwind/ \
          --exclude=tools/clang/ \
          --exclude=tools/lld/ \
        $BUILDBOT_MONO_REPO_PATH/${repo_name/cfe/clang}/ \
        $tree/ || exit 1
    return
  fi

  update_or_checkout "$rev_arg" http://llvm.org/svn/llvm-project/$repo_name/trunk $tree &
}


function buildbot_update {
    echo @@@BUILD_STEP update $BUILDBOT_REVISION@@@
    if [[ "$USE_GIT" != "0" ]]; then
      buildbot_update_git
      return
    fi
    if [[ -d "$BUILDBOT_MONO_REPO_PATH" ]]; then
      BUILDBOT_REVISION="-"
    else
      if [[ "$BUILDBOT_REVISION" == "-" ]]; then
        return
      fi
    fi

    local rev_arg=
    if [ "$BUILDBOT_REVISION" != "" ]; then
        rev_arg="-r$BUILDBOT_REVISION"
    fi

    if [ "$rev_arg" == "" ]; then
        rev_arg="-r"$(svn info http://llvm.org/svn/llvm-project/llvm/trunk | grep '^Revision:' | awk '{print $2}')
    fi

    rm -rf svn_checkout

    get_sources "$rev_arg" llvm llvm

    # XXX: Keep this list in sync with the change filter in buildbot/osuosl/master/master.cfg.
    get_sources "$rev_arg" cfe llvm/tools/clang
    get_sources "$rev_arg" compiler-rt llvm/projects/compiler-rt
    if [ "$CHECK_LIBCXX" != "0" ]; then
      get_sources "$rev_arg" libcxx llvm/projects/libcxx
      get_sources "$rev_arg" libcxxabi llvm/projects/libcxxabi
      get_sources "$rev_arg" libunwind llvm/projects/libunwind
    fi
    if [ "$CHECK_LLD" != "0" ]; then
      get_sources "$rev_arg" lld llvm/tools/lld
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

function buildbot_update_git {
  if [[ -d "$BUILDBOT_MONO_REPO_PATH" ]]; then
    LLVM=$BUILDBOT_MONO_REPO_PATH/llvm
  else
    (
      local DEPTH=100
      [[ -d llvm-project ]] || (
        mkdir -p llvm-project
        cd llvm-project
        git init
        git remote add origin https://github.com/llvm/llvm-project.git
      )
      cd llvm-project
      git clean -fd
      local REV=
      if [[ "$BUILDBOT_REVISION" == "" ]] ; then
        REV=origin/master
        git fetch origin
      elif echo ${BUILDBOT_REVISION} | grep -P "^[0-9]{1,7}$"; then
        while true ; do
          REV=$(git log --format="%H" -n1 --grep "^llvm-svn: ${BUILDBOT_REVISION}$" origin/master)
          [[ "$REV" == "" ]] || break
          git rev-list --pretty --max-count=1 origin/master
          git rev-list --pretty --max-parents=0 origin/master
          echo "DEPTH=$DEPTH is too small"
          echo @@@STEP_EXCEPTION@@@
          [[ "$DEPTH" -le "1000000" ]] || exit 1
          DEPTH=$(( $DEPTH * 10 ))
          git fetch --depth $DEPTH origin
        done
      else
        REV=${BUILDBOT_REVISION}
        #git fetch --depth 1 origin $REV
        while true ; do
          git checkout $REV && break
          git rev-list --pretty --max-count=1 origin/master
          git rev-list --pretty --max-parents=0 origin/master
          echo "DEPTH=$DEPTH is too small"
          echo @@@STEP_EXCEPTION@@@
          [[ "$DEPTH" -le "1000000" ]] || exit 1
          DEPTH=$(( $DEPTH * 10 ))
          git fetch --depth $DEPTH origin
        done
      fi
      git checkout $REV
      git status
      git rev-list --pretty --max-count=1 HEAD
    ) || { echo @@@STEP_EXCEPTION@@@ ; exit 1 ; }
    LLVM=$ROOT/llvm-project/llvm
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

function common_stage1_variables {
  STAGE1_DIR=llvm_build0
  stage1_clang_path=$ROOT/${STAGE1_DIR}/bin
  llvm_symbolizer_path=${stage1_clang_path}/llvm-symbolizer
  STAGE1_AS_COMPILER="-DCMAKE_C_COMPILER=${stage1_clang_path}/clang -DCMAKE_CXX_COMPILER=${stage1_clang_path}/clang++"
}

function build_stage1_clang_impl {
  mkdir -p ${STAGE1_DIR}
  local cmake_stage1_options="${CMAKE_COMMON_OPTIONS}"
  if [[ "$USE_GIT" != "0" ]]; then
    cmake_stage1_options="${cmake_stage1_options} -DLLVM_ENABLE_PROJECTS='clang;compiler-rt;lld'"
  fi
  (cd ${STAGE1_DIR} && cmake ${cmake_stage1_options} $LLVM && \
    ninja clang lld compiler-rt llvm-symbolizer)
}

function build_stage1_clang {
  echo @@@BUILD_STEP build stage1 clang@@@
  export STAGE1_DIR=llvm_build0
  common_stage1_variables
  build_stage1_clang_impl

  echo @@@BUILD_STEP Clobber stage1 users
  stage1_clobber
}

function build_stage1_clang_at_revison {
  local HOST_CLANG_REVISION=e7ab59eda98094183cd4d75f5edde9e07e27072b
  common_stage1_variables

  if  [ -r ${STAGE1_DIR}/host_clang_revision ] && \
      [ "$(cat ${STAGE1_DIR}/host_clang_revision)" == $HOST_CLANG_REVISION ]
  then
    echo @@@BUILD_STEP using pre-built stage1 clang at r$HOST_CLANG_REVISION@@@
  else
    BUILDBOT_REVISION=$HOST_CLANG_REVISION buildbot_update

    rm -rf ${STAGE1_DIR}
    echo @@@BUILD_STEP build stage1 clang at r$HOST_CLANG_REVISION@@@
    build_stage1_clang_impl && \
      ( echo $HOST_CLANG_REVISION > ${STAGE1_DIR}/host_clang_revision )
  fi
}

function common_stage2_variables {
  cmake_stage2_common_options="\
    ${CMAKE_COMMON_OPTIONS} ${STAGE1_AS_COMPILER}"
}

function build_stage2 {
  local sanitizer_name=$1
  local step_result=$2
  local libcxx_build_dir=libcxx_build_${sanitizer_name}
  local build_dir=llvm_build_${sanitizer_name}
  export STAGE2_DIR=${build_dir}

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
    local cmake_stage2_libcxx_options=
    if [[ "$USE_GIT" != "0" ]]; then
      cmake_stage2_libcxx_options="-DLLVM_ENABLE_PROJECTS='libcxx;libcxxabi'"
    fi
    (cd ${libcxx_build_dir} && \
      cmake \
        ${cmake_stage2_common_options} \
        ${cmake_stage2_libcxx_options} \
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
  local cmake_stage2_clang_options=
  if [[ "$USE_GIT" != "0" ]]; then
    local projects=clang
    if [[ "$CHECK_LLD" != "0" ]]; then
      projects="${projects};lld"
    fi
    cmake_stage2_clang_options="-DLLVM_ENABLE_PROJECTS='${projects}'"
  fi
  (cd ${build_dir} && \
   cmake \
     ${cmake_stage2_common_options} \
     ${cmake_stage2_clang_options} \
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
  build_stage2 msan @@@STEP_FAILURE@@@
}

function build_stage2_asan {
  build_stage2 asan @@@STEP_FAILURE@@@
}

function build_stage2_ubsan {
  build_stage2 ubsan @@@STEP_FAILURE@@@
}

function check_stage2 {
  local sanitizer_name=$1
  local step_result=$2
  local build_dir=${STAGE2_DIR}
  
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
  check_stage2 msan @@@STEP_FAILURE@@@
}

function check_stage2_asan {
  check_stage2 asan @@@STEP_FAILURE@@@
}

function check_stage2_ubsan {
  check_stage2 ubsan @@@STEP_FAILURE@@@
}

function build_stage3 {
  local sanitizer_name=$1
  local step_result=$2
  local build_dir=llvm_build2_${sanitizer_name}

  local clang_path=$ROOT/${STAGE2_DIR}/bin
  local cmake_stage3_options="${CMAKE_COMMON_OPTIONS} -DCMAKE_C_COMPILER=${clang_path}/clang -DCMAKE_CXX_COMPILER=${clang_path}/clang++"
  if [[ "$USE_GIT" != "0" ]]; then
    cmake_stage3_options="${cmake_stage3_options} -DLLVM_ENABLE_PROJECTS='clang'"
  fi

  echo @@@BUILD_STEP build stage3/$sanitizer_name clang@@@
  (mkdir -p ${build_dir} && cd ${build_dir} && cmake ${cmake_stage3_options} $LLVM && ninja clang) || \
      echo $step_result
}

function build_stage3_msan {
  build_stage3 msan @@@STEP_FAILURE@@@
}

function build_stage3_asan {
  build_stage3 asan @@@STEP_FAILURE@@@
}

function build_stage3_ubsan {
  build_stage3 ubsan @@@STEP_FAILURE@@@
}

function check_stage3 {
  local sanitizer_name=$1
  local step_result=$2
  local build_dir=llvm_build2_${sanitizer_name}

  echo @@@BUILD_STEP stage3/$sanitizer_name check-llvm@@@
  (cd ${build_dir} && ninja check-llvm) || echo $step_result

  echo @@@BUILD_STEP stage3/$sanitizer_name check-clang@@@
  (cd ${build_dir} && ninja check-clang) || echo $step_result
}

function check_stage3_msan {
  check_stage3 msan @@@STEP_FAILURE@@@
}

function check_stage3_asan {
  check_stage3 asan @@@STEP_FAILURE@@@
}

function check_stage3_ubsan {
  check_stage3 ubsan @@@STEP_FAILURE@@@
}
