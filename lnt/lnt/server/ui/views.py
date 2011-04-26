import os

import flask
from flask import abort
from flask import current_app
from flask import g
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

@db_route('/submitRun')
def submit_run():
    raise NotImplementedError

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

@db_route("/simple/<tag>")
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

@db_route("/simple/<tag>/<id>")
def simple_run(tag, id):
    db = request.get_db()

    run = db.getRun(id)

    # Get the run summary.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)
    sri = runinfo.SimpleRunInfo(db, ts_summary)

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
    options['show_graphs'] = bool(request.args.get('show_graphs'))
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
