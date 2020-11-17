#!/bin/bash
#===-- run.sh -------------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# This script will start the buildbot worker
# 
#===----------------------------------------------------------------------===//

set -eu

# Read the worker password from a mounted file.
WORKER_PASSWORD=$(cat /vol/secrets/token)

# Set up buildbot host and maintainer info.
mkdir -p "${WORKER_NAME}/info/" 
echo "Christian Kuehnel <kuhnel@google.com>" > "${WORKER_NAME}/info/admin"

# generate the host information of this worker
( 
  uname -a ; \
  cat /proc/cpuinfo | grep "model name" | head -n1 | cut -d " " -f 3- ;\
  echo "number of cores: $(nproc)" ;\
  cat /proc/meminfo | grep MemTo ;\
  lsb_release -d | cut -f 2- ; \
  clang --version | head -n1 ; \
  ld.lld-11 --version ; \
  cmake --version | head -n1 ; \
) > ${WORKER_NAME}/info/host 

echo "Host information:"
cat ${WORKER_NAME}/info/host

# create the folder structure
echo "creating worker ${WORKER_NAME} at port ${BUILDBOT_PORT}..."
buildbot-worker create-worker --keepalive=200 "${WORKER_NAME}" \
  lab.llvm.org:${BUILDBOT_PORT} "${WORKER_NAME}" "${WORKER_PASSWORD}"

# start the daemon, this command return immetiately
echo "starting worker..."
buildbot-worker start "${WORKER_NAME}"

# To keep the container running and produce log outputs: dump the worker
# log to stdout
echo "Following worker log..."
tail -f ${WORKER_NAME}/twistd.log
