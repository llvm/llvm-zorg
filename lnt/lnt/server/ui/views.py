import flask
from flask import redirect
from flask import render_template
from flask import url_for

frontend = flask.Module(__name__)

@frontend.route('/')
def index():
    return render_template("index.html")

@frontend.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('.static', filename='favicon.ico'))
