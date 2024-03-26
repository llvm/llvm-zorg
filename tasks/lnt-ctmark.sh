SUBMIT_URL="$(build arg --optional SUBMIT_URL)"
SUBMIT_NAME="$(build arg --optional SUBMIT_NAME)"
SUBMIT_ORDER="$(build arg --optional SUBMIT_ORDER)"
# This is should be used to supply the cmake cache file to use
LNT_FLAGS="$(build arg --optional LNT_FLAGS)"

# Set defaults for missing/empty parameters.
: ${SUBMIT_URL:='http://104.154.54.203/db_default/v4/nts/submitRun'}
: ${SUBMIT_NAME:="${NODE_NAME-}_${JOB_NAME-}"}
: ${SUBMIT_ORDER:="${GIT_DISTANCE-}"}

. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/pip_install.sh --upgrade pip
. "${TASKDIR}"/utils/pip_install.sh awscli

# A generic ctmark run designed to run as a recurring jenkins job with varying
# cmake caches and submission to an lnt server.
build get compiler
build get test-suite
build get lnt

DEPENDENCY_FILES="${TASKDIR}"/lnt-testsuite.dep
. "${TASKDIR}"/utils/check_dependencies.sh
. "${TASKDIR}"/utils/normalize_compiler.sh
. "${TASKDIR}"/utils/venv_lit.sh
. "${TASKDIR}"/utils/venv_lnt.sh

LNT_FLAGS+=" --cmake-define TEST_SUITE_RUN_BENCHMARKS=Off"
LNT_FLAGS+=" --build-threads 1"
LNT_FLAGS+=" --cmake-define TEST_SUITE_SUBDIRS=\"CTMark\""
. "${TASKDIR}"/utils/lnt_test_suite.sh
. "${TASKDIR}"/utils/lnt_submit.sh

. "${TASKDIR}"/utils/lnt_move_results.sh
. "${TASKDIR}"/utils/lnt_check_no_errors.sh
