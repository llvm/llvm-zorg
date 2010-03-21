import plistlib
import urllib
import urllib2
import urllib2_file

def submitFiles(url, files, commit):
    for file in files:
        data = { 'file' : open(file),
                 'commit' : ("0","1")[not not commit] }

        response = urllib2.urlopen(url, data)
        the_page = response.read()

        print the_page
