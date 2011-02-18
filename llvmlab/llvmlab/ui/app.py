import flask
from flask import redirect, url_for

# Construct the Flask application.
app = flask.Flask(__name__)

@app.route('/')
def index():
    return "Ceci n'est pas un laboratoire."

@app.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('static', filename='favicon.ico'))

if __name__ == '__main__':
    app.debug = True
    app.run()
