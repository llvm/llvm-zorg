#!/usr/bin/python

"""
Command line tool for sending an LNT email report.
"""

# FIXME: Roll into lnttool or just kill?

import os
import smtplib
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),'../'))

import StringIO
import viewer
from viewer import PerfDB
from viewer.NTUtil import *

def main():
    global opts
    from optparse import OptionParser
    parser = OptionParser("usage: %prog database run-id baseurl sendmail-host from to")
    opts,args = parser.parse_args()

    if len(args) != 6:
        parser.error("incorrect number of argments")

    dbpath,runID,baseurl,host,from_,to = args

    db = PerfDB.PerfDB(dbpath)
    run = db.getRun(int(runID))

    emailReport(db, run, baseurl, host, from_, to)

def emailReport(db, run, baseurl, host, from_, to):
    import email.mime.text

    subject, report = getReport(db, run, baseurl)

    msg = email.mime.text.MIMEText(report)
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to

    s = smtplib.SMTP(host)
    s.sendmail(from_, [to], msg.as_string())
    s.quit()

def findPreceedingRun(query, run):
    """findPreceedingRun - Find the most recent run in query which
    preceeds run."""
    best = None
    for r in query:
        # Restrict to nightlytest runs.
        if 'tag' in r.info and r.info['tag'].value != 'nightlytest':
            continue

        # Select most recent run prior to the one we are reporting on.
        if (r.start_time < run.start_time and
            (best is None or r.start_time > best.start_time)):
            best = r
    return best

def getReport(db, run, baseurl):
    report = StringIO.StringIO()

    machine = run.machine
    compareTo = None

    # Find comparison run.
    # FIXME: Share this code with similar stuff in the viewer.
    # FIXME: Scalability.
    compareCrossesMachine = False
    compareTo = findPreceedingRun(db.runs(machine=machine), run)

    # If we didn't find a comparison run against this machine, look
    # for a comparison run against the same machine name, and warn the
    # user we are crosses machines.
    if compareTo is None:
        compareCrossesMachine = True
        q = db.session.query(PerfDB.Run).join(PerfDB.Machine)
        q = q.filter_by(name=machine.name)
        compareTo = findPreceedingRun(q, run)

    summary = RunSummary()
    summary.addRun(db, run)
    if compareTo:
        summary.addRun(db, compareTo)

    def getTestValue(run, testname, keyname):
        fullname = 'nightlytest.' + testname + '.' + keyname
        t = summary.testMap.get(str(fullname))
        if t is None:
            return None
        samples = summary.getRunSamples(run).get(t.id)
        if not samples:
            return None
        return samples[0]
    def getTestSuccess(run, testname, keyname):
        res = getTestValue(run, testname, keyname + '.success')
        if res is None:
            return res
        return not not res

    newPasses = Util.multidict()
    newFailures = Util.multidict()
    addedTests = Util.multidict()
    removedTests = Util.multidict()
    allTests = set()
    allFailures = set()
    allFailuresByKey = Util.multidict()
    for keyname,title in kTSKeys.items():
        for testname in summary.testNames:
            curResult = getTestSuccess(run, testname, keyname)
            prevResult = getTestSuccess(compareTo, testname, keyname)

            if curResult is not None:
                allTests.add((testname,keyname))
                if curResult is False:
                    allFailures.add((testname,keyname))
                    allFailuresByKey[title] = testname

            # Count as new pass if it passed, and previous result was failure.
            if curResult and prevResult == False:
                newPasses[testname] = title

            # Count as new failure if it failed, and previous result was not
            # failure.
            if curResult == False and prevResult != False:
                newFailures[testname] = title

            if curResult is not None and prevResult is None:
                addedTests[testname] = title
            if curResult is None and prevResult is not None:
                removedTests[testname] = title

    changes = Util.multidict()
    for i,(name,key) in enumerate(kComparisonKinds):
        if not key:
            # FIXME: File Size
            continue

        for testname in summary.testNames:
            curValue = getTestValue(run, testname, key)
            prevValue = getTestValue(compareTo, testname, key)

            # Skip missing tests.
            if curValue is None or prevValue is None:
                continue

            pct = Util.safediv(curValue, prevValue)
            if pct is None:
                continue
            pctDelta = pct - 1.
            if abs(pctDelta) < .05:
                continue
            if min(prevValue, curValue) <= .2:
                continue

            changes[name] = (testname, curValue, prevValue, pctDelta)

    if baseurl[-1] == '/':
        baseurl = baseurl[:-1]
    print >>report, """%s/%d/""" % (baseurl, run.id)
    print >>report, """Name: %s""" % (machine.info['name'].value,)
    print >>report, """Nickname: %s:%d""" % (machine.name, machine.number)
    print >>report
    print >>report, """Run: %d, Start Time: %s, End Time: %s""" % (run.id, run.start_time, run.end_time)
    if compareTo:
        print >>report, """Comparing To: %d, Start Time: %s, End Time: %s""" % (compareTo.id, compareTo.start_time, compareTo.end_time)
        if compareCrossesMachine:
            print >>report, """*** WARNING ***:""",
            print >>report, """comparison is against a different machine""",
            print >>report, """(%s:%d)""" % (compareTo.machine.name,
                                             compareTo.machine.number)
    else:
        print >>report, """Comparing To: (none)"""
    print >>report

    print >>report, """--- Changes Summary ---"""
    for title,elts in (('New Test Passes', newPasses),
                       ('New Test Failures', newFailures),
                       ('Added Tests', addedTests),
                       ('Removed Tests', removedTests)):
        print >>report, """%s: %d""" % (title,
                                        sum([len(values)
                                             for key,values in elts.items()]))
    numSignificantChanges = sum([len(changelist)
                                 for name,changelist in changes.items()])
    print >>report, """Significant Changes: %d""" % (numSignificantChanges,)
    print >>report
    print >>report, """--- Tests Summary ---"""
    print >>report, """Total Tests: %d""" % (len(allTests),)
    print >>report, """Total Test Failures: %d""" % (len(allFailures),)
    print >>report
    print >>report, """Total Test Failures By Type:"""
    for name,items in Util.sorted(allFailuresByKey.items()):
        print >>report, """  %s: %d""" % (name, len(set(items)))

    print >>report
    print >>report, """--- Changes Detail ---"""
    for title,elts in (('New Test Passes', newPasses),
                       ('New Test Failures', newFailures),
                       ('Added Tests', addedTests),
                       ('Removed Tests', removedTests)):
        print >>report, """%s:""" % (title,)
        print >>report, "".join("%s [%s]\n" % (key, ", ".join(values))
                                for key,values in Util.sorted(elts.items()))
    print >>report, """Significant Changes in Test Results:"""
    for name,changelist in changes.items():
        print >>report, """%s:""" % name
        for name,curValue,prevValue,delta in Util.sorted(changelist):
            print >>report, """ %s: %.2f%% (%.4f => %.4f)""" % (name, delta*100, prevValue, curValue)

    # FIXME: Where is the old mailer getting the arch from?
    subject = """%s nightly tester results""" % machine.name
    return subject,report.getvalue()

if __name__ == '__main__':
    main()
