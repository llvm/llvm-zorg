import hashlib
import os

import flask

import llvmlab.data
import llvmlab.user
from llvmlab.ui.ci.views import ci as ci_views
from llvmlab.ui.frontend.views import frontend as frontend_views

class App(flask.Flask):
    @staticmethod
    def create_standalone(config = None, data = None, config_path = None):
        if config_path is not None:
            assert config is None
            assert data is None

        # Construct the application.
        app = App(__name__)

        # Load the application configuration.
        app.load_config(config, config_path)

        # Load the database.
        app.load_data(data)

        # Load the application routes.
        app.register_module(ci_views)
        app.register_module(frontend_views)

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
            "SECRET_KEY" : secret_key,
            "DATA_PATH" : None }

        # Construct an empty test database.
        data = llvmlab.data.Data(users = [])

        return App.create_standalone(config, data)

    def __init__(self, name):
        super(App, self).__init__(name)

    def load_config(self, config = None, config_path = None):
        if config_path is not None:
            # Load the configuration file.
            self.config.from_pyfile(os.path.abspath(config_path))
        elif config is None:
            # Load the configuration file.
            self.config.from_envvar("LLVMLAB_CONFIG")
        else:
            self.config.update(config)

        # Set the application secret key.
        self.secret_key = self.config["SECRET_KEY"]

        # Set the debug mode.
        self.debug = self.config["DEBUG"]

    def load_data(self, data = None):
        if data is None:
            data_path = self.config["DATA_PATH"]
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
        file = open(self.config["DATA_PATH"], 'w')
        flask.json.dump(self.config.data.todata(), file, indent=2)
        print >>file
        file.close()

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
