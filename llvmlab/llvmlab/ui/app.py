import hashlib
import os

import flask
from flask import redirect, render_template, request, session, url_for

import llvmlab.data
import llvmlab.user

class LLVMLabApp(flask.Flask):
    def __init__(self, name):
        super(LLVMLabApp, self).__init__(name)

    def load_config(self):
        # Load the configuration file.
        app.config.from_envvar("LLVMLAB_CONFIG")

        # Set the application secret key.
        app.secret_key = app.config["SECRET_KEY"]

    def load_data(self):
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

        self.config.data = data

    def authenticate_login(self, username, password):
        passhash = hashlib.sha256(
            password + app.config["SECRET_KEY"]).hexdigest()
        user = app.config.data.users.get(username)
        return user and passhash == user.passhash

###

# Construct the Flask application.
app = LLVMLabApp(__name__)

# Load the application configuration.
app.load_config()

# Load the LLVM-Lab database.
app.load_data()

###
# Routing

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('static', filename='favicon.ico'))

@app.route('/users')
def users():
    return render_template("users.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If this isn't a post request, return the login template.
    if request.method != 'POST':
        return render_template("login.html", error=None)

    # Authenticate the user.
    username = request.form['username']
    if not app.authenticate_login(username, request.form['password']):
        return render_template("login.html",
                               error="Invalid login")

    # Log the user in.
    session['logged_in'] = True
    session['active_user'] = username
    flask.flash('You were logged in as "%s"!' % username)
    return redirect(url_for("index"))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('active_user', None)
    flask.flash('You were logged out!')
    return redirect(url_for("index"))

###

if __name__ == '__main__':
    app.debug = app.config['DEBUG']
    app.run()
