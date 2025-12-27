import sqlite3

import flask
from flask import Flask

import advisor_lib
import git_utils

advisor_blueprint = flask.Blueprint("advisor", __name__)


def _get_db():
    if "db" not in flask.g:
        flask.g.db = advisor_lib.setup_db(flask.current_app.config["DB_PATH"])
    return flask.g.db


def _close_db(exception):
    db = flask.g.pop("db", None)
    if db is not None:
        db.close()


@advisor_blueprint.route("/upload", methods=["POST"])
def upload():
    advisor_lib.upload_failures(
        flask.request.json, _get_db(), flask.current_app.config["REPO_PATH"]
    )
    return flask.Response(status=204)


@advisor_blueprint.route("/explain")
def explain():
    return advisor_lib.explain_failures(
        flask.request.json,
        flask.current_app.config["REPO_PATH"],
        _get_db(),
        flask.current_app.config["DEBUG_FOLDER"],
    )


<<<<<<< HEAD
@advisor_blueprint.route("/flaky_tests")
def flaky_tests():
    return advisor_lib.get_flaky_tests(_get_db())


def create_app(db_path: str, repository_path: str):
=======
def create_app(db_path: str, repository_path: str, debug_folder: str):
>>>>>>> 932f0fe5 ([CI] Add debug logging for premerge advisor explanations)
    app = Flask(__name__)
    app.register_blueprint(advisor_blueprint)
    app.teardown_appcontext(_close_db)
    git_utils.clone_repository_if_not_present(repository_path)
    with app.app_context():
        app.config["DB_PATH"] = db_path
        app.config["REPO_PATH"] = repository_path
        app.config["DEBUG_FOLDER"] = debug_folder
    return app
