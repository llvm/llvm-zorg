"""
Utility for submitting files to a web server over HTTP.
"""

import plistlib
import urllib
import urllib2

def submitFile(url, file, commit):
    values = { 'input_data' : file.read(),
               'commit' : ("0","1")[not not commit] }

    data = urllib.urlencode(values)
    response = urllib2.urlopen(urllib2.Request(url, data))
    the_page = response.read()

    print the_page

def submitFiles(url, files, commit):
    for file in files:
        f = open(file, 'rb')
        submitFile(url, f, commit)
        f.close()
