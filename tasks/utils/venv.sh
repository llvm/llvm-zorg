echo "@@@ LNT VirtualEnv @@@"
/usr/local/bin/virtualenv --python=python3 venv
set +u
. venv/bin/activate
set -u
echo "@@@@@@@"
