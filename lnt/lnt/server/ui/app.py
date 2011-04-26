import logging
import logging.handlers
import os

import flask

import lnt.server.ui.views

# FIXME: Redesign this.
import lnt.viewer.Config

class App(flask.Flask):
    @staticmethod
    def create_standalone(config_path):
        # Construct the application.
        app = App(__name__)

        # Load the application configuration.
        app.load_config(config_path)

        # Load the application routes.
        app.register_module(lnt.server.ui.views.frontend)
                        
        return app

    def __init__(self, name):
        super(App, self).__init__(name)

    def load_config(self, config_path):
        config_data = {}
        exec open(config_path) in config_data

        self.old_config = lnt.viewer.Config.Config.fromData(
            config_path, config_data)
