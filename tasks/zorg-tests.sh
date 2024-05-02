. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/pip_install.sh --upgrade pip
. "${TASKDIR}"/utils/venv_lit.sh
. "${TASKDIR}"/utils/pip_install.sh -r config/zorg/jenkins/jobs/requirements.txt

mkdir -p result
cd "config/test/jenkins"
lit --xunit-xml-output="${WORKSPACE}/result/xunit.xml" -v .
