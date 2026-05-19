set -ex

LLVM_MAJOR_VERSION=22

until (
  set -e
  # Delete this repository as it does not exist for Ubuntu 24.04 and apt-get
  # will fail in every invocation otherwise.
  sudo rm -rf /etc/apt/sources.list.d/scalibr-apt.list
  apt-get update
  apt-get -o DPkg::Lock::Timeout=-1 install -y python3 python3-pip cmake ninja-build git ccache lsb-release wget software-properties-common gnupg
  pip3 install --break-system-packages buildbot-worker==3.11.7

  rm -rf /tmp/llvm.sh
  wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh
  chmod +x /tmp/llvm.sh
  /tmp/llvm.sh ${LLVM_MAJOR_VERSION}
); do
  echo "A command during package installation failed. Retrying."
done

ln -sf /usr/bin/clang-${LLVM_MAJOR_VERSION} /usr/bin/cc
ln -sf /usr/bin/clang++-${LLVM_MAJOR_VERSION} /usr/bin/c++
ln -sf /usr/bin/ld.lld-${LLVM_MAJOR_VERSION} /usr/bin/ld

rm -rf /b
BOT_DIR=/b
SERVER_PORT=9994
WORKER_NAME="$(hostname -s)"
WORKER_PASSWORD="$(gsutil cat gs://sanitizer-buildbot/$(hostname -s)-password)"

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
  uname -a
  echo "32 core GCP instance"
  grep MemTotal /proc/meminfo
  echo "-DLLVM_ENABLE_PROFCHECK=ON passed to CMake"
} > $BOT_DIR/info/host

sudo -u buildbot buildbot-worker start $BOT_DIR
