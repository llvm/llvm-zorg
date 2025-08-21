#!/bin/bash

set -ex

echo @@@CMake@@@

cmake -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=sccache \
  -DLLVM_LIT_ARGS='--exclude-xfail' \
  -DLLVM_ENABLE_PROFCHECK=ON \
  ../llvm-project/llvm

echo @@@Ninja@@@

export LIT_XFAIL="$(cat ../llvm/utils/profcheck-xfail.txt | tr '\n' ';')"
ninja check-llvm

