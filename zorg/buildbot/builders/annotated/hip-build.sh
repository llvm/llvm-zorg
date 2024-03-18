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

# Set-up variables
setup_env() {
build_step "Setting up the buildbot"
BUILDBOT_ROOT=${BUILDBOT_ROOT:-/buildbot}
BUILDBOT_SLAVENAME=$(whoami)
AMDGPU_ARCHS=${AMDGPU_ARCHS:="gfx908;gfx90a;gfx1030;gfx1100"}
EXTERNAL_DIR="${EXTERNAL_DIR:-/buildbot/Externals}"
BUILD_DIR="${BUILDBOT_ROOT}/${BUILDBOT_SLAVENAME}/${BUILDBOT_BUILDERNAME}"
DESTDIR=${BUILD_DIR}/install

LLVM_ROOT="${LLVM_ROOT:-${BUILDBOT_ROOT}/llvm-project}"
LLVM_REVISION="${BUILDBOT_REVISION:-origin/main}"
LLVM_BUILD_DIR="${LLVM_BUILD_DIR:-${BUILD_DIR}/llvm}"

TESTSUITE_ROOT="${TESTSUITE_ROOT:-${BUILDBOT_ROOT}/llvm-test-suite}"
TEST_BUILD_DIR="${TEST_BUILD_DIR:-${BUILD_DIR}/test-suite-build}"
NINJAOPT="${NINJAOPT:-}"

echo "BUILDBOT_ROOT=${BUILDBOT_ROOT}"
echo "BUILDBOT_SLAVENAME=${BUILDBOT_SLAVENAME}"
echo "AMDGPU_ARCHS=${AMDGPU_ARCHS}"
echo "LLVM_ROOT=${LLVM_ROOT}"
echo "TESTSUITE_ROOT=${TESTSUITE_ROOT}"
echo "EXTERNAL_DIR=${EXTERNAL_DIR}"
echo "BUILD_DIR=${BUILD_DIR}"
echo "DESTDIR=${DESTDIR}"
echo "LLVM_BUILD_DIR=${LLVM_BUILD_DIR}"
echo "TEST_BUILD_DIR=${TEST_BUILD_DIR}"
}

# Set-up llvm-project
update_llvm() {
if [ ! -d "${LLVM_ROOT}" ]; then
  build_step "Cloning llvm-project repo"
  git clone --progress https://github.com/llvm/llvm-project.git ${LLVM_ROOT}
fi

build_step "Updating llvm-project repo"
git -C "${LLVM_ROOT}" fetch origin
git -C "${LLVM_ROOT}" reset --hard "${LLVM_REVISION}"
}

# Set-up llvm-test-suite
update_test_suite() {
if [ ! -d "${TESTSUITE_ROOT}" ]; then
  build_step "Cloning llvm-test-suite repo"
  git clone --progress https://github.com/llvm/llvm-test-suite.git ${TESTSUITE_ROOT}
fi

build_step "Updating llvm-test-suite repo"
git -C "${TESTSUITE_ROOT}" fetch origin
git -C "${TESTSUITE_ROOT}" reset --hard origin/main
}

# Start building LLVM, Clang, Lld, clang-tools-extra, compiler-rt
build_llvm() {
build_step "Configure LLVM Build"
mkdir -p "${LLVM_BUILD_DIR}"
cd "${LLVM_BUILD_DIR}"
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE="Release" \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DCMAKE_VERBOSE_MAKEFILE=1 \
  -DLLVM_TARGETS_TO_BUILD="AMDGPU;X86" \
  -DLLVM_ENABLE_PROJECTS="clang;lld;clang-tools-extra;compiler-rt" \
  -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind" \
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
ninja $NINJAOPT

build_step "Install LLVM"
rm -rf "${DESTDIR}"
ninja install-runtimes
ninja install
}

# Start building llvm-test-suite's hip tests
build_test_suite() {
build_step "Configuring HIP test-suite"
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
ninja $NINJAOPT hip-tests-simple

build_step "Testing HIP test-suite"
ninja $NINJAOPT check-hip-simple
}

setup_env
update_llvm
build_llvm
update_test_suite
build_test_suite

exit 0

