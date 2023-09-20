##### Interface Variables & Targets #####
BUILDROOT?=$(error "BUILDROOT has to be the path to the worker's build/ directory.")

# Renders one target per line in make order.  Each target will made with a
# build step with the 'get-steps' annotated builder (ve-linux.py).
get-steps:
	@echo "prepare"
	@echo "build-llvm"
	@echo "check-llvm"
	@echo "check-crt-ve"
#	@echo "check-unwind"
#	@echo "check-cxxabi"
#	@echo "check-cxx"
#	@echo "check-openmp"
#	@echo "check-all"

##### Tools #####
CMAKE?=cmake
NINJA?=ninja
TOOL_CONFIG_CACHE?=${HOME}/tools-config.cmake

##### Derived Configuration #####

# Path
MONOREPO=${BUILDROOT}/../llvm-project

# VE cache
VE_CONFIG_CACHE?=${MONOREPO}/clang/cmake/caches/VectorEngine.cmake

# Build foders
LLVM_BUILD=${BUILDROOT}/build_llvm

# 'Install' into the LLVM build tree.
LLVM_PREFIX=${BUILDROOT}/install

# Install prefix structure
X86_TARGET=x86_64-unknown-linux-gnu
VE_TARGET=ve-unknown-linux-gnu

### LLVM
LLVM_BUILD_TYPE=RelWithDebInfo
LLVM_OPTFLAGS=-O2
LLVM_TEST_OPTFLAGS=-O2
LLVM_OPENMP_TEST_OPTFLAGS=

##### Build Steps #####

# Compile crt and other llvm components at once.  This was previously
# impossible since crt is not compilable with other libraries.  By
# https://reviews.llvm.org/D153989, the problem is solved.  So, we can
# compile whole components at once even for VE.
#
# Our compiling mechanism is something like below because whole test is
# not implemented correctly, yet.
#  1. Build llvm for X86 and VE with all runtimes.
#  2. Perform check clang and check-llvm.
#  3. Perform check compiler-rt for VE.
# We will improve test cases.  And will use traditional build script
# once check-all work for VE well.

build-llvm:
	touch "${TOOL_CONFIG_CACHE}"
	mkdir -p "${LLVM_BUILD}"
	cd "${LLVM_BUILD}" && ${CMAKE} "${MONOREPO}/llvm" -G Ninja \
	      -C "${TOOL_CONFIG_CACHE}" \
	      -C "${VE_CONFIG_CACHE}" \
	      -DCMAKE_BUILD_TYPE="${LLVM_BUILD_TYPE}" \
	      -DCMAKE_INSTALL_PREFIX="${LLVM_PREFIX}" \
	      -DCMAKE_CXX_FLAGS="${LLVM_OPTFLAGS}" \
	      -DCMAKE_C_FLAGS="${LLVM_OPTFLAGS}" \
	      -DCLANG_LINK_CLANG_DYLIB=Off \
	      -DLLVM_BUILD_LLVM_DYLIB=Off \
	      -DLLVM_LINK_LLVM_DYLIB=Off \
	      -DLLVM_ENABLE_PROJECTS="clang" \
	      -DRUNTIMES_${X86_TARGET}_LIBOMP_OMPT_SUPPORT=Off \
	      -DRUNTIMES_${VE_TARGET}_COMPILER_RT_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${LLVM_TEST_OPTFLAGS}" \
	      -DRUNTIMES_${VE_TARGET}_LIBCXXABI_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${LLVM_TEST_OPTFLAGS} -ldl" \
	      -DRUNTIMES_${VE_TARGET}_LIBCXX_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${LLVM_TEST_OPTFLAGS} -ldl" \
	      -DRUNTIMES_${VE_TARGET}_LIBUNWIND_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${LLVM_TEST_OPTFLAGS}" \
	      -DRUNTIMES_${VE_TARGET}_OPENMP_TEST_OPENMP_FLAGS="-target ${VE_TARGET} ${LLVM_OPENMP_TEST_OPTFLAGS} -fopenmp -pthread -lrt -ldl -Wl,-rpath,${LLVM_BUILD}/lib/${VE_TARGET}"
	cd "${LLVM_BUILD}" && ${NINJA}

check-llvm:
	cd "${LLVM_BUILD}" && ${NINJA} check-clang
	cd "${LLVM_BUILD}" && ${NINJA} check-llvm
check-crt-ve:
	cd "${LLVM_BUILD}" && ${NINJA} check-compiler-rt-ve-unknown-linux-gnu
check-unwind:
	cd "${LLVM_BUILD}" && ${NINJA} check-unwind-ve-unknown-linux-gnu
check-cxxabi:
	cd "${LLVM_BUILD}" && ${NINJA} check-cxxabi-ve-unknown-linux-gnu
check-cxxabi-x86:
	cd "${LLVM_BUILD}" && ${NINJA} check-cxxabi-x86_64-unknown-linux-gnu
check-cxx:
	cd "${LLVM_BUILD}" && ${NINJA} check-cxx-ve-unknown-linux-gnu
check-cxx-x86:
	cd "${LLVM_BUILD}" && ${NINJA} check-cxx-x86_64-unknown-linux-gnu
check-openmp:
	cd "${LLVM_BUILD}" && ${NINJA} check-openmp-ve-unknown-linux-gnu
check-openmp-x86:
	cd "${LLVM_BUILD}" && ${NINJA} check-openmp-x86_64-unknown-linux-gnu
check-all:
	cd "${LLVM_BUILD}" && ${NINJA} check-all

# Clearout the temporary install prefix.
prepare:
	# Build everything from scratch - TODO: incrementalize later.
	rm -rf "${LLVM_PREFIX}"
	rm -rf "${LLVM_BUILD}"
