#!/bin/sh
set -eu

. config

JOB="$1"

mkdir -p build/jenkins/job
DESTJOB="job/$(basename "${JOB}")"
DESTFILE="build/jenkins/${DESTJOB}"
PIPELINE_GIT_PATH="$(git ls-tree --full-name --name-only HEAD "${JOB}")"
if [ -z "${PIPELINE_GIT_PATH}" ]; then
    echo 1>&2 "Could not determine git path of ${PIPELINE_FILE}. Is it checked in?"
    exit 1
fi

echo "GEN ${DESTFILE}"
util/make_pipeline.py "${PIPELINE_GIT_URL}" "${PIPELINE_GIT_PATH}" description.txt > "$DESTFILE"

echo "UPDATE ${DESTJOB}"
cd build/jenkins
if ! ../../util/update.sh "${DESTJOB}"; then
    # Try to create it
    echo "CREATE ${DESTJOB}"
    ../../util/create.sh "${DESTJOB}" || echo "... failed to create job"
fi
