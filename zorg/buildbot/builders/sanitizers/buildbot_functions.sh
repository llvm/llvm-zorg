#!/usr/bin/env bash

set -eu

ulimit -Ss 12288

ROOT=$(pwd)
LLVM=$ROOT/llvm-project/llvm

BUILDBOT_CLOBBER="${BUILDBOT_CLOBBER:-}"
BUILDBOT_REVISION="${BUILDBOT_REVISION:-origin/main}"

CMAKE_COMMON_OPTIONS+=" -DLLVM_APPEND_VC_REV=OFF -GNinja -DCMAKE_BUILD_TYPE=Release"

export LC_ALL=C

if ccache -s ; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_CCACHE_BUILD=ON"
fi

if ld.lld --version ; then
  CMAKE_COMMON_OPTIONS+=" -DLLVM_USE_LINKER=lld"
fi

SANITIZER_LOG_DIR=$ROOT/sanitizer_logs

function build_step() {
  echo "@@@BUILD_STEP ${1}@@@"
  CURRENT_STEP="${1}"
}

function include_config() {
  local P=.
  while true ; do
    local F=${P}/sanitizer_buildbot_config
    if [[ -f ${F} ]] ; then
      # shellcheck source=/dev/null
      . ${F}
      break
    fi
    [[ "${P}" -ef '/' ]] && break
    P="${P}/.."
  done
}

include_config

build_step "Info"
(
  set +e
  date
  env | sort
  echo
  ulimit -a
  echo
  df -h
  echo
  ccache -ps
  echo
  lscpu
  echo
  g++ --version
  echo
  cmake --version
  echo
  uname -a
  echo
  ldd --version
  echo
  uptime
  echo
  hostname -f
)

build_step "Prepare"

export LIT_OPTS="--time-tests"
# --timeout requires psutil missing on some bots.
if [[ ! "$(arch)" =~ "ppc64" ]] ; then
  LIT_OPTS+=" --timeout=900"
fi

CMAKE="$(which cmake)"

function cmake() {
  (
    set -x
    "${CMAKE}" "$@"
  )
}

function rm_dirs {
  while ! rm -rf "$@" ; do sleep 1; done
}

function cleanup() {
  [[ -v BUILDBOT_BUILDERNAME ]] || return 0
  build_step "cleanup"
  rm_dirs llvm_build2_* llvm_build_* libcxx_build_* libcxx_install_* compiler_rt_build* symbolizer_build* "$@"
  if ccache -s >/dev/null ; then
    rm_dirs llvm_build64
  fi
  # Workaround the case when a new unittest was reverted, but incremental build continues to execute the leftover binary.
  find . -path ./llvm-project -prune -o -executable -type f -path '*unittests*' -print -exec rm -f {} \;
  du -hs ./* | sort -h
}

function clobber {
  if [[ "$BUILDBOT_CLOBBER" != "" ]]; then
    build_step "clobber"
    if [[ ! -v BUILDBOT_BUILDERNAME ]]; then
      echo "Clobbering is supported on buildbot only!"
      exit 1
    fi
    # Keep sources in ./llvm-project and ./llvm_build0 for faster builds.
    find . -maxdepth 1 -mindepth 1 -path ./llvm-project -prune -o -path ./llvm_build0 -prune -o -print -exec rm -rf {} \;
    du -hs ./* | sort -h
    return 0
  else
    BUILDBOT_BUILDERNAME=1 cleanup "$@"
  fi
}

BUILDBOT_MONO_REPO_PATH=${BUILDBOT_MONO_REPO_PATH:-}

function buildbot_update {
  if [[ "${BUILDBOT_BISECT_MODE:-}" == "1" ]]; then
    build_step "bisect status"
    (
      cd llvm-project
      git bisect visualize --oneline
      git bisect log
      git status
    )
    LLVM=$ROOT/llvm-project/llvm
    return 0
  fi
  build_step "update $BUILDBOT_REVISION"
  if [[ -d "$BUILDBOT_MONO_REPO_PATH" ]]; then
    LLVM=$BUILDBOT_MONO_REPO_PATH/llvm
  else
    (
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
    ) || { build_warning ; exit 0 ; }
    LLVM=$ROOT/llvm-project/llvm
  fi
}

function print_sanitizer_logs() {
  if compgen -G "${SANITIZER_LOG_DIR}"/* ; then
    build_step "sanitizer logs: ${CURRENT_STEP}"
    head -n -1 "${SANITIZER_LOG_DIR}"/*
    buildbot_build && rm -rf "${SANITIZER_LOG_DIR}"
    mkdir -p "${SANITIZER_LOG_DIR}"
    build_warning
  fi
}


function run_ninja() {
  env
  local ec=0
  /usr/bin/time -o "${ROOT}/time.txt" -- ninja "$@" || ec=$?
  buildbot_build || print_sanitizer_logs
  if [[ $ec -ne 0 ]] ; then
    build_failure
    rm -f "${ROOT}/time.txt"
  fi
  print_sanitizer_logs
}

function common_stage1_variables {
  STAGE1_DIR=llvm_build0
  stage1_clang_path=$ROOT/${STAGE1_DIR}/bin
  llvm_symbolizer_path=${stage1_clang_path}/llvm-symbolizer
  export LLVM_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
  STAGE1_AS_COMPILER="-DCMAKE_C_COMPILER=${stage1_clang_path}/clang -DCMAKE_CXX_COMPILER=${stage1_clang_path}/clang++"
}

function build_stage1_clang_impl {
  [[ ! -f "${STAGE1_DIR}/delete_next_time" ]] || rm -rf "${STAGE1_DIR}"
  mkdir -p "${STAGE1_DIR}"
  local cmake_stage1_options="${CMAKE_COMMON_OPTIONS}"
  cmake_stage1_options+=" -DLLVM_ENABLE_PROJECTS='clang;lld'"
  cmake_stage1_options+=" -DLLVM_ENABLE_RUNTIMES='compiler-rt;libunwind;libcxx;libcxxabi'"
  if clang -v ; then
    cmake_stage1_options+=" -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++"
  fi
  (cd ${STAGE1_DIR} && cmake ${cmake_stage1_options} $LLVM && ninja) || {
    touch "${STAGE1_DIR}/delete_next_time"
    return 1
  }
}

function build_stage1_clang {
  build_step "stage1 build all"
  common_stage1_variables
  build_stage1_clang_impl
}

function download_clang_from_chromium {
  common_stage1_variables

  curl -s https://raw.githubusercontent.com/chromium/chromium/main/tools/clang/scripts/update.py \
    | python3 - --output-dir=${STAGE1_DIR}

  build_step "using pre-built stage1 clang at $(cat ${STAGE1_DIR}/cr_build_revision)"
}

function build_clang_at_release_tag {
  common_stage1_variables

  local host_clang_revision
  host_clang_revision=llvmorg-$(
    git ls-remote --tags https://github.com/llvm/llvm-project.git | \
      grep -oE "refs/tags/llvmorg-[0-9.]+$" | \
      grep -Eo "[0-9.]+" | \
      sort -n | \
      tail -n1
    )

  if  [ -r "${STAGE1_DIR}/host_clang_revision" ] && \
      [ "$(cat "${STAGE1_DIR}/host_clang_revision")" == "$host_clang_revision" ]
  then
    build_step "using pre-built stage1 clang at r${host_clang_revision}"
  else
    BUILDBOT_MONO_REPO_PATH="" BUILDBOT_REVISION="${host_clang_revision}" buildbot_update

    rm -rf ${STAGE1_DIR}
    build_step "build stage1 clang at $host_clang_revision"
    # PGO, can improve build time by 10%. However bots spend most of the time
    # running tests and compilation mostly incremental or CCCACH-ed.
    build_stage1_clang_impl && \
      ( echo "$host_clang_revision" > "${STAGE1_DIR}/host_clang_revision" )
  fi
}

function build_stage1_clang_at_revison {
  build_clang_at_release_tag
}

function common_stage2_variables {
  cmake_stage2_common_options="${CMAKE_COMMON_OPTIONS} ${STAGE1_AS_COMPILER}"
}

function build_stage2 {
  local sanitizer_name=$1
  build_step "stage2/$sanitizer_name build libcxx"

  local libcxx_build_dir=libcxx_build_${sanitizer_name}
  local libcxx_install_dir=libcxx_install_${sanitizer_name}
  local build_dir=llvm_build_${sanitizer_name}
  export STAGE2_DIR=${build_dir}
  local cmake_libcxx_cflags=

  common_stage2_variables

  ccache -z || true

  local fno_sanitize_flag=
  local cmake_options="-DLIBCXXABI_USE_LLVM_UNWINDER=OFF"

  rm -rf "${SANITIZER_LOG_DIR}"
  mkdir -p "${SANITIZER_LOG_DIR}"

  local log_path="${SANITIZER_LOG_DIR}/report"
  local san_options="log_path=${log_path}:log_exe_name=1:abort_on_error=1"

  if [ "$sanitizer_name" == "msan" ]; then
    export MSAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export MSAN_OPTIONS="${san_options}"
    llvm_use_sanitizer="Memory"
    fsanitize_flag="-fsanitize=memory"
  elif [ "$sanitizer_name" == "msan_track_origins" ]; then
    export MSAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export MSAN_OPTIONS="${san_options}"
    llvm_use_sanitizer="MemoryWithOrigins"
    fsanitize_flag="-fsanitize=memory -fsanitize-memory-track-origins"
  elif [ "$sanitizer_name" == "asan" ]; then
    export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    # TODO strict_init_order=true
    export ASAN_OPTIONS="check_initialization_order=true"
    export ASAN_OPTIONS+=":${san_options}"
    llvm_use_sanitizer="Address"
    fsanitize_flag="-fsanitize=address"
  elif [ "$sanitizer_name" == "hwasan" ]; then
    export HWASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export HWASAN_OPTIONS="${san_options}"
    llvm_use_sanitizer="HWAddress"
    fsanitize_flag="-fsanitize=hwaddress"
    # FIXME: Support globals with DSO https://github.com/llvm/llvm-project/issues/57206
    cmake_stage2_common_options+=" -DLLVM_ENABLE_PLUGINS=OFF"
  elif [ "$sanitizer_name" == "ubsan" ]; then
    export UBSAN_OPTIONS="external_symbolizer_path=${llvm_symbolizer_path}:print_stacktrace=1"
    export UBSAN_OPTIONS+=":${san_options}"
    llvm_use_sanitizer="Undefined"
    fsanitize_flag="-fsanitize=undefined -fno-sanitize-recover=all"
    # FIXME: After switching to LLVM_ENABLE_RUNTIMES, vptr has infitine
    # recursion.
    fno_sanitize_flag+=" -fno-sanitize=vptr"
  elif [ "$sanitizer_name" == "asan_ubsan" ]; then
    # TODO strict_init_order=true
    export ASAN_SYMBOLIZER_PATH="${llvm_symbolizer_path}"
    export ASAN_OPTIONS="check_initialization_order=true"
    export ASAN_OPTIONS+=":${san_options}"
    export UBSAN_OPTIONS="print_stacktrace=1"
    llvm_use_sanitizer="Address;Undefined"
    fsanitize_flag="-fsanitize=address,undefined -fno-sanitize-recover=all"
    # FIXME: After switching to LLVM_ENABLE_RUNTIMES, vptr has infitine
    # recursion.
    fno_sanitize_flag+=" -fno-sanitize=vptr"
  else
    echo "Unknown sanitizer!"
    exit 1
  fi

  mkdir -p "${libcxx_build_dir}"
  cmake -B "${libcxx_build_dir}" \
    ${cmake_stage2_common_options} \
    ${cmake_options} \
    -DCMAKE_INSTALL_PREFIX="${ROOT}/${libcxx_install_dir}" \
    -DLLVM_ENABLE_RUNTIMES='libcxx;libcxxabi' \
    -DLIBCXX_TEST_PARAMS='long_tests=False' \
    -DLIBCXX_INCLUDE_BENCHMARKS=OFF \
    -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
    -DCMAKE_C_FLAGS="${fsanitize_flag} ${cmake_libcxx_cflags} ${fno_sanitize_flag}" \
    -DCMAKE_CXX_FLAGS="${fsanitize_flag} ${cmake_libcxx_cflags} ${fno_sanitize_flag}" \
      "$LLVM/../runtimes" || build_failure
  
  run_ninja -C "${libcxx_build_dir}"
  run_ninja -C "${libcxx_build_dir}" install

  local libcxx_so_path
  libcxx_so_path="$(find "${ROOT}/${libcxx_install_dir}" -name libc++.so)"
  test -f "${libcxx_so_path}" || build_failure
  local libcxx_runtime_path
  libcxx_runtime_path=$(dirname "${libcxx_so_path}")

  local sanitizer_ldflags="-Wl,--rpath=${libcxx_runtime_path} -L${libcxx_runtime_path}"
  local sanitizer_cflags="-nostdinc++ -isystem ${ROOT}/${libcxx_install_dir}/include -isystem ${ROOT}/${libcxx_install_dir}/include/c++/v1 $fsanitize_flag"

  build_step "stage2/$sanitizer_name build"

  # See http://llvm.org/bugs/show_bug.cgi?id=19071, http://www.cmake.org/Bug/view.php?id=15264
  sanitizer_cflags+=" $sanitizer_ldflags -w"

  mkdir -p "${build_dir}"
  local cmake_stage2_clang_options="-DLLVM_ENABLE_PROJECTS='clang;lld;clang-tools-extra;mlir'"
  if [[ "$(arch)" == "aarch64" ]] ; then
    # FIXME: clangd tests fail.
    cmake_stage2_clang_options="-DLLVM_ENABLE_PROJECTS='clang;lld;mlir'"
  fi
  cmake -B "${build_dir}" \
     ${cmake_stage2_common_options} \
     ${cmake_stage2_clang_options} \
     -DLLVM_USE_SANITIZER=${llvm_use_sanitizer} \
     -DLLVM_ENABLE_LIBCXX=ON \
     -DCMAKE_C_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_CXX_FLAGS="${sanitizer_cflags}" \
     -DCMAKE_EXE_LINKER_FLAGS="${sanitizer_ldflags}" \
     "$LLVM" || {
      build_failure
      # No stats on failure.
      return 0
    }
  run_ninja -C "${build_dir}"

  upload_stats stage2
  ccache -s || true
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

  # covered by sanitizer-*-linux bot.
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
      LIT_OPTS+=" --timeout=1500"
      build_step "stage2/$sanitizer_name check-cxx"
      # Very slow.
      export LIT_FILTER_OUT="std/utilities/format/format.functions/format.locale.runtime_format.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format.runtime_format.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to_n.locale.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to_n.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to.locale.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format_to.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format.locale.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/format.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/formatted_size.locale.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/formatted_size.pass.cpp"
      LIT_FILTER_OUT+="|std/utilities/format/format.functions/vformat"

      if [[ "$(arch)" == "aarch64" && "$sanitizer_name" == "msan" ]] ; then
        # TODO: Investigate one slow tests.
        LIT_FILTER_OUT+="|test_demangle.pass.cpp"
      fi
      if [[ "$(arch)" == "aarch64" && "$sanitizer_name" == "hwasan" ]] ; then
        # TODO: Investigate one slow tests.
        LIT_FILTER_OUT+="|test_demangle.pass.cpp"
      fi
      
      if [[ "$(arch)" == "aarch64" ]] ; then
        # TODO: Investigate what is wrong with aarch64 unwinder.
        LIT_FILTER_OUT+="|ostream.formatted.print/vprint_nonunicode.pass.cpp"
        LIT_FILTER_OUT+="|ostream.formatted.print/vprint_unicode.pass.cpp"
      fi
      run_ninja -C "libcxx_build_${sanitizer_name}" check-runtimes
    )
  fi

  build_step "stage2/$sanitizer_name check"
  run_ninja -C "${STAGE2_DIR}" check-all
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
  local sanitizer_name
  sanitizer_name="${1}"
  build_step "build stage3/$sanitizer_name build"

  local build_dir
  build_dir="llvm_build2_${sanitizer_name}"

  local clang_path
  clang_path="${ROOT}/${STAGE2_DIR}/bin"
  local sanitizer_cflags=
  mkdir -p "${build_dir}"
  local stage3_projects='clang;lld;clang-tools-extra'
  if [[ "$(arch)" == "aarch64" ]] ; then
    # FIXME: clangd tests fail.
    stage3_projects='clang;lld'
  fi
  # -DLLVM_CCACHE_BUILD=OFF to track real build time.
  cmake -B "${build_dir}" \
    ${CMAKE_COMMON_OPTIONS} \
    -DLLVM_ENABLE_PROJECTS="${stage3_projects}" \
    -DCMAKE_C_COMPILER="${clang_path}/clang" \
    -DCMAKE_CXX_COMPILER="${clang_path}/clang++" \
    -DCMAKE_CXX_FLAGS="${sanitizer_cflags}" \
    -DLLVM_CCACHE_BUILD=OFF \
    "${LLVM}" || {
    build_failure
    # No stats on failure.
    return 0
  }
  run_ninja -C "${build_dir}"
  upload_stats stage3
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
  build_step "stage3/$sanitizer_name check"

  local build_dir=llvm_build2_${sanitizer_name}

  run_ninja -C "${build_dir}" check-all
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

function buildbot_build() {
  [[ "${BUILDBOT_BISECT_MODE:-}" != "1" && -v BUILDBOT_BUILDERNAME ]]
}

function build_failure() {
  # In bisect mode exit early.
  echo
  echo "How to reproduce locally: https://github.com/google/sanitizers/wiki/SanitizerBotReproduceBuild"
  echo

  # Repeat, server sometimes ignores failures or warnings.
  for _ in 0 1 2 ; do
    echo
    echo "@@@STEP_FAILURE@@@"
    sleep 5
  done

  buildbot_build || exit 1
}

function build_exception() {
  # Repeat, server sometimes ignores failures or warnings.
  for _ in 0 1 2 ; do
    echo
    echo "@@@STEP_EXCEPTION@@@"
    sleep 5
  done

  buildbot_build || exit 2
}

function build_warning() {
  # Repeat, server sometimes ignores failures or warnings.
  for _ in 0 1 2 ; do
    echo
    echo "@@@STEP_WARNINGS@@@"
    sleep 5
  done
  
  buildbot_build || exit 2
}

function upload_stats() {
  if buildbot_build ; then
    lscpu > "${ROOT}/cpu.txt"
    curl http://metadata.google.internal/computeMetadata/v1/instance/machine-type \
      -H Metadata-Flavor:Google > "${ROOT}/machine-type.txt" || true
    gsutil cp "${ROOT}/"{time,cpu,machine-type}".txt" "gs://sanitizer-buildbot-out/${BUILDBOT_BUILDERNAME}/${1}/${BUILDBOT_REVISION}/" || true
  fi
  cat "${ROOT}/time.txt"
}
