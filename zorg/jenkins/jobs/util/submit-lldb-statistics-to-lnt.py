import datetime
import requests
import json
import pprint
import time
import os
import sys

# Note there are fewer git commits in the monorepo than there were svn revisions.
LLVM_REV=os.environ["GIT_DISTANCE"]
JOB_NAME=f'{os.environ["NODE_NAME"]}_{os.environ["JOB_NAME"]}'

if len(sys.argv) != 2:
    print("Usage: submit-lldb-statistics-to-lnt.py <path/to/stats/directory>")
    sys.exit(1)

LLDB_STATS_PATH=sys.argv[1]

_data = {}
for filename in os.listdir(LLDB_STATS_PATH):
    if not filename.endswith(".json"):
        continue

    json_path = os.path.join(LLDB_STATS_PATH, filename)
    with open(json_path, 'r') as f:
        # Test-case is the filename without the extension
        testcase_name = os.path.splitext(filename)[0]
        _data[testcase_name] = json.load(f)

if len(_data) == 0:
    print("Empty data...exiting.")
    sys.exit(1)

# For each test-case, create a separate LNT entry
# (so we can compare statistics per test-case over time).
for testcase_name, stats in _data.items():
    run_infos = {
        "end_time": datetime.datetime.now().isoformat(),
        "start_time": datetime.datetime.now().isoformat(),
        "llvm_project_revision":LLVM_REV,
    }

    to_send = {
        "format_name": 'json',
        "format_version": "2",
        "machine": {
            "name": "%s_%s-v1"%(testcase_name, JOB_NAME),
        },
        "run": run_infos,
        "tests": stats
    }
    to_send = {
        "merge": "replace",
        'format_name': 'json',
        'input_data': json.dumps(to_send),
        'commit': "1",  # compatibility with old servers.
    }


    pprint.pprint(to_send)
    try:
        requests.post("http://104.154.54.203/db_default/v4/nts/submitRun", data=to_send).raise_for_status()
    except:
        time.sleep(10)
        print("Sleeping because of error.")
        requests.post("http://104.154.54.203/db_default/v4/nts/submitRun", data=to_send).raise_for_status()
