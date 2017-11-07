#!/bin/bash
set -eu

MYDIR="$(dirname $0)"
. "${MYDIR}/../config"
. "${MYDIR}/../auth"

QUERY="$1"

curl -g -XGET -u "${JENKINS_USER}:${JENKINS_TOKEN}" "${URL}/${QUERY}" -f
