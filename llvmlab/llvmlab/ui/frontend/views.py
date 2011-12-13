import flask
from flask import abort
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app

import llvmlab
import llvmlab.machine

###
# Top-level Information

frontend = flask.Module(__name__, name="frontend")

@frontend.route('/')
def index():
    return render_template("index.html")

@frontend.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('.static', filename='favicon.ico'))

@frontend.route('/admin')
def admin():
    return render_template("admin.html")

###
# Machine Management

@frontend.route('/add_machine', methods=['GET', 'POST'])
def add_machine():
    # Check that we have an active user.
    user = current_app.get_active_user()
    if user is None:
        abort(401)

    # Check that the user has authority to access the lab.
    if not user.has_lab_access():
        abort(401)

    # If this isn't a post request, return the template.
    if request.method != 'POST':
        return render_template("add_machine.html", error=None)

    # Validate the entry data.
    id = request.form['id']
    hostname = request.form['hostname']
    if id in current_app.config.data.machines:
        return render_template("add_machine.html",
                               error='machine "%s" already exists' % id)
    if hostname in set(m.hostname
                       for m in current_app.config.data.machines.values()):
        return render_template("add_machine.html",
                               error='hostname "%s" already used' % hostname)

    # Add the machine record.
    machine = llvmlab.machine.Machine(id, hostname, user.id)
    current_app.config.data.machines[machine.id] = machine
    flask.flash('Added machine "%s"!' % machine.id)

    # Save the application data.
    current_app.save_data()
    flask.flash('Saved data!')

    return redirect(url_for("admin"))

@frontend.route('/machines')
def machines():
    return render_template("machines.html")

###
# User Management

@frontend.route('/users')
def users():
    return render_template("users.html")

@frontend.route('/user/<username>')
def user(username):
    user = current_app.config.data.users.get(username)
    if user is None:
        abort(404)

    return render_template("user.html", user=user)

###
# Session Management

@frontend.route('/login', methods=['GET', 'POST'])
def login():
    # If this isn't a post request, return the login template.
    if request.method != 'POST':
        return render_template("login.html", error=None)

    # Authenticate the user.
    username = request.form['username']
    if not current_app.authenticate_login(username, request.form['password']):
        return render_template("login.html",
                               error="Invalid login")

    # Log the user in.
    session['logged_in'] = True
    session['active_user'] = username
    flask.flash('You were logged in as "%s"!' % username)
    return redirect(url_for("index"))

@frontend.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('active_user', None)
    flask.flash('You were logged out!')
    return redirect(url_for("index"))
