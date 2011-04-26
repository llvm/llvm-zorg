#!/usr/bin/python

"""
Command line tool for sending an LNT email report.
"""

# FIXME: Roll into lnttool or just kill?

import os
import smtplib
import sys
import urllib

import StringIO
from lnt import viewer
from lnt.db import runinfo
from lnt.db import perfdbsummary
from lnt.viewer import GraphUtil
from lnt.viewer import Util
from lnt.db import perfdb
from lnt.viewer.NTUtil import *

from lnt.db.perfdb import Run, Sample

def main():
    global opts
    from optparse import OptionParser
    parser = OptionParser("usage: %prog database run-id baseurl sendmail-host from to")
    opts,args = parser.parse_args()

    if len(args) != 6:
        parser.error("incorrect number of argments")

    dbpath,runID,baseurl,host,from_,to = args

    db = lnt.db.perfdb.PerfDB(dbpath)
    run = db.getRun(int(runID))

    emailReport(db, run, baseurl, host, from_, to)

def emailReport(result, db, run, baseurl, email_config, to, was_added=True,
                will_commit=True):
    import email.mime.multipart
    import email.mime.text

    subject, report, html_report = getReport(result, db, run, baseurl,
                                             was_added, will_commit)

    # Ignore if no to address was given, we do things this way because of the
    # awkward way we collect result information as part of generating the email
    # report.
    if email_config is None or to is None:
        return

    # Generate a plain text message if we have no html report.
    if not html_report:
        msg = email.mime.text.MIMEText(report)
        msg['Subject'] = subject
        msg['From'] = email_config.from_address
        msg['To'] = to
    else:
        msg = email.mime.multipart.MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email_config.from_address
        msg['To'] = to

        # Attach parts into message container, according to RFC 2046, the last
        # part of a multipart message, in this case the HTML message, is best
        # and preferred.
        msg.attach(email.mime.text.MIMEText(report, 'plain'))
        msg.attach(email.mime.text.MIMEText(html_report, 'html'))

    s = smtplib.SMTP(email_config.host)
    s.sendmail(email_config.from_address, [to], msg.as_string())
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

def getSimpleReport(result, db, run, baseurl, was_added, will_commit,
                    only_html_body = False, show_graphs = False,
                    num_comparison_runs = 10):
    machine = run.machine
    tag = run.info['tag'].value

    # Get the run summary.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)

    # Ignore run's which don't appear in the summary, for whatever reason.
    if not run_summary.contains_run(run.id):
        return ("No report for run", "No report for run", None)

    # Load the test suite summary.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)

    # Get the run pass/fail information.
    sri = runinfo.SimpleRunInfo(db, ts_summary)

    # Gather the runs to use for statistical data.
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
    else:
        # FIXME: Look for run across machine.
        compare_to = None

    # Get the test status style used in each run.
    run_status_kind = run_summary.get_run_status_kind(db, run.id)
    if compare_to:
        compare_to_status_kind = run_summary.get_run_status_kind(
            db, compare_to.id)
    else:
        compare_to_status_kind = None

    # Get the list of tests we are interested in.
    interesting_runs = [run.id]
    if compare_to:
        interesting_runs.append(compare_to.id)
    test_names = ts_summary.get_test_names_in_runs(db, interesting_runs)

    # Gather the changes to report, mapped by parameter set.
    new_failures = Util.multidict()
    new_passes = Util.multidict()
    perf_regressions = Util.multidict()
    perf_improvements = Util.multidict()
    added_tests = Util.multidict()
    removed_tests = Util.multidict()
    existing_failures = Util.multidict()
    unchanged_tests = Util.multidict()
    num_total_tests = len(test_names) * len(ts_summary.parameter_sets)
    for name in test_names:
        for pset in ts_summary.parameter_sets:
            cr = sri.get_run_comparison_result(
                run, run_status_kind, compare_to, compare_to_status_kind,
                name, pset, comparison_window)
            test_status = cr.get_test_status()
            perf_status = cr.get_value_status()
            if test_status == runinfo.REGRESSED:
                new_failures[pset] = (name, cr)
            elif test_status == runinfo.IMPROVED:
                new_passes[pset] = (name, cr)
            elif cr.current is None and cr.previous is not None:
                removed_tests[pset] = (name, cr)
            elif cr.current is not None and cr.previous is None:
                added_tests[pset] = (name, cr)
            elif test_status == runinfo.UNCHANGED_FAIL:
                existing_failures[pset] = (name, cr)
            elif perf_status == runinfo.REGRESSED:
                perf_regressions[pset] = (name, cr)
            elif perf_status == runinfo.IMPROVED:
                perf_improvements[pset] = (name, cr)
            else:
                unchanged_tests[pset] = (name, cr)

    # Collect the simplified results, if desired, for sending back to clients.
    if result is not None:
        test_results = result['test_results'] = []
        for pset in ts_summary.parameter_sets:
            pset_results = []
            for name in test_names:
                cr = sri.get_run_comparison_result(
                    run, run_status_kind, compare_to, compare_to_status_kind,
                    name, pset, comparison_window)
                test_status = cr.get_test_status()
                perf_status = cr.get_value_status()
                # FIXME: Include additional information about performance
                # changes.
                pset_results.append( (name, test_status, perf_status) )
            test_results.append({ 'pset' : pset, 'results' : pset_results })

    # Generate the report.
    report = StringIO.StringIO()
    html_report = StringIO.StringIO()

    machine = run.machine
    subject = """%s nightly tester results""" % machine.name


    # Generate the report header.
    if baseurl[-1] == '/':
        baseurl = baseurl[:-1]

    report_url = """%s/simple/%s/%d/""" % (baseurl, tag, run.id)
    print >>report, report_url
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
        print >>report, """   To: (none)"""
    print >>report

    # Generate the HTML report header.
    print >>html_report, """\
<h1>%s</h1>
<table>""" % subject
    print >>html_report, """\
<tr><td>URL</td><td><a href="%s">%s</a></td></tr>""" % (report_url, report_url)
    print >>html_report, "<tr><td>Nickname</td><td>%s:%d</td></tr>" % (
        machine.name, machine.number)
    if 'name' in machine.info:
        print >>html_report, """<tr><td>Name</td<td>%s</td></tr>""" % (
            machine.info['name'].value,)
    print >>html_report, """</table>"""
    print >>html_report, """\
<p>
<table>
  <tr>
    <th>Run</th>
    <th>ID</th>
    <th>Order</th>
    <th>Start Time</th>
    <th>End Time</th>
  </tr>"""
    print >>html_report, """\
<tr><td>Current</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>""" % (
        run.id, run.info['run_order'].value, run.start_time, run.end_time)
    if compare_to:
        print >>html_report, """\
<tr><td>Previous</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>""" % (
            compare_to.id, compare_to.info['run_order'].value,
            compare_to.start_time, compare_to.end_time)
    else:
        print >>html_report, """<tr><td colspan=4>No Previous Run</td></tr>"""
    print >>html_report, """</table>"""
    if compare_to and run.machine != compare_to.machine:
        print >>html_report, """<p><b>*** WARNING ***:""",
        print >>html_report, """comparison is against a different machine""",
        print >>html_report, """(%s:%d)</b></p>""" % (compare_to.machine.name,
                                                      compare_to.machine.number)

    # Generate the summary of the changes.
    items_info = (('New Failures', new_failures, False),
                  ('New Passes', new_passes, False),
                  ('Performance Regressions', perf_regressions, True),
                  ('Performance Improvements', perf_improvements, True),
                  ('Removed Tests', removed_tests, False),
                  ('Added Tests', added_tests, False),
                  ('Existing Failures', existing_failures, False),
                  ('Unchanged Tests', unchanged_tests, False))
    total_changes = sum([sum(map(len, items.values()))
                         for name,items,_ in items_info
                         if name != 'Unchanged Tests'])
    graphs = []
    print >>report, """==============="""
    print >>report, """Tests Summary"""
    print >>report, """==============="""
    print >>report
    print >>html_report, """
<hr>
<h3>Tests Summary</h3>
<table>
<thead><tr><th>Status Group</th><th align="right">#</th></tr></thead>
"""
    for name,items,_ in items_info:
        if items:
            num_items = sum(map(len, items.values()))
            print >>report, '%s: %d' % (name, num_items)
            print >>html_report, """
<tr><td>%s</td><td align="right">%d</td></tr>""" % (name, num_items)
    print >>report, """Total Tests: %d""" % num_total_tests
    print >>report
    print >>html_report, """
<tfoot>
  <tr><td><b>Total Tests</b></td><td align="right"><b>%d</b></td></tr>
</tfoot>
</table>
""" % num_total_tests

    if total_changes:
        print >>report, """=============="""
        print >>report, """Changes Detail"""
        print >>report, """=============="""
        print >>html_report, """
<p>
<h3>Changes Detail</h3>"""
        for name,items,show_perf in items_info:
            if not items or name == 'Unchanged Tests':
                continue

            show_pset = items.items()[0][0] or len(items) > 1
            pset_names = dict(
                (pset, 'pset.%d' % i)
                for i,pset in enumerate(ts_summary.parameter_sets))
            print >>report
            print >>report, name
            print >>report, '-' * len(name)
            for pset,tests in items.items():
                if show_perf:
                    tests.sort(key = lambda (_,cr): -abs(cr.pct_delta))

                # Group tests by final component.
                def get_last_component(t):
                    name = t[0]
                    if '.' in name:
                        return name.rsplit('.', 1)[1]
                    return ''
                grouped = Util.multidict(
                    (get_last_component(t), t)
                    for t in tests)

                test_name = name
                for group,grouped_tests in Util.sorted(grouped.items()):
                    group_name = {
                        "" : "(ungrouped)",
                        "exec" : "Execution",
                        "compile" : "Compile" }.get(group, group)
                    if show_pset:
                        table_name = "%s - %s" % (test_name, pset)
                    else:
                        table_name = test_name
                    print >>report, "%s - %s" % (table_name, group_name)
                    print >>html_report, """
    <p>
    <table class="sortable">
    <tr><th>%s - %s </th>""" % (table_name, group_name)
                    if show_perf:
                        print >>html_report, """
    <th>&Delta;</th><th>Previous</th><th>Current</th> <th>&sigma;</th>"""
                    print >>html_report, """</tr>"""
                    for i,(name,cr) in enumerate(grouped_tests):
                        if show_perf:
                            if cr.stddev is not None:
                                print >>report, (
                                    '  %s: %.2f%%'
                                    '(%.4f => %.4f, std. dev.: %.4f)') % (
                                    name, 100. * cr.pct_delta,
                                    cr.previous, cr.current, cr.stddev)
                            else:
                                print >>report, (
                                    '  %s: %.2f%%'
                                    '(%.4f => %.4f)') % (
                                    name, 100. * cr.pct_delta,
                                    cr.previous, cr.current)

                            # Show inline charts for top 10 changes.
                            if show_graphs and i < 10:
                                graph_name = "graph.%d" % len(graphs)
                                graphs.append( (graph_name,name,pset) )
                                extra_cell_value = """
    <br><canvas id="%s" width="400" height="100"></canvas/>
    """ % (graph_name)
                            else:
                                extra_cell_value = ""

                            # Link the regression to the chart of its
                            # performance.
                            pset_name = pset_names[pset]
                            form_data = urllib.urlencode([(pset_name, 'on'),
                                                          ('test.'+name, 'on')])
                            linked_name = '<a href="%s?%s">%s</a>' % (
                                os.path.join(report_url, "graph"),
                                form_data, name)

                            pct_value = Util.PctCell(cr.pct_delta).render()
                            if cr.stddev is not None:
                                print >>html_report, """
    <tr><td>%s%s</td>%s<td>%.4f</td><td>%.4f</td><td>%.4f</td></tr>""" %(
                                    linked_name, extra_cell_value, pct_value,
                                    cr.previous, cr.current, cr.stddev)
                            else:
                                print >>html_report, """
    <tr><td>%s%s</td>%s<td>%.4f</td><td>%.4f</td><td>-</td></tr>""" %(
                                    name, extra_cell_value, pct_value,
                                    cr.previous, cr.current)
                        else:
                            print >>report, '  %s' % (name,)
                            print >>html_report, """
    <tr><td>%s</td></tr>""" % (name,)
                    print >>html_report, """
    </table>"""

    # Finish up the HTML report.
    if graphs:
        # Get the test ids we want data for.
        test_ids = [ts_summary.test_id_map[(name,pset)]
                     for _,name,pset in graphs]

        plots_iter = GraphUtil.get_test_plots(db, machine, test_ids,
                                              run_summary, ts_summary,
                                              show_mad_error = True,
                                              show_points = True)

        print >>html_report, """
<script type="text/javascript">
function init_report() {"""
        for (graph_item, plot_info) in zip(graphs, plots_iter):
            graph_name = graph_item[0]
            plot_js = plot_info[1]
            print >>html_report, """
        graph = new Graph2D("%s");
        graph.clearColor = [1, 1, 1];
        %s
        graph.draw();
""" % (graph_name, plot_js)
        print >>html_report, """
}
</script>"""

    html_report = html_report.getvalue()
    if not only_html_body:
        # We embed the additional resources, so that the message is self
        # contained.
        viewer_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "viewer")
        style_css = open(os.path.join(viewer_path, "resources",
                                      "style.css")).read()
        header = """
    <style type="text/css">
%s
    </style>""" % style_css
        if graphs:
            view2d_js = open(os.path.join(viewer_path, "js",
                                          "View2D.js")).read()
            header += """
    <script type="text/javascript">
%(view2d_js)s
    </script>""" % locals()

        html_report = """
<html>
  <head>
%(header)s
    <title>%(subject)s</title>
  </head>
  <body onload="init_report()">
%(html_report)s
  </body>
</html>""" % locals()

    return subject, report.getvalue(), html_report

def getReport(result, db, run, baseurl, was_added, will_commit):
    report = StringIO.StringIO()

    # Use a simple report unless the tag indicates this is an old style nightly
    # test run.
    if 'tag' in run.info and run.info['tag'].value != 'nightlytest':
        return getSimpleReport(result, db, run, baseurl, was_added, will_commit)

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
        q = db.session.query(perfdb.Run).join(perfdb.Machine)
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
    print >>report, """%s/nightlytest/%d/""" % (baseurl, run.id)
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
    return subject, report.getvalue(), None

if __name__ == '__main__':
    main()
