"""Implement the command line 'lnt' tool."""

from werkzeug import script

###

kConfigVersion = (0,1,0)
kConfigTemplate = """\
# LNT (aka Zorg) configuration file
#
# Paths are resolved relative to this file.

# The configuration file version.
config_version = %(cfg_version)r

# Name to use for this installation. This appears in web page headers, for
# example.
name = %(name)r

# Path to the LNT root.
zorg = %(zorg_dir)r

# Path to the LNT server.
zorgURL = %(hosturl)r

# Temporary directory, for use by the web app. This must be writable by the user
# the web app runs as.
tmp_dir = %(tmp_dir)r

# Database directory, for easily rerooting the entire set of database. Database
# paths are resolved relative to the config path + this path.
db_dir = %(db_dir)r

# The list of available databases, and their properties. At a minimum, there
# should be a 'default' entry for the default database.
databases = {
    'default' : { 'path' : %(default_db)r,
                  'showNightlytest' : 1 },
    }

# The LNT email configuration.
#
# The 'to' field can be either a single email address, or a list of
# (regular-expression, address) pairs. In the latter form, the machine name of
# the submitted results is matched against the regular expressions to determine
# which email address to use for the results.
nt_emailer = {
    'enabled' : False,
    'host' : None,
    'from' : None,

    # This is a list of (filter-regexp, address) pairs -- it is evaluated in
    # order based on the machine name. This can be used to dispatch different
    # reports to different email address.
    'to' : [(".*", None)],
    }

# Enable automatic restart using the wsgi_restart module; this should be off in
# a production environment.
wsgi_restart = False
"""

kWSGITemplate = """\
#!/usr/bin/env python2.6
# -*- Python -*-

from lnt.viewer import app

application = app.create_app(%(cfg_path)r)

if __name__ == "__main__":
    import werkzeug
    werkzeug.run_simple('localhost', 8000, application)
"""

###

import os
import platform
from lnt.viewer import app

def action_runserver(config='', hostname=('h','localhost'), port=('p',8000),
                     reloader=False, debugger=False, evalex=False,
                     threaded=False, processes=1):
    """Start a new development server."""
    from werkzeug import run_simple

    # Accept paths to config files, or to directories containing 'lnt.cfg'.
    if os.path.isdir(config):
        tmp = os.path.join(config, 'lnt.cfg')
        if os.path.exists(tmp):
            config = tmp

    if not config or not os.path.exists(config):
        raise SystemExit,"error: invalid config: %r" % config

    run_simple(hostname, port, app.create_app(config), reloader, debugger,
               evalex, None, 1, threaded, processes)


def action_create(path='', name='LNT', config='lnt.cfg', wsgi='lnt.wsgi',
                  tmp_dir='lnt_tmp', db_dir='data', default_db='lnt.db',
                  hostname=platform.uname()[1], hostsuffix='perf'):
    """Create an LLVM nightly test installation"""

    if not path:
        raise SystemExit,"error: invalid path: %r" % path

    basepath = os.path.abspath(path)
    if os.path.exists(basepath):
        raise SystemExit,"error: invalid path: %r already exists" % path

    hosturl = "http://%s/%s" % (hostname, hostsuffix)

    # FIXME: Eliminate this variable and just require that LNT be installed.
    import lnt
    zorg_dir = os.path.dirname(lnt.__file__)

    db_dir_path = os.path.join(basepath, db_dir)
    cfg_path = os.path.join(basepath, config)
    db_path = os.path.join(db_dir_path, default_db)
    tmp_path = os.path.join(basepath, tmp_dir)
    wsgi_path = os.path.join(basepath, wsgi)

    os.mkdir(path)
    os.mkdir(db_dir_path)
    os.mkdir(tmp_path)

    cfg_version = kConfigVersion
    cfg_file = open(cfg_path, 'w')
    cfg_file.write(kConfigTemplate % locals())
    cfg_file.close()

    wsgi_file = open(wsgi_path, 'w')
    wsgi_file.write(kWSGITemplate % locals())
    wsgi_file.close()

    from lnt.viewer import PerfDB
    db = PerfDB.PerfDB('sqlite:///' + db_path)
    db.commit()

    print 'created LNT configuration in %r' % basepath
    print '  configuration file: %s' % cfg_path
    print '  WSGI app          : %s' % wsgi_path
    print '  database file     : %s' % db_path
    print '  temporary dir     : %s' % tmp_path
    print '  host URL          : %s' % hosturl
    print
    print 'You can execute:'
    print '  python %s' % wsgi_path
    print 'to test your installation with the builtin server.'
    print
    print 'For production use configure this application to run with any'
    print 'WSGI capable web server. You may need to modify the permissions'
    print 'on the database and temporary file directory to allow writing'
    print 'by the web app.'
    print

def main():
    script.run(globals())

if __name__ == '__main__':
    main()
