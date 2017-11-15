# Note: This task assumes that mysql and postgres are installed with homebrew.

build get lnt

. "${TASKDIR}"/utils/venv.sh
. "${TASKDIR}"/utils/venv_lit.sh

. "${TASKDIR}"/utils/pip_install.sh -r lnt/requirements.server.txt
. "${TASKDIR}"/utils/pip_install.sh mysql-python

python lnt/setup.py develop --server

cd "${WORKSPACE}"
mkdir result
mkdir build
cd build
lit -j1 --xunit-xml-output="${WORKSPACE}/result/xunit.xml" -v "${WORKSPACE}/lnt/tests" -D postgres=True -D mysql=True
