SUBMIT_URL="$(build arg --optional SUBMIT_URL)"
SUBMIT_NAME="$(build arg --optional SUBMIT_NAME)"
SUBMIT_ORDER="$(build arg --optional SUBMIT_ORDER)"
LNT_FLAGS="$(build arg --optional LNT_FLAGS)"

# Set defaults for missing/empty parameters.
: ${SUBMIT_URL:='http://104.154.54.203/db_default/v4/nts/submitRun'}
: ${SUBMIT_NAME:="${JOB_NAME-}"}

build get lnt
build get compiler
build get test-suite


DEPENDENCY_FILES="${TASKDIR}"/lnt-testsuite.dep
. "${TASKDIR}"/utils/check_dependencies.sh

. "${TASKDIR}"/utils/normalize_compiler.sh
. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/venv_lit.sh
. "${TASKDIR}"/utils/venv_lnt.sh

. "${TASKDIR}"/utils/lnt_test_suite.sh
. "${TASKDIR}"/utils/lnt_submit.sh

. "${TASKDIR}"/utils/lnt_move_results.sh
. "${TASKDIR}"/utils/lnt_check_no_errors.sh
