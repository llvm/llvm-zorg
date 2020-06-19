#! /bin/bash
#===-- pod_login.sh ------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# This script will give get the console logs form the container. 
#  
# Arguments:
#     pod name fragement : 
#             part of the name of the pod to log in, eg. name of the 
#             deployment, if we have only one of them
#===----------------------------------------------------------------------===//

set -eu

WORKLOAD_NAME=$1
# get name of the pod
POD=$(kubectl get pod -o name | grep "$1")

# FIXME: exit if more than one pod is returned

# fetch the logd for the pod
kubectl logs "${POD}"
