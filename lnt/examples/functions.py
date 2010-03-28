#!/usr/bin/env python

"""
Simple example of a test generator which just produces data on some mathematical
functions, keyed off of the current time.
"""

import sys, time
import math, random

from lnt.testing import *

def main():
    from optparse import OptionParser
    parser = OptionParser("usage: %prog [options] [output]")
    opts,args = parser.parse_args()

    if len(args) == 0:
        output = '-'
    elif len(args) == 1:
        output, = args
    else:
        parser.error("invalid number of arguments")

    if output == '-':
        output = sys.stdout
    else:
        output = open(output,'w')

    offset = math.pi/5
    delay = 120.

    machine = Machine('Mr. Sin Wave', info = { 'delay' : delay })

    start = time.time()

    run = Run(start, start, info = { 't' : start,
                                     'tag' : 'simple' })
    tests = [TestSamples('simple.%s' % name,
                         [fn(start*2*math.pi / delay  + j * offset)],
                         info = { 'offset' : j })
             for j in range(5)
             for name,fn in (('sin',math.sin),
                             ('cos',math.cos),
                             ('random',lambda x: random.random()))]

    report = Report(machine, run, tests)

    print >>output, report.render()

    if output is not sys.stderr:
        output.close()

if __name__ == '__main__':
    main()
