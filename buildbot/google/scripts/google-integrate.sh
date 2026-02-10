set -ex

# Delete this repository as it does not exist for Ubuntu 24.04 and apt-get
# will fail in every invocation otherwise.
sudo rm -rf /etc/apt/sources.list.d/scalibr-apt.list
apt-get -o DPkg::Lock::Timeout=-1 update
apt-get -o DPkg::Lock::Timeout=-1 install -y python3 python3-pip cmake ninja-build git ccache lsb-release wget software-properties-common gnupg
pip3 install --break-system-packages buildbot-worker==3.11.7

wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh
chmod +x /tmp/llvm.sh
/tmp/llvm.sh 21
ln -sf /usr/bin/clang-21 /usr/bin/cc
ln -sf /usr/bin/clang++-21 /usr/bin/c++
ln -sf /usr/bin/ld.lld-21 /usr/bin/ld

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
  echo "Aiden Grossman <aidengrossman@google.com>"
} > $BOT_DIR/info/admin

{
  echo "To reproduce locally, use a standard CMake invocation with the latest release clang as your system compiler and the options -DLLVM_ENABLE_WERROR=ON, -DCMAKE_BUILD_TYPE=Release, and -DLLVM_ENABLE_ASSERTIONS=OFF"
  echo "Example:"
  echo "cmake -GNinja"
  echo "  -DCMAKE_BUILD_TYPE=Release"
  echo "  -DLLVM_ENABLE_ASSERTIONS=OFF"
  echo "  -DLLVM_ENABLE_WERROR=ON"
  echo
  uname -a | head -n1
  date
  cmake --version | head -n1
  c++ --version | head -n1
  ld --version | head -n1
  lscpu
} > $BOT_DIR/info/host

sudo -u buildbot buildbot-worker start $BOT_DIR
