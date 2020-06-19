#!/bin/bash
#===-- build_run.sh ------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# This script will deploy a docker image to the registry.
# Arguments:
#     <path to Dockerfile>
#     <path containing secrets>
#     optional: <command to be executed in the container>
#===----------------------------------------------------------------------===//

set -eux

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
IMAGE_NAME="${1%/}"
SECRET_STORAGE="$2"
CMD=
if [ "$#" -eq 3 ];
then
    CMD="$3"
fi

cd "${DIR}/${IMAGE_NAME}"

docker build -t "${IMAGE_NAME}:latest" .
docker run -it -v "${SECRET_STORAGE}":/secrets "${IMAGE_NAME}" ${CMD}
