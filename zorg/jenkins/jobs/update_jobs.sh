#!/bin/sh
set -eu

. config

rm -rf build

# Create pipeline job files
mkdir -p build/jenkins/job
for i in jobs/*; do
    DESTFILE="build/jenkins/job/$(basename "$i")"
    PIPELINE_GIT_PATH="$(git ls-tree --full-name --name-only HEAD "${i}")"
    if [ -z "${PIPELINE_GIT_PATH}" ]; then
        echo 1>&2 "Could not determine git path of ${PIPELINE_FILE}. Is it checked in?"
        exit 1
    fi

    echo "GEN ${DESTFILE}"
    util/make_pipeline.py "${PIPELINE_GIT_URL}" "${PIPELINE_GIT_PATH}" description.txt > "$DESTFILE"
done

if test "${1-}" = "-d"; then
    echo "New jobs created in build"
    echo "Double check and rerun script without -d to apply to server."
else
    cd build/jenkins
    for file in $(find . -type f); do
        # Try to update, if it fails to create it
        echo "UPDATE ${file}"
        if ! ../../util/update.sh $file; then
            # Try to create it
            echo "CREATE ${file}"
            ../../util/create.sh $file || echo "... failed to create job"
        fi
    done
    cd -

    ./delete_old_Jobs.py
fi
