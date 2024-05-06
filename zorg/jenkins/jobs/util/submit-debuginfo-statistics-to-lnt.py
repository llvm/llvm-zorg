import datetime
import requests
import json
import pprint
import time
import os

# Note there are fewer git commits in the monorepo than there were svn revisions.
LLVM_REV=os.environ["GIT_DISTANCE"]
JOB_NAME=os.environ["JOB_NAME"]

with open("stats.json", 'r') as f:
    _data = json.load(f)

# Create ratio data.
if not ((_data.get('version')) and _data.get('sum_all_variables(#bytes in parent scope)') and _data.get('#source variables')):
    exit(1)
version = int(_data['version'])
_data['percent regions covered'] = 100.0 * (
        float(_data['sum_all_variables(#bytes in parent scope covered by DW_AT_location)']) /
        _data['sum_all_variables(#bytes in parent scope)'])
_data['percent variables with location'] = 100.0 * (
        float(_data['#source variables with location']) / _data['#source variables'])

run_infos = {
    "end_time": datetime.datetime.now().isoformat(),
    "start_time": datetime.datetime.now().isoformat(),
    "llvm_project_revision":LLVM_REV,
}
to_send = {
    "format_name": 'json',
    "format_version": "2",
    "machine": {
        "name": "%s-v%d"%(JOB_NAME, version),
    },
    "run": run_infos,
    "tests": [{"name": x[0], "score": [x[1]]} for x in _data.items() if isinstance(x[1], int) or isinstance(x[1], float)]
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