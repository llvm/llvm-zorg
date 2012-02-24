"""
Report functionality centered around individual runs.
"""

import StringIO
import os
import time
import urllib

import lnt.server.reporting.analysis
import lnt.server.ui.util
from lnt.db import runinfo

def generate_run_report(run, baseurl, only_html_body = False,
                        num_comparison_runs = 10, result = None,
                        compare_to = None, baseline = None,
                        comparison_window = None):
    """
    generate_run_report(...) -> (str: subject, str: text_report,
                                 str: html_report)

    Generate a comprehensive report on the results of the given individual
    run, suitable for emailing or presentation on a web page.
    """

    assert num_comparison_runs > 0

    start_time = time.time()

    ts = run.testsuite
    machine = run.machine
    machine_parameters = machine.parameters

    # Gather the runs to use for statistical data.
    if comparison_window is None:
        comparison_start_run = compare_to or run
        comparison_window = list(ts.get_previous_runs_on_machine(
                comparison_start_run, num_comparison_runs))
    if baseline:
        baseline_window = list(ts.get_previous_runs_on_machine(
                baseline, num_comparison_runs))
    else:
        baseline_window = []

    # If we don't have an explicit baseline run or a comparison run, use the
    # previous run.
    if compare_to is None and comparison_window:
        compare_to = comparison_window[0]

    # Create the run info analysis object.
    runs_to_load = set(r.id for r in comparison_window)
    for r in baseline_window:
        runs_to_load.add(r.id)
    runs_to_load.add(run.id)
    if compare_to:
        runs_to_load.add(compare_to.id)
    if baseline:
        runs_to_load.add(baseline.id)
    sri = lnt.server.reporting.analysis.RunInfo(ts, runs_to_load)

    # Get the test names, primary fields and total test counts.
    test_names = ts.query(ts.Test.name, ts.Test.id).order_by(ts.Test.name).all()
    primary_fields = list(ts.Sample.get_primary_fields())
    num_total_tests = len(primary_fields) * len(test_names)

    # If we have a baseline, gather the run-over-baseline information.
    run_to_baseline_info = {}
    if baseline:
        for field in primary_fields:
            for name,test_id in test_names:
                cr = sri.get_run_comparison_result(
                    run, baseline, test_id, field, baseline_window)
                run_to_baseline_info[(name,field)] = cr

    # Gather the run-over-run changes to report, organized by field and then
    # collated by change type.
    test_results = []
    for field in primary_fields:
        new_failures = []
        new_passes = []
        perf_regressions = []
        perf_improvements = []
        removed_tests = []
        added_tests = []
        existing_failures = []
        unchanged_tests = []
        for name,test_id in test_names:
            cr = sri.get_run_comparison_result(run, compare_to, test_id, field,
                                               comparison_window)
            test_status = cr.get_test_status()
            perf_status = cr.get_value_status()
            if test_status == runinfo.REGRESSED:
                bucket = new_failures
            elif test_status == runinfo.IMPROVED:
                bucket = new_passes
            elif cr.current is None and cr.previous is not None:
                bucket = removed_tests
            elif cr.current is not None and cr.previous is None:
                bucket = added_tests
            elif test_status == runinfo.UNCHANGED_FAIL:
                bucket = existing_failures
            elif perf_status == runinfo.REGRESSED:
                bucket = perf_regressions
            elif perf_status == runinfo.IMPROVED:
                bucket = perf_improvements
            else:
                bucket = unchanged_tests

            bucket.append((name, cr, test_id))

        test_results.append(
            (field, (('New Failures', new_failures, False),
                     ('New Passes', new_passes, False),
                     ('Performance Regressions', perf_regressions, True),
                     ('Performance Improvements', perf_improvements, True),
                     ('Removed Tests', removed_tests, False),
                     ('Added Tests', added_tests, False),
                     ('Existing Failures', existing_failures, False),
                     ('Unchanged Tests', unchanged_tests, False))))

    # Collect the simplified results, if desired, for sending back to clients.
    if result is not None:
        pset_results = []
        result['test_results'] = [{ 'pset' : (), 'results' : pset_results}]
        for field,field_results in test_results:
            for _,bucket,_ in field_results:
                for name,cr,_ in bucket:
                    # FIXME: Include additional information about performance
                    # changes.
                    pset_results.append(("%s.%s" % (name, field.name),
                                         cr.get_test_status(),
                                         cr.get_value_status()))

    # Begin report generation...
    subject = """%s test results""" % (machine.name,)
    report = StringIO.StringIO()
    html_report = StringIO.StringIO()

    # Generate the report header.
    if baseurl[-1] == '/':
        baseurl = baseurl[:-1]

    report_url = """%s/v4/%s/%d""" % (baseurl, ts.name, run.id)
    print >>report, report_url
    print >>report, """Nickname: %s:%d""" % (machine.name, machine.id)
    if 'name' in machine_parameters:
        print >>report, """Name: %s""" % (machine_parameters['name'],)
    print >>report, "Comparing:"
    # FIXME: Remove hard coded field use here.
    print >>report, "     Run: %d, Order: %s, Start Time: %s, End Time: %s" % (
        run.id, run.order.llvm_project_revision, run.start_time, run.end_time)
    if compare_to:
        # FIXME: Remove hard coded field use here.
        print >>report, ("      To: %d, Order: %s, "
                         "Start Time: %s, End Time: %s") % (
            compare_to.id, compare_to.order.llvm_project_revision,
            compare_to.start_time, compare_to.end_time)
        if run.machine != compare_to.machine:
            print >>report, """*** WARNING ***:""",
            print >>report, """comparison is against a different machine""",
            print >>report, """(%s:%d)""" % (compare_to.machine.name,
                                             compare_to.machine.id)
    else:
        print >>report, "      To: (none)"
    if baseline:
        # FIXME: Remove hard coded field use here.
        print >>report, ("Baseline: %d, Order: %s, "
                         "Start Time: %s, End Time: %s") % (
            baseline.id, baseline.order.llvm_project_revision,
            baseline.start_time, baseline.end_time)
    print >>report

    # Generate the HTML report header.
    print >>html_report, """\
<h1>%s</h1>
<table>""" % subject
    print >>html_report, """\
<tr><td>URL</td><td><a href="%s">%s</a></td></tr>""" % (report_url, report_url)
    print >>html_report, "<tr><td>Nickname</td><td>%s:%d</td></tr>" % (
        machine.name, machine.id)
    if 'name' in machine_parameters:
        print >>html_report, """<tr><td>Name</td><td>%s</td></tr>""" % (
            machine_parameters['name'],)
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
    <th>Machine</th>
  </tr>"""
    # FIXME: Remove hard coded field use here.
    print >>html_report, """\
<tr><td>Current</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td>\
<td>%s:%d</td></tr>""" % (
        run.id, run.order.llvm_project_revision, run.start_time, run.end_time,
        run.machine.name, run.machine.id)
    if compare_to:
        # FIXME: Remove hard coded field use here.
        print >>html_report, """\
<tr><td>Previous</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td>\
<td>%s:%d</td></tr>""" % (
            compare_to.id, compare_to.order.llvm_project_revision,
            compare_to.start_time, compare_to.end_time, compare_to.machine.name,
            compare_to.machine.id)
    else:
        print >>html_report, """<tr><td colspan=4>No Previous Run</td></tr>"""
    if baseline:
        # FIXME: Remove hard coded field use here.
        print >>html_report, """\
<tr><td>Baseline</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td>\
<td>%s:%d</td></tr>""" % (
            baseline.id, baseline.order.llvm_project_revision,
            baseline.start_time, baseline.end_time, baseline.machine.name,
            baseline.machine.id)
    print >>html_report, """</table>"""
    if compare_to and run.machine != compare_to.machine:
        print >>html_report, """<p><b>*** WARNING ***:""",
        print >>html_report, """comparison is against a different machine""",
        print >>html_report, """(%s:%d)</b></p>""" % (compare_to.machine.name,
                                                      compare_to.machine.id)

    # Generate the summary of the changes.
    num_total_changes = sum(len(bucket)
                            for _,field_results in test_results
                            for name,bucket,_ in field_results
                            if name != 'Unchanged Tests')

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
    # For now, we aggregate across all bucket types for reports.
    for i,(name,_,_) in enumerate(test_results[0][1]):
        num_items = sum(len(field_results[i][1])
                        for _,field_results in test_results)
        if num_items:
                print >>report, '%s: %d' % (name, num_items)
                print >>html_report, """
<tr><td>%s</td><td align="right">%d</td></tr>""" % (
                    name, num_items)
    print >>report, """Total Tests: %d""" % num_total_tests
    print >>report
    print >>html_report, """
<tfoot>
  <tr><td><b>Total Tests</b></td><td align="right"><b>%d</b></td></tr>
</tfoot>
</table>
""" % num_total_tests

    # Add the changes detail.
    if num_total_changes:
        print >>report, """=============="""
        print >>report, """Changes Detail"""
        print >>report, """=============="""
        print >>html_report, """
<p>
<h3>Changes Detail</h3>"""

        _add_report_changes_detail(ts, test_results, report,
                                   html_report, report_url,
                                   run_to_baseline_info)

    report_time = time.time() - start_time
    print >>report, "Report Time: %.2fs" % (report_time,)
    print >>html_report, """
<hr>
<b>Report Time</b>: %.2fs""" % (report_time,)

    # Finish up the HTML report (wrapping the body, if necessary).
    html_report = html_report.getvalue()
    if not only_html_body:
        # We embed the additional resources, so that the message is self
        # contained.
        static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "ui", "static")
        style_css = open(os.path.join(static_path,
                                      "style.css")).read()

        html_report = """\
<html>
  <head>
    <style type="text/css">
%(style_css)s
    </style>
    <title>%(subject)s</title>
  </head>
  <body onload="init_report()">
%(html_report)s
  </body>
</html>""" % locals()

    return subject, report.getvalue(), html_report, sri

def _add_report_changes_detail(ts, test_results, report, html_report,
                               report_url, run_to_baseline_info):
    # Reorder results to present by most important bucket first.
    prioritized = [(priority, field, bucket_name, bucket, show_perf)
                   for field,field_results in test_results
                   for priority,(bucket_name, bucket,
                                 show_perf) in enumerate(field_results)]
    prioritized.sort(key = lambda item: (item[0], item[1].name))

    for _,field,bucket_name,bucket,show_perf in prioritized:
        _add_report_changes_detail_for_field_and_bucket(
            ts, field, bucket_name, bucket, show_perf, report,
            html_report, report_url, run_to_baseline_info)

def _add_report_changes_detail_for_field_and_bucket(ts, field, bucket_name,
                                                    bucket, show_perf, report,
                                                    html_report, report_url,
                                                    run_to_baseline_info):
    if not bucket or bucket_name == 'Unchanged Tests':
        return

    field_index = ts.sample_fields.index(field)
    # FIXME: Do not hard code field display names here, this should be in the
    # test suite metadata.
    field_display_name = { "compile_time" : "Compile Time",
                           "execution_time" : "Execution Time" }.get(
        field.name, field.name)

    print >>report, "%s - %s" % (bucket_name, field_display_name)
    print >>report, '-' * (len(bucket_name) + len(field_display_name) + 3)
    print >>html_report, """
<p>
<table class="sortable">
<tr><th width="500">%s - %s </th>""" % (bucket_name, field_display_name)
    if show_perf:
        print >>html_report, """\
<th>&Delta;</th><th>Previous</th><th>Current</th> <th>&sigma;</th>"""
        if run_to_baseline_info:
            print >>html_report, """<th>&Delta; (B)</th>"""
            print >>html_report, """<th>&sigma; (B)</th>"""
        print >>html_report, """</tr>"""

    # If we aren't displaying any performance results, just write out the
    # list of tests and continue.
    if not show_perf:
        for name,cr,_ in bucket:
            print >>report, '  %s' % (name,)
            print >>html_report, """
<tr><td>%s</td></tr>""" % (name,)
        print >>report
        print >>html_report, """
</table>"""
        return

    bucket.sort(key = lambda (_,cr,__): -abs(cr.pct_delta))

    for name,cr,test_id in bucket:
        if cr.stddev is not None:
            stddev_value = ', std. dev.: %.4f' % cr.stddev
        else:
            stddev_value = ''
        print >>report, ('  %s: %.2f%% (%.4f => %.4f%s)') % (
            name, 100. * cr.pct_delta,
            cr.previous, cr.current, stddev_value)

        # Link the regression to the chart of its performance.
        form_data = urllib.urlencode([('test.%d' % test_id,
                                       str(field_index))])
        linked_name = '<a href="%s?%s">%s</a>' % (
            os.path.join(report_url, "graph"),
            form_data, name)

        pct_value = lnt.server.ui.util.PctCell(cr.pct_delta).render()
        if cr.stddev is not None:
            stddev_value = "%.4f" % cr.stddev
        else:
            stddev_value = "-"

        if run_to_baseline_info:
            a_cr = run_to_baseline_info[(name,field)]
            if cr.stddev is not None:
                a_stddev_value = "%.4f" % a_cr.stddev
            else:
                a_stddev_value = "-"
            baseline_info = "%s<td>%s</td>""" % (
                lnt.server.ui.util.PctCell(a_cr.pct_delta).render(),
                a_stddev_value)
        else:
            baseline_info = ""
        print >>html_report, """\
<tr><td>%s</td>%s<td>%.4f</td><td>%.4f</td><td>%s</td>%s</tr>""" %(
            linked_name, pct_value, cr.previous, cr.current, stddev_value,
            baseline_info)
    print >>report
    print >>html_report, """
</table>"""
