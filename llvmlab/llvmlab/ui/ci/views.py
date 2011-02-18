import flask
from flask import abort
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app
ci = flask.Module(__name__, url_prefix='/ci')
print __name__

@ci.route('/')
def dashboard():
    return render_template("dashboard.html")

