"""
Module for defining additional Jinja global functions.
"""

import flask

def db_url_for(*args, **kwargs):
    """
    Like url_for, but handles automatically providing the db_name argument.
    """
    return flask.url_for(*args, db_name=flask.g.db_name, **kwargs)

def v4_url_for(*args, **kwargs):
    """
    Like url_for, but handles automatically providing the db_name and
    testsuite_name arguments.
    """
    return flask.url_for(*args, db_name=flask.g.db_name,
                          testsuite_name=flask.g.testsuite_name, **kwargs)

def register(app):
    app.jinja_env.globals.update(
        db_url_for=db_url_for,
        v4_url_for=v4_url_for)
