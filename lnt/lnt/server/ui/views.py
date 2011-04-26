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
from lnt.db import perfdbsummary

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

@db_route("/simple/<tag>/machines/<id>")
def simple_machine(tag, id):
    raise NotImplementedError

@db_route("/simple/<tag>/<id>")
def simple_run(tag, id):
    raise NotImplementedError
