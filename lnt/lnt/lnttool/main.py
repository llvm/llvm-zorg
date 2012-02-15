"""Implement the command line 'lnt' tool."""

import os
import sys
from optparse import OptionParser, OptionGroup

import StringIO
import lnt
from lnt import testing
from lnt.db import perfdb
from lnt.testing.util.commands import note, warning, error, fatal

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

    import lnt.server.ui.app
    instance = lnt.server.ui.app.App.create_standalone(
        config_path = config)
    if opts.debugger:
        instance.debug = True
    instance.run(opts.hostname, opts.port,
                 use_reloader = opts.reloader,
                 use_debugger = opts.debugger,
                 threaded = opts.threaded,
                 processes = opts.processes)

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

    path, = args
    db = perfdb.PerfDB('sqlite:///%s' % path)
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

    db = perfdb.PerfDB('sqlite:///:memory:')

    data = formats.read_any(input, '<auto>')
    perfdb.importDataFromDict(db, data)

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
        from lnt.util import ImportData
        import tempfile

        # Save the report to a temporary file.
        tmp = tempfile.NamedTemporaryFile(suffix='.json')
        print >>tmp, report.render()
        tmp.flush()

        # Construct a temporary database and import the result.
        db = lnt.db.perfdb.PerfDB("sqlite:///:memory:")
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
from lnt.db.perfdb import Run, RunInfo, Machine, Sample, Test
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

    parser = OptionParser("""\
%%prog %s [options] <db>""" % name)
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="show verbose test results",
                      action="store_true", default=False)
    parser.add_option("", "--run-order", dest="run_order",
                      help="run order to select on",
                      type=int, default=None)
    parser.add_option("", "--arch", dest="arch",
                      help="arch field to select on",
                      type=str, default=None)
    parser.add_option("", "--optflags", dest="optflags",
                      help="optimization flags field to select on",
                      type=str, default=None)
    parser.add_option("", "--machine", dest="machine_name",
                      help="machine name to select on",
                      type=str, default=None)

    (opts, args) = parser.parse_args(args)
    if len(args) != 1:
        parser.error("incorrect number of argments")

    path, = args
    db = perfdb.PerfDB('sqlite:///%s' % path)
    tag = 'nts'

    if opts.run_order is None:
        parser.error("--run-order is required")

    # First, find all runs with the desired order.
    q = db.session.query(Run).\
        join(RunInfo).\
        order_by(Run.start_time.desc()).\
        filter(RunInfo.key == "run_order").\
        filter(RunInfo.value == "% 7d" % opts.run_order)
    matching_runs = list(q)

    # Try to help user if nothing was found.
    if not matching_runs:
        available_orders = set(
            db.session.query(RunInfo.value).\
                filter(RunInfo.key == "run_order"))
        fatal("no runs found matching --run-order %d, available orders: %s" % (
                opts.run_order, str(sorted(int(x)
                                           for x, in available_orders))))

    # Match based on the machine name, if given.
    if opts.machine_name:
        selected = [r for r in matching_runs
                    if r.machine.name == opts.machine_name]
        if not selected:
            available_names = set(r.machine.name
                                  for r in matching_runs)
            fatal(
                "no runs found matching --machine %s, available names: [%s]" %(
                    opts.machine_name, ", ".join(sorted(available_names))))
        matching_runs = selected

    # Match based on the architecture, if given.
    if opts.arch:
        selected = [r for r in matching_runs
                    if 'ARCH' in r.info
                    if r.info['ARCH'].value == opts.arch]
        if not selected:
            available_archs = set(r.info['ARCH'].value
                                  for r in matching_runs
                                  if 'ARCH' in r.info)
            fatal("no runs found matching --arch %s, available archs: [%s]" % (
                    opts.arch, ", ".join(sorted(available_archs))))
        matching_runs = selected

    # Match based on the optflags, if given.
    if opts.optflags:
        selected = [r for r in matching_runs
                    if 'OPTFLAGS' in r.info
                    if r.info['OPTFLAGS'].value == opts.optflags]
        if not selected:
            available_flags = set(r.info['OPTFLAGS'].value
                                  for r in matching_runs
                                  if 'OPTFLAGS' in r.info)
            fatal(
                "no runs found matching --optflags %s, available flags: [%s]" %(
                    opts.optflags, ", ".join(sorted(available_flags))))
        matching_runs = selected

    # Inform the user of the final list of selected runs.
    note("selection arguments resulted in %d runs" % (len(matching_runs),))
    for run in matching_runs:
        note("Run: % 5d, Start Time: %s, Machine: %s:%d" % (
            run.id, run.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            run.machine.name, run.machine.number))

    # Take only the first matched run, for now. This will be the latest, by the
    # original ordering clause.
    note("selecting newest run for reporting...")
    matching_runs = [matching_runs[0]]

    # Inform the user of the final list of selected runs.
    note("reporting over %d total runs" % (len(matching_runs),))
    for run in matching_runs:
        note("Run: % 5d, Start Time: %s, Machine: %s:%d" % (
            run.id, run.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            run.machine.name, run.machine.number))

    # Get the run summary which has run ordering information.
    run_summary = perfdbsummary.SimpleSuiteRunSummary.get_summary(db, tag)

    # Load the test suite summary.
    ts_summary = perfdbsummary.get_simple_suite_summary(db, tag)

    # Gather the names of all tests across these runs, for more normalized
    # reporting.
    test_names = ts_summary.get_test_names_in_runs(
        db, [r.id for r in matching_runs])
    test_components = sorted(set(t.rsplit('.',1)[1] for t in test_names))
    test_base_names = sorted(set(t.rsplit('.',1)[0] for t in test_names))

    # Load all the data.
    items = {}
    for test_component in test_components:
        for name,value in get_test_passes(db, run_summary, ts_summary,
                                          test_component, test_base_names,
                                          matching_runs):
            items[(test_component, name)] = value

    # Dump the results.
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
        "Test", "Mean Compile Time", "Mean Execution Time",
        "Std.Dev. Compile Time", "Std.Dev. Execution Time",
        "Num. Compile Time Samples", "Num. Execution Time Samples")
    for name in test_base_names:
        compile_results = items.get(('compile', name), [])
        exec_results = items.get(('exec', name), [])
        if compile_results:
            compile_value = "%.4f" % stats.mean(compile_results)
            compile_stddev = "%.4f" % stats.standard_deviation(compile_results)
        else:
            compile_value = compile_stddev = ""
        if exec_results:
            exec_value = "%.4f" % stats.mean(exec_results)
            exec_stddev = "%.4f" % stats.standard_deviation(exec_results)
        else:
            exec_value = exec_stddev = ""
        print "%s\t%s\t%s\t%s\t%s\t%d\t%d" % (
            name, compile_value, exec_value,
            compile_stddev, exec_stddev,
            len(compile_results), len(exec_results))

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

        yield (test_base_name, run_values)


###

commands = dict((name[7:], f) for name,f in locals().items()
                if name.startswith('action_'))
def main():
    cmds_width = max(map(len, commands))
    parser = OptionParser("""\
%%prog [options] <command> ... arguments ...

Available commands:
%s""" % ("\n".join("  %-*s - %s" % (cmds_width, name, func.__doc__)
                   for name, func in sorted(commands.items()))),
                          version = "lnt version %s" % lnt.__version__)
    parser.disable_interspersed_args()
    (opts, args) = parser.parse_args()

    if not args:
        parser.print_usage()
        return

    cmd = args[0]
    if cmd not in commands:
        parser.error("invalid command: %r" % cmd)

    commands[cmd](cmd, args[1:])

if __name__ == '__main__':
    main()
