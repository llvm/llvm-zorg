import os

import flask
from flask import redirect, render_template, url_for

import llvmlab.data
import llvmlab.user

def load_llvmlab_data(app):
    """load_llvmlab_data(app) -> data.Data

    Load the LLVM-Lab data for the given application.
    """

    data_path = app.config["DATA_PATH"]
    data_file = open(data_path, "rb")
    data_object = flask.json.load(data_file)
    data_file.close()

    # Create the internal Data object.
    data = llvmlab.data.Data.fromdata(data_object)

    # Set the admin pseudo-user.
    data.set_admin_user(llvmlab.user.User(
            id = app.config['ADMIN_LOGIN'],
            passhash = app.config['ADMIN_PASSHASH'],
            name = app.config['ADMIN_NAME'],
            email = app.config['ADMIN_EMAIL']))

    return data

###

# Construct the Flask application.
app = flask.Flask(__name__)

# Load the configuration file.
app.config.from_envvar("LLVMLAB_CONFIG")

# Load the LLVM-Lab database.
app.config.data = load_llvmlab_data(app)

###
# Routing

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('static', filename='favicon.ico'))

###

if __name__ == '__main__':
    app.debug = app.config['DEBUG']
    app.run()
