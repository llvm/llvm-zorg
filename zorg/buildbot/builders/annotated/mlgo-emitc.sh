#!/bin/bash

# Enable Error tracing
set -o errtrace

# Print trace for all commands ran before execution
set -x

# Include the Buildbot helper functions
HERE="$(dirname $0)"
. ${HERE}/buildbot-helper.sh

# Ensure all commands pass, and not dereferencing unset variables.
set -eu

set -o pipefail

halt_on_failure

LLVM_ROOT="${LLVM_ROOT:-$(realpath ../llvm-project)}"
BUILD_MLGO_DEPS="${BUILD_MLGO_DEPS:-${LLVM_ROOT}/build-mlgo-deps}"
BUILD_MLGO="${BUILD_MLGO:-${LLVM_ROOT}/build-mlgo}"
MLGO_CACHE_DIR="${MLGO_CACHE_DIR:-$(realpath -m ../mlgo-cache)}"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python3}"

ML_COMPILER_OPT_URL="${ML_COMPILER_OPT_URL:-https://github.com/google/ml-compiler-opt.git}"
ML_COMPILER_OPT_COMMIT="${ML_COMPILER_OPT_COMMIT:-e677c4f8443e53b6658667ba15a13e193c335876}"

INLINER_RELEASE_TAG="${INLINER_RELEASE_TAG:-inlining-Oz-v1.2}"
INLINER_RELEASE_ASSET="${INLINER_RELEASE_ASSET:-saved_model.zip}"

REGALLOC_RELEASE_TAG="${REGALLOC_RELEASE_TAG:-regalloc-evict-v1.1}"
REGALLOC_RELEASE_ASSET="${REGALLOC_RELEASE_ASSET:-model.zip}"

build_step "Set up Python Environment and ml-compiler-opt"

mkdir -p "${MLGO_CACHE_DIR}"

VENV_DIR="${MLGO_CACHE_DIR}/venv"
PIP_PACKAGES=("tosa-converter-for-tflite==2026.2.0" "ai-edge-litert==2.2.0" "absl-py==2.1.0")
VENV_STAMP_FILE="${VENV_DIR}/.stamp"
VENV_STAMP_EXPECTED="python=$("${PYTHON_EXECUTABLE}" --version 2>&1);packages=${PIP_PACKAGES[*]}"

# we only recreate the venv if the stamp file doesn't exist
if [[ ! -x "${VENV_DIR}/bin/python3" || \
      ! -x "${VENV_DIR}/bin/tosa-converter-for-tflite" || \
      ! -f "${VENV_STAMP_FILE}" || \
      "$(cat "${VENV_STAMP_FILE}")" != "${VENV_STAMP_EXPECTED}" ]]; then
  rm -rf "${VENV_DIR}"
  if "${PYTHON_EXECUTABLE}" -m ensurepip --version >/dev/null 2>&1; then
    "${PYTHON_EXECUTABLE}" -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/python3" -m pip install --only-binary=numpy "${PIP_PACKAGES[@]}"
  else
    "${PYTHON_EXECUTABLE}" -m venv --without-pip "${VENV_DIR}"
    "${PYTHON_EXECUTABLE}" -m pip --python "${VENV_DIR}/bin/python3" install --only-binary=numpy "${PIP_PACKAGES[@]}"
  fi
  printf '%s' "${VENV_STAMP_EXPECTED}" > "${VENV_STAMP_FILE}.tmp"
  mv "${VENV_STAMP_FILE}.tmp" "${VENV_STAMP_FILE}"
fi

VENV_PYTHON="${VENV_DIR}/bin/python3"
TOSA_CONVERTER="${VENV_DIR}/bin/tosa-converter-for-tflite"
TOSA_CONVERTER_VERSION="$("${TOSA_CONVERTER}" --version 2>&1 | tr '\n' ' ')"

ML_COMPILER_OPT_DIR="${MLGO_CACHE_DIR}/ml-compiler-opt"
if [[ ! -d "${ML_COMPILER_OPT_DIR}/.git" ]]; then
  rm -rf "${ML_COMPILER_OPT_DIR}"
  git clone "${ML_COMPILER_OPT_URL}" "${ML_COMPILER_OPT_DIR}"
fi

if [[ "$(git -C "${ML_COMPILER_OPT_DIR}" rev-parse HEAD 2>/dev/null || true)" != "${ML_COMPILER_OPT_COMMIT}" ]]; then
  git -C "${ML_COMPILER_OPT_DIR}" fetch --prune origin
  git -C "${ML_COMPILER_OPT_DIR}" checkout --force "${ML_COMPILER_OPT_COMMIT}"
fi

build_step "Fetch and Convert Released Models to TOSA"

prepare_tosa_model() {
  local model_name="$1"
  local release_tag="$2"
  local release_asset="$3"
  local out_tosa_mlir="$4"

  local model_cache_dir="${MLGO_CACHE_DIR}/models/${model_name}"
  local stamp_file="${model_cache_dir}/.stamp"
  local release_url="https://github.com/google/ml-compiler-opt/releases/download/${release_tag}/${release_asset}"
  local expected_stamp="url=${release_url};ml_compiler_opt=${ML_COMPILER_OPT_COMMIT};tosa_converter=${TOSA_CONVERTER_VERSION}"

  if [[ -f "${stamp_file}" && -s "${out_tosa_mlir}" && "$(cat "${stamp_file}")" == "${expected_stamp}" ]]; then
    echo "Using cached TOSA model for ${model_name} (${release_tag})"
    return 0
  fi

  rm -rf "${model_cache_dir}"
  mkdir -p "${model_cache_dir}/extracted"

  local zip_path="${model_cache_dir}/${release_asset}"
  curl -fLsS --retry 3 -o "${zip_path}" "${release_url}"
  if [[ ! -s "${zip_path}" ]]; then
    echo "Error: downloaded archive '${zip_path}' is missing or empty" >&2
    return 1
  fi

  "${PYTHON_EXECUTABLE}" -m zipfile -e "${zip_path}" "${model_cache_dir}/extracted"
  local tflite_files=()
  mapfile -t tflite_files < <(find "${model_cache_dir}/extracted" -type f -name "model.tflite" -not -path "*/__MACOSX/*")
  if [[ "${#tflite_files[@]}" -ne 1 || ! -s "${tflite_files[0]}" ]]; then
    echo "Error: expected a single non-empty model.tflite in '${zip_path}', found ${#tflite_files[@]}" >&2
    return 1
  fi

  local stripped_tflite="${model_cache_dir}/model.stripped.tflite"
  PYTHONPATH="${ML_COMPILER_OPT_DIR}" "${VENV_PYTHON}" -m compiler_opt.tools.strip_tfa_tflite \
    --input_path="${tflite_files[0]}" \
    --output_path="${stripped_tflite}"
  if [[ ! -s "${stripped_tflite}" ]]; then
    echo "Error: stripped TFLite model '${stripped_tflite}' is missing or empty" >&2
    return 1
  fi

  "${TOSA_CONVERTER}" "${stripped_tflite}" --bytecode -o "${out_tosa_mlir}.tmp"
  if [[ ! -s "${out_tosa_mlir}.tmp" ]]; then
    echo "Error: converted TOSA model '${out_tosa_mlir}.tmp' is missing or empty" >&2
    return 1
  fi
  mv "${out_tosa_mlir}.tmp" "${out_tosa_mlir}"

  printf '%s' "${expected_stamp}" > "${stamp_file}.tmp"
  mv "${stamp_file}.tmp" "${stamp_file}"
}

INLINER_REAL_MODEL="${MLGO_CACHE_DIR}/models/inliner/model.tosa.mlir"
REGALLOC_REAL_MODEL="${MLGO_CACHE_DIR}/models/regalloc/model.tosa.mlir"

prepare_tosa_model "inliner" "${INLINER_RELEASE_TAG}" "${INLINER_RELEASE_ASSET}" "${INLINER_REAL_MODEL}"
prepare_tosa_model "regalloc" "${REGALLOC_RELEASE_TAG}" "${REGALLOC_RELEASE_ASSET}" "${REGALLOC_REAL_MODEL}"

build_step "Install Python Dependencies"

python3 -m pip install --break-system-packages -r "${LLVM_ROOT}/llvm/tools/llvm-ir2vec/Bindings/requirements.txt"

build_step "Build MLIR Dependencies (mlir-opt and mlir-translate)"

mkdir -p "${BUILD_MLGO_DEPS}"

cmake -GNinja \
  -S "${LLVM_ROOT}/llvm" \
  -B "${BUILD_MLGO_DEPS}" \
  -DCMAKE_BUILD_TYPE="Release" \
  -DLLVM_CCACHE_BUILD=ON \
  -DLLVM_ENABLE_PROJECTS="mlir" \
  -DLLVM_TARGETS_TO_BUILD=Native \
  -DLLVM_INCLUDE_TESTS=OFF \
  -DMLIR_INCLUDE_TESTS=OFF

ninja -C "${BUILD_MLGO_DEPS}" mlir-opt mlir-translate

MLIR_OPT="${BUILD_MLGO_DEPS}/bin/mlir-opt"
MLIR_TRANSLATE="${BUILD_MLGO_DEPS}/bin/mlir-translate"
INLINER_MODEL="${LLVM_ROOT}/mlir/test/Integration/Dialect/EmitC/inline-oz-test-model-tosa.mlir"
REGALLOC_MODEL="${LLVM_ROOT}/mlir/test/Integration/Dialect/EmitC/regalloc-eviction-test-model-tosa.mlir"

build_step "Build LLVM"

mkdir -p "${BUILD_MLGO}"

cmake -GNinja \
  -S "${LLVM_ROOT}/llvm" \
  -B "${BUILD_MLGO}" \
  -DCMAKE_BUILD_TYPE="Release" \
  -DLLVM_CCACHE_BUILD=ON \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_IR2VEC_ENABLE_PYTHON_BINDINGS=ON \
  "-DLLVM_MLGO_MODELS=inliner,${INLINER_MODEL},inliner;regalloc,${REGALLOC_MODEL},regalloc;real_model,${INLINER_REAL_MODEL},inliner;real_model,${REGALLOC_REAL_MODEL},regalloc" \
  -DLLVM_MLGO_MLIR_OPT="${MLIR_OPT}" \
  -DLLVM_MLGO_MLIR_TRANSLATE="${MLIR_TRANSLATE}" \
  '-DLLVM_LIT_ARGS=-v -vv'

build_step "Run tests"

ninja -C "${BUILD_MLGO}" check-llvm
