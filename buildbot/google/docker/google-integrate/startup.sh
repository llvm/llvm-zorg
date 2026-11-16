#!/bin/bash

set -e

export PATH=$PATH:~/.local/bin

BOT_DIR=/home/gha/worker
mkdir $BOT_DIR
buildbot-worker create-worker $BOT_DIR \
  lab.llvm.org:9994 \
  $BUILDBOT_USERNAME \
  $BUILDBOT_PASSWORD

{
  echo "Aiden Grossman <aidengrossman@google.com>"
} > $BOT_DIR/info/admin

{
  echo "32 core GCP Instance, 128GB of RAM"
  echo "-DLLVM_ENABLE_WERROR=ON with the latest clang release"
} > $BOT_DIR/info/host

buildbot-worker start $BOT_DIR

sleep 31536000000
