"""
Report functionality centered around individual runs.
"""

import StringIO
import os

def generate_run_report(run, baseurl, only_html_body = False,
                        num_comparison_runs = 10):
    """
    generate_run_report(...) -> (str: subject, str: text_report,
                                 str: html_report)

    Generate a comprehensive report on the results of the given individual
    run, suitable for emailing or presentation on a web page.
    """

    assert num_comparison_runs > 0


    ts = run.testsuite
    machine = run.machine
    machine_parameters = machine.parameters

    # Gather the runs to use for statistical data.
    comparison_window = list(ts.get_previous_runs_on_machine(
            run, num_comparison_runs))

    # Get the specific run to compare to.
    if comparison_window:
        compare_to = comparison_window[0]
    else:
        compare_to = None

    # Begin report generation...
    subject = """%s test results: %s""" % (
        machine.name, run.start_time.strftime('%Y-%m-%d %H:%M:%S %Z PST'))
    report = StringIO.StringIO()
    html_report = StringIO.StringIO()

    # Generate the report header.
    if baseurl[-1] == '/':
        baseurl = baseurl[:-1]

    report_url = """%s/%d/""" % (baseurl, run.id)
    print >>report, report_url
    print >>report, """Nickname: %s:%d""" % (machine.name, machine.id)
    if 'name' in machine_parameters:
        print >>report, """Name: %s""" % (machine_parameters['name'],)
    print >>report, """Comparing:"""
    # FIXME: Remove hard coded field use here.
    print >>report, """  Run: %d, Order: %s, Start Time: %s, End Time: %s""" % (
        run.id, run.order.llvm_project_revision, run.start_time, run.end_time)
    if compare_to:
        # FIXME: Remove hard coded field use here.
        print >>report, ("""   To: %d, Order: %s, """
                         """Start Time: %s, End Time: %s""") % (
            compare_to.id, compare_to.order.llvm_project_revision,
            compare_to.start_time, compare_to.end_time)
        if run.machine != compare_to.machine:
            print >>report, """*** WARNING ***:""",
            print >>report, """comparison is against a different machine""",
            print >>report, """(%s:%d)""" % (compare_to.machine.name,
                                             compare_to.machine.id)
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
  </tr>"""
    # FIXME: Remove hard coded field use here.
    print >>html_report, """\
<tr><td>Current</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>""" % (
        run.id, run.order.llvm_project_revision, run.start_time, run.end_time)
    if compare_to:
        # FIXME: Remove hard coded field use here.
        print >>html_report, """\
<tr><td>Previous</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>""" % (
            compare_to.id, compare_to.order.llvm_project_revision,
            compare_to.start_time, compare_to.end_time)
    else:
        print >>html_report, """<tr><td colspan=4>No Previous Run</td></tr>"""
    print >>html_report, """</table>"""
    if compare_to and run.machine != compare_to.machine:
        print >>html_report, """<p><b>*** WARNING ***:""",
        print >>html_report, """comparison is against a different machine""",
        print >>html_report, """(%s:%d)</b></p>""" % (compare_to.machine.name,
                                                      compare_to.machine.id)

    html_report = html_report.getvalue()
    if not only_html_body:
        # We embed the additional resources, so that the message is self
        # contained.
        static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "ui", "static")
        style_css = open(os.path.join(static_path,
                                      "style.css")).read()

        html_report = """
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

    return subject, report.getvalue(), html_report
