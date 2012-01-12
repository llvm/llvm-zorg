import logging
import logging.handlers
import os
import time

import flask
from flask import current_app
from flask import g
from flask import url_for

import lnt
import lnt.server.config
import lnt.server.ui.filters
import lnt.server.ui.globals
import lnt.server.ui.views
import lnt.server.db.v4db

from lnt.db import perfdbsummary
from lnt.db import perfdb

class RootSlashPatchMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] == '':
            return flask.redirect(environ['SCRIPT_NAME'] + '/')(
                environ, start_response)
        return self.app(environ, start_response)

class Request(flask.Request):
    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)

        self.request_time = time.time()
        self.db = None
        self.db_summary = None
        self.testsuite = None

    def elapsed_time(self):
        return time.time() - self.request_time

    # Utility Methods

    def get_db(self):
        if self.db is None:
            echo = bool(self.args.get('db_log') or self.form.get('db_log'))

            self.db = current_app.old_config.get_database(g.db_name, echo=echo)

            # Enable SQL logging with db_log.
            #
            # FIXME: Conditionalize on an is_production variable.
            if echo:
                import logging, StringIO
                g.db_log = StringIO.StringIO()
                logger = logging.getLogger("sqlalchemy")
                logger.addHandler(logging.StreamHandler(g.db_log))

        return self.db

    def get_testsuite(self):
        if self.testsuite is None:
            testsuites = self.get_db().testsuite
            if g.testsuite_name not in testsuites:
                flask.abort(404)

            self.testsuite = testsuite[g.testsuite_name]

        return self.testsuite

    def get_db_summary(self):
        return current_app.get_db_summary(g.db_name, self.get_db())

class App(flask.Flask):
    @staticmethod
    def create_standalone(config_path):
        # Construct the application.
        app = App(__name__)

        # Register additional filters.
        lnt.server.ui.filters.register(app)

        # Load the application configuration.
        app.load_config(config_path)

        # Load the application routes.
        app.register_module(lnt.server.ui.views.frontend)
                        
        return app

    def __init__(self, name):
        super(App, self).__init__(name)
        self.start_time = time.time()
        self.db_summaries = {}

        # Override the request class.
        self.request_class = Request

        # Store a few global things we want available to templates.
        self.version = lnt.__version__

        # Inject a fix for missing slashes on the root URL (see Flask issue
        # #169).
        self.wsgi_app = RootSlashPatchMiddleware(self.wsgi_app)

    def load_config(self, config_path):
        config_data = {}
        exec open(config_path) in config_data

        self.old_config = lnt.server.config.Config.fromData(
            config_path, config_data)

        self.jinja_env.globals.update(
            app=current_app,
            perfdb=perfdb,
            old_config=self.old_config)

        lnt.server.ui.globals.register(self)

    def get_db_summary(self, db_name, db):
        # FIXME/v3removal: Eliminate this, V4DB style has no need for summary
        # abstraction.
        db_summary = self.db_summaries.get(db_name)
        if db_summary is None or not db_summary.is_up_to_date(db):
            self.db_summaries[db_name] = db_summary = db.get_db_summary()
        return db_summary

