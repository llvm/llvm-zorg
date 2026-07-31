#!/bin/bash

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
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DLLVM_ENABLE_PROJECTS="mlir"

ninja mlir-opt mlir-translate

MLIR_OPT="$(pwd)/bin/mlir-opt"
MLIR_TRANSLATE="$(pwd)/bin/mlir-translate"

cd ..

build_step "Configure Clang with MLGO EmitC"

cmake -GNinja \
  -S ../llvm-project/llvm \
  -B . \
  -DCMAKE_BUILD_TYPE="Release" \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DLLVM_ENABLE_PROJECTS="clang" \
  -DLLVM_MLGO_MODELS="tosa1,${PWD}/model_tosa1.mlir,inliner" \
  -DLLVM_ENABLE_LLD=ON \
  -DLLVM_TARGETS_TO_BUILD="Native" \
  -DLLVM_MLGO_MLIR_OPT="${MLIR_OPT}" \
  -DLLVM_MLGO_MLIR_TRANSLATE="${MLIR_TRANSLATE}"

build_step "Build Clang"

ninja clang

build_step "Test Clang"

ninja check-clang