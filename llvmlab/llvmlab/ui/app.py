import hashlib
import os

import flask

import llvmlab.data
import llvmlab.user
import llvmlab.ui.views

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

# Load the application routes.
app.register_module(llvmlab.ui.views.ui)

###

if __name__ == '__main__':
    app.debug = app.config['DEBUG']
    app.run()
