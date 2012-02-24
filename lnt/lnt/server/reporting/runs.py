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

    # If no baseline was given, find one close to the requested baseline run
    # order.
    if baseline is None:
        # Find the closest order to the requested baseline order, for which this
        # machine also reported.
        #
        # FIXME: Scalability! Pretty fast in practice, but still pretty lame.
        order_to_find = ts.Order(llvm_project_revision = '% 7d' % 144168)
        best = None
        for order in ts.query(ts.Order).\
                join(ts.Run).\
                filter(ts.Run.machine == machine).distinct():
            if order >= order_to_find and (best is None or order < best):
                best = order

        # Find the most recent run on this machine that used that order.
        if best:
            baseline = ts.query(ts.Run).\
                filter(ts.Run.machine == run.machine).\
                filter(ts.Run.order == best).\
                order_by(ts.Run.start_time.desc()).first()

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

    # Gather the run-over-run changes to report, organized by field and then
    # collated by change type.
    run_to_run_info,test_results = _get_changes_by_type(
        run, compare_to, primary_fields, test_names, comparison_window, sri)

    # If we have a baseline, gather the run-over-baseline results and
    # changes.
    if baseline:
        run_to_baseline_info,baselined_results = _get_changes_by_type(
            run, baseline, primary_fields, test_names, baseline_window, sri)
    else:
        run_to_baseline_info = baselined_results = None

    # Gather the run-over-run changes to report.

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

    ts_url = """%s/v4/%s""" % (baseurl, ts.name)
    run_url = """%s/%d""" % (ts_url, run.id)
    report_url = run_url
    url_fields = []
    if compare_to:
        url_fields.append(('compare_to', str(compare_to.id)))
    if baseline:
        url_fields.append(('baseline', str(baseline.id)))
    report_url = "%s?%s" % (run_url, "&".join("%s=%s" % (k,v)
                                              for k,v in url_fields))
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
    print >>html_report, """<h1><a href="%s">%s</a></h1>""" % (
        report_url, subject)
    print >>html_report, """\
<p>
<table>
  <tr>
    <th>Run</th>
    <th>Order</th>
    <th>Start Time</th>
    <th>Duration</th>
  </tr>"""
    for (title, r) in (('Current', run),
                       ('Previous', compare_to),
                       ('Baseline', baseline)):
        if r is None:
            print >>html_report, """<tr><td colspan=4>No %s Run</td></tr>""" % (
                title,)
            continue

        # FIXME: Remove hard coded field use here.
        print >>html_report, """\
<tr><td><a href="%s/%d">%s</a></td>\
<td><a href="%s/order/%d">%s</a></td><td>%s</td><td>%s</td></tr>""" % (
        ts_url, r.id, title,
        ts_url, r.order.id, r.order.llvm_project_revision,
        r.start_time, r.end_time - r.start_time)
    print >>html_report, """</table>"""
    if compare_to and run.machine != compare_to.machine:
        print >>html_report, """<p><b>*** WARNING ***:""",
        print >>html_report, """comparison is against a different machine""",
        print >>html_report, """(%s:%d)</b></p>""" % (compare_to.machine.name,
                                                      compare_to.machine.id)
    if baseline and run.machine != baseline.machine:
        print >>html_report, """<p><b>*** WARNING ***:""",
        print >>html_report, """baseline is against a different machine""",
        print >>html_report, """(%s:%d)</b></p>""" % (baseline.machine.name,
                                                      baseline.machine.id)

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
<thead><tr><th>Status Group</th><th align="right">#</th>"""
    if baseline:
        print >>html_report, """<th align="right"># (B)</th>"""
    print >>html_report, """</tr></thead> """
    # For now, we aggregate across all bucket types for reports.
    for i,(name,_,_) in enumerate(test_results[0][1]):
        num_items = sum(len(field_results[i][1])
                        for _,field_results in test_results)
        if baseline:
            num_items_vs_baseline = sum(
                len(field_results[i][1])
                for _,field_results in baselined_results)
        else:
            num_items_vs_baseline = None
        if num_items or num_items_vs_baseline:
            if baseline:
                print >>report, '%s: %d (%d on baseline)' % (
                    name, num_items, num_items_vs_baseline)
            else:
                print >>report, '%s: %d' % (name, num_items)
            print >>html_report, """
<tr><td>%s</td><td align="right">%d</td>""" % (
                name, num_items)
            if baseline:
                print >>html_report, """<td align="right">%d</td>""" % (
                    num_items_vs_baseline)
            print >>html_report, """</tr>"""
    print >>report, """Total Tests: %d""" % num_total_tests
    print >>report
    print >>html_report, """
<tfoot>
  <tr><td><b>Total Tests</b></td><td align="right"><b>%d</b></td>""" % (
        num_total_tests,)
    if baseline:
        print >>html_report, """<td align="right"><b>%d</b></td>""" % (
            num_total_tests,)
    print >>html_report, """</tr>
</tfoot>
</table>
"""

    # Add the run-over-run changes detail (if any were present).
    print >>report, """==========================="""
    print >>report, """Run-Over-Run Changes Detail"""
    print >>report, """==========================="""
    print >>html_report, """
<p>
<h3>Run-Over-Run Changes Detail</h3>"""

    _add_report_changes_detail(ts, test_results, report,
                               html_report, run_url,
                               run_to_baseline_info,
                               'Previous', '', ' (B)')

    # Add the run-over-baseline changes detail.
    if baseline:
        print >>report, """================================"""
        print >>report, """Run-Over-Baseline Changes Detail"""
        print >>report, """================================"""
        print >>html_report, """
<p>
<h3>Run-Over-Baseline Changes Detail</h3>"""

        _add_report_changes_detail(ts, baselined_results, report,
                                   html_report, run_url,
                                   run_to_run_info,
                                   'Baseline', '(B)', '')

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

def _get_changes_by_type(run_a, run_b, primary_fields, test_names,
                         comparison_window, sri):
    comparison_results = {}
    results_by_type = []
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
            cr = sri.get_run_comparison_result(run_a, run_b, test_id, field,
                                               comparison_window)
            comparison_results[(name,field)] = cr
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

        results_by_type.append(
            (field, (('New Failures', new_failures, False),
                     ('New Passes', new_passes, False),
                     ('Performance Regressions', perf_regressions, True),
                     ('Performance Improvements', perf_improvements, True),
                     ('Removed Tests', removed_tests, False),
                     ('Added Tests', added_tests, False),
                     ('Existing Failures', existing_failures, False),
                     ('Unchanged Tests', unchanged_tests, False))))
    return comparison_results, results_by_type

def _add_report_changes_detail(ts, test_results, report, html_report,
                               run_url, run_to_baseline_info,
                               primary_name, primary_field_suffix,
                               secondary_field_suffix):
    # Reorder results to present by most important bucket first.
    prioritized = [(priority, field, bucket_name, bucket, show_perf)
                   for field,field_results in test_results
                   for priority,(bucket_name, bucket,
                                 show_perf) in enumerate(field_results)]
    prioritized.sort(key = lambda item: (item[0], item[1].name))

    for _,field,bucket_name,bucket,show_perf in prioritized:
        _add_report_changes_detail_for_field_and_bucket(
            ts, field, bucket_name, bucket, show_perf, report,
            html_report, run_url, run_to_baseline_info,
            primary_name, primary_field_suffix, secondary_field_suffix)

def _add_report_changes_detail_for_field_and_bucket(
      ts, field, bucket_name, bucket, show_perf, report,
      html_report, run_url, secondary_info,
      primary_name, primary_field_suffix, secondary_field_suffix):
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
<th>&Delta;%s</th><th>%s</th><th>Current</th> <th>&sigma;%s</th>""" % (
            primary_field_suffix, primary_name, primary_field_suffix)
        if secondary_info:
            print >>html_report, """<th>&Delta;%s</th>""" % (
                secondary_field_suffix,)
            print >>html_report, """<th>&sigma;%s</th>""" % (
                secondary_field_suffix,)
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
            os.path.join(run_url, "graph"),
            form_data, name)

        pct_value = lnt.server.ui.util.PctCell(cr.pct_delta).render()
        if cr.stddev is not None:
            stddev_value = "%.4f" % cr.stddev
        else:
            stddev_value = "-"

        if secondary_info:
            a_cr = secondary_info[(name,field)]
            if a_cr.stddev is not None:
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
