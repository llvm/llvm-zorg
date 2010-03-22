"""
Utility for submitting files to a web server over HTTP.
"""

import plistlib
import urllib
import urllib2

def submitFiles(url, files, commit):
    for file in files:
        f = open(file, 'rb')
        values = { 'input_data' : f.read(),
                   'commit' : ("0","1")[not not commit] }
        f.close()

        data = urllib.urlencode(values)
        response = urllib2.urlopen(urllib2.Request(url, data))
        the_page = response.read()

        print the_page
