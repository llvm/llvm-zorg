import flask
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app
from flask import Module
ui = Module('app.py')

@ui.route('/')
def index():
    return render_template("index.html")

@ui.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('static', filename='favicon.ico'))

@ui.route('/users')
def users():
    return render_template("users.html")

@ui.route('/login', methods=['GET', 'POST'])
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

@ui.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('active_user', None)
    flask.flash('You were logged out!')
    return redirect(url_for("index"))
