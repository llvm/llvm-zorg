import os
import platform

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

def action_create(name, args):
    """create an LLVM nightly test installation"""

    from optparse import OptionParser, OptionGroup
    parser = OptionParser("%%prog %s [options] [<path|config file>]" % name)
    parser.add_option("", "--name", dest="name", default="LNT",
                      help="name to use for the installation [%default]")
    parser.add_option("", "--config", dest="config", default="lnt.cfg",
                      help="name of the LNT config file [%default]")
    parser.add_option("", "--wsgi", dest="wsgi",  default="lnt.wsgi",
                      help="name of the WSGI app  [%default]")
    parser.add_option("", "--tmp-dir", dest="tmp_dir", default="lnt_tmp",
                      help="name of the temp file directory [%default]")
    parser.add_option("", "--db-dir", dest="db_dir", default="data",
                      help="name of the directory to hold databases")
    parser.add_option("", "--default-db", dest="default_db", default="lnt.db",
                      help="name for the default db [%default]", metavar="NAME")
    parser.add_option("", "--hostname", dest="hostname",
                      default=platform.uname()[1],
                      help="host name of the server [%default]", metavar="NAME")
    parser.add_option("", "--hostsuffix", dest="hostsuffix", default="perf",
                      help="suffix at which WSGI app lives [%default]",
                      metavar="NAME")

    (opts, args) = parser.parse_args(args)
    if len(args) != 1:
        parser.error("invalid number of arguments")

    path, = args

    name = opts.name
    config = opts.config
    wsgi = opts.wsgi
    tmp_dir = opts.tmp_dir
    db_dir = opts.db_dir
    default_db = opts.default_db
    hostname = opts.hostname
    hostsuffix = opts.hostsuffix

    basepath = os.path.abspath(path)
    if os.path.exists(basepath):
        raise SystemExit,"error: invalid path: %r already exists" % path

    hosturl = "http://%s/%s" % (hostname, hostsuffix)

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
