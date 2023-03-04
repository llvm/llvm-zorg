##### Interface Variables & Targets #####
BUILDROOT?=$(error "BUILDROOT has to be the path to the worker's build/ directory.")

# Renders one target per line in make order.  Each target will made with a
# build step with the 'get-steps' annotated builder (ve-linux.py).
get-steps:
	@echo "prepare"
	@echo "build-llvm"
	@echo "check-llvm"
	@echo "install-llvm"
	@echo "build-crt-ve"
	@echo "check-crt-ve"
	@echo "install-crt-ve"
	@echo "build-runtimes-ve"
	@echo "install-runtimes-ve"
# @echo "check-runtimes-ve"

##### Tools #####
CMAKE?=cmake
NINJA?=ninja
TOOL_CONFIG_CACHE?=${HOME}/tools-config.cmake

##### Derived Configuration #####

# Path

MONOREPO=${BUILDROOT}/../llvm-project

# Build foders
LLVM_BUILD=${BUILDROOT}/build_llvm
CRT_BUILD_VE=${BUILDROOT}/build_crt_ve
RUNTIMES_BUILD_VE=${BUILDROOT}/build_runtimes_ve

# 'Install' into the LLVM build tree.
LLVM_PREFIX=${BUILDROOT}/install

# Install prefix structure
BUILT_CLANG=${LLVM_PREFIX}/bin/clang
BUILT_CLANGXX=${LLVM_PREFIX}/bin/clang++
X86_TARGET=x86_64-unknown-linux-gnu
VE_TARGET=ve-unknown-linux-gnu

### LLVM
LLVM_BUILD_TYPE=RelWithDebInfo

### Compiler-RT
CRT_BUILD_TYPE=Release
CRT_OPTFLAGS=-O2
CRT_TEST_OPTFLAGS=-O2

## Runtimes
RUNTIMES_BUILD_TYPE=Release
RUNTIMES_OPTFLAGS=-O2

##### Build Steps #####

# Standalone build has been prohibited.  However, runtime build is not
# possible for VE because crt-ve is needed to be compiled by just compiled
# llvm.  Such bootstrap build CMakefile is not merged yet.  Check
# https://reviews.llvm.org/D89492 for details.
#
# As a result, we compile llvm for ve using following three steps.
#  1. Build llvm for X86 and VE with only X86 runtimes.
#  1.1 check-llvm
#  2. Build llvm for X86 and VE with x86 and VE compiler-rt runtimes.
#  2.1 check-compiler-rt for VE
#  3. Build x86 and VE all possible runtimes using 2.

### Vanilla LLVM stage ###
build-llvm:
	touch "${TOOL_CONFIG_CACHE}"
	mkdir -p "${LLVM_BUILD}"
	cd "${LLVM_BUILD}" && ${CMAKE} "${MONOREPO}/llvm" -G Ninja \
	      -C "${TOOL_CONFIG_CACHE}" \
	      -DCMAKE_BUILD_TYPE="${LLVM_BUILD_TYPE}" \
	      -DCMAKE_INSTALL_PREFIX="${LLVM_PREFIX}" \
	      -DCLANG_LINK_CLANG_DYLIB=Off \
	      -DLLVM_BUILD_LLVM_DYLIB=Off \
	      -DLLVM_LINK_LLVM_DYLIB=Off \
	      -DLLVM_TARGETS_TO_BUILD="X86;VE" \
	      -DLLVM_ENABLE_PROJECTS="clang" \
	      -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=On
	cd "${LLVM_BUILD}" && ${NINJA}

check-llvm:
	cd "${LLVM_BUILD}" && ${NINJA} check-all

install-llvm:
	cd "${LLVM_BUILD}" && ${NINJA} install

### Compiler-RT ###

build-crt-ve:
	mkdir -p "${CRT_BUILD_VE}"
	cd "${CRT_BUILD_VE}" && ${CMAKE} "${MONOREPO}/llvm" -G Ninja \
	      -C "${TOOL_CONFIG_CACHE}" \
	      -DCMAKE_BUILD_TYPE="${CRT_BUILD_TYPE}" \
	      -DCMAKE_INSTALL_PREFIX="${LLVM_PREFIX}" \
	      -DCMAKE_C_COMPILER="${BUILT_CLANG}" \
	      -DCMAKE_CXX_COMPILER="${BUILT_CLANGXX}" \
	      -DCMAKE_CXX_FLAGS_RELEASE="${CRT_OPTFLAGS}" \
	      -DCMAKE_C_FLAGS_RELEASE="${CRT_OPTFLAGS}" \
	      -DCLANG_LINK_CLANG_DYLIB=Off \
	      -DLLVM_BUILD_LLVM_DYLIB=Off \
	      -DLLVM_LINK_LLVM_DYLIB=Off \
	      -DLLVM_TARGETS_TO_BUILD="X86;VE" \
	      -DLLVM_ENABLE_PROJECTS="clang" \
	      -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
	      -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=On \
	      -DLLVM_INSTALL_UTILS=On \
	      -DLLVM_RUNTIME_TARGETS="${X86_TARGET};${VE_TARGET}" \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_BUILTINS=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_CRT=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_SANITIZERS=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_XRAY=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_LIBFUZZER=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_PROFILE=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_MEMPROF=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_ORC=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_GWP_ASAN=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_USE_BUILTINS_LIBRARY=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${CRT_TEST_OPTFLAGS}"
	cd "${CRT_BUILD_VE}" && ${NINJA}

check-crt-ve:
	cd "${CRT_BUILD_VE}" && ${NINJA} check-compiler-rt-ve-unknown-linux-gnu

install-crt-ve:
	cd "${CRT_BUILD_VE}" && ${NINJA} install

### Runtimes ###

# It is not possible to compile clang nor compiler-rt with other runtimes
# at once for VE.  Because the crtbegin bootstrap mechanism is merged yet.
# See https://reviews.llvm.org/D89492 for details.  Without this patch,
# running regression tests for runtimes is also not possible for VE.
#
# Once this patch is merged, it will be possible to compile runtimes
# with following defines using single build step.
#             -DLLVM_ENABLE_PROJECTS="clang" \
#             -DLLVM_ENABLE_RUNTIMES="compiler-rt;libunwind" \
#             -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BOOTSTRAP=On \

build-runtimes-ve:
	mkdir -p "${RUNTIMES_BUILD_VE}"
	cd "${RUNTIMES_BUILD_VE}" && ${CMAKE} "${MONOREPO}/llvm" -G Ninja \
	      -C "${TOOL_CONFIG_CACHE}" \
	      -DCMAKE_BUILD_TYPE="${RUNTIMES_BUILD_TYPE}" \
	      -DCMAKE_INSTALL_PREFIX="${LLVM_PREFIX}" \
	      -DCMAKE_C_COMPILER="${BUILT_CLANG}" \
	      -DCMAKE_CXX_COMPILER="${BUILT_CLANGXX}" \
	      -DCMAKE_CXX_FLAGS_RELEASE="${RUNTIMES_OPTFLAGS}" \
	      -DCMAKE_C_FLAGS_RELEASE="${RUNTIMES_OPTFLAGS}" \
	      -DCLANG_LINK_CLANG_DYLIB=Off \
	      -DLLVM_BUILD_LLVM_DYLIB=Off \
	      -DLLVM_LINK_LLVM_DYLIB=Off \
	      -DLLVM_TARGETS_TO_BUILD="X86;VE" \
	      -DLLVM_ENABLE_PROJECTS="" \
	      -DLLVM_ENABLE_RUNTIMES="libunwind" \
	      -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=On \
	      -DLLVM_RUNTIME_TARGETS="${X86_TARGET};${VE_TARGET}" \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_BUILTINS=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_CRT=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_SANITIZERS=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_XRAY=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_LIBFUZZER=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_PROFILE=On \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_MEMPROF=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_ORC=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_BUILD_GWP_ASAN=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_USE_BUILTINS_LIBRARY=On \
	      -DRUNTIMES_${VE_TARGET}_LIBCXXABI_USE_LLVM_UNWINDER=On \
	      -DRUNTIMES_${VE_TARGET}_LIBCXXABI_USE_COMPILER_RT=On \
	      -DRUNTIMES_${VE_TARGET}_LIBCXX_USE_COMPILER_RT=On \
	      -DRUNTIMES_${VE_TARGET}_CMAKE_C_COMPILER="${BUILT_CLANG}" \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${RUNTIMES_TEST_OPTFLAGS}" \
	      -DRUNTIMES_${VE_TARGET}_LIBCXXABI_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${RUNTIMES_TEST_OPTFLAGS}" \
	      -DRUNTIMES_${VE_TARGET}_LIBCXX_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${RUNTIMES_TEST_OPTFLAGS}" \
	      -DRUNTIMES_${VE_TARGET}_LIBUNWIND_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${RUNTIMES_TEST_OPTFLAGS}"
	cd "${RUNTIMES_BUILD_VE}" && ${NINJA}

check-runtimes-ve:
	cd "${RUNTIMES_BUILD_VE}" && ${NINJA} check-runtimes-ve-unknown-linux-gnu

install-runtimes-ve:
	cd "${RUNTIMES_BUILD_VE}" && ${NINJA} install

# Clearout the temporary install prefix.
prepare:
	# Build everything from scratch - TODO: incrementalize later.
	rm -rf "${LLVM_PREFIX}"
	rm -rf "${LLVM_BUILD}"
	rm -rf "${CRT_BUILD_VE}"
	rm -rf "${RUNTIMES_BUILD_VE}"
