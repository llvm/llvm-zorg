"""Implement the command line 'lnt' tool."""

import os
import sys
from optparse import OptionParser, OptionGroup

import StringIO

def action_runserver(name, args):
    """start a new development server."""

    parser = OptionParser("%%prog %s [options] [<path|config file>]" % name)
    parser.add_option("", "--hostname", dest="hostname", type=str,
                      help="host interface to use [%default]",
                      default='localhost')
    parser.add_option("", "--port", dest="port", type=int, metavar="N",
                      help="local port to use [%default]", default=8000)
    parser.add_option("", "--reloader", dest="reloader", default=False,
                      action="store_true", help="use WSGI reload monitor")
    parser.add_option("", "--debugger", dest="debugger", default=False,
                      action="store_true", help="use WSGI debugger")
    parser.add_option("", "--threaded", dest="threaded", default=False,
                      action="store_true", help="use a threaded server")
    parser.add_option("", "--processes", dest="processes", type=int,
                      metavar="N", help="number of processes to use [%default]",
                      default=1)

    (opts, args) = parser.parse_args(args)
    if len(args) != 1:
        parser.error("invalid number of arguments")

    config, = args

    # Accept paths to config files, or to directories containing 'lnt.cfg'.
    if os.path.isdir(config):
        tmp = os.path.join(config, 'lnt.cfg')
        if os.path.exists(tmp):
            config = tmp

    if not config or not os.path.exists(config):
        raise SystemExit,"error: invalid config: %r" % config

    from werkzeug import run_simple
    from lnt.viewer import app
    run_simple(opts.hostname, opts.port, app.create_app(config),
               opts.reloader, opts.debugger,
               False, None, 1, opts.threaded, opts.processes)

from create import action_create
from convert import action_convert
from import_data import action_import

# FIXME: We really just need a web admin interface. That makes this kind of
# stuff much easier to work with, and also simplifies dealing with things like
# file permissions.
def action_createdb(name, args):
    """create a new empty LNT sqlite3 database."""

    parser = OptionParser("%%prog %s [options] path" % name)

    (opts, args) = parser.parse_args(args)
    if len(args) != 1:
        parser.error("incorrect number of argments")

    from lnt.viewer import PerfDB

    path, = args
    db = PerfDB.PerfDB('sqlite:///%s' % path)
    db.commit()

def action_checkformat(name, args):
    """check the format of an LNT test report file."""

    parser = OptionParser("%%prog %s [options] files" % name)

    (opts, args) = parser.parse_args(args)
    if len(args) > 1:
        parser.error("incorrect number of argments")

    if len(args) == 0:
        input = '-'
    else:
        input, = args

    if input == '-':
        input = StringIO.StringIO(sys.stdin.read())

    from lnt import formats
    from lnt.viewer import PerfDB

    db = PerfDB.PerfDB('sqlite:///:memory:')

    data = formats.read_any(input, '<auto>')
    PerfDB.importDataFromDict(db, data)

def action_runtest(name, args):
    parser = OptionParser("%%prog %s test-name [options]" % name)
    parser.disable_interspersed_args()
    parser.add_option("", "--submit", dest="submit_url", metavar="URL",
                      help=("autosubmit the test result to the given server "
                            "[%default]"),
                      type=str, default=None)
    parser.add_option("", "--commit", dest="commit",
                      help=("whether the autosubmit result should be committed "
                            "[%default]"),
                      type=int, default=True)

    (opts, args) = parser.parse_args(args)
    if len(args) < 1:
        parser.error("incorrect number of argments")

    test_name,args = args[0],args[1:]

    import lnt.tests
    try:
        test_instance = lnt.tests.get_test_instance(test_name)
    except KeyError:
        parser.error('invalid test name %r' % test_name)

    report = test_instance.run_test('%s %s' % (name, test_name), args)

    if opts.submit_url is not None:
        if report is None:
            raise SystemExit,"error: report generation failed"

        from lnt.util import ServerUtil
        io = StringIO.StringIO(report.render(indent=None))
        ServerUtil.submitFile(opts.submit_url, io, True)

def action_showtests(name, args):
    """show the available built-in tests."""

    parser = OptionParser("%%prog %s" % name)
    (opts, args) = parser.parse_args(args)
    if len(args) != 0:
        parser.error("incorrect number of argments")

    import lnt.tests

    print 'Available tests:'
    test_names = lnt.tests.get_test_names()
    max_name = max(map(len, test_names))
    for name in test_names:
        print '  %-*s - %s' % (max_name, name,
                               lnt.tests.get_test_description(name))

def action_submit(name, args):
    """submit a test report to the server."""

    parser = OptionParser("%%prog %s [options] <url> <file>+" % name)
    parser.add_option("", "--commit", dest="commit", type=int,
                      default=False)

    (opts, args) = parser.parse_args(args)
    if len(args) < 2:
        parser.error("incorrect number of argments")

    from lnt.util import ServerUtil
    ServerUtil.submitFiles(args[0], args[1:], opts.commit)

###

commands = dict((name[7:], f) for name,f in locals().items()
                if name.startswith('action_'))

def usage():
    print >>sys.stderr, "Usage: %s command [options]" % (
        os.path.basename(sys.argv[0]))
    print >>sys.stderr
    print >>sys.stderr, "Available commands:"
    cmds_width = max(map(len, commands))
    for name,func in sorted(commands.items()):
        print >>sys.stderr, "  %-*s - %s" % (cmds_width, name, func.__doc__)
    sys.exit(1)

def main():
    import sys

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        if len(sys.argv) >= 2:
            print >>sys.stderr,"error: invalid command %r\n" % sys.argv[1]

        usage()

    cmd = sys.argv[1]
    commands[cmd](cmd, sys.argv[2:])

if __name__ == '__main__':
    main()
