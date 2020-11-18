#!/usr/bin/env bash

echo @@@BUILD_STEP Info@@@
(
  set +e
  env
  echo
  uptime
  echo
  ulimit -n 100000
  ulimit -a
  echo
  df -h
  echo
  ccache -s
  echo
  echo "How to reproduce locally: https://github.com/google/sanitizers/wiki/SanitizerBotReproduceBuild"
  echo
  exit 0
)
echo @@@BUILD_STEP Prepare@@@

BUILDBOT_CLOBBER="${BUILDBOT_CLOBBER:-}"
BUILDBOT_REVISION="${BUILDBOT_REVISION:-origin/master}"

function rm_dirs {
  while ! rm -rf $@ ; do sleep 1; done
}

function stage1_clobber {
  rm_dirs llvm_build2_* llvm_build_* libcxx_build_* ${STAGE1_CLOBBER:-}
}

function clobber {
  if [ "$BUILDBOT_CLOBBER" != "" ]; then
    echo @@@BUILD_STEP clobber@@@
    rm_dirs svn_checkout llvm llvm-project llvm_build0 ${CLOBBER:-}
    stage1_clobber
    ! test "$(ls -A .)" || echo @@@STEP_EXCEPTION@@@
  fi
}

BUILDBOT_MONO_REPO_PATH=${BUILDBOT_MONO_REPO_PATH:-}

function buildbot_update {
  echo @@@BUILD_STEP update $BUILDBOT_REVISION@@@
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
      git fetch --depth $DEPTH origin master
      git clean -fd
      local REV=${BUILDBOT_REVISION}
      if [[  "$REV" != "origin/master" ]] ; then
        # "git fetch --depth 1 origin $REV" does not work with 2.11 on bots
        while true ; do
          git checkout $REV && break
          git rev-list --pretty --max-count=1 origin/master
          git rev-list --pretty --max-parents=0 origin/master
          echo "DEPTH=$DEPTH is too small"
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

function common_stage1_variables {
  STAGE1_DIR=llvm_build0
  stage1_clang_path=$ROOT/${STAGE1_DIR}/bin
  llvm_symbolizer_path=${stage1_clang_path}/llvm-symbolizer
  STAGE1_AS_COMPILER="-DCMAKE_C_COMPILER=${stage1_clang_path}/clang -DCMAKE_CXX_COMPILER=${stage1_clang_path}/clang++"
}

function build_stage1_clang_impl {
  rm -rf ${STAGE1_DIR}
  mkdir -p ${STAGE1_DIR}
  local cmake_stage1_options="${CMAKE_COMMON_OPTIONS}"
  cmake_stage1_options="${cmake_stage1_options} -DLLVM_ENABLE_PROJECTS='clang;compiler-rt;lld'"
  if ccache -s ; then
    cmake_stage1_options="${cmake_stage1_options} -DLLVM_CCACHE_BUILD=ON"
  fi
  (cd ${STAGE1_DIR} && cmake ${cmake_stage1_options} $LLVM && ninja)
}

function build_stage1_clang {
  echo @@@BUILD_STEP stage1 build all@@@
  export STAGE1_DIR=llvm_build0
  common_stage1_variables
  build_stage1_clang_impl

  echo @@@BUILD_STEP Clobber stage1 users
  stage1_clobber
}

function build_stage1_clang_at_revison {
  common_stage1_variables

  curl -s https://raw.githubusercontent.com/chromium/chromium/master/tools/clang/scripts/update.py \
    | python - --output-dir=${STAGE1_DIR}

  echo @@@BUILD_STEP using pre-built stage1 clang at $(cat ${STAGE1_DIR}/cr_build_revision)@@@
}

function common_stage2_variables {
  cmake_stage2_common_options="\
    ${CMAKE_COMMON_OPTIONS} ${STAGE1_AS_COMPILER} -DLLVM_USE_LINKER=lld"
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

  # Don't use libc++/libc++abi in UBSan builds (due to known bugs).
  echo @@@BUILD_STEP stage2/$sanitizer_name build libcxx@@@
  rm -rf ${libcxx_build_dir}
  mkdir -p ${libcxx_build_dir}
  (cd ${libcxx_build_dir} && \
    cmake \
      ${cmake_stage2_common_options} \
      -DLLVM_ENABLE_PROJECTS='libcxx;libcxxabi' \
      -DCMAKE_BUILD_TYPE=${build_type} \
      -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
      $LLVM && \
    ninja cxx cxxabi) || echo $step_result
  local sanitizer_ldflags="-lc++abi -Wl,--rpath=${ROOT}/${libcxx_build_dir}/lib -L${ROOT}/${libcxx_build_dir}/lib"
  local sanitizer_cflags="-nostdinc++ -isystem ${ROOT}/${libcxx_build_dir}/include -isystem ${ROOT}/${libcxx_build_dir}/include/c++/v1"

  echo @@@BUILD_STEP stage2/$sanitizer_name build@@@

  # See http://llvm.org/bugs/show_bug.cgi?id=19071, http://www.cmake.org/Bug/view.php?id=15264
  local cmake_bug_workaround_cflags="$sanitizer_ldflags $fsanitize_flag -w"
  sanitizer_cflags="$sanitizer_cflags $cmake_bug_workaround_cflags"

  rm -rf ${build_dir}
  mkdir -p ${build_dir}
  local cmake_stage2_clang_options="-DLLVM_ENABLE_PROJECTS='clang;lld;clang-tools-extra'"
  (cd ${build_dir} && \
   cmake \
     ${cmake_stage2_common_options} \
     ${cmake_stage2_clang_options} \
     -DCMAKE_BUILD_TYPE=${build_type} \
     -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
     -DLLVM_ENABLE_LIBCXX=ON \
     -DCMAKE_C_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_CXX_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_EXE_LINKER_FLAGS="${sanitizer_ldflags}" \
     $LLVM && \
   ninja) || echo $step_result
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
  
  echo @@@BUILD_STEP stage2/$sanitizer_name check@@@
  ninja -C ${build_dir} check-all || echo $step_result
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
  echo @@@BUILD_STEP build stage3/$sanitizer_name build@@@
  rm -rf ${build_dir}
  mkdir -p ${build_dir}
  (cd ${build_dir} && \
   cmake \
     ${CMAKE_COMMON_OPTIONS} \
     -DLLVM_ENABLE_PROJECTS='clang;lld,clang-tools-extra' \
     -DCMAKE_C_COMPILER=${clang_path}/clang \
     -DCMAKE_CXX_COMPILER=${clang_path}/clang++ \
     -DLLVM_USE_LINKER=lld \
     $LLVM && \
  ninja clang) || echo $step_result
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

  echo @@@BUILD_STEP stage3/$sanitizer_name check@@@
  (cd ${build_dir} && ninja check-all) || echo $step_result
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
