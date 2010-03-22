import os
import sys

def create_publisher(configPath):
    import warnings
    warnings.simplefilter("ignore", category=DeprecationWarning)

    configData = {}
    exec open(configPath) in configData

    # Find the zorg installation dir.
    zorgDir = os.path.join(os.path.dirname(configPath),
                           configData.get('zorg', ''))
    if zorgDir and zorgDir not in sys.path:
        sys.path.append(zorgDir)

    # Optionally enable auto-restart.
    if configData.get('wsgi_restart', False):
        from viewer import wsgi_restart
        wsgi_restart.track(configPath)
        wsgi_restart.start()

    from viewer import publisher
    return publisher.create_publisher(configPath, configData, threaded=True)

def create_app(cfg_path=None):
    import quixote.wsgi
    return quixote.wsgi.QWIP(create_publisher(cfg_path))
