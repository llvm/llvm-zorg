"""Implement the command line 'lnt' tool."""

from werkzeug import script

from lnt.viewer import app

action_runserver = script.make_runserver(app.create_app, use_reloader=True)

def main():
    script.run(globals())

if __name__ == '__main__':
    main()
