##### Interface Variables & Targets #####
BUILDROOT?=$(error "BUILDROOT has to be the path to the worker's build/ directory.")

# Renders one target per line in make order.  Each target will made with a
# build step with the 'get-steps' annotated builder (ve-linux.py).
get-steps:
	@echo "prepare"
	@echo "build-llvm"
	@echo "check-llvm"
	@echo "build-crt-ve"
	@echo "install-crt-ve"
	@echo "check-crt-ve"
	@echo "build-libunwind-ve"
	@echo "install-libunwind-ve"
# @echo "build-libcxx-ve"
# @echo "install-libcxx-ve"
# @echo "build-libcxxabi-ve"
# @echo "install-libcxxabi-ve"


##### Tools #####
CMAKE?=cmake
NINJA?=ninja
TOOL_CONFIG_CACHE?=${HOME}/tools-config.cmake

##### Derived Configuration #####

# Path

MONOREPO=${BUILDROOT}/../llvm-project

# Build foders
LLVM_BUILD="${BUILDROOT}/build_llvm"
CRT_BUILD_VE="${BUILDROOT}/build_crt_ve"
LIBUNWIND_BUILD_VE="${BUILDROOT}/build_libunwind_ve"
LIBCXXABI_BUILD_VE="${BUILDROOT}/build_libcxxabi_ve"
LIBCXX_BUILD_VE="${BUILDROOT}/build_libcxx_ve"

# 'Install' into the LLVM build tree.
INTREE_PREFIX="${LLVM_BUILD}"
LLVM_PREFIX="${BUILDROOT}/install"

# Install prefix structure
BUILT_CLANG="${INTREE_PREFIX}/bin/clang"
BUILT_CLANGXX="${INTREE_PREFIX}/bin/clang++"
VE_TARGET="ve-unknown-linux-gnu"
LINUX_VE_LIBSUFFIX=/linux/ve

# Resource dir
RES_VERSION=$(shell grep 'set.*LLVM_VERSION_MAJOR  *' ${MONOREPO}/llvm/CMakeLists.txt | sed -e 's/.*LLVM_VERSION_MAJOR //' -e 's/[^0-9][^0-9]*//')
CLANG_RESDIR="${INTREE_PREFIX}/lib/clang/${RES_VERSION}"

### LLVM
LLVM_BUILD_TYPE=RelWithDebInfo

### Compiler-RT
CRT_BUILD_TYPE=Release
CRT_OPTFLAGS=-O2
CRT_TEST_OPTFLAGS=-O2

## libunwind
LIBUNWIND_BUILD_TYPE=Release
LIBUNWIND_OPTFLAGS=-O2

## libcxxabi
LIBCXXABI_BUILD_TYPE=Release
LIBCXXABI_OPTFLAGS=-O2

## libcxxabi
LIBCXX_BUILD_TYPE=Release
LIBCXX_OPTFLAGS=-O2




##### Build Steps #####

### Vanilla LLVM stage ###
build-llvm:
	touch ${TOOL_CONFIG_CACHE}
	mkdir -p ${LLVM_BUILD}
	cd ${LLVM_BUILD} && ${CMAKE} ${MONOREPO}/llvm -G Ninja \
	      -C ${TOOL_CONFIG_CACHE} \
	      -DCMAKE_BUILD_TYPE=RelWithDebInfo \
	      -DLLVM_BUILD_LLVM_DYLIB=Off \
	      -DLLVM_LINK_LLVM_DYLIB=Off \
	      -DCLANG_LINK_CLANG_DYLIB=Off \
	      -DLLVM_TARGETS_TO_BUILD="X86;VE" \
	      -DLLVM_ENABLE_PROJECTS="clang" \
	      -DCMAKE_INSTALL_PREFIX="${LLVM_PREFIX}" \
	      -DLLVM_INSTALL_UTILS=On
	cd ${LLVM_BUILD} && ${NINJA}

# install-llvm:
# 	# build-llvm
# 	cd ${LLVM_BUILD} && ${NINJA} install

check-llvm:
	# build-llvm
	cd ${LLVM_BUILD} && ${NINJA} check-all


### Compiler-RT standalone ###

build-crt-ve:
	mkdir -p ${CRT_BUILD_VE}
	cd ${CRT_BUILD_VE} && ${CMAKE} ${MONOREPO}/runtimes -G Ninja \
            -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
	    -DCOMPILER_RT_BUILD_BUILTINS=ON \
	    -DCOMPILER_RT_BUILD_SANITIZERS=OFF \
	    -DCOMPILER_RT_BUILD_XRAY=OFF \
	    -DCOMPILER_RT_BUILD_LIBFUZZER=OFF \
	    -DCOMPILER_RT_BUILD_PROFILE=ON \
	    -DBUILD_SHARED_LIBS=ON \
	    -DCMAKE_C_COMPILER=${BUILT_CLANG} \
	    -DCMAKE_C_COMPILER_TARGET="${VE_TARGET}" \
	    -DCMAKE_CXX_COMPILER=${BUILT_CLANGXX} \
	    -DCMAKE_CXX_COMPILER_TARGET="${VE_TARGET}" \
	    -DCMAKE_ASM_COMPILER_TARGET="${VE_TARGET}" \
	    -DCMAKE_AR=${INTREE_PREFIX}/bin/llvm-ar \
	    -DCMAKE_RANLIB=${INTREE_PREFIX}/bin/llvm-ranlib \
	    -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON \
	    -DLLVM_CMAKE_DIR=${INTREE_PREFIX} \
	    -DCMAKE_BUILD_TYPE="${CRT_BUILD_TYPE}" \
	    -DCMAKE_INSTALL_PREFIX="${CLANG_RESDIR}" \
	    -DCMAKE_CXX_FLAGS="-nostdlib" \
	    -DCMAKE_CXX_FLAGS_RELEASE="${CRT_OPTFLAGS}" \
	    -DCMAKE_C_FLAGS="-nostdlib" \
	    -DCMAKE_C_FLAGS_RELEASE="${CRT_OPTFLAGS}" \
	    -DCOMPILER_RT_INCLUDE_TESTS=ON \
	    -DCOMPILER_RT_TEST_COMPILER=${BUILT_CLANG} \
	    -DCOMPILER_RT_TEST_COMPILER_CFLAGS="-target ${VE_TARGET} ${CRT_TEST_OPTFLAGS}"
	cd ${CRT_BUILD_VE} && ${NINJA}

check-crt-ve: build-crt-ve
	cd ${CRT_BUILD_VE} && env PATH=${INTREE_PREFIX}/bin:${PATH} ${NINJA} check-compiler-rt

install-crt-ve: build-crt-ve
	cd ${CRT_BUILD_VE} && ${NINJA} install


### libunwind standalone ###
build-libunwind-ve:
	mkdir -p ${LIBUNWIND_BUILD_VE}
	cd ${LIBUNWIND_BUILD_VE} && ${CMAKE} ${MONOREPO}/runtimes -G Ninja \
            -DLLVM_ENABLE_RUNTIMES="libunwind" \
	    -DCMAKE_C_COMPILER=${BUILT_CLANG} \
	    -DCMAKE_CXX_COMPILER=${BUILT_CLANGXX} \
	    -DCMAKE_AR=${INTREE_PREFIX}/bin/llvm-ar \
	    -DCMAKE_RANLIB=${INTREE_PREFIX}/bin/llvm-ranlib \
	    -DCMAKE_ASM_COMPILER_TARGET="${VE_TARGET}" \
	    -DCMAKE_C_COMPILER_TARGET="${VE_TARGET}" \
	    -DCMAKE_CXX_COMPILER_TARGET="${VE_TARGET}" \
	    -DCMAKE_BUILD_TYPE="${LIBUNWIND_BUILD_TYPE}" \
	    -DCMAKE_INSTALL_PREFIX="${CLANG_RESDIR}" \
	    -DLIBUNWIND_LIBDIR_SUFFIX="${LINUX_VE_LIBSUFFIX}" \
	    -DCMAKE_CXX_FLAGS="-nostdlib" \
	    -DCMAKE_CXX_FLAGS_RELEASE="${LIBUNWIND_OPTFLAGS}" \
	    -DCMAKE_C_FLAGS="-nostdlib" \
	    -DCMAKE_C_FLAGS_RELEASE="${LIBUNWIND_OPTFLAGS}" \
	    -DLIBUNWIND_LIBCXX_PATH=${MONOREPO}/libcxx \
	    -DLLVM_PATH=${MONOREPO}/llvm
	cd ${LIBUNWIND_BUILD_VE} && ${NINJA}

install-libunwind-ve:
	cd ${LIBUNWIND_BUILD_VE} && ${NINJA} install


### libcxx standalone ###

build-libcxx-ve:
	mkdir -p ${LIBCXX_BUILD_VE}
	cd ${LIBCXX_BUILD_VE} && ${CMAKE} ${MONOREPO}/runtimes -G Ninja \
                -DLLVM_ENABLE_RUNTIMES="libcxx" \
	        -DLIBCXX_USE_COMPILER_RT=True \
  	        -DCMAKE_C_COMPILER=${BUILT_CLANG} \
  	        -DCMAKE_CXX_COMPILER=${BUILT_CLANGXX} \
  	        -DCMAKE_AR=${INTREE_PREFIX}/bin/llvm-ar \
  	        -DCMAKE_RANLIB=${INTREE_PREFIX}/bin/llvm-ranlib \
  	        -DCMAKE_C_COMPILER_TARGET="${VE_TARGET}" \
  	        -DCMAKE_CXX_COMPILER_TARGET="${VE_TARGET}" \
  	        -DCMAKE_BUILD_TYPE="${LIBCXX_BUILD_TYPE}" \
  	        -DCMAKE_INSTALL_PREFIX="${CLANG_RESDIR}" \
  	        -DLIBCXX_LIBDIR_SUFFIX="${LINUX_VE_LIBSUFFIX}" \
  	        -DLIBCXXABI_USE_LLVM_UNWINDER=True \
  	        -DLIBCXX_CXX_ABI=libcxxabi \
  	        -DLIBCXX_CXX_ABI_INCLUDE_PATHS=${MONOREPO}/libcxxabi/include \
  	        -DCMAKE_C_FLAGS_RELEASE="${LIBCXX_OPTFLAGS}" \
  	        -DCMAKE_CXX_FLAGS="-nostdlib++" \
  	        -DCMAKE_CXX_FLAGS_RELEASE="${LIBCXX_OPTFLAGS}" \
  	        -DLIBCXX_USE_COMPILER_RT=True
	cd ${LIBCXX_BUILD_VE} && ${NINJA}

check-libcxx-ve:
	cd ${LIBCXX_BUILD_VE} && ${NINJA} check-cxx

install-libcxx-ve:
	cd ${LIBCXX_BUILD_VE} && ${NINJA} install
        



### libcxxabi standalone ###

build-libcxxabi-ve:
	mkdir -p ${LIBCXXABI_BUILD_VE}
	cd ${LIBCXXABI_BUILD_VE} && ${CMAKE} ${MONOREPO}/runtimes -G Ninja \
              -DLLVM_ENABLE_RUNTIMES="libcxxabi" \
	      -DCMAKE_C_COMPILER=${BUILT_CLANG} \
	      -DCMAKE_CXX_COMPILER=${BUILT_CLANGXX} \
	      -DCMAKE_AR=${INTREE_PREFIX}/bin/llvm-ar \
	      -DCMAKE_RANLIB=${INTREE_PREFIX}/bin/llvm-ranlib \
	      -DCMAKE_C_COMPILER_TARGET="${VE_TARGET}" \
	      -DCMAKE_CXX_COMPILER_TARGET="${VE_TARGET}" \
	      -DCMAKE_BUILD_TYPE="${LIBCXXABI_BUILD_TYPE}" \
	      -DCMAKE_INSTALL_PREFIX="${CLANG_RESDIR}" \
	      -DLIBCXXABI_LIBDIR_SUFFIX="${LINUX_VE_LIBSUFFIX}" \
	      -DLIBCXXABI_USE_LLVM_UNWINDER=YES \
	      -DCMAKE_CXX_FLAGS="-nostdlib++" \
	      -DCMAKE_CXX_FLAGS_RELEASE="${LIBCXX_OPTFLAGS}" \
	      -DCMAKE_C_FLAGS_RELEASE="${LIBCXX_OPTFLAGS}" \
	      -DLLVM_PATH=${MONOREPO}/llvm \
	      -DLLVM_MAIN_SRC_DIR=${MONOREPO}/llvm \
	      -DLIBCXXABI_USE_COMPILER_RT=True \
	      -DLIBCXXABI_HAS_NOSTDINCXX_FLAG=True \
	      -DLIBCXXABI_LIBCXX_INCLUDES="${CLANG_RESDIR}/include/c++/v1/"
	cd ${LIBCXXABI_BUILD_VE} && ${NINJA}
        
check-libcxxabi-ve:
	cd ${LIBCXXABI_BUILD_VE} && ${NINJA} check-cxxabi

install-libcxxabi-ve:
	cd ${LIBCXXABI_BUILD_VE} && ${NINJA} install
        
# Clearout the temporary install prefix.
prepare:
	# Build everything from scratch - TODO: incrementalize later.
	rm -rf ${LLVM_PREFIX}
	rm -rf ${LLVM_BUILD}
	rm -rf ${CRT_BUILD_VE}
	rm -rf ${LIBUNWIND_BUILD_VE}
	rm -rf ${LIBCXXABI_BUILD_VE}
	rm -rf ${LIBCXX_BUILD_VE}
