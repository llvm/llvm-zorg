import os

import flask
from flask import abort
from flask import current_app
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

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

@frontend.route('/')
@frontend.route('/db_<name>')
@frontend.route('/db_<name>/')
def index(name = None):
    name = name or "default"
    db_info = current_app.old_config.databases.get(name)
    return render_template("index.html", db_name=name, db_info=db_info)

###
# Database Actions

@frontend.route('/browse')
def browse(name = None):
    name = name or "default"
    db_info = current_app.old_config.databases.get(name)
    raise NotImplementedError

@frontend.route('/submitRun')
def submit_run(name = None):
    name = name or "default"
    db_info = current_app.old_config.databases.get(name)
    raise NotImplementedError
