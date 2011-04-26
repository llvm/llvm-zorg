import os
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
def db_route(rule, **options):
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

            return f(**args)

        frontend.add_url_rule(rule, f.__name__, wrap, **options)
        frontend.add_url_rule("/db_<db_name>" + rule,
                              f.__name__, wrap, **options)

        return wrap
    return decorator

@db_route('/')
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

        if not input_file.content_length and not input_data:
            return render_template(
                "submit_run.html", error="must provide input file or data")
        if input_file.content_length and input_data:
            return render_template(
                "submit_run.html", error="cannot provide input file *and* data")

        if input_file.content_length:
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

        return flask.jsonify(data = result)

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

from lnt.db.perfdb import Machine, Run, RunInfo
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
    from lnt.viewer import Util
    grouped_runs = Util.multidict(
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
        None, db, run, str("%s/db_%s/") % (current_app.old_config.zorgURL,
                                           g.db_name),
        True, True, show_graphs = show_graphs)

    return make_response(html_report)

@db_route("/simple/<tag>/<id>/text_report")
def simple_text_report(tag, id):
    db, run, run_summary, compare_to = get_simple_run_info(tag, id)

    _, text_report, _ = NTEmailReport.getSimpleReport(
        None, db, run, str("%s/db_%s/") % (current_app.old_config.zorgURL,
                                           g.db_name),
        True, True)

    response = make_response(text_report)
    response.mimetype = "text/plain"
    return response

@db_route("/simple/<tag>/<int:id>")
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
    options['show_stddev'] =  bool(request.args.get('show_stddev'))
    options['show_mad'] = bool(request.args.get('show_mad'))
    options['show_all'] = bool(request.args.get('show_all'))
    options['show_all_samples'] = bool(request.args.get('show_all_samples'))
    options['show_sample_counts'] = bool(request.args.get('show_sample_counts'))
    options['show_graphs'] = show_graphs = bool(request.args.get('show_graphs'))
    try:
        num_comparison_runs = int(request.args.get('num_comparison_runs'))
    except:
        num_comparison_runs = 10
    options['num_comparison_runs'] = num_comparison_runs

    _, text_report, html_report = NTEmailReport.getSimpleReport(
        None, db, run, str("%s/db_%s/") % (current_app.old_config.zorgURL,
                                           g.db_name),
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
    from lnt.viewer import GraphUtil
    from lnt.viewer import Util

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
    plots_iter = GraphUtil.get_test_plots(
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
        deltas = [(Util.safediv(p1[1], p0[1]), p0, p1)
                  for p0,p1 in Util.pairs(points)]
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

