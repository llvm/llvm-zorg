set -ex

apt-get update
apt-get install -y python3 python3-pip cmake ninja-build git ccache lsb-release wget software-properties-common gnupg wget
pip3 install --break-system-packages buildbot-worker==3.11.7

bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)" 20
ln -sf /usr/bin/clang-20 /usr/bin/cc
ln -sf /usr/bin/clang++-20 /usr/bin/c++
ln -sf /usr/bin/ld.lld-20 /usr/bin/ld

rm -rf /b
BOT_DIR=/b
SERVER_PORT=9994
WORKER_NAME="$(hostname)"
WORKER_PASSWORD="$(gsutil cat gs://sanitizer-buildbot/$(hostname)-password)"

userdel buildbot | true
groupadd -f buildbot
useradd buildbot -g buildbot -m -d /b/home
chown buildbot:buildbot $BOT_DIR

sudo -u buildbot buildbot-worker create-worker -f --allow-shutdown=signal $BOT_DIR lab.llvm.org:$SERVER_PORT \
   "${WORKER_NAME}" "${WORKER_PASSWORD}"

{
  echo "Mircea Trofin <mtrofin@google.com>"
  echo "Aiden Grossman <aidengrossman@google.com>"
} > $BOT_DIR/info/admin

{
  echo "To reproduce locally, use a standard CMake invocation with -DLLVM_ENABLE_PROFCHECK=ON and -DLLVM_LIT_ARGS='--exclude-xfail'"
  echo
  uname -a | head -n1
  date
  cmake --version | head -n1
  c++ --version | head -n1
  ld --version | head -n1
  lscpu
} > $BOT_DIR/info/host

sudo -u buildbot buildbot-worker start $BOT_DIR
