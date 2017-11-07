#!/bin/bash
set -eux

MYDIR="$(dirname $0)"
. "${MYDIR}/../config"
. "${MYDIR}/../auth"

NAME="$1"

curl -f -s -u "${JENKINS_USER}:${JENKINS_TOKEN}" -XPOST "${URL}/job/${NAME}/doDelete" --data-binary "" -H "Content-Type:text/xml"
