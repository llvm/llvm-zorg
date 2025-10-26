#!/usr/bin/env python
import glob
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

new_jobs = set()
for g in glob.glob('build/jenkins/job/*'):
    new_jobs.add(os.path.basename(g))

if len(new_jobs) == 0:
    print("No new jobs?!?")
    sys.exit(1)

query = subprocess.check_output(['util/query.sh', 'api/xml?tree=jobs[name,description]'], )

existing_jobs = set()
tree = ET.fromstring(query)
for job in tree.findall('.//job'):
    name = job.find('name').text
    description_e = job.find('description')
    if description_e is None:
        continue
    description = description_e.text
    if description is None:
        continue
    if '$$job generated from ' in description:
        existing_jobs.add(name.strip())
if len(existing_jobs) == 0:
    print("No existing jobs?!?")
    sys.exit(1)

# We should have already uploaded all the new jobs
missing = new_jobs - existing_jobs
if len(missing) > 0:
    print("Missing jobs?!?")
    sys.exit(1)

to_delete = existing_jobs - new_jobs
if len(to_delete) > 0:
    print("")
    print("")
    print("Will delete the following jobs:")
    for jobname in to_delete:
        print("    %s" % jobname)
    print("You have 5 seconds to abort")
    time.sleep(5)
    for jobname in to_delete:
        subprocess.check_call(['util/delete_job.sh', jobname])
