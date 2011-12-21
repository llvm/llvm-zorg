"""
Utility for submitting files to a web server over HTTP.
"""

import plistlib
import sys
import urllib
import urllib2

from lnt.util import json
from lnt.util import ImportData

# FIXME: I used to maintain this file in such a way that it could be used
# separate from LNT to do submission. This could be useful for adapting an older
# system to report to LNT, for example. It might be nice to factor the
# simplified submit code into a separate utility.

def submitFile(url, file, commit, verbose):
    values = { 'input_data' : file.read(),
               'commit' : ("0","1")[not not commit] }

    data = urllib.urlencode(values)
    response = urllib2.urlopen(urllib2.Request(url, data))
    result_data = response.read()

    # The result is expected to be a JSON object.
    try:
        result = json.loads(result_data)
    except:
        import traceback
        print "Unable to load result, not a valid JSON object."
        print
        print "Traceback:"
        traceback.print_exc()
        print
        print "Result:"
        print result
        return

    # Print the test report.
    ImportData.print_report_result(result, sys.stdout, sys.stderr, verbose)

def submitFiles(url, files, commit, verbose):
    for file in files:
        f = open(file, 'rb')
        submitFile(url, f, commit, verbose)
        f.close()
