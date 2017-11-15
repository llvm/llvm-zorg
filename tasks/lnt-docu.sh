build get lnt

. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/venv_lit.sh

. "${TASKDIR}"/utils/pip_install.sh -r lnt/requirements.client.txt
. "${TASKDIR}"/utils/pip_install.sh sphinx sphinx-bootstrap-theme

cd "${WORKSPACE}"
mkdir -p build/docs
make BUILDDIR="${WORKSPACE}/build/docs" -C "${WORKSPACE}/lnt/docs" html
