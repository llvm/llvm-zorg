from optparse import OptionParser, OptionGroup

from lnt import testing
from lnt.db import perfdb
from lnt.db import perfdbsummary, runinfo
from lnt.db.perfdb import Run, RunInfo, Machine, Sample, Test
from lnt.testing.util.commands import note, warning, error, fatal
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
