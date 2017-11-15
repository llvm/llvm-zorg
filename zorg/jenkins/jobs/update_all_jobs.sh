#!/bin/sh
set -eu

. config

rm -rf build

# Create pipeline job files
mkdir -p build/jenkins/job
for i in jobs/*; do
    ./update_single_job.sh "$i"
done
./delete_old_Jobs.py
