import os

import flask
from flask import redirect, render_template, url_for

# Construct the Flask application.
app = flask.Flask(__name__)

# Load the configuration file.
app.config.from_envvar("LLVMLAB_CONFIG")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('static', filename='favicon.ico'))

if __name__ == '__main__':
    app.debug = app.config['DEBUG']
    app.run()
