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
halt_on_failure

BUILDBOT_ROOT=/buildbot
LLVM_ROOT="${BUILDBOT_ROOT}/llvm-project"
REVISION=${BUILDBOT_REVISION:-origin/main}
AMDGPU_ARCHS=${AMDGPU_ARCHS:="gfx900;gfx906;gfx908;gfx1030"}

# Set-up llvm-project
if [ ! -d "${LLVM_ROOT}" ]; then
  build_step "Cloning llvm-project repo"
  git clone --progress https://github.com/llvm/llvm-project.git ${LLVM_ROOT}
fi

build_step "Updating llvm-project repo"
git -C "${LLVM_ROOT}" fetch origin
git -C "${LLVM_ROOT}" reset --hard ${REVISION}

# Set-up llvm-test-suite
TESTSUITE_ROOT="${BUILDBOT_ROOT}/llvm-test-suite"
if [ ! -d "${TESTSUITE_ROOT}" ]; then
  build_step "Cloning llvm-test-suite repo"
  git clone --progress https://github.com/llvm/llvm-test-suite.git ${TESTSUITE_ROOT}
fi

build_step "Updating llvm-test-suite repo"
git -C "${TESTSUITE_ROOT}" fetch origin
git -C "${TESTSUITE_ROOT}" reset --hard origin/main

# Set-up variables
BUILDBOT_SLAVENAME=$(whoami)
BUILD_DIR="${BUILDBOT_ROOT}/${BUILDBOT_SLAVENAME}/${BUILDBOT_BUILDERNAME}"
DESTDIR=${BUILD_DIR}/install
EXTERNAL_DIR=/buildbot/Externals

build_step "Setting up the buildbot"
echo "BUILDBOT_ROOT=${BUILDBOT_ROOT}"
echo "LLVM_ROOT=${LLVM_ROOT}"
echo "BUILD_DIR=${BUILD_DIR}"
echo "DESTDIR=${DESTDIR}"
echo "EXTERNAL_DIR=${EXTERNAL_DIR}"

# Start building LLVM, Clang, Lld, clang-tools-extra, compiler-rt
build_step "Configure LLVM Build"
LLVM_BUILD_DIR="${BUILD_DIR}/llvm"
mkdir -p "${LLVM_BUILD_DIR}"
cd "${LLVM_BUILD_DIR}"
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE="Release" \
  -DCMAKE_VERBOSE_MAKEFILE=1 \
  -DLLVM_TARGETS_TO_BUILD="AMDGPU;X86" \
  -DLLVM_ENABLE_PROJECTS="clang;lld;clang-tools-extra;compiler-rt;libcxx;libcxxabi" \
  -DLIBCXX_ENABLE_SHARED=OFF \
  -DLIBCXX_ENABLE_STATIC=ON \
  -DLIBCXX_INSTALL_LIBRARY=OFF \
  -DLIBCXX_INSTALL_HEADERS=OFF \
  -DLIBCXXABI_ENABLE_SHARED=OFF \
  -DLIBCXXABI_ENABLE_STATIC=ON \
  -DLIBCXXABI_INSTALL_STATIC_LIBRARY=OFF \
  -DCMAKE_INSTALL_PREFIX="${DESTDIR}" \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_ENABLE_Z3_SOLVER=OFF \
  -DLLVM_ENABLE_ZLIB=ON \
  -DLLVM_LIT_ARGS="-v -vv" \
  ${LLVM_ROOT}/llvm

build_step "Building LLVM"
ninja

build_step "Install LLVM"
rm -rf "${DESTDIR}"
ninja install

# Start building llvm-test-suite's hip tests
build_step "Configuring HIP test-suite"
TEST_BUILD_DIR=${BUILD_DIR}/test-suite-build
rm -rf ${TEST_BUILD_DIR}
mkdir -p ${TEST_BUILD_DIR}
cd ${TEST_BUILD_DIR}
PATH="${LLVM_BUILD_DIR}/bin:$PATH" cmake -G Ninja \
  -DTEST_SUITE_SUBDIRS=External \
  -DTEST_SUITE_EXTERNALS_DIR=${EXTERNAL_DIR}/ \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF \
  -DTEST_SUITE_COLLECT_COMPILE_TIME=OFF \
  -DAMDGPU_ARCHS="${AMDGPU_ARCHS}" \
  -DCMAKE_CXX_COMPILER="${LLVM_BUILD_DIR}/bin/clang++" \
  -DCMAKE_C_COMPILER="${LLVM_BUILD_DIR}/bin/clang" \
  -DCMAKE_VERBOSE_MAKEFILE=ON \
  ${TESTSUITE_ROOT}

build_step "Building HIP test-suite"
ninja hip-tests-simple

build_step "Testing HIP test-suite"
ninja check-hip-simple

exit 0

