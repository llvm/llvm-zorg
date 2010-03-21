#!/usr/bin/env python2.6
# -*- Python -*-

import app

application = app.create_app()

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print "Running test application."
    print "  open http://localhost:8000/"
    httpd = make_server('', 8000, application)
    httpd.serve_forever()
