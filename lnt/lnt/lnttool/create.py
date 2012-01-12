import os
import platform
import sys

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

# Path to the LNT server. This is required for use in emails where we need to
# provide an absolute URL to the server.
zorgURL = %(hosturl)r

# Temporary directory, for use by the web app. This must be writable by the user
# the web app runs as.
tmp_dir = %(tmp_dir)r

# Database directory, for easily rerooting the entire set of databases. Database
# paths are resolved relative to the config path + this path.
db_dir = %(db_dir)r

# The list of available databases, and their properties. At a minimum, there
# should be a 'default' entry for the default database.
databases = {
    'default' : { 'path' : %(default_db)r,
                  'showGeneral' : 1,
                  'showNightlytest' : 1,
                  'showSimple' : 1,
                  'db_version' : %(default_db_version)r },
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
#!%(python_executable)s
# -*- Python -*-

import lnt.server.ui.app

application = lnt.server.ui.app.App.create_standalone(
  %(cfg_path)r)

if __name__ == "__main__":
    import werkzeug
    werkzeug.run_simple('localhost', 8000, application)
"""

###

import lnt.db.perfdb
import lnt.testing

def _create_v4_nt_database(db_path):
    from lnt.server.db import v4db, testsuite

    # Create the initial database.
    db = lnt.server.db.v4db.V4DB('sqlite:///' + db_path)
    db.commit()

    # Create an NT compatible test suite, automatically.
    ts = testsuite.TestSuite("nts", "NT")

    # Define the default status kinds.
    #
    # FIXME: This should probably be done by V4DB.
    db.add(testsuite.StatusKind(lnt.testing.PASS, "PASS"))
    db.add(testsuite.StatusKind(lnt.testing.FAIL, "FAIL"))
    db.add(testsuite.StatusKind(lnt.testing.XFAIL, "XFAIL"))

    # Define the default sample types.
    #
    # FIXME: This should probably be done by V4DB.
    real_sample_type = testsuite.SampleType("Real")
    status_sample_type = testsuite.SampleType("Status")

    # Promote the natural information produced by 'runtest nt' to fields.
    ts.machine_fields.append(testsuite.MachineField("hardware", "hardware"))
    ts.machine_fields.append(testsuite.MachineField("os", "os"))

    # The only reliable order currently is the "run_order" field. We will want
    # to revise this over time.
    ts.order_fields.append(testsuite.OrderField("llvm_project_revision",
                                                "run_order", 0))

    # We are only interested in simple runs, so we expect exactly four fields
    # per test.
    compile_status = testsuite.SampleField(
            "compile_status", status_sample_type, ".compile.status")
    compile_time = testsuite.SampleField(
        "compile_time", real_sample_type, ".compile",
        status_field = compile_status)
    exec_status = testsuite.SampleField(
            "execution_status", status_sample_type, ".exec.status")
    exec_time = testsuite.SampleField(
            "execution_time", real_sample_type, ".exec",
            status_field = exec_status)
    ts.sample_fields.append(compile_time)
    ts.sample_fields.append(compile_status)
    ts.sample_fields.append(exec_time)
    ts.sample_fields.append(exec_status)

    db.add(ts)
    db.commit()

    # Finally, ensure the tables for the test suite we just defined are
    # constructed.
    ts_db = db.testsuite['nts']

def action_create(name, args):
    """create an LLVM nightly test installation"""

    from optparse import OptionParser, OptionGroup
    parser = OptionParser("%%prog %s [options] <path>" % name)
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
    parser.add_option("", "--use-v4", dest="use_v4",
                      help="use the v0.4 database schema [%default]",
                      action="store_true", default=False)

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
    default_db_version = "0.3"
    if opts.use_v4:
        default_db_version = "0.4"
    else:
        default_db_version = "0.3"

    basepath = os.path.abspath(path)
    if os.path.exists(basepath):
        raise SystemExit,"error: invalid path: %r already exists" % path

    hosturl = "http://%s/%s" % (hostname, hostsuffix)

    python_executable = sys.executable
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
    os.chmod(wsgi_path, 0755)

    if opts.use_v4:
        _create_v4_nt_database(db_path)
    else:
        db = lnt.db.perfdb.PerfDB('sqlite:///' + db_path)
        db.commit()

    print 'created LNT configuration in %r' % basepath
    print '  configuration file: %s' % cfg_path
    print '  WSGI app          : %s' % wsgi_path
    print '  database file     : %s' % db_path
    print '  temporary dir     : %s' % tmp_path
    print '  host URL          : %s' % hosturl
    print
    print 'You can execute:'
    print '  %s' % wsgi_path
    print 'to test your installation with the builtin server.'
    print
    print 'For production use configure this application to run with any'
    print 'WSGI capable web server. You may need to modify the permissions'
    print 'on the database and temporary file directory to allow writing'
    print 'by the web app.'
    print
