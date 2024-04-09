CMAKE_FLAGS="$(build arg --optional CMAKE_FLAGS)"

. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/pip_install.sh --upgrade pip
. "${TASKDIR}"/utils/pip_install.sh awscli

build get compiler
build get test-suite

. "${TASKDIR}"/utils/normalize_compiler.sh
. "${TASKDIR}"/utils/venv_lit.sh

TEST_SUITE_CMAKE_FLAGS+=" -C ${TASKDIR}/cmake/caches/verify-machineinstrs.cmake"
TEST_SUITE_CMAKE_FLAGS+=" ${CMAKE_FLAGS}"
TEST_SUITE_NINJA_FLAGS+=" -v -k0"
. "${TASKDIR}"/utils/test_suite_compile.sh
