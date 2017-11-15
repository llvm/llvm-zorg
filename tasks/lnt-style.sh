build get lnt

. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/pip_install.sh pycodestyle

cd lnt
utils/lint.sh
