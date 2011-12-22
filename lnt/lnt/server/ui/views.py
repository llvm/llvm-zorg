import os
import re
import tempfile
import time

import flask
from flask import abort
from flask import current_app
from flask import g
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from lnt.db import perfdb
from lnt.server.ui.globals import v4_url_for

frontend = flask.Module(__name__)

###
# Root-Only Routes

@frontend.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('.static', filename='favicon.ico'))

@frontend.route('/select_db')
def select_db():
    path = request.args.get('path')
    db = request.args.get('db')
    if path is None:
        abort(400)
    if db not in current_app.old_config.databases:
        abort(404)

    # Rewrite the path.
    new_path = "/db_%s" % db
    if not path.startswith("/db_"):
        new_path += path
    else:
        if '/' in path[1:]:
            new_path += "/" + path.split("/", 2)[2]
    return redirect(request.script_root + new_path)

#####
# Per-Database Routes

# Decorator for implementing per-database routes.
def db_route(rule, only_v3 = True, **options):
    """
    LNT specific route for endpoints which always refer to some database
    object.

    This decorator handles adding the routes for both the default and explicit
    database, as well as initializing the global database information objects.
    """
    def decorator(f):
        def wrap(db_name = None, **args):
            # Initialize the database parameters on the app globals object.
            g.db_name = db_name or "default"
            g.db_info = current_app.old_config.databases.get(g.db_name)
            if g.db_info is None:
                abort(404)

            # Disable non-v0.3 database support, if requested.
            if only_v3 and g.db_info.db_version != '0.3':
                return render_template("error.html", message="""\
UI support for database with version %r is not yet implemented.""" % (
                        g.db_info.db_version))


            return f(**args)

        frontend.add_url_rule(rule, f.__name__, wrap, **options)
        frontend.add_url_rule("/db_<db_name>" + rule,
                              f.__name__, wrap, **options)

        return wrap
    return decorator

@db_route('/', only_v3 = False)
def index():
    return render_template("index.html")

###
# Database Actions

@db_route('/browse')
def browse():
    return render_template("browse.html")

@db_route('/submitRun', methods=('GET', 'POST'))
def submit_run():
    from lnt.util import ImportData

    if request.method == 'POST':
        input_file = request.files.get('file')
        input_data = request.form.get('input_data')
        commit = int(request.form.get('commit', 0))

	if input_file and not input_file.content_length:
            input_file = None

        if not input_file and not input_data:
            return render_template(
                "submit_run.html", error="must provide input file or data")
        if input_file and input_data:
            return render_template(
                "submit_run.html", error="cannot provide input file *and* data")

        if input_file:
            data_value = input_file.read()
        else:
            data_value = input_data

        # Stash a copy of the raw submission.
        prefix = time.strftime("data-%Y-%m-%d_%H-%M-%S")
        fd,path = tempfile.mkstemp(prefix=prefix,
                                   suffix='.plist',
                                   dir=current_app.old_config.tempDir)
        os.write(fd, data_value)
        os.close(fd)

        # Get a DB connection.
        db = request.get_db()

        # Import the data.
        #
        # FIXME: Gracefully handle formats failures and DOS attempts. We
        # should at least reject overly large inputs.
        result = ImportData.import_and_report(
            current_app.old_config, g.db_name, db, path, '<auto>', commit)

        return flask.jsonify(**result)

    return render_template("submit_run.html")

###
# Generic Database Views

@db_route("/machines/<id>/")
def machine(id):
    return render_template("machine.html", id=id)

@db_route("/runs/<id>/")
def run(id):
    return render_template("run.html", id=id)

@db_route("/tests/<id>/")
def test(id):
    return render_template("test.html", id=id)

###
# Simple LNT Schema Viewer

from lnt.db.perfdb import Machine, Run, RunInfo, Sample
from lnt.db import runinfo
from lnt.db import perfdbsummary
from lnt.util import NTEmailReport

@db_route("/simple/<tag>/")
def simple_overview(tag):
    db = request.get_db()

    # Get the most recent runs in this tag, we just arbitrarily limit to looking
    # at the last 100 submission.
    recent_runs = db.query(Run).\
        join(RunInfo).\
        order_by(Run.start_time.desc()).\
        filter(RunInfo.key == "tag").\
        filter(RunInfo.value == tag).limit(100)
    recent_runs = list(recent_runs)

    # Compute the active machine list.
    active_machines = dict((run.machine.name, run)
                           for run in recent_runs[::-1])

    # Compute the active submission list.
    N = 30
    active_run_orders = dict(
        db.query(RunInfo.run_id, RunInfo.value).\
            filter(RunInfo.key == "run_order").\
            filter(RunInfo.run_id.in_(s.id for s in recent_runs[:N])))
    active_submissions = [(r, active_run_orders.get(r.id))
                          for r in recent_runs[:N]]

    return render_template("simple_overview.html", tag=tag,
                           active_machines=active_machines,
                           active_submissions=active_submissions)

@db_route("/simple/<tag>/machines/<int:id>")
def simple_machine(tag, id):
    db = request.get_db()

    # Get the run summary.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)

    # Compute the list of associated runs, grouped by order.
    from lnt.server.ui import util
    grouped_runs = util.multidict(
        (run_summary.get_run_order(run_id), run_id)
        for run_id in run_summary.get_runs_on_machine(id))

    associated_runs = [(order, [db.getRun(run_id)
                                for run_id in runs])
                       for order,runs in grouped_runs.items()]

    return render_template("simple_machine.html", tag=tag, id=id,
                           associated_runs=associated_runs)

def get_simple_run_info(tag, id):
    db = request.get_db()

    run = db.getRun(id)

    # Get the run summary.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)

    # Get the comparison run.
    compare_to = None
    compare_to_id = request.args.get('compare')
    if compare_to_id is not None:
        try:
            compare_to = db.getRun(int(compare_to_id))
        except:
            pass
    if compare_to is None:
        prev_id = run_summary.get_previous_run_on_machine(run.id)
        if prev_id is not None:
            compare_to = db.getRun(prev_id)

    return db, run, run_summary, compare_to

@db_route("/simple/<tag>/<id>/report")
def simple_report(tag, id):
    db, run, run_summary, compare_to = get_simple_run_info(tag, id)

    show_graphs = bool(request.args.get('show_graphs'))
    _, _, html_report = NTEmailReport.getSimpleReport(
        None, db, run, url_for('index', db_name=g.db_name),
        True, True, show_graphs = show_graphs)

    return make_response(html_report)

@db_route("/simple/<tag>/<id>/text_report")
def simple_text_report(tag, id):
    db, run, run_summary, compare_to = get_simple_run_info(tag, id)

    _, text_report, _ = NTEmailReport.getSimpleReport(
        None, db, run, url_for('index', db_name=g.db_name),
        True, True)

    response = make_response(text_report)
    response.mimetype = "text/plain"
    return response

@db_route("/simple/<tag>/<int:id>")
@db_route("/simple/<tag>/<int:id>/")
def simple_run(tag, id):
    db, run, run_summary, compare_to = get_simple_run_info(tag, id)

    # Get additional summaries.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)
    sri = runinfo.SimpleRunInfo(db, ts_summary)

    # Get the neighboring runs.
    cur_id = run.id
    for i in range(3):
        next_id = run_summary.get_next_run_on_machine(cur_id)
        if not next_id:
            break
        cur_id = next_id
    neighboring_runs = []
    for i in range(6):
        neighboring_runs.append(db.getRun(cur_id))
        cur_id = run_summary.get_previous_run_on_machine(cur_id)
        if cur_id is None:
            break

    # Parse the view options.
    options = {}
    options['show_delta'] = bool(request.args.get('show_delta'))
    options['show_previous'] = bool(request.args.get('show_previous'))
    options['show_stddev'] =  bool(request.args.get('show_stddev'))
    options['show_mad'] = bool(request.args.get('show_mad'))
    options['show_all'] = bool(request.args.get('show_all'))
    options['show_all_samples'] = bool(request.args.get('show_all_samples'))
    options['show_sample_counts'] = bool(request.args.get('show_sample_counts'))
    options['show_graphs'] = show_graphs = bool(request.args.get('show_graphs'))
    options['show_data_table'] = bool(request.args.get('show_data_table'))
    options['hide_report_by_default'] = bool(
        request.args.get('hide_report_by_default'))
    try:
        num_comparison_runs = int(request.args.get('num_comparison_runs'))
    except:
        num_comparison_runs = 10
    options['num_comparison_runs'] = num_comparison_runs
    options['test_filter'] = test_filter_str = request.args.get(
        'test_filter', '')
    if test_filter_str:
        test_filter_re = re.compile(test_filter_str)
    else:
        test_filter_re = None

    _, text_report, html_report = NTEmailReport.getSimpleReport(
        None, db, run, url_for('index', db_name=g.db_name),
        True, True, only_html_body = True, show_graphs = show_graphs,
        num_comparison_runs = num_comparison_runs)

    # Get the test status style used in each run.
    run_status_kind = run_summary.get_run_status_kind(db, run.id)
    if compare_to:
        compare_to_status_kind = run_summary.get_run_status_kind(
            db, compare_to.id)
    else:
        compare_to_status_kind = None

    # Get the list of tests we are interest in.
    interesting_runs = [run.id]
    if compare_to:
        interesting_runs.append(compare_to.id)
    test_names = ts_summary.get_test_names_in_runs(db, interesting_runs)

    # Filter the list of tests, if requested.
    if test_filter_re:
        test_names = [test
                      for test in test_names
                      if test_filter_re.search(test)]

    # Gather the runs to use for statistical data, if enabled.
    cur_id = run.id
    comparison_window = []
    for i in range(num_comparison_runs):
        cur_id = run_summary.get_previous_run_on_machine(cur_id)
        if not cur_id:
            break
        comparison_window.append(cur_id)

    return render_template("simple_run.html", tag=tag, id=id,
                           compare_to=compare_to,
                           compare_to_status_kind=compare_to_status_kind,
                           run_summary=run_summary, ts_summary=ts_summary,
                           simple_run_info=sri, test_names=test_names,
                           neighboring_runs=neighboring_runs,
                           text_report=text_report, html_report=html_report,
                           options=options, runinfo=runinfo,
                           comparison_window=comparison_window)

@db_route("/simple/<tag>/<int:id>/graph")
def simple_graph(tag, id):
    from lnt.server.ui import graphutil
    from lnt.server.ui import util

    db, run, run_summary, compare_to = get_simple_run_info(tag, id)

    # Get additional summaries.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)

    # Get the neighboring runs.
    cur_id = run.id
    for i in range(3):
        next_id = run_summary.get_next_run_on_machine(cur_id)
        if not next_id:
            break
        cur_id = next_id
    neighboring_runs = []
    for i in range(6):
        neighboring_runs.append(db.getRun(cur_id))
        cur_id = run_summary.get_previous_run_on_machine(cur_id)
        if cur_id is None:
            break

    # Parse the view options.
    options = {}
    show_mad = bool(request.args.get('show_mad', True))
    show_stddev = bool(request.args.get('show_stddev'))
    show_linear_regression = bool(
        request.args.get('show_linear_regression', True))

    # Load the graph parameters.
    graph_tests = []
    graph_psets = []
    for name,value in request.args.items():
        if name.startswith(str('test.')):
            graph_tests.append(name[5:])
        elif name.startswith(str('pset.')):
            graph_psets.append(ts_summary.parameter_sets[int(name[5:])])

    # Get the test ids we want data for.
    test_ids = [ts_summary.test_id_map[(name,pset)]
                 for name in graph_tests
                 for pset in graph_psets]

    # Build the graph data
    pset_id_map = dict([(pset,i)
                        for i,pset in enumerate(ts_summary.parameter_sets)])
    legend = []
    num_points = 0
    plot_points = []
    plots = ""
    plots_iter = graphutil.get_test_plots(
        db, run.machine, test_ids, run_summary, ts_summary,
        show_mad_error = show_mad, show_stddev = show_stddev,
        show_linear_regression = show_linear_regression, show_points = True)
    for test_id, plot_js, col, points, ext_points in plots_iter:
        test = db.getTest(test_id)
        name = test.name
        pset = test.get_parameter_set()

        num_points += len(points)
        legend.append(("%s : P%d" % (name, pset_id_map[pset]), tuple(col)))
        plots += plot_js
        plot_points.append(ext_points)

    # Build the sample info.
    resample_list = set()
    new_sample_list = []
    plot_deltas = []
    for (name,col),points in zip(legend,plot_points):
        points.sort()
        deltas = [(util.safediv(p1[1], p0[1]), p0, p1)
                  for p0,p1 in util.pairs(points)]
        deltas.sort()
        deltas.reverse()
        plot_deltas.append(deltas[:20])
        for (pct,(r0,t0,mad0,med0),(r1,t1,mad1,med1)) in deltas[:20]:
            # Find the best next revision to sample, unless we have
            # sampled to the limit. To conserve resources, we try to
            # align to the largest "nice" revision boundary that we can,
            # so that we tend to sample the same revisions, even as we
            # drill down.
            assert r0 < r1 and r0 != r1
            if r0 + 1 != r1:
                for align in [scale * boundary
                              for scale in (100000,10000,1000,100,10,1)
                              for boundary in (5, 1)]:
                    r = r0 + 1 + (r1 - r0)//2
                    r = (r // align) * align
                    if r0 < r < r1:
                        new_sample_list.append(r)
                        break

            resample_list.add(r0)
            resample_list.add(r1)

    return render_template("simple_graph.html", tag=tag, id=id,
                           compare_to=compare_to,
                           neighboring_runs=neighboring_runs,
                           run_summary=run_summary, ts_summary=ts_summary,
                           graph_plots=plots, legend=legend,
                           num_plots=len(test_ids), num_points=num_points,
                           new_sample_list=new_sample_list,
                           resample_list=resample_list,
                           plot_deltas=plot_deltas)

@db_route("/simple/<tag>/order_aggregate_report")
def simple_order_aggregate_report(tag):
    from lnt.server.ui import util

    db = request.get_db()

    # Get the run summary.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)
    # Load the test suite summary.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)
    # Get the run pass/fail information.
    sri = runinfo.SimpleRunInfo(db, ts_summary)

    # Get this list of orders we are aggregating over.
    orders_to_aggregate = request.args.get('orders', '')
    orders_to_aggregate = orders_to_aggregate.split(',')

    # Collect the runs, aggregated by order and machine.
    runs_to_summarize = []
    runs_by_machine_and_order = util.multidict()
    available_machine_ids = set()
    for order in orders_to_aggregate:
        for id in run_summary.runs_by_order["%7s" % order]:
            r = db.getRun(id)
            runs_to_summarize.append(r)
            available_machine_ids.add(r.machine_id)
            runs_by_machine_and_order[(r.machine_id, order)] = r
    available_machine_ids = list(available_machine_ids)
    available_machine_ids.sort()
    available_machines = [db.getMachine(id)
                          for id in available_machine_ids]

    # We currently only compare the null pset.
    pset = ()

    # Get the list of tests we are interested in.
    test_names = ts_summary.get_test_names_in_runs(db, (
            r.id for r in runs_to_summarize))

    # Create test subsets, by name.
    test_subsets = util.multidict()
    for test_name in test_names:
        if '.' in test_name:
            subset = test_name.rsplit('.', 1)[1]
        else:
            subset = test_name, ''
        test_subsets[subset] = test_name

    # Convert subset names to pretty form.
    def convert((subset, tests)):
        subset_name = { "compile" : "Compile Time",
                        "exec" : "Execution Time" }.get(subset, subset)
        return (subset_name, tests)
    test_subsets = dict(convert(item) for item in test_subsets.items())

    # Batch load all the samples for all the runs we are interested in.
    start_time = time.time()
    all_samples = db.session.query(Sample.run_id, Sample.test_id,
                                   Sample.value).\
                                   filter(Sample.run_id.in_(
            r.id for r in runs_to_summarize))
    all_samples = list(all_samples)

    # Aggregate samples for easy lookup.
    aggregate_samples = util.multidict()
    for run_id, test_id, value in all_samples:
        aggregate_samples[(run_id, test_id)] = value

    # Create the data table as:
    #  data_table[subset_name][test_name][order index][machine index] = (
    #    status samples, samples)
    def get_test_samples(machine_id, test_name, order):
        status_name = test_name + '.status'
        status_test_id = ts_summary.test_id_map.get(
            (status_name, pset))
        test_id = ts_summary.test_id_map.get(
            (test_name, pset))

        status_samples = []
        samples = []
        for run in runs_by_machine_and_order.get((machine_id,order), []):
            status_samples.extend(aggregate_samples.get(
                    (run.id, status_test_id), []))
            samples.extend(aggregate_samples.get(
                    (run.id, test_id), []))

        # For now, return simplified sample set. We can return all the data if
        # we find a use for it.
        if status_samples or not samples:
            return None
        return min(samples)
    data_table = {}
    for subset_name,tests_in_subset in test_subsets.items():
        data_table[subset_name] = subset_table = {}
        for test_name in tests_in_subset:
            subset_table[test_name] = test_data = [
                [get_test_samples(id, test_name, order)
                 for id in available_machine_ids]
                for order in orders_to_aggregate]

    # Create some other data tables of serializable info.
    available_machine_info = [(m.id, m.name)
                              for m in available_machines]

    return render_template("simple_order_aggregate_report.html", **locals())

###
# V4 Schema Viewer

# Decorator for implementing per-testsuite routes.
def v4_route(rule, **options):
    """
    LNT V4 specific route for endpoints which always refer to some testsuite
    object.
    """

    # FIXME: This is manually composed with db_route.
    def decorator(f):
        def wrap(testsuite_name, db_name = None, **args):
            # Initialize the test suite parameters on the app globals object.
            g.testsuite_name = testsuite_name

            # Initialize the database parameters on the app globals object.
            g.db_name = db_name or "default"
            g.db_info = current_app.old_config.databases.get(g.db_name)
            if g.db_info is None:
                abort(404)

            return f(**args)

        frontend.add_url_rule("/v4/<testsuite_name>" + rule,
                              f.__name__, wrap, **options)
        frontend.add_url_rule("/db_<db_name>/v4/<testsuite_name>" + rule,
                              f.__name__, wrap, **options)

        return wrap
    return decorator

@v4_route("/")
def v4_overview():
    ts = request.get_testsuite()

    # Get the most recent runs in this tag, we just arbitrarily limit to looking
    # at the last 100 submission.
    recent_runs = ts.query(ts.Run).\
        order_by(ts.Run.start_time.desc()).limit(100)
    recent_runs = list(recent_runs)

    # Compute the active machine list.
    active_machines = dict((run.machine.name, run)
                           for run in recent_runs[::-1])

    # Compute the active submission list.
    #
    # FIXME: Remove hard coded field use here.
    N = 30
    active_submissions = [(r, r.order.llvm_project_revision)
                          for r in recent_runs[:N]]

    return render_template("v4_overview.html",
                           testsuite_name=g.testsuite_name,
                           active_machines=active_machines,
                           active_submissions=active_submissions)

@v4_route("/machine/<int:id>")
def v4_machine(id):
    # Compute the list of associated runs, grouped by order.
    from lnt.server.ui import util

    # Gather all the runs on this machine.
    ts = request.get_testsuite()

    # FIXME: Remove hard coded field use here.
    associated_runs = util.multidict(
        (run_order, r)
        for r,run_order in ts.query(ts.Run, ts.Order.llvm_project_revision).\
            join(ts.Order).\
            filter(ts.Run.machine_id == id))
    associated_runs = associated_runs.items()

    return render_template("v4_machine.html",
                           testsuite_name=g.testsuite_name, id=id,
                           associated_runs=associated_runs)

@v4_route("/<int:id>/report")
def v4_report(id):
    db = request.get_db()
    ts = request.get_testsuite()
    run = ts.getRun(id)

    _, _, html_report = NTEmailReport.getReport(
        result=None, db=db, run=run, baseurl=v4_url_for('index'),
        was_added=True, will_commit=True, only_html_body=False)

    return make_response(html_report)

@v4_route("/<int:id>/text_report")
def v4_text_report(id):
    db = request.get_db()
    ts = request.get_testsuite()
    run = ts.getRun(id)

    _, text_report, _ = NTEmailReport.getReport(
        result=None, db=db, run=run, baseurl=v4_url_for('index'),
        was_added=True, will_commit=True, only_html_body=True)

    response = make_response(text_report)
    response.mimetype = "text/plain"
    return response

@v4_route("/<int:id>")
def v4_run(id):
    db = request.get_db()
    ts = request.get_testsuite()
    run = ts.getRun(id)

    # Find the neighboring runs, by order.
    prev_runs = list(ts.get_previous_runs_on_machine(run, N = 3))
    next_runs = list(ts.get_next_runs_on_machine(run, N = 3))
    neighboring_runs = next_runs[::-1] + [run] + prev_runs

    # Parse the view options.
    options = {}
    options['show_delta'] = bool(request.args.get('show_delta'))
    options['show_previous'] = bool(request.args.get('show_previous'))
    options['show_stddev'] =  bool(request.args.get('show_stddev'))
    options['show_mad'] = bool(request.args.get('show_mad'))
    options['show_all'] = bool(request.args.get('show_all'))
    options['show_all_samples'] = bool(request.args.get('show_all_samples'))
    options['show_sample_counts'] = bool(request.args.get('show_sample_counts'))
    options['show_graphs'] = show_graphs = bool(request.args.get('show_graphs'))
    options['show_data_table'] = bool(request.args.get('show_data_table'))
    options['hide_report_by_default'] = bool(
        request.args.get('hide_report_by_default'))
    try:
        num_comparison_runs = int(request.args.get('num_comparison_runs'))
    except:
        num_comparison_runs = 10
    options['num_comparison_runs'] = num_comparison_runs
    options['test_filter'] = test_filter_str = request.args.get(
        'test_filter', '')
    if test_filter_str:
        test_filter_re = re.compile(test_filter_str)
    else:
        test_filter_re = None

    # Generate the report for inclusion in the run page.
    #
    # FIXME: This is a crummy implementation of the concept that we want the
    # webapp UI to be easy to correlate with the email reports.
    _, text_report, html_report = NTEmailReport.getReport(
        result=None, db=db, run=run, baseurl=v4_url_for('index'),
        was_added=True, will_commit=True, only_html_body=True)

    return render_template("v4_run.html", ts=ts, run=run,
                           options=options, neighboring_runs=neighboring_runs,
                           text_report=text_report, html_report=html_report)

@v4_route("/order/<int:ordinal>")
def v4_order(ordinal):
    # Get the testsuite.
    ts = request.get_testsuite()

    # Get the order.
    order = ts.query(ts.Order).filter_by(ordinal = ordinal).first()
    if order is None:
        abort(404)

    return render_template("v4_order.html", ts=ts, order=order)
