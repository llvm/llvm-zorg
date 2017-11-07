echo "@@@ LNT @@@"

mkdir "lnt-sandbox"

LNT_FLAGS+=" --sandbox ${WORKSPACE}/lnt-sandbox"
LNT_FLAGS+=" --no-timestamp"
LNT_FLAGS+=" --use-lit=lit"
LNT_FLAGS+=" --cc ${WORKSPACE}/compiler/bin/clang"
LNT_FLAGS+=" --cxx ${WORKSPACE}/compiler/bin/clang++"
LNT_FLAGS+=" --test-suite=${WORKSPACE}/test-suite"
LNT_FLAGS+=" --cmake-define TEST_SUITE_BENCHMARKING_ONLY=On"
LNT_FLAGS+=" --output \"${WORKSPACE}/lnt-sandbox/report.json\""
if [ -n "${SUBMIT_NAME:=}" ]; then
    # Use jenkins job name as submission name
    LNT_FLAGS+=" --no-auto-name '${SUBMIT_NAME}'"
    if test -n "${SUBMIT_ORDER:=}"; then
        LNT_FLAGS+=" --run-order \"${SUBMIT_ORDER}\""
    fi
fi

eval lnt runtest test-suite ${LNT_FLAGS}

echo "@@@@@@"
