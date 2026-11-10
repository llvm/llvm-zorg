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

ENABLE_TF_AOT="${ENABLE_TF_AOT:-OFF}"
for arg in "$@"; do
  case "${arg}" in
    --enable-tf-aot)
      ENABLE_TF_AOT="ON"
      ;;
    --jobs=*)
      ;;
    *)
      echo "Error: unknown argument '${arg}'" >&2
      exit 1
      ;;
  esac
done

LLVM_ROOT="${LLVM_ROOT:-$(realpath ../llvm-project)}"
BUILD_MLGO="${BUILD_MLGO:-${LLVM_ROOT}/build-mlgo}"
TFLITE_CMAKE="${TFLITE_CMAKE:-/tflite/tflite.cmake}"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python3}"

if [[ ! -s "${TFLITE_CMAKE}" ]]; then
  echo "Error: TFLite CMake cache file '${TFLITE_CMAKE}' is missing or empty" >&2
  exit 1
fi

build_step "Build LLVM"

CMAKE_ARGS=(
  -GNinja
  -S "${LLVM_ROOT}/llvm"
  -B "${BUILD_MLGO}"
  -DCMAKE_BUILD_TYPE="Release"
  -DLLVM_CCACHE_BUILD=ON
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
