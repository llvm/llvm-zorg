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

build_step "Build MLIR Dependencies (mlir-opt and mlir-translate)"

mkdir -p deps
cd deps

cmake -GNinja \
  -S ../../llvm-project/llvm \
  -B . \
  -DCMAKE_BUILD_TYPE="Release" \
  -DLLVM_CCACHE_BUILD=ON \
  -DLLVM_ENABLE_PROJECTS="mlir"

ninja mlir-opt mlir-translate

MLIR_OPT="$(pwd)/bin/mlir-opt"
MLIR_TRANSLATE="$(pwd)/bin/mlir-translate"

cd ..

build_step "Build LLVM"

cmake -GNinja \
  -S ../llvm-project/llvm \
  -B . \
  -DCMAKE_BUILD_TYPE="Release" \
  -DLLVM_CCACHE_BUILD=ON \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_IR2VEC_ENABLE_PYTHON_BINDINGS=ON \
  "-DLLVM_MLGO_MODELS=inliner,../llvm-project/mlir/test/Integration/Dialect/EmitC/inline-oz-test-model-tosa.mlir,inliner;regalloc,../llvm-project/mlir/test/Integration/Dialect/EmitC/regalloc-eviction-test-model-tosa.mlir,regalloc" \
  -DLLVM_MLGO_MLIR_OPT="${MLIR_OPT}" \
  -DLLVM_MLGO_MLIR_TRANSLATE="${MLIR_TRANSLATE}" \
  '-DLLVM_LIT_ARGS=-v -vv'

build_step "Run tests"

ninja check-llvm
