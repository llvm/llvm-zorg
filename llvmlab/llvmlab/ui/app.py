import hashlib
import os

import flask

import llvmlab.data
import llvmlab.user
import llvmlab.ui.views

class App(flask.Flask):
    @staticmethod
    def create_standalone():
        # Construct the application.
        app = App(__name__)

        # Load the application configuration.
        app.load_config()

        # Load the database.
        app.load_data()

        # Load the application routes.
        app.register_module(llvmlab.ui.views.ui)

        return app

    def __init__(self, name):
        super(App, self).__init__(name)

    def load_config(self):
        # Load the configuration file.
        self.config.from_envvar("LLVMLAB_CONFIG")

        # Set the application secret key.
        self.secret_key = self.config["SECRET_KEY"]

        # Set the debug mode.
        self.debug = self.config["DEBUG"]

    def load_data(self):
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
                email = self.config['ADMIN_EMAIL']))

        self.config.data = data

    def authenticate_login(self, username, password):
        passhash = hashlib.sha256(
            password + self.config["SECRET_KEY"]).hexdigest()
        user = self.config.data.users.get(username)
        return user and passhash == user.passhash

if __name__ == '__main__':
    app = App.create_standalone()
    app.run()
