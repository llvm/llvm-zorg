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
  echo "Mircea Trofin <mtrofin@google.com>"
  echo "Aiden Grossman <aidengrossman@google.com>"
} > $BOT_DIR/info/admin

{
  echo "To reproduce locally, use a standard CMake invocation with -DLLVM_ENABLE_PROFCHECK=ON and -DLLVM_LIT_ARGS='--exclude-xfail'"
  echo "Example:"
  echo "cmake -GNinja"
  echo "  -DCMAKE_BUILD_TYPE=Release"
  echo "  -DLLVM_ENABLE_ASSERTIONS=ON"
  echo "  -DLLVM_LIT_ARGS='--exclude-xfail'"
  echo "  -DLLVM_ENABLE_PROFCHECK=ON"
  echo
} > $BOT_DIR/info/host

buildbot-worker start $BOT_DIR

sleep 31536000000
