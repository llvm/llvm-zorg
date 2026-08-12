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

build_step "Build LLVM"

mkdir -p deps
cd deps

cmake -GNinja \
  -S ../../llvm-project/llvm \
  -B . \
  -DCMAKE_BUILD_TYPE="Release" \
  -DLLVM_CCACHE_BUILD=ON \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_IR2VEC_ENABLE_PYTHON_BINDINGS=ON \
  -DLLVM_ENABLE_PROJECTS="llvm" \
  '-DLLVM_LIT_ARGS=-v -vv'

build_step "Run tests"

ninja check
