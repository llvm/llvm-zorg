"""Implement the command line 'lnt' tool."""

import os
import sys
from optparse import OptionParser, OptionGroup

import StringIO
from lnt import testing

def action_runserver(name, args):
    """start a new development server"""

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
    """create a new empty LNT sqlite3 database"""

    parser = OptionParser("%%prog %s [options] path" % name)

    (opts, args) = parser.parse_args(args)
    if len(args) != 1:
        parser.error("incorrect number of argments")

    from lnt.viewer import PerfDB

    path, = args
    db = PerfDB.PerfDB('sqlite:///%s' % path)
    db.commit()

def action_checkformat(name, args):
    """check the format of an LNT test report file"""

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
    """run a builtin test application"""

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
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="show verbose test results",
                      action="store_true", default=False)

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
        ServerUtil.submitFile(opts.submit_url, io, True, opts.verbose)
    else:
        # Simulate a submission to retrieve the results report.
        import lnt.viewer
        from lnt.util import ImportData
        import tempfile

        # Save the report to a temporary file.
        tmp = tempfile.NamedTemporaryFile(suffix='.json')
        print >>tmp, report.render()
        tmp.flush()

        # Construct a temporary database and import the result.
        db = lnt.viewer.PerfDB.PerfDB("sqlite:///:memory:")
        result = ImportData.import_and_report(
            None, None, db, tmp.name, 'json', commit = True)
        ImportData.print_report_result(result, sys.stdout, opts.verbose)

        tmp.close()

def action_showtests(name, args):
    """show the available built-in tests"""

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
    """submit a test report to the server"""

    parser = OptionParser("%%prog %s [options] <url> <file>+" % name)
    parser.add_option("", "--commit", dest="commit", type=int,
                      help=("whether the result should be committed "
                            "[%default]"),
                      default=False)
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="show verbose test results",
                      action="store_true", default=False)

    (opts, args) = parser.parse_args(args)
    if len(args) < 2:
        parser.error("incorrect number of argments")

    from lnt.util import ServerUtil
    ServerUtil.submitFiles(args[0], args[1:], opts.commit, opts.verbose)

from lnt.db import perfdbsummary, runinfo
from lnt.viewer import PerfDB
from lnt.viewer.PerfDB import Run, Machine, Sample, Test
from lnt.util import stats

def print_table(rows):
    def format_cell(value):
        if isinstance(value, str):
            return value
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, float):
            return "%.4f" % value
        else:
            return str(value)

    N = len(rows[0])
    for row in rows:
        if len(row) != N:
            raise ValueError,"Invalid table"

        print "\t".join(map(format_cell, row))

def action_report(name, args):
    """performance reporting tools"""

    parser = OptionParser("%%prog %s [options] <db> <machine>" % name)
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="show verbose test results",
                      action="store_true", default=False)

    (opts, args) = parser.parse_args(args)
    if len(args) != 2:
        parser.error("incorrect number of argments")

    path,machine = args
    db = PerfDB.PerfDB('sqlite:///%s' % path)

    # FIXME: Argument
    tag = "nts"

    # FIXME: Optional arguments
    machines = [machine]
    run_orders = [23, 107, 121, 124, 125]
    runs = None

    # Get the run summary which has run ordering information.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)

    # Load the test suite summary.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)

    # First, collect the runs we are going to aggregate over, eagerly limiting
    # by machine name.
    q = db.session.query(Run)
    if machines:
        q = q.join(Machine)
        q = q.filter(Machine.name.in_(machines))
    runs = list(q)

    # Gather the names of all tests across these runs, for more normalized
    # reporting.
    test_names = ts_summary.get_test_names_in_runs(db, [r.id for r in runs])
    test_components = list(set(t.rsplit('.',1)[1] for t in test_names))
    test_base_names = list(set(t.rsplit('.',1)[0] for t in test_names))
    test_components.sort()
    test_base_names.sort()
    test_names = set(test_names)

    # Limit by run orders.
    runs_by_order = {}
    for r in runs:
        run_order = int(r.info["run_order"].value)
        runs_by_order[run_order] = runs_by_order.get(run_order,[]) + [r]

    # Load all the data.
    items = {}
    for test_component in test_components:
        for order in run_orders:
            order_runs = runs_by_order.get(order)
            for name,value in get_test_passes(db, run_summary, ts_summary,
                                              test_component, test_base_names,
                                              order_runs):
                items[(test_component, order, name)] = value

    # Go through and compute global information.
    machine_name = machine.rsplit("-",1)[1]
    if '.' not in machine_name:
        print "%s -O3" % machine_name
    else:
        print machine_name.replace(".", " -")
    print "\t".join(["Run Order"] + map(str, run_orders))
    print
    for test_component in test_components:
        normalized_values = []
        for test_base_name in test_base_names:
            # Ignore tests which never were given.
            test_name = "%s.%s" % (test_base_name, test_component)
            if test_name not in test_names:
                continue

            values = [items.get((test_component, order, test_base_name))
                      for order in run_orders]
            ok_values = [i for i in values
                         if i is not None]
            if ok_values:
                baseline = max(ok_values[0], 0.0001)
            else:
                baseline = None

            normalized = []
            for value in values:
                if value is None:
                    normalized.append(None)
                else:
                    normalized.append(value / baseline)
            normalized_values.append((test_base_name, normalized, baseline))

        # Print summary table.
        print "%s%s Time" % (test_component[0].upper(), test_component[1:])
        table = [("Pct. Pass",
                  "Mean", "Std. Dev.",
                  "Median", "MAD",
                  "Min", "Max",
                  "N (Total)", "N (Perf)")]
        for i,r in enumerate(run_orders):
            num_tests = len(normalized_values)
            num_pass = len([True for nv in normalized_values
                            if nv[1][i] is not None])
            pct_pass = num_pass / float(num_tests)

            # Get non-fail normalized values above a reasonable baseline.
            values = [nv[1][i] for nv in normalized_values
                      if nv[1][i] is not None
                      if nv[2] >= 1.0]
            if not values:
                table.append((pct_pass,
                              "", "", "", "",
                              "", "",
                              num_tests, 0))
                continue

            min_value = min(values)
            max_value = max(values)
            mean = stats.mean(values)
            median = stats.median(values)
            mad = stats.median_absolute_deviation(values)
            sigma = stats.standard_deviation(values)
            table.append((pct_pass,
                          mean, sigma, median, mad,
                          min_value, max_value,
                          num_tests, len(values)))

        print_table(zip(*table))
        print

def get_test_passes(db, run_summary, ts_summary,
                    test_component, test_base_names, runs):
    if not runs:
        return

    sri = runinfo.SimpleRunInfo(db, ts_summary)
    sri._load_samples_for_runs([r.id for r in runs])

    run_status_info = [(r, run_summary.get_run_status_kind(db, r.id))
                       for r in runs]

    pset = ()
    for test_base_name in test_base_names:
        test_name = "%s.%s" % (test_base_name, test_component)
        test_id = ts_summary.test_id_map.get((test_name, pset))
        if test_id is None:
            continue

        run_values = sum((sri.sample_map.get((run.id, test_id))
                          for run in runs
                          if (run.id, test_id) in sri.sample_map), [])
        # Ignore tests that weren't reported in some runs (e.g., -disable-cxx).
        if not run_values:
            continue

        # Find the test status, treat any non-determinism as a FAIL.
        run_status = list(set([sri.get_test_status_in_run(
                r.id, rsk, test_name, pset)
                      for (r,rsk) in run_status_info]))
        if len(run_status) == 1:
            status_kind = run_status[0]
        else:
            status_kind = testing.FAIL

        # Ignore failing methods.
        if status_kind == testing.FAIL:
            continue

        value = min(run_values)
        yield (test_base_name, value)


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
