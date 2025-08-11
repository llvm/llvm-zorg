#!/bin/bash

# This script performs all the necessary setup and then starts the buildbot
# worker.

mkdir /worker
buildbot-worker create-worker /worker \
  lab.llvm.org:9994 \
  $BUILDBOT_USERNAME \
  $BUILDBOT_PASSWORD

echo "Google LLVM Premerge Infra Rotation <llvm-presubmit-infra@google.com>" \
  > /worker/info/admin

{
  echo "Premerge container (https://github.com/llvm/llvm-project/pkgs/container/ci-ubuntu-24.04)"
  echo "GCP n2/n2d standard instances."
} > /worker/info/host

buildbot-worker start /worker

sleep 31536000000
