from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Ceci n'est pas un laboratoire."

if __name__ == '__main__':
    app.run()
