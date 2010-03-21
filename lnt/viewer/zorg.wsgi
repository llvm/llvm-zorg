#!/usr/bin/env python2.6
# -*- Python -*-

import sys
import os

def create_publisher():
    import warnings
    warnings.simplefilter("ignore", category=DeprecationWarning)

    # We expect the config file to be adjacent to the absolute path of
    # the cgi script.
    configPath = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          "zorg.cfg")
    configData = {}
    exec open(configPath) in configData

    # Find the zorg installation dir.
    zorgDir = os.path.join(os.path.dirname(configPath),
                           configData.get('zorg', ''))
    if zorgDir and zorgDir not in sys.path:
        sys.path.append(zorgDir)

    # Optionally enable auto-restart.
    if configData.get('wsgiAutoRestart', 'True'):
        from viewer import wsgi_restart
        wsgi_restart.track(configPath)
        wsgi_restart.start()

    from viewer import publisher
    return publisher.create_publisher(configPath, configData, threaded=True)

from quixote.wsgi import QWIP
application = QWIP(create_publisher())

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print "Running test application."
    print "  open http://localhost:8000/"
    httpd = make_server('', 8000, application)
    httpd.serve_forever()
