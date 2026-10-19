#!/bin/bash

# Enable Error tracing
set -o errtrace

# Print trace for all commands ran before execution
set -x

# Include the Buildbot helper functions when running from a checkout
HERE="$(dirname $0)"
if [[ -f "${HERE}/buildbot-helper.sh" ]]; then
  . "${HERE}/buildbot-helper.sh"
else
  halt_on_failure() { :; }
  build_step() { echo "=== $* ==="; }
fi

# Ensure all commands pass, and not dereferencing unset variables.
set -eu

set -o pipefail

halt_on_failure

ENABLE_TF_AOT="${ENABLE_TF_AOT:-OFF}"
TFLITE_ONLY="${TFLITE_ONLY:-OFF}"
for arg in "$@"; do
  case "${arg}" in
    --enable-tf-aot)
      ENABLE_TF_AOT="ON"
      ;;
    --tflite-only)
      TFLITE_ONLY="ON"
      ;;
    --jobs=*)
      ;;
    *)
      echo "Error: unknown argument '${arg}'" >&2
      exit 1
      ;;
  esac
done

if [[ "${TFLITE_ONLY}" == "ON" ]]; then
  TFLITE_ROOT="${TFLITE_ROOT:-${PWD}}"
else
  LLVM_ROOT="${LLVM_ROOT:-$(realpath ../llvm-project)}"
  BUILD_MLGO="${BUILD_MLGO:-${LLVM_ROOT}/build-mlgo}"
  MLGO_CACHE_DIR="${MLGO_CACHE_DIR:-$(realpath -m ../mlgo-cache)}"
  TFLITE_ROOT="${TFLITE_ROOT:-${MLGO_CACHE_DIR}/tflite}"
fi
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python3}"

TFLITE_CCACHE_ARGS=()
LLVM_CCACHE_BUILD="OFF"
if command -v ccache >/dev/null 2>&1; then
  TFLITE_CCACHE_ARGS=(
    -DCMAKE_C_COMPILER_LAUNCHER=ccache
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
  )
  LLVM_CCACHE_BUILD="ON"
fi

readonly CPUINFO_REPOSITORY="https://github.com/pytorch/cpuinfo"
readonly CPUINFO_TAG="05332fd802d9109a2a151ec32154b107c1e5caf9"

readonly RUY_REPOSITORY="https://github.com/google/ruy"
readonly RUY_TAG="c08ec529fc91722bde519628d9449258082eb847"

readonly ABSEIL_REPOSITORY="https://github.com/abseil/abseil-cpp"
readonly ABSEIL_TAG="1278ee9bd9bd4916181521fac96d6fa1100e38e6"

readonly EIGEN_REPOSITORY="https://gitlab.com/libeigen/eigen"
readonly EIGEN_TAG="d791d48859c6fc7850c9fd5270d2b236c818068d"

readonly NEON_2_SSE_REPOSITORY="https://github.com/intel/ARM_NEON_2_x86_SSE"
readonly NEON_2_SSE_TAG="6315d3c5007e6c209eb77abae4deece4978d8dbc"

readonly FLATBUFFERS_REPOSITORY="https://github.com/google/flatbuffers"
readonly FLATBUFFERS_TAG="fb9afbafc7dfe226b9db54d4923bfb8839635274"

readonly GEMMLOWP_REPOSITORY="https://github.com/google/gemmlowp"
readonly GEMMLOWP_TAG="16e8662c34917be0065110bfcd9cc27d30f52fdf"

readonly ML_DTYPES_REPOSITORY="https://github.com/jax-ml/ml_dtypes"
readonly ML_DTYPES_TAG="f739b2f0256d543e68caf214cd54b367302fbf68"

readonly FARMHASH_REPOSITORY="https://github.com/google/farmhash"
readonly FARMHASH_TAG="0d859a811870d10f53a594927d0d0b97573ad06d"

readonly PROTOBUF_REPOSITORY="https://github.com/protocolbuffers/protobuf"
readonly PROTOBUF_TAG="90b73ac3f0b10320315c2ca0d03a5a9b095d2f66"

readonly TENSORFLOW_REPOSITORY="https://github.com/tensorflow/tensorflow"
readonly TENSORFLOW_TAG="bbed5f60cd2efbbc3f1032a4e7f9fe393a1760af"

ACTIVE_TFLITE_STEP_DIR=""

cleanup_tflite_step_on_exit() {
  local exit_code=$?
  if [[ -n "${ACTIVE_TFLITE_STEP_DIR}" ]]; then
    rm -rf "${ACTIVE_TFLITE_STEP_DIR}" "${TFLITE_CMAKE}"
    echo "@@@STEP_EXCEPTION@@@"
  fi
  exit "${exit_code}"
}

trap cleanup_tflite_step_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

clone_and_checkout() {
  local repo="$1"
  local tag="$2"
  local dest="$3"
  rm -rf "${dest}"
  mkdir -p "${dest}"
  git init "${dest}"
  GIT_HTTP_LOW_SPEED_LIMIT=1024 GIT_HTTP_LOW_SPEED_TIME=60 \
    timeout 300s git -C "${dest}" fetch --depth 1 "${repo}" "${tag}"
  git -C "${dest}" checkout FETCH_HEAD
}

begin_tflite_step() {
  local step_dir="$1"
  local expected_stamp="$2"
  local stamp_file="${step_dir}/.stamp"
  if [[ -f "${stamp_file}" && "$(cat "${stamp_file}")" == "${expected_stamp}" ]]; then
    return 1
  fi
  ACTIVE_TFLITE_STEP_DIR="${step_dir}"
  rm -rf "${step_dir}" "${TFLITE_ROOT}/tensorflow/.stamp" "${TFLITE_CMAKE}"
  mkdir -p "${step_dir}"
  return 0
}

end_tflite_step() {
  local step_dir="$1"
  local expected_stamp="$2"
  local stamp_file="${step_dir}/.stamp"
  printf '%s' "${expected_stamp}" > "${stamp_file}.tmp"
  mv "${stamp_file}.tmp" "${stamp_file}"
  ACTIVE_TFLITE_STEP_DIR=""
}

build_step "Build TFLite"

mkdir -p "${TFLITE_ROOT}"

TFLITE_CMAKE="${TFLITE_ROOT}/tflite.cmake"
TFLITE_STAMP_EXPECTED="cpuinfo=${CPUINFO_TAG};ruy=${RUY_TAG};abseil=${ABSEIL_TAG};eigen=${EIGEN_TAG};neon2sse=${NEON_2_SSE_TAG};flatbuffers=${FLATBUFFERS_TAG};gemmlowp=${GEMMLOWP_TAG};ml_dtypes=${ML_DTYPES_TAG};farmhash=${FARMHASH_TAG};protobuf=${PROTOBUF_TAG};tensorflow=${TENSORFLOW_TAG}"

# cpuinfo
if begin_tflite_step "${TFLITE_ROOT}/cpuinfo" "cpuinfo=${CPUINFO_TAG}"; then
  rm -f "${TFLITE_ROOT}/ruy/.stamp"
  clone_and_checkout "${CPUINFO_REPOSITORY}" "${CPUINFO_TAG}" "${TFLITE_ROOT}/cpuinfo/src/cpuinfo"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/cpuinfo/src/cpuinfo" \
    -B "${TFLITE_ROOT}/cpuinfo/src/cpuinfo-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/cpuinfo" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
    -DCPUINFO_BUILD_UNIT_TESTS:BOOL=OFF \
    -DCPUINFO_BUILD_MOCK_TESTS:BOOL=OFF \
    -DCPUINFO_BUILD_BENCHMARKS:BOOL=OFF
  ninja -C "${TFLITE_ROOT}/cpuinfo/src/cpuinfo-build" install
  end_tflite_step "${TFLITE_ROOT}/cpuinfo" "cpuinfo=${CPUINFO_TAG}"
fi

# ruy
if begin_tflite_step "${TFLITE_ROOT}/ruy" "cpuinfo=${CPUINFO_TAG};ruy=${RUY_TAG}"; then
  clone_and_checkout "${RUY_REPOSITORY}" "${RUY_TAG}" "${TFLITE_ROOT}/ruy/src/ruy"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/ruy/src/ruy" \
    -B "${TFLITE_ROOT}/ruy/src/ruy-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/ruy" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
    -Dcpuinfo_DIR:PATH="${TFLITE_ROOT}/cpuinfo/share/cpuinfo" \
    -DRUY_MINIMAL_BUILD:BOOL=ON \
    -DRUY_ENABLE_INSTALL:BOOL=ON \
    -DRUY_FIND_CPUINFO:BOOL=ON
  ninja -C "${TFLITE_ROOT}/ruy/src/ruy-build" install
  end_tflite_step "${TFLITE_ROOT}/ruy" "cpuinfo=${CPUINFO_TAG};ruy=${RUY_TAG}"
fi

# absl
if begin_tflite_step "${TFLITE_ROOT}/abseil-cpp" "abseil=${ABSEIL_TAG}"; then
  clone_and_checkout "${ABSEIL_REPOSITORY}" "${ABSEIL_TAG}" "${TFLITE_ROOT}/abseil-cpp/src/abseil-cpp"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/abseil-cpp/src/abseil-cpp" \
    -B "${TFLITE_ROOT}/abseil-cpp/src/abseil-cpp-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/abseil-cpp" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
    -DABSL_BUILD_TESTING:BOOL=OFF \
    -DABSL_ENABLE_INSTALL:BOOL=ON
  ninja -C "${TFLITE_ROOT}/abseil-cpp/src/abseil-cpp-build" install
  end_tflite_step "${TFLITE_ROOT}/abseil-cpp" "abseil=${ABSEIL_TAG}"
fi

# eigen
if begin_tflite_step "${TFLITE_ROOT}/eigen" "eigen=${EIGEN_TAG}"; then
  clone_and_checkout "${EIGEN_REPOSITORY}" "${EIGEN_TAG}" "${TFLITE_ROOT}/eigen/src/eigen"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/eigen/src/eigen" \
    -B "${TFLITE_ROOT}/eigen/src/eigen-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/eigen" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
    -DEIGEN_BUILD_DOC:BOOL=OFF \
    -DEIGEN_BUILD_TESTING:BOOL=OFF
  ninja -C "${TFLITE_ROOT}/eigen/src/eigen-build" install
  end_tflite_step "${TFLITE_ROOT}/eigen" "eigen=${EIGEN_TAG}"
fi

# ARM_NEON_2_x86_SSE
if begin_tflite_step "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE" "neon2sse=${NEON_2_SSE_TAG}"; then
  clone_and_checkout "${NEON_2_SSE_REPOSITORY}" "${NEON_2_SSE_TAG}" "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE/src/ARM_NEON_2_x86_SSE"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE/src/ARM_NEON_2_x86_SSE" \
    -B "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE/src/ARM_NEON_2_x86_SSE-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/ARM_NEON_2_x86_SSE" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON
  ninja -C "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE/src/ARM_NEON_2_x86_SSE-build" install
  end_tflite_step "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE" "neon2sse=${NEON_2_SSE_TAG}"
fi

# flatbuffers
if begin_tflite_step "${TFLITE_ROOT}/flatbuffers" "flatbuffers=${FLATBUFFERS_TAG}"; then
  clone_and_checkout "${FLATBUFFERS_REPOSITORY}" "${FLATBUFFERS_TAG}" "${TFLITE_ROOT}/flatbuffers/src/flatbuffers"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/flatbuffers/src/flatbuffers" \
    -B "${TFLITE_ROOT}/flatbuffers/src/flatbuffers-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/flatbuffers" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
    -DFLATBUFFERS_BUILD_TESTS:BOOL=OFF
  ninja -C "${TFLITE_ROOT}/flatbuffers/src/flatbuffers-build" install
  end_tflite_step "${TFLITE_ROOT}/flatbuffers" "flatbuffers=${FLATBUFFERS_TAG}"
fi

# gemmlowp
if begin_tflite_step "${TFLITE_ROOT}/gemmlowp" "gemmlowp=${GEMMLOWP_TAG}"; then
  clone_and_checkout "${GEMMLOWP_REPOSITORY}" "${GEMMLOWP_TAG}" "${TFLITE_ROOT}/gemmlowp/src/gemmlowp"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/gemmlowp/src/gemmlowp/contrib" \
    -B "${TFLITE_ROOT}/gemmlowp/src/gemmlowp-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/gemmlowp" \
    -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON \
    -DCMAKE_INSTALL_LIBDIR=lib
  ninja -C "${TFLITE_ROOT}/gemmlowp/src/gemmlowp-build" install
  end_tflite_step "${TFLITE_ROOT}/gemmlowp" "gemmlowp=${GEMMLOWP_TAG}"
fi

# ml_dtypes
if begin_tflite_step "${TFLITE_ROOT}/ml_dtypes" "ml_dtypes=${ML_DTYPES_TAG}"; then
  clone_and_checkout "${ML_DTYPES_REPOSITORY}" "${ML_DTYPES_TAG}" "${TFLITE_ROOT}/ml_dtypes/src/ml_dtypes"
  end_tflite_step "${TFLITE_ROOT}/ml_dtypes" "ml_dtypes=${ML_DTYPES_TAG}"
fi

# farmhash
if begin_tflite_step "${TFLITE_ROOT}/farmhash" "farmhash=${FARMHASH_TAG}"; then
  clone_and_checkout "${FARMHASH_REPOSITORY}" "${FARMHASH_TAG}" "${TFLITE_ROOT}/farmhash/src/farmhash"
  end_tflite_step "${TFLITE_ROOT}/farmhash" "farmhash=${FARMHASH_TAG}"
fi

# protobuf
if begin_tflite_step "${TFLITE_ROOT}/protobuf" "protobuf=${PROTOBUF_TAG}"; then
  clone_and_checkout "${PROTOBUF_REPOSITORY}" "${PROTOBUF_TAG}" "${TFLITE_ROOT}/protobuf/src/protobuf"
  end_tflite_step "${TFLITE_ROOT}/protobuf" "protobuf=${PROTOBUF_TAG}"
fi

# tflite
if [[ ! -s "${TFLITE_CMAKE}" ]]; then
  rm -f "${TFLITE_ROOT}/tensorflow/.stamp"
fi
if begin_tflite_step "${TFLITE_ROOT}/tensorflow" "${TFLITE_STAMP_EXPECTED}"; then
  clone_and_checkout "${TENSORFLOW_REPOSITORY}" "${TENSORFLOW_TAG}" "${TFLITE_ROOT}/tensorflow/src/tensorflow"
  cmake -GNinja \
    -S "${TFLITE_ROOT}/tensorflow/src/tensorflow/tensorflow/lite" \
    -B "${TFLITE_ROOT}/tensorflow/src/tensorflow-build" \
    "${TFLITE_CCACHE_ARGS[@]}" \
    -DCMAKE_FIND_PACKAGE_PREFER_CONFIG:BOOL=ON \
    -DCMAKE_INSTALL_PREFIX:PATH="${TFLITE_ROOT}/tensorflow" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DTFLITE_ENABLE_INSTALL:BOOL=ON \
    -DTFLITE_ENABLE_XNNPACK:BOOL=OFF \
    -Dcpuinfo_DIR:PATH="${TFLITE_ROOT}/cpuinfo/share/cpuinfo" \
    -Druy_DIR:PATH="${TFLITE_ROOT}/ruy/lib/cmake/ruy" \
    -Dabsl_DIR:PATH="${TFLITE_ROOT}/abseil-cpp/lib/cmake/absl" \
    -DEigen3_DIR:PATH="${TFLITE_ROOT}/eigen/share/eigen3/cmake" \
    -Dgemmlowp_DIR:PATH="${TFLITE_ROOT}/gemmlowp/lib/cmake/gemmlowp" \
    -DNEON_2_SSE_DIR:PATH="${TFLITE_ROOT}/ARM_NEON_2_x86_SSE/lib/cmake/NEON_2_SSE" \
    -DFlatBuffers_DIR:PATH="${TFLITE_ROOT}/flatbuffers/lib/cmake/flatbuffers" \
    -DML_DTYPES_SOURCE_DIR:PATH="${TFLITE_ROOT}/ml_dtypes/src/ml_dtypes" \
    -DFETCHCONTENT_SOURCE_DIR_ML_DTYPES:PATH="${TFLITE_ROOT}/ml_dtypes/src/ml_dtypes" \
    -DFETCHCONTENT_SOURCE_DIR_FARMHASH:PATH="${TFLITE_ROOT}/farmhash/src/farmhash" \
    -DFETCHCONTENT_SOURCE_DIR_PROTOBUF:PATH="${TFLITE_ROOT}/protobuf/src/protobuf"
  ninja -C "${TFLITE_ROOT}/tensorflow/src/tensorflow-build" install

  cat <<EOF > "${TFLITE_CMAKE}.tmp"
set(cpuinfo_DIR "${TFLITE_ROOT}/cpuinfo/share/cpuinfo" CACHE PATH "")
set(ruy_DIR "${TFLITE_ROOT}/ruy/lib/cmake/ruy" CACHE PATH "")
set(absl_DIR "${TFLITE_ROOT}/abseil-cpp/lib/cmake/absl" CACHE PATH "")
set(Eigen3_DIR "${TFLITE_ROOT}/eigen/share/eigen3/cmake" CACHE PATH "")
set(NEON_2_SSE_DIR "${TFLITE_ROOT}/ARM_NEON_2_x86_SSE/lib/cmake/NEON_2_SSE" CACHE PATH "")
set(gemmlowp_DIR "${TFLITE_ROOT}/gemmlowp/lib/cmake/gemmlowp" CACHE PATH "")
set(FlatBuffers_DIR "${TFLITE_ROOT}/flatbuffers/lib/cmake/flatbuffers" CACHE PATH "")
set(tensorflow-lite_DIR "${TFLITE_ROOT}/tensorflow/lib/cmake/tensorflow-lite" CACHE PATH "")
set(TENSORFLOW_SRC_DIR "${TFLITE_ROOT}/tensorflow/src/tensorflow" CACHE PATH "")
set(LLVM_HAVE_TFLITE ON CACHE BOOL "")
EOF
  mv "${TFLITE_CMAKE}.tmp" "${TFLITE_CMAKE}"
  end_tflite_step "${TFLITE_ROOT}/tensorflow" "${TFLITE_STAMP_EXPECTED}"
fi

if [[ ! -s "${TFLITE_CMAKE}" ]]; then
  echo "Error: TFLite CMake cache file '${TFLITE_CMAKE}' is missing or empty" >&2
  echo "@@@STEP_EXCEPTION@@@"
  exit 1
fi

if [[ "${TFLITE_ONLY}" == "ON" ]]; then
  exit 0
fi

build_step "Build LLVM"

CMAKE_ARGS=(
  -GNinja
  -S "${LLVM_ROOT}/llvm"
  -B "${BUILD_MLGO}"
  -DCMAKE_BUILD_TYPE="Release"
  -DLLVM_CCACHE_BUILD="${LLVM_CCACHE_BUILD}"
  -DLLVM_ENABLE_ASSERTIONS=ON
  -DLLVM_IR2VEC_ENABLE_PYTHON_BINDINGS=ON
  -C "${TFLITE_CMAKE}"
  -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON
  '-DLLVM_LIT_ARGS=-v -vv'
)

if [[ "${ENABLE_TF_AOT}" == "ON" ]]; then
  TENSORFLOW_AOT_PATH="${TENSORFLOW_AOT_PATH:-$("${PYTHON_EXECUTABLE}" -c "import os, tensorflow as tf; print(os.path.dirname(tf.__file__))")}"
  if [[ ! -d "${TENSORFLOW_AOT_PATH}/xla_aot_runtime_src" ]]; then
    echo "Error: xla_aot_runtime_src not found under TENSORFLOW_AOT_PATH='${TENSORFLOW_AOT_PATH}'" >&2
    exit 1
  fi
  CMAKE_ARGS+=(-DTENSORFLOW_AOT_PATH="${TENSORFLOW_AOT_PATH}")
fi

mkdir -p "${BUILD_MLGO}"
cmake "${CMAKE_ARGS[@]}"

build_step "Run tests"

ninja -C "${BUILD_MLGO}" check-llvm
