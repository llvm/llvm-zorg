#!/bin/bash
set -eu

MYDIR="$(dirname $0)"
. "${MYDIR}/../config"
. "${MYDIR}/../auth"

NAME="$1"

mkdir -p "$(dirname ${NAME})"
curl -s -XGET -u "${JENKINS_USER}:${JENKINS_TOKEN}" "${URL}/${NAME}/config.xml" -o "${NAME}" -f || echo "Error: Could not get ${NAME}"
