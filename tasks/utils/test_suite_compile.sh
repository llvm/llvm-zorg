echo "@@@ Test-Suite Compile @@@"
rm -rf "test-suite-build"
mkdir -p "test-suite-build"
cd "test-suite-build"
TEST_SUITE_CMAKE_FLAGS+="" # Make sure variable is defined
# Note that we prepend CMAKE_C_COMPILER to ensure it is set before cache files
# (-C flags) are executed.
TEST_SUITE_CMAKE_FLAGS="-DCMAKE_C_COMPILER=\"${WORKSPACE}/compiler/bin/clang\" ${TEST_SUITE_CMAKE_FLAGS}"

# Default value
: ${TEST_SUITE_PGO_BUILD:=}

TEST_SUITE_CMAKE_FLAGS+=" -GNinja"
TEST_SUITE_CMAKE_FLAGS+=" ${WORKSPACE}/test-suite"
if [ "${TEST_SUITE_PGO_BUILD}" = "1" ]; then
    TEST_SUITE_CMAKE_FLAGS+=" -DTEST_SUITE_RUN_TYPE=train"
    TEST_SUITE_CMAKE_FLAGS+=" -DTEST_SUITE_PROFILE_GENERATE=On"
fi
eval cmake ${TEST_SUITE_CMAKE_FLAGS}

TEST_SUITE_NINJA_FLAGS+="" # Make sure variable is defined
eval ninja "${TEST_SUITE_NINJA_FLAGS}"

if [ "${TEST_SUITE_PGO_BUILD}" = "1" ]; then
    if [ -z ${TEST_SUITE_LIT_TARGETS+x} ]; then
        TEST_SUITE_LIT_TARGETS="."
    fi
    TEST_SUITE_LIT_FLAGS+="" # make sure variable is defined
    eval lit -j1 ${TEST_SUITE_LIT_FLAGS} ${TEST_SUITE_LIT_TARGETS}
    # Rerun cmake with flipped profile flags
    eval cmake -DTEST_SUITE_PROFILE_GENERATE=Off -DTEST_SUITE_PROFILE_USE=On -DTEST_SUITE_RUN_TYPE=ref .
    eval ninja "${TEST_SUITE_NINJA_FLAGS}"
fi

cd "${WORKSPACE}"
echo "@@@@@@"
