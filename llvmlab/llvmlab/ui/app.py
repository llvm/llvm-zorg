import hashlib
import logging
import logging.handlers
import os
import shutil

import flask

import llvmlab.data
import llvmlab.user
import llvmlab.ci.summary
import llvmlab.ci.status
import llvmlab.ui.ci.views
import llvmlab.ui.filters
import llvmlab.ui.frontend.views

class App(flask.Flask):
    @staticmethod
    def create_standalone(config = None, data = None, status = None,
                          config_path = None):
        if config_path is not None:
            assert config is None

        # Construct the application.
        app = App(__name__)

        # Register additional filters.
        llvmlab.ui.filters.register(app)

        # Load the application configuration.
        app.load_config(config, config_path)

        # Configure error logging.
        install_path = app.config["INSTALL_PATH"]
        if install_path:
            error_log_path = os.path.join(install_path, "error.log")
            handler = logging.FileHandler(error_log_path)
            handler.setLevel(logging.WARNING)
            app.logger.addHandler(handler)
        
        # Configure error emails, if requested.
        if app.config['MAIL_ERRORS']:
            handler = logging.handlers.SMTPHandler(
                app.config['EMAIL_RELAY_SERVER'], app.config['ADMIN_EMAIL'],
                app.config['ADMIN_EMAIL'], 'LLVM Lab Failure')
            handler.setLevel(logging.ERROR)
            app.logger.addHandler(handler)

        # Load the database.
        app.load_data(data)

        # Load the buildbot status.
        app.load_status(status)

        # Load the application routes.
        app.register_module(llvmlab.ui.ci.views.ci)
        app.register_module(llvmlab.ui.frontend.views.frontend)

        # Clear the dashboard summary object.
        app.config.summary = None

        # Load any dashboard plugins.
        plugins_module = app.config["PLUGIN_MODULE"]
        if plugins_module:
            module = __import__(plugins_module, fromlist=['__name__'])
            module.register(app)

        return app

    @staticmethod
    def create_test_instance():
        secret_key = "not so secret"

        # Manually construct a test configuration.
        #
        # FIXME: Would be nice to vet that this matches the sample config.
        config = {
            "ADMIN_LOGIN" : "admin",
            "ADMIN_PASSHASH" : hashlib.sha256(
                "admin" + secret_key).hexdigest(),
            "ADMIN_NAME" : "Administrator",
            "ADMIN_EMAIL" : "admin@example.com",
            "DEBUG" : True,
            "EMAIL_RELAY_SERVER" : "localhost",
            "MAIL_ERRORS" : False,
            "SECRET_KEY" : secret_key,
            "INSTALL_PATH" : None,
            "PLUGIN_MODULE" : None }

        # Construct an empty test database.
        data = llvmlab.data.Data(users = [], machines = [])

        # Construct an empty status file.
        status = llvmlab.ci.status.Status(None, {})

        return App.create_standalone(config, data, status)

    def __init__(self, name):
        super(App, self).__init__(name)
        self.monitor = None

    def load_config(self, config = None, config_path = None):
        if config_path is not None:
            # Load the configuration file.
            self.config.from_pyfile(os.path.abspath(config_path))
        elif config is None:
            # Load the configuration file.
            self.config.from_envvar("LLVMLAB_CONFIG")
        else:
            self.config.update(config)

        # Set the default revision URL.
        self.config.revlink_url = \
            "http://llvm.org/viewvc/llvm-project?view=rev&revision=%s"

        # Set the application secret key.
        self.secret_key = self.config["SECRET_KEY"]

        # Set the debug mode.
        self.debug = self.config["DEBUG"]

    def load_data(self, data = None):
        if data is None:
            install_path = self.config["INSTALL_PATH"]
            data_path = os.path.join(install_path, "lab-data.json")
            data_file = open(data_path, "rb")
            data_object = flask.json.load(data_file)
            data_file.close()

            # Create the internal Data object.
            data = llvmlab.data.Data.fromdata(data_object)

        # Set the admin pseudo-user.
        data.set_admin_user(llvmlab.user.User(
                id = self.config['ADMIN_LOGIN'],
                passhash = self.config['ADMIN_PASSHASH'],
                name = self.config['ADMIN_NAME'],
                email = self.config['ADMIN_EMAIL'],
                htpasswd = None))

        self.config.data = data

    def save_data(self):
        install_path = self.config["INSTALL_PATH"]
        data_path = os.path.join(install_path, "lab-data.json")
        file = open(data_path, 'w')
        flask.json.dump(self.config.data.todata(), file, indent=2)
        print >>file
        file.close()

    def load_status(self, status = None):
        if status is None:
            install_path = self.config["INSTALL_PATH"]
            data_path = os.path.join(install_path, "lab-status.json")
            data_file = open(data_path, "rb")
            data_object = flask.json.load(data_file)
            data_file.close()

            # Create the internal Status object.
            status = llvmlab.ci.status.Status.fromdata(data_object)

        self.config.status = status

    def save_status(self):
        install_path = self.config["INSTALL_PATH"]
        data_path = os.path.join(install_path, "lab-status.json.new")
        file = open(data_path, 'w')
        flask.json.dump(self.config.status.todata(), file, indent=2)
        print >>file
        file.close()

        # Backup the current status.
        backup_path = os.path.join(install_path, "lab-status.json.bak")
        status_path = os.path.join(install_path, "lab-status.json")
        try:
            os.remove(backup_path)
        except:
            pass
        if os.path.exists(status_path):
            shutil.move(status_path, backup_path)
        shutil.move(data_path, status_path)

    def authenticate_login(self, username, password):
        passhash = hashlib.sha256(
            password + self.config["SECRET_KEY"]).hexdigest()
        user = self.config.data.users.get(username)
        return user and passhash == user.passhash

    def get_active_user(self):
        # Lookup the active user.
        id = flask.session.get('active_user', None)
        if id is None:
            return None

        # Return the appropriate user object.
        return self.config.data.users[id]

    def __call__(self, environ, start_response):
        # This works around an annoying property of the werkzeug reloader where
        # we can't tell if we are in the actual web app instance.
        #
        # FIXME: Find a nicer solution.
        if not self.monitor:
            # Spawn the status monitor thread.
            self.monitor = self.config.status.start_monitor(self)

        return flask.Flask.__call__(self, environ, start_response)
