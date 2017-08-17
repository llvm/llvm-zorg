#!/usr/bin/python
"""
Kill all the Zombie Gunicon processes.

"""
import re
import subprocess

out = subprocess.check_output(["ps", "auxxxf"])

stranded = re.compile(r"^lnt\s+(?P<pid>\d+).*00\sgunicorn:\swork")
pids = []
for line in out.split('\n'):
    m = stranded.match(line)
    if m:
        pid = m.groupdict()['pid']
        pids.append(pid)
    else:
        print ">", line

if not pids:
    print "No PIDs to kill."

for pid in pids:
    print subprocess.check_output(["kill", "-9", "{}".format(pid)])
