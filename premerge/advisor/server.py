import flask
from flask import Flask

import advisor_lib

app = Flask(__name__)


@app.route("/upload", methods=["POST"])
def upload():
    advisor_lib.upload_failures(flask.request.json)
    return flask.Response(status=204)


@app.route("/explain")
def explain():
    return advisor_lib.explain_failures(flask.request.json)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
