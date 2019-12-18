echo "@@@ Install VirtualEnv Lit @@@"
svn checkout -q --trust-server-cert-failures=unknown-ca --non-interactive https://github.com/llvm/llvm-project/trunk/llvm/utils/lit/ lit-src
. "${TASKDIR}"/utils/pip_install.sh lit-src/
echo "@@@@@@"
