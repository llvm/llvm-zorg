echo "@@@ Install VirtualEnv LNT @@@"
# It seems that lnt/setup.py does not utilize the python/wheel package caches.
# Not sure why, we work around the problem by installing the requirements
# first:
. "${TASKDIR}"/utils/pip_install.sh -r lnt/requirements.client.txt
python lnt/setup.py develop
echo "@@@@@@"
