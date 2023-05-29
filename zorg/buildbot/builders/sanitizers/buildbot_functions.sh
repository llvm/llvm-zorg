#!/usr/bin/env bash

BUILDBOT_CLOBBER="${BUILDBOT_CLOBBER:-}"
BUILDBOT_REVISION="${BUILDBOT_REVISION:-origin/main}"

HOST_CLANG_REVISION=llvmorg-$(curl https://api.github.com/repos/llvm/llvm-project/releases/latest -s | jq .name -r | cut -f2 -d' ')
CMAKE_COMMON_OPTIONS+=" -DLLVM_APPEND_VC_REV=OFF -GNinja -DCMAKE_BUILD_TYPE=Release"

export LC_ALL=C

if ccache -s ; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_CCACHE_BUILD=ON"
fi

if lld --version ; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_ENABLE_LLD=ON"
fi

function include_config() {
  local P=.
  while true ; do
    local F=${P}/sanitizer_buildbot_config
    if [[ -f ${F} ]] ; then
      . ${F}
      break
    fi
    [[ "${P}" -ef '/' ]] && break
    P="${P}/.."
  done
}

include_config

echo @@@BUILD_STEP Info@@@
(
  set +e
  env | sort
  echo
  uptime
  echo
  ulimit -n 1000000
  ulimit -a
  echo
  df -h
  echo
  ccache -ps
  exit 0
)

echo @@@BUILD_STEP Prepare@@@

export LIT_OPTS="--time-tests"

function rm_dirs {
  while ! rm -rf $@ ; do sleep 1; done
}

function cleanup() {
  [[ -v BUILDBOT_BUILDERNAME ]] || return 0
  echo @@@BUILD_STEP cleanup@@@
  rm_dirs llvm_build2_* llvm_build_* libcxx_build_* compiler_rt_build* symbolizer_build* $@
  if ccache -s >/dev/null ; then
    rm_dirs llvm_build64 clang_build
  fi
  ls
}

function clobber {
  if [[ "$BUILDBOT_CLOBBER" != "" ]]; then
    echo @@@BUILD_STEP clobber@@@
    if [[ ! -v BUILDBOT_BUILDERNAME ]]; then
      echo "Clobbering is supported only on buildbot only!"
      exit 1
    fi
    rm_dirs *
  else
    BUILDBOT_BUILDERNAME=1 cleanup $@
  fi
}

BUILDBOT_MONO_REPO_PATH=${BUILDBOT_MONO_REPO_PATH:-}

function buildbot_update {
  if [[ "${BUILDBOT_BISECT_MODE:-}" == "1" ]]; then
    echo "@@@BUILD_STEP bisect status@@@"
    (
      cd llvm-project
      git bisect visualize --oneline
      git bisect log
      git status
    )
    LLVM=$ROOT/llvm-project/llvm
    return 0
  fi
  echo "@@@BUILD_STEP update $BUILDBOT_REVISION@@@"
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
        git config --local advice.detachedHead false
      )
      cd llvm-project
      git fetch origin
      git clean -fd
      git reset --hard
      git checkout -f "${BUILDBOT_REVISION}"
      git status
      git rev-list --pretty --max-count=1 HEAD
    ) || { build_exception ; exit 1 ; }
    LLVM=$ROOT/llvm-project/llvm
  fi
}

function common_stage1_variables {
  STAGE1_DIR=llvm_build0
  stage1_clang_path=$ROOT/${STAGE1_DIR}/bin
  llvm_symbolizer_path=${stage1_clang_path}/llvm-symbolizer
  export LLVM_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
  STAGE1_AS_COMPILER="-DCMAKE_C_COMPILER=${stage1_clang_path}/clang -DCMAKE_CXX_COMPILER=${stage1_clang_path}/clang++"
}

function build_stage1_clang_impl {
  mkdir -p ${STAGE1_DIR}
  local cmake_stage1_options="${CMAKE_COMMON_OPTIONS} -DLLVM_ENABLE_PROJECTS='clang;compiler-rt;lld'"
  if clang -v ; then
    cmake_stage1_options+=" -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++"
  fi
  (cd ${STAGE1_DIR} && cmake ${cmake_stage1_options} $LLVM && ninja)
  md5sum ${STAGE1_DIR}/bin/clang* || true
}

function build_stage1_clang {
  echo @@@BUILD_STEP stage1 build all@@@
  common_stage1_variables
  build_stage1_clang_impl
}

function download_clang_from_chromium {
  common_stage1_variables

  curl -s https://raw.githubusercontent.com/chromium/chromium/main/tools/clang/scripts/update.py \
    | python3 - --output-dir=${STAGE1_DIR}

  echo @@@BUILD_STEP using pre-built stage1 clang at $(cat ${STAGE1_DIR}/cr_build_revision)@@@
}

function build_clang_at_release_tag {
  common_stage1_variables

  if  [ -r ${STAGE1_DIR}/host_clang_revision ] && \
      [ "$(cat ${STAGE1_DIR}/host_clang_revision)" == $HOST_CLANG_REVISION ]
  then
    echo "@@@BUILD_STEP using pre-built stage1 clang at r${HOST_CLANG_REVISION}@@@"
  else
    BUILDBOT_MONO_REPO_PATH= BUILDBOT_REVISION="${HOST_CLANG_REVISION}" buildbot_update

    rm -rf ${STAGE1_DIR}
    echo @@@BUILD_STEP build stage1 clang at $HOST_CLANG_REVISION@@@
    build_stage1_clang_impl && \
      ( echo $HOST_CLANG_REVISION > ${STAGE1_DIR}/host_clang_revision )
  fi
}

function build_stage1_clang_at_revison {
  build_clang_at_release_tag
}

function common_stage2_variables {
  cmake_stage2_common_options="\
    ${CMAKE_COMMON_OPTIONS} ${STAGE1_AS_COMPILER} -DLLVM_USE_LINKER=lld"
}

function build_stage2 {
  local sanitizer_name=$1
  echo @@@BUILD_STEP stage2/$sanitizer_name build libcxx@@@

  local libcxx_build_dir=libcxx_build_${sanitizer_name}
  local build_dir=llvm_build_${sanitizer_name}
  export STAGE2_DIR=${build_dir}
  local cmake_libcxx_cflags=

  common_stage2_variables

  local fno_sanitize_flag=

  if [ "$sanitizer_name" == "msan" ]; then
    export MSAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    llvm_use_sanitizer="Memory"
    fsanitize_flag="-fsanitize=memory"
  elif [ "$sanitizer_name" == "msan_track_origins" ]; then
    export MSAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    llvm_use_sanitizer="MemoryWithOrigins"
    fsanitize_flag="-fsanitize=memory -fsanitize-memory-track-origins"
  elif [ "$sanitizer_name" == "asan" ]; then
    export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export ASAN_OPTIONS="check_initialization_order=true"
    llvm_use_sanitizer="Address"
    fsanitize_flag="-fsanitize=address"
    # FIXME: False ODR violations in libcxx tests.
    # https://github.com/google/sanitizers/issues/1017
    cmake_libcxx_cflags="-mllvm -asan-use-private-alias=1"
  elif [ "$sanitizer_name" == "hwasan" ]; then
    export HWASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export HWASAN_OPTIONS="abort_on_error=1"
    llvm_use_sanitizer="HWAddress"
    fsanitize_flag="-fsanitize=hwaddress -mllvm -hwasan-use-after-scope=1"
    # FIXME: Support globals with DSO https://github.com/llvm/llvm-project/issues/57206
    cmake_stage2_common_options+=" -DLLVM_ENABLE_PLUGINS=OFF"
  elif [ "$sanitizer_name" == "ubsan" ]; then
    export UBSAN_OPTIONS="external_symbolizer_path=${llvm_symbolizer_path}:print_stacktrace=1"
    llvm_use_sanitizer="Undefined"
    fsanitize_flag="-fsanitize=undefined"
    # FIXME: After switching to LLVM_ENABLE_RUNTIMES, vptr has infitine
    # recursion.
    fno_sanitize_flag+=" -fno-sanitize=vptr"
  elif [ "$sanitizer_name" == "asan_ubsan" ]; then
    export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export ASAN_OPTIONS="check_initialization_order=true"
    llvm_use_sanitizer="Address;Undefined"
    fsanitize_flag="-fsanitize=address,undefined"
    # FIXME: After switching to LLVM_ENABLE_RUNTIMES, vptr has infitine
    # recursion.
    fno_sanitize_flag+=" -fno-sanitize=vptr"
  else
    echo "Unknown sanitizer!"
    exit 1
  fi

  mkdir -p ${libcxx_build_dir}
  (cd ${libcxx_build_dir} && \
    cmake \
      ${cmake_stage2_common_options} \
      -DLLVM_ENABLE_RUNTIMES='libcxx;libcxxabi' \
      -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
      -DCMAKE_C_FLAGS="${fsanitize_flag} ${cmake_libcxx_cflags} ${fno_sanitize_flag}" \
      -DCMAKE_CXX_FLAGS="${fsanitize_flag} ${cmake_libcxx_cflags} ${fno_sanitize_flag}" \
      $LLVM/../runtimes && \
    ninja cxx cxxabi) || build_failure

  local libcxx_runtime_path=$(dirname $(find ${ROOT}/${libcxx_build_dir} -name libc++.so))
  local sanitizer_ldflags="-Wl,--rpath=${libcxx_runtime_path} -L${libcxx_runtime_path}"
  local sanitizer_cflags="-nostdinc++ -isystem ${ROOT}/${libcxx_build_dir}/include -isystem ${ROOT}/${libcxx_build_dir}/include/c++/v1 $fsanitize_flag"

  echo @@@BUILD_STEP stage2/$sanitizer_name build@@@

  # See http://llvm.org/bugs/show_bug.cgi?id=19071, http://www.cmake.org/Bug/view.php?id=15264
  sanitizer_cflags+=" $sanitizer_ldflags -w"

  mkdir -p ${build_dir}
  local cmake_stage2_clang_options="-DLLVM_ENABLE_PROJECTS='clang;lld;clang-tools-extra;mlir'"
  if [[ "$(arch)" == "aarch64" ]] ; then
    # FIXME: clangd tests fail.
    cmake_stage2_clang_options="-DLLVM_ENABLE_PROJECTS='clang;lld;mlir'"
  fi
  (cd ${build_dir} && \
   cmake \
     ${cmake_stage2_common_options} \
     ${cmake_stage2_clang_options} \
     -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
     -DLLVM_ENABLE_LIBCXX=ON \
     -DCMAKE_C_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_CXX_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_EXE_LINKER_FLAGS="${sanitizer_ldflags}" \
     $LLVM && \
   time ninja) || build_failure
   md5sum ${build_dir}/bin/clang* || true
}

function build_stage2_msan {
  build_stage2 msan
}

function build_stage2_msan_track_origins {
  build_stage2 msan_track_origins
}

function build_stage2_asan {
  build_stage2 asan
}

function build_stage2_hwasan {
  build_stage2 hwasan
}

function build_stage2_ubsan {
  build_stage2 ubsan
}

function build_stage2_asan_ubsan {
  build_stage2 asan_ubsan
}

function check_stage1 {
  local sanitizer_name=$1

  echo @@@BUILD_STEP stage1/$sanitizer_name check-sanitizer@@@
  ninja -C ${STAGE1_DIR} check-sanitizer || build_failure

  # Uses by asan and hwasan.
  echo @@@BUILD_STEP stage1/$sanitizer_name check-lsan@@@
  ninja -C ${STAGE1_DIR} check-lsan || build_failure

  echo @@@BUILD_STEP stage1/$sanitizer_name check-${sanitizer_name}@@@
  ninja -C ${STAGE1_DIR} check-${sanitizer_name} || build_failure
}

function check_stage1_msan {
  check_stage1 msan
}

function check_stage1_asan {
  check_stage1 asan
}

function check_stage1_hwasan {
  check_stage1 hwasan
}

function check_stage1_ubsan {
  check_stage1 ubsan
}

function check_stage1_asan_ubsan {
  check_stage1 asan_ubsan
}

function check_stage2 {
  local sanitizer_name=$1

  if [[ "${STAGE2_SKIP_TEST_CXX:-}" != "1" ]] ; then
    (
      # Very slow, run in background.
      LIT_OPTS+=" --timeout=1500"
      (
        # Very slow.
        export LIT_FILTER_OUT="modules_include.sh.cpp"
        LIT_FILTER_OUT+="|std/algorithms/alg.modifying.operations/alg.transform/ranges.transform.pass.cpp"
        LIT_FILTER_OUT+="|std/containers/sequences/deque/deque.modifiers/insert_iter_iter.pass.cpp"
        LIT_FILTER_OUT+="|std/numerics/rand/rand.dist/rand.dist.bern/rand.dist.bern.negbin/eval.pass.cpp"
        LIT_FILTER_OUT+="|std/numerics/rand/rand.dist/rand.dist.samp/rand.dist.samp.discrete/eval.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/charconv/charconv.msvc/test.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to_n.locale.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to_n.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to.locale.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/format.locale.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/format.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/formatted_size.locale.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/formatted_size.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/format/format.functions/vformat"
        LIT_FILTER_OUT+="|std/utilities/variant/variant.visit/visit_return_type.pass.cpp"
        LIT_FILTER_OUT+="|std/utilities/variant/variant.visit/visit.pass.cpp"

        if [[ "$(arch)" == "aarch64" && "$sanitizer_name" == "asan" ]] ; then
          # TODO: Investigate one leak and two slowest tests.
          LIT_FILTER_OUT+="|test_vector2.pass.cpp|catch_multi_level_pointer.pass.cpp"
          LIT_FILTER_OUT+="|guard_threaded_test.pass.cpp"
        fi
        if [[ "$(arch)" == "aarch64" && "$sanitizer_name" == "msan" ]] ; then
          # TODO: Investigate one slow tests.
          LIT_FILTER_OUT+="|catch_multi_level_pointer.pass.cpp"
          LIT_FILTER_OUT+="|guard_threaded_test.pass.cpp"
          LIT_FILTER_OUT+="|test_demangle.pass.cpp"
        fi
        if [[ "$(arch)" == "aarch64" && "$sanitizer_name" == "hwasan" ]] ; then
          # TODO: Investigate one slow tests.
          LIT_FILTER_OUT+="|catch_multi_level_pointer.pass.cpp"
          LIT_FILTER_OUT+="|guard_threaded_test.pass.cpp"
          LIT_FILTER_OUT+="|test_demangle.pass.cpp"
          LIT_FILTER_OUT+="|test_vector2.pass.cpp"
          LIT_FILTER_OUT+="|forced_unwind2.pass.cpp"
        fi
        ninja -C libcxx_build_${sanitizer_name} check-cxx check-cxxabi
      ) || build_failure
    ) &>check_cxx.log &
  fi

  echo @@@BUILD_STEP stage2/$sanitizer_name check@@@
  ninja -C ${STAGE2_DIR} check-all || build_failure

  if [[ "${STAGE2_SKIP_TEST_CXX:-}" != "1" ]] ; then
    echo @@@BUILD_STEP stage2/$sanitizer_name check-cxx@@@
    wait
    sleep 5
    cat check_cxx.log
  fi
}

function check_stage2_msan {
  check_stage2 msan
}

function check_stage2_msan_track_origins {
  check_stage2 msan_track_origins
}

function check_stage2_asan {
  check_stage2 asan
}

function check_stage2_hwasan {
  check_stage2 hwasan
}

function check_stage2_ubsan {
  check_stage2 ubsan
}

function check_stage2_asan_ubsan {
  check_stage2 asan_ubsan
}

function build_stage3 {
  local sanitizer_name=$1
  echo @@@BUILD_STEP build stage3/$sanitizer_name build@@@

  local build_dir=llvm_build2_${sanitizer_name}

  local clang_path=$ROOT/${STAGE2_DIR}/bin
  local sanitizer_cflags=
  mkdir -p ${build_dir}
  local stage3_projects='clang;lld;clang-tools-extra'
  if [[ "$(arch)" == "aarch64" ]] ; then
    # FIXME: clangd tests fail.
    stage3_projects='clang;lld'
  fi
  (cd ${build_dir} && \
   cmake \
     ${CMAKE_COMMON_OPTIONS} \
     -DLLVM_ENABLE_PROJECTS="${stage3_projects}" \
     -DCMAKE_C_COMPILER=${clang_path}/clang \
     -DCMAKE_CXX_COMPILER=${clang_path}/clang++ \
     -DCMAKE_CXX_FLAGS="${sanitizer_cflags}" \
     -DLLVM_CCACHE_BUILD=OFF \
     $LLVM && \
  time ninja) || build_failure
}

function build_stage3_msan {
  build_stage3 msan
}

function build_stage3_msan_track_origins {
  build_stage3 msan_track_origins
}

function build_stage3_asan {
  build_stage3 asan
}

function build_stage3_hwasan {
  build_stage3 hwasan
}

function build_stage3_ubsan {
  build_stage3 ubsan
}

function check_stage3 {
  local sanitizer_name=$1
  echo @@@BUILD_STEP stage3/$sanitizer_name check@@@

  local build_dir=llvm_build2_${sanitizer_name}

  (cd ${build_dir} && env && ninja check-all) || build_failure
}

function check_stage3_msan {
  check_stage3 msan
}

function check_stage3_msan_track_origins {
  check_stage3 msan_track_origins
}

function check_stage3_asan {
  check_stage3 asan
}

function check_stage3_hwasan {
  check_stage3 hwasan
}

function check_stage3_ubsan {
  check_stage3 ubsan
}

function build_failure() {
  # In bisect mode exit early.
  echo
  echo "How to reproduce locally: https://github.com/google/sanitizers/wiki/SanitizerBotReproduceBuild"
  echo

  sleep 5
  echo "@@@STEP_FAILURE@@@"
  [[ "${BUILDBOT_BISECT_MODE:-}" == "1" ]] && exit 1
}

function build_exception() {
  echo
  echo "How to reproduce locally: https://github.com/google/sanitizers/wiki/SanitizerBotReproduceBuild"
  echo

  sleep 5
  echo "@@@STEP_EXCEPTION@@@"
}
