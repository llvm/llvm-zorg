import os
import sys

def create_publisher(configPath):
    import warnings
    warnings.simplefilter("ignore", category=DeprecationWarning)

    configData = {}
    exec open(configPath) in configData

    # Optionally enable auto-restart.
    if configData.get('wsgi_restart', False):
        from lnt.viewer import wsgi_restart
        wsgi_restart.track(configPath)
        wsgi_restart.start()

    from lnt.viewer import publisher
    return publisher.create_publisher(configPath, configData, threaded=True)

def create_app(cfg_path=None):
    import quixote.wsgi
    return quixote.wsgi.QWIP(create_publisher(cfg_path))
