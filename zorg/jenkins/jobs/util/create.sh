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

# This is a bit ugly as it only works reliably on the toplevel jenkins URL.
# (i.e. we cannot say job/createItem?name=Bla  or view/createItem?name=Blup,
#  so instead just take the filename as name and create it at the toplevel)
BASENAME="$(basename ${NAME})"
curl -f -s -u "${JENKINS_USER}:${JENKINS_TOKEN}" -XPOST "${URL}/createItem?name=${BASENAME}" --data-binary "@${NAME}" -H "Content-Type:text/xml"
