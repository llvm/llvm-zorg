#!/usr/bin/env bash

set -x
set -e
set -u

HERE="$(cd $(dirname $0) && pwd)"
. ${HERE}/buildbot_functions.sh

buildbot_update

if git -c $LLVM merge-base HEAD "${1}" | grep "${1}"; then
  build_failure
fi
