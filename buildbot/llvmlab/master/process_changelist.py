#!/usr/bin/env python

import sys, getopt, subprocess, json, time, os

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "h", ["help"])
        except getopt.error, msg:
             raise Usage(msg)
        category = args[0]
        filename = args[1]
        changelist = []
        if not os.path.isfile(filename):
            return
        for line in open(filename).readlines():
            change = json.loads(line)
            if not change in changelist:
                print "rejected duplicate: %s" % change['revision']
                changelist.append(change)
        while len(changelist) > 0:
            changelist = sorted(changelist, key=lambda k: k['timestamp'])
            change = changelist.pop(0)
            command = ['./sendchange.py', category, json.dumps(change)]
            status = subprocess.call(command)
            if status:
                print 'An error occurred will retry in sixty seconds'
                print change
                changelist.append(change)
                time.sleep(60)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

def wait(res):
    time.sleep(15)

if __name__ == "__main__":
    sys.exit(main())