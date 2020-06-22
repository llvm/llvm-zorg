#! /bin/bash
#===-- pod_login.sh ------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# This script will give you a terminal in on of the pods. This is useful
# to debug problems in a running container. This is much faster than going
# through the Google Cloud UI.
#  
# Arguments:
#     pod name fragement : 
#             part of the name of the pod to log in, eg. name of the 
#             deployment, if we have only one of them
#     command (optional):
#             Command to be run in the container. Default: /bin/bash
#===----------------------------------------------------------------------===//

set -eu

WORKLOAD_NAME=$1
CMD="/bin/bash"
if [ "$#" -eq 2 ];
then
    CMD="$2"
fi

# get name of the pod
POD=$(kubectl get pod -o name | grep "$1")

# FIXME: exit if more than one pod is returned

# login to the pod
kubectl exec --stdin --tty "${POD}" -- "${CMD}"
