import logging
import logging.handlers
import os
import time

import flask
from flask import current_app

import lnt
import lnt.server.ui.filters
import lnt.server.ui.views

# FIXME: Redesign this.
import lnt.viewer.Config

class Request(flask.Request):
    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)

        self.request_time = time.time()

    def elapsed_time(self):
        return time.time() - self.request_time

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

        # Override the request class.
        self.request_class = Request

        # Store a few global things we want available to templates.
        self.version = lnt.__version__

    def load_config(self, config_path):
        config_data = {}
        exec open(config_path) in config_data

        self.old_config = lnt.viewer.Config.Config.fromData(
            config_path, config_data)

        self.jinja_env.globals.update(
            app=current_app,
            old_config=self.old_config)
