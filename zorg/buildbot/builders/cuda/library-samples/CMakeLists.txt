# Builds and runs NVIDIA's CUDA library samples for the CUDA bots (see
# _getCudaLibrarySamplesSteps in CudaBuilder.py).
#
# Every sample is a CMake project which refers to its siblings through CMAKE_SOURCE_DIR,
# so each is an ExternalProject of its own, once per toolkit, with a test named
# <toolkit>/<library>[/<group>]/<sample>.
#
# Inputs:
#   SAMPLES_DIR           A checkout of the samples.
#   TEST_SUITE_EXTERNALS  The LLVM test suite externals directory of the worker
#                         (TEST_SUITE_EXTERNALS_DIR there). Its cuda/ subdirectory holds
#                         the CUDA toolkits as cuda-<version> entries, each a toolkit
#                         install or a link to one: the samples get built against every
#                         one of them which is recent enough.
#   CLANG_DIR             The toolchain to build the samples with.
#   GPU_ARCH              The GPU to build them for, e.g. sm_86.
#
# This is a test suite more than a builder, and might be better off in the LLVM test
# suite (External/CUDA), next to the CUDA tests, which already use the same externals.

cmake_minimum_required(VERSION 3.20)
project(library-samples NONE)

include(ExternalProject)
enable_testing()

foreach(var SAMPLES_DIR TEST_SUITE_EXTERNALS CLANG_DIR GPU_ARCH)
  if("${${var}}" STREQUAL "")
    message(FATAL_ERROR "${var} is not set")
  endif()
endforeach()

# The directories holding one CMake project per sample: <library>[/<group>]. Left out:
#   - cuBLAS's Emulation group, as what it supports depends on the toolkit and on the
#     GPU.
#   - cuBLASLt, as most of its samples need a newer GPU than the sm_86 A10s of the
#     nvidia-cuda-a10-* builders. A builder on a newer GPU could add it.
#   - NPP and nvJPEG, whose samples need OpenCV or input images.
#   - The multi-process libraries (*Mp), which need MPI and NCCL, and the libraries
#     which do not come with the toolkit (cuTENSOR, cuDSS, nvCOMP and the like).
set(SAMPLE_GROUPS
  cuBLAS/Level-1
  cuBLAS/Level-2
  cuBLAS/Level-3
  cuBLAS/Extensions
  cuFFT
  cuRAND/Host
  cuSOLVER
  cuSPARSE
)

# The samples of those groups not to build, each for a reason which is not Clang's:
# <library>[/<group>]/<sample> for every toolkit, or <toolkit>/<library>[/<group>]/<sample>
# for one of them. Workers differ in their toolkits, so an exclusion for one toolkit is
# ignored where that toolkit is not tested.
set(EXCLUDED_SAMPLES
  # Passes cudaMemcpy2D a source pitch narrower than the row it copies, which fails
  # whoever compiles it.
  cuSOLVER/gesv
  # Links cuFFT's callbacks with nvJitLink LTO, which CMake only sets up for nvcc.
  cuFFT/lto_callback_window_1d
  # The custom operator samples compile their operators with NVRTC at run time,
  # against /usr/local/cuda: spmm_csr_op fails inside cuSPARSE when it plans them, and
  # spmvop_csr uses an API newer than the toolkit's cuSPARSE.
  cuSPARSE/spmm_csr_op
  cuSPARSE/spmvop_csr
  # Fails inside CUDA 13.4's cuSOLVER-Mg with nvcc as well ("cusolver error"), while
  # it passes on 13.1.
  cuda-13.4/cuSOLVER/MgPotrf
)

# The cuBLAS samples share a header which uses the CUDA 13 floating point emulation
# types unconditionally. One minimum for all the libraries keeps one list of toolkits.
set(MIN_CUDA_VERSION 13.0)

# The same toolkits as the CUDA tests of the LLVM test suite, except the older ones.
file(GLOB toolkits LIST_DIRECTORIES true "${TEST_SUITE_EXTERNALS}/cuda/cuda-*")
set(tested_toolkits)
set(tested_toolkit_names)
foreach(toolkit IN LISTS toolkits)
  get_filename_component(toolkit_name "${toolkit}" NAME)
  string(REGEX REPLACE "^cuda-" "" toolkit_version "${toolkit_name}")
  if(toolkit_version VERSION_LESS MIN_CUDA_VERSION)
    message(STATUS "${toolkit_name}: skipped, the samples need CUDA ${MIN_CUDA_VERSION} or newer")
  else()
    list(APPEND tested_toolkits "${toolkit}")
    list(APPEND tested_toolkit_names "${toolkit_name}")
  endif()
endforeach()
if(NOT tested_toolkits)
  message(FATAL_ERROR "no CUDA ${MIN_CUDA_VERSION} or newer in ${TEST_SUITE_EXTERNALS}/cuda")
endif()

# A group without samples means that the layout of the samples has changed.
set(samples)
set(excluded)
foreach(group IN LISTS SAMPLE_GROUPS)
  file(GLOB group_samples LIST_DIRECTORIES true RELATIVE "${SAMPLES_DIR}" "${SAMPLES_DIR}/${group}/*")
  set(group_count 0)
  foreach(sample IN LISTS group_samples)
    if(NOT EXISTS "${SAMPLES_DIR}/${sample}/CMakeLists.txt")
      continue()
    endif()
    if(sample IN_LIST EXCLUDED_SAMPLES)
      message(STATUS "${sample}: excluded")
      list(APPEND excluded "${sample}")
      continue()
    endif()
    list(APPEND samples "${sample}")
    math(EXPR group_count "${group_count} + 1")
  endforeach()
  if(group_count EQUAL 0)
    message(FATAL_ERROR "no samples in ${SAMPLES_DIR}/${group}")
  endif()
  message(STATUS "${group}: ${group_count} samples")
endforeach()

# A test runs every executable its sample built, and fails when there are none, so that
# a sample which failed to build does not pass. It also fails when a sample reports a
# wrong result, which the samples which check their results do while exiting
# successfully:
#   - "FAILED": "<sample> test FAILED: wrong result" from cuSPARSE, "FAILED with L2
#     error = ..." from the cuFFT multi-GPU samples, and "Check: FAILED" from cuSOLVER's
#     Xtrtri.
#   - "Error: max_relerr is bigger than eps" from cuSOLVER's Xgesvdr.
# The samples' other error messages come with a failing exit status.
set(runner "${CMAKE_BINARY_DIR}/run-sample.cmake")
file(WRITE "${runner}" [=[
file(GLOB executables "${BIN_DIR}/*")
if(NOT executables)
  message(FATAL_ERROR "no executables in ${BIN_DIR}")
endif()
foreach(executable IN LISTS executables)
  message(STATUS "running ${executable}")
  execute_process(COMMAND "${executable}" RESULT_VARIABLE result
                  OUTPUT_VARIABLE output ERROR_VARIABLE output)
  message("${output}")
  if(NOT result EQUAL 0)
    message(FATAL_ERROR "${executable} failed: ${result}")
  endif()
  if(output MATCHES "(^|[^A-Za-z])FAILED([^A-Za-z]|$)" OR
     output MATCHES "max_relerr is bigger than eps")
    message(FATAL_ERROR "${executable} reported a wrong result")
  endif()
endforeach()
]=])

foreach(toolkit IN LISTS tested_toolkits)
  get_filename_component(toolkit_name "${toolkit}" NAME)
  set(sample_count 0)
  foreach(sample IN LISTS samples)
    # An exclusion can also name a sample of one toolkit only, as <toolkit>/<sample>.
    if("${toolkit_name}/${sample}" IN_LIST EXCLUDED_SAMPLES)
      message(STATUS "${toolkit_name}/${sample}: excluded")
      list(APPEND excluded "${toolkit_name}/${sample}")
      continue()
    endif()
    math(EXPR sample_count "${sample_count} + 1")
    string(REPLACE "/" "_" target "${toolkit_name}_${sample}")
    set(binary_dir "${CMAKE_BINARY_DIR}/${toolkit_name}/${sample}")
    ExternalProject_Add(${target}
      SOURCE_DIR              "${SAMPLES_DIR}/${sample}"
      BINARY_DIR              "${binary_dir}"
      PREFIX                  "${CMAKE_BINARY_DIR}/ep/${target}"
      CMAKE_ARGS
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_C_COMPILER=${CLANG_DIR}/bin/clang
        -DCMAKE_CXX_COMPILER=${CLANG_DIR}/bin/clang++
        -DCMAKE_CUDA_COMPILER=${CLANG_DIR}/bin/clang++
        -DCUDAToolkit_ROOT=${toolkit}
        # Some samples compile as plain C or C++ and link the libraries by name only,
        # and the toolkits share sonames, so put the toolkit under test on the default
        # include, link and run paths rather than whichever one /usr/local/cuda is.
        -DCMAKE_C_STANDARD_INCLUDE_DIRECTORIES=${toolkit}/include
        -DCMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES=${toolkit}/include
        "-DCMAKE_EXE_LINKER_FLAGS=-L${toolkit}/lib64 -Wl,-rpath,${toolkit}/lib64"
        # The samples turn CUDA_ARCHITECTURES off, and clang's default GPU is older
        # than CUDA 13 supports.
        -DCMAKE_CUDA_FLAGS=--cuda-gpu-arch=${GPU_ARCH}
        # The samples set it themselves only after they have created their targets.
        -DCMAKE_RUNTIME_OUTPUT_DIRECTORY=${binary_dir}/bin
      # The outer ninja runs a sample per job, so a sample builds with one.
      BUILD_COMMAND           "${CMAKE_COMMAND}" --build <BINARY_DIR> --parallel 1
      INSTALL_COMMAND         ""
    )
    add_test(NAME "${toolkit_name}/${sample}"
             COMMAND "${CMAKE_COMMAND}" "-DBIN_DIR=${binary_dir}/bin" -P "${runner}")
    # The samples take seconds, so one which hangs must not hold up the GPU worker.
    set_tests_properties("${toolkit_name}/${sample}" PROPERTIES TIMEOUT 300)
    # The cuFFT multi-GPU samples run their GPUs as device 0 twice, and then compute
    # wrong results, or fail, when other processes use the GPU. So they run one at a
    # time, and the factory runs the tests with this label in a step of their own, with
    # the GPU to themselves.
    if(sample MATCHES "^cuFFT/.*_mgpu_")
      set_tests_properties("${toolkit_name}/${sample}" PROPERTIES
                           LABELS exclusive_gpu RUN_SERIAL TRUE)
    endif()
  endforeach()
  message(STATUS "${toolkit_name}: ${sample_count} tests")
endforeach()

# An exclusion which matches no sample is stale, unless it is for a toolkit which is not
# tested here.
foreach(sample IN LISTS EXCLUDED_SAMPLES)
  if(sample IN_LIST excluded)
    continue()
  endif()
  string(REGEX MATCH "^cuda-[^/]+" toolkit_name "${sample}")
  if(toolkit_name AND NOT toolkit_name IN_LIST tested_toolkit_names)
    message(STATUS "${sample}: ignored, ${toolkit_name} is not tested")
    continue()
  endif()
  message(FATAL_ERROR "the excluded sample ${sample} is not one of the samples")
endforeach()
