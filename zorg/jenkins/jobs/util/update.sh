#!/bin/bash
set -eu

MYDIR="$(dirname $0)"
. "${MYDIR}/../config"
. "${MYDIR}/../auth"

NAME="$1"
if ! test -r "$NAME"; then
	echo 1>&2 "Input file $NAME does not exist"
	exit 1
fi

curl -f -u "${JENKINS_USER}:${JENKINS_TOKEN}" -XPOST "${URL}/${NAME}/config.xml" --data-binary "@${NAME}" -H "Content-Type:text/xml"
