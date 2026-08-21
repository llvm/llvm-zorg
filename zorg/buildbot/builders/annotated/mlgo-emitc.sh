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

build_step "Build MLIR Dependencies (mlir-opt and mlir-translate)"

mkdir -p "${BUILD_MLGO_DEPS}"

cmake -GNinja \
  -S "${LLVM_ROOT}/llvm" \
  -B "${BUILD_MLGO_DEPS}" \
  -DCMAKE_BUILD_TYPE="Release" \
  -DLLVM_CCACHE_BUILD=ON \
  -DLLVM_ENABLE_PROJECTS="mlir"

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
  "-DLLVM_MLGO_MODELS=inliner,${INLINER_MODEL},inliner;regalloc,${REGALLOC_MODEL},regalloc" \
  -DLLVM_MLGO_MLIR_OPT="${MLIR_OPT}" \
  -DLLVM_MLGO_MLIR_TRANSLATE="${MLIR_TRANSLATE}" \
  '-DLLVM_LIT_ARGS=-v -vv'

build_step "Run tests"

ninja -C "${BUILD_MLGO}" check-llvm
