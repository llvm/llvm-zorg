import flask
from flask import Flask
import advisor_lib

advisor_blueprint = flask.Blueprint("advisor", __name__)


@advisor_blueprint.route("/upload", methods=["POST"])
def upload():
    advisor_lib.upload_failures(flask.request.json)
    return flask.Response(status=204)


@advisor_blueprint.route("/explain")
def explain():
    return advisor_lib.explain_failures(flask.request.json)


def create_app():
    app = Flask(__name__)
    app.register_blueprint(advisor_blueprint)
    return app
