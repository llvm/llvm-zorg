#!/bin/bash
set -eux

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# load project configuration
source "${ROOT_DIR}/config.sh"

gcloud config set project ${GCP_PROJECT}
gcloud config set compute/zone ${GCP_ZONE}
gcloud auth configure-docker
gcloud container clusters get-credentials $GCP_CLUSTER
