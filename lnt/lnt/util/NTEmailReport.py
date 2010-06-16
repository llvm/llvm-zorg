#!/usr/bin/python

"""
Command line tool for sending an LNT email report.
"""

# FIXME: Roll into lnttool or just kill?

import os
import smtplib
import sys

import StringIO
from lnt import viewer
from lnt.db import runinfo
from lnt.db import perfdbsummary
from lnt.viewer import Util
from lnt.viewer import PerfDB
from lnt.viewer.NTUtil import *

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

def emailReport(db, run, baseurl, host, from_, to, was_added=True,
                will_commit=True):
    import email.mime.text

    subject, report = getReport(db, run, baseurl, was_added, will_commit)

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

def getSimpleReport(db, run, baseurl, was_added, will_commit):
    tag = run.info['tag'].value

    # Get the run summary.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)

    # Load the test suite summary.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)

    # Get the run pass/fail information.
    sri = runinfo.SimpleRunInfo(db, ts_summary)

    # Gather the runs to use for statistical data.
    num_comparison_runs = 5
    cur_id = run.id
    comparison_window = []
    for i in range(num_comparison_runs):
        cur_id = run_summary.get_previous_run_on_machine(cur_id)
        if not cur_id:
            break
        comparison_window.append(cur_id)

    # Find previous run to compare to.
    id = run_summary.get_previous_run_on_machine(run.id)
    if id is not None:
        compare_to = db.getRun(id)

    # Gather the changes to report, mapped by parameter set.
    new_failures = Util.multidict()
    new_passes = Util.multidict()
    perf_regressions = Util.multidict()
    perf_improvements = Util.multidict()
    added_tests = Util.multidict()
    removed_tests = Util.multidict()
    existing_failures = Util.multidict()
    for name in ts_summary.test_names:
        for pset in ts_summary.parameter_sets:
            cr = sri.get_run_comparison_result(run, compare_to, name, pset,
                                               comparison_window)
            test_status = cr.get_test_status()
            perf_status = cr.get_value_status()
            if test_status == runinfo.REGRESSED:
                new_failures[pset] = (name, cr)
            elif test_status == runinfo.IMPROVED:
                new_passes[pset] = (name, cr)
            elif cr.current is None:
                removed_tests[pset] = (name, cr)
            elif cr.previous is None:
                added_tests[pset] = (name, cr)
            elif test_status == runinfo.UNCHANGED_FAIL:
                existing_failures[pset] = (name, cr)
            elif perf_status == runinfo.REGRESSED:
                perf_regressions[pset] = (name, cr)
            elif perf_status == runinfo.IMPROVED:
                perf_improvements[pset] = (name, cr)

    # Generate the report.
    report = StringIO.StringIO()

    machine = run.machine
    subject = """%s nightly tester results""" % machine.name

    # Generate the report header.
    if baseurl[-1] == '/':
        baseurl = baseurl[:-1]
    print >>report, """%s/%d/""" % (baseurl, run.id)
    print >>report, """Nickname: %s:%d""" % (machine.name, machine.number)
    if 'name' in machine.info:
        print >>report, """Name: %s""" % (machine.info['name'].value,)
    print >>report, """Comparing:"""
    print >>report, """  Run: %d, Order: %s, Start Time: %s, End Time: %s""" % (
        run.id, run.info['run_order'].value, run.start_time, run.end_time)
    if compare_to:
        print >>report, ("""   To: %d, Order: %s, """
                         """Start Time: %s, End Time: %s""") % (
            compare_to.id, compare_to.info['run_order'].value,
            compare_to.start_time, compare_to.end_time)
        if run.machine != compare_to.machine:
            print >>report, """*** WARNING ***:""",
            print >>report, """comparison is against a different machine""",
            print >>report, """(%s:%d)""" % (compare_to.machine.name,
                                             compare_to.machine.number)
    else:
        print >>report, """    To: (none)"""
    print >>report

    if existing_failures:
        print >>report, 'Total Existing Failures:',  sum(
            map(len, existing_failures.values()))
        print >>report

    # Generate the summary of the changes.
    items_info = (('New Failures', new_failures, False),
                  ('New Passes', new_passes, False),
                  ('Performance Regressions', perf_regressions, True),
                  ('Performance Improvements', perf_improvements, True),
                  ('Removed Tests', removed_tests, False),
                  ('Added Tests', added_tests, False))
    total_changes = sum([sum(map(len, items.values()))
                         for _,items,_ in items_info])
    if total_changes:
        print >>report, """==============="""
        print >>report, """Changes Summary"""
        print >>report, """==============="""
        print >>report
        for name,items,_ in items_info:
            if items:
                print >>report, '%s: %d' % (name, sum(map(len, items.values())))
        print >>report

        print >>report, """=============="""
        print >>report, """Changes Detail"""
        print >>report, """=============="""
        for name,items,show_perf in items_info:
            if not items:
                continue

            print >>report
            print >>report, name
            print >>report, '-' * len(name)
            for pset,tests in items.items():
                if show_perf:
                    tests.sort(key = lambda (_,cr): -abs(cr.pct_delta))

                if pset or len(items) > 1:
                    print >>report
                    print >>report, "Parameter Set:", pset
                for name,cr in tests:
                    if show_perf:
                        print >>report, ('  %s: %.2f%%'
                                         '(%.4f => %.4f, std. dev.: %.4f)') % (
                            name, 100. * cr.pct_delta,
                            cr.previous, cr.current, cr.stddev)
                    else:
                        print >>report, '  %s' % (name,)

    # Generate a list of the existing failures.
    if False and existing_failures:
        print >>report
        print >>report, """================="""
        print >>report, """Existing Failures"""
        print >>report, """================="""
        for pset,tests in existing_failures.items():
            if pset or len(existing_failures) > 1:
                print >>report
                print >>report, "Parameter Set:", pset
            for name,cr in tests:
                print >>report, '  %s' % (name,)

    print 'Subject:',subject
    print report.getvalue()
    raise SystemExit,0
    return subject, report.getvalue()

def getReport(db, run, baseurl, was_added, will_commit):
    report = StringIO.StringIO()

    # Use a simple report unless the tag indicates this is an old style nightly
    # test run.
    if 'tag' in run.info and run.info['tag'].value != 'nightlytest':
        return getSimpleReport(db, run, baseurl, was_added, will_commit)

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

    if will_commit:
        if not was_added:
            print >>report, ("*** NOTE ***: This was a duplicate submission, "
                             "and did not modify the database.\n")
    else:
        if was_added:
            print >>report, ("*** NOTE ***: This is a test submission, "
                             "it will not be committed to the database.\n")
        else:
            print >>report, ("*** NOTE ***: This is a test submission, "
                             "and was a duplicate of an existing run.\n")

    if baseurl[-1] == '/':
        baseurl = baseurl[:-1]
    print >>report, """%s/%d/""" % (baseurl, run.id)
    print >>report, """Nickname: %s:%d""" % (machine.name, machine.number)
    if 'name' in machine.info:
        print >>report, """Name: %s""" % (machine.info['name'].value,)
    print >>report
    print >>report, """Run: %d, Start Time: %s, End Time: %s""" % (
        run.id, run.start_time, run.end_time)
    if compareTo:
        print >>report, """Comparing To: %d, Start Time: %s, End Time: %s""" % (
            compareTo.id, compareTo.start_time, compareTo.end_time)
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
            print >>report, """ %s: %.2f%% (%.4f => %.4f)""" % (
                name, delta*100, prevValue, curValue)

    # FIXME: Where is the old mailer getting the arch from?
    subject = """%s nightly tester results""" % machine.name
    return subject,report.getvalue()

if __name__ == '__main__':
    main()
