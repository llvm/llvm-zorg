#!/bin/bash

set -e

export PATH=$PATH:~/.local/bin

BOT_DIR=/b
mkdir $BOT_DIR
buildbot-worker create-worker $BOT_DIR \
  lab.llvm.org:$BUILDBOT_PORT \
  $BUILDBOT_USERNAME \
  $BUILDBOT_PASSWORD

{
  echo "Mircea Trofin <mtrofin@google.com>"
  echo "Aiden Grossman <aidengrossman@google.com>"
} > $BOT_DIR/info/admin

{
  echo "See the instructions in https://github.com/google/ml-compiler-opt/blob/main/buildbot/BuildBotReproduceLocallyRel.md"
} > $BOT_DIR/info/host

buildbot-worker start $BOT_DIR

sleep 31536000000
