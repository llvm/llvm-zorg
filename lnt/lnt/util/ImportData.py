import os, re, time

import lnt.db.perfdb
from lnt import formats
from lnt.db import runinfo
from lnt.util import NTEmailReport

def import_and_report(config, db_name, db, file, format, commit=False,
                      show_sample_count=False, disable_email=False):
    """
    import_and_report(config, db_name, db, file, format,
                      [commit], [show_sample_count],
                      [disable_email]) -> ... object ...

    Import a test data file into an LNT server and generate a test report. On
    success, run is the newly imported run. Note that success is uneffected by
    the value of commit, this merely changes whether the run (on success) is
    committed to the database.

    The result object is a dictionary containing information on the imported run
    and its comparison to the previous run.
    """
    numMachines = db.getNumMachines()
    numRuns = db.getNumRuns()
    numTests = db.getNumTests()

    # If the database gets fragmented, count(*) in SQLite can get really slow!?!
    if show_sample_count:
        numSamples = db.getNumSamples()

    result = {}
    result['success'] = False
    result['error'] = None
    result['import_file'] = file

    startTime = time.time()
    try:
        data = formats.read_any(file, format)
    except KeyboardInterrupt:
        raise
    except:
        import traceback
        result['error'] = "load failure: %s" % traceback.format_exc()
        return result

    result['load_time'] = time.time() - startTime

    # Find the email address for this machine's results.
    toAddress = email_config = None
    if config and not disable_email:
        email_config = config.databases[db_name].email_config
        if email_config.enabled:
            # Find the machine name.
            machineName = str(data.get('Machine',{}).get('Name'))
            toAddress = email_config.get_to_address(machineName)
            if toAddress is None:
                result['error'] = ("unable to match machine name "
                                   "for test results email address!")
                return result

    importStartTime = time.time()
    try:
        success,run = db.importDataFromDict(data)
    except KeyboardInterrupt:
        raise
    except:
        import traceback
        result['error'] = "import failure: %s" % traceback.format_exc()
        return result

    # If the import succeeded, save the import path.
    run.imported_from = file

    result['import_time'] = time.time() - importStartTime
    if not success:
        # Record the original run this is a duplicate of.
        result['original_run'] = run.id

    reportStartTime = time.time()
    result['report_to_address'] = toAddress
    if config:
        report_url = "%s/db_%s/" % (config.zorgURL, db_name)
    else:
        report_url = 'localhost'
    NTEmailReport.emailReport(result, db, run, report_url,
                              email_config, toAddress, success, commit)

    result['added_machines'] = db.getNumMachines() - numMachines
    result['added_runs'] = db.getNumRuns() - numRuns
    result['added_tests'] = db.getNumTests() - numTests
    if show_sample_count:
        result['added_samples'] = db.getNumSamples() - numSamples

    result['committed'] = commit
    if commit:
        db.commit()
    else:
        db.rollback()

    result['report_time'] = time.time() - importStartTime
    result['total_time'] = time.time() - startTime

    # If this database has a shadow import configured, import the run into that
    # database as well.
    if config and config.databases[db_name].shadow_import:
        # Load the shadow database to import into.
        db_config = config.databases[db_name]
        shadow_name = db_config.shadow_import
        shadow_db = config.get_database(shadow_name)
        if shadow_db is None:
            raise ValueError,("invalid configuration, shadow import "
                              "database %r does not exist") % shadow_name

        # Perform the shadow import.
        shadow_result = import_and_report(config, shadow_name,
                                          shadow_db, file, format, commit,
                                          show_sample_count, disable_email)

        # Append the shadow result to the result.
        result['shadow_result'] = shadow_result

    result['success'] = True
    return result

def print_report_result(result, out, err, verbose = True):
    """
    import_and_report(result, out) -> None

    Print a human readable form of an import result object to the given output
    stream. Test results are printed in 'lit' format.
    """

    # Print the generic import information.
    print >>out, "Importing %r" % os.path.basename(result['import_file'])
    if result['success']:
        print >>out, "Import succeeded."
        print >>out
    else:
        out.flush()
        print >>err, "Import Failed:"
        print >>err, "--\n%s--\n" % result['error']
        err.flush()
        return

    if 'original_run' in result:
        print >>out, ("This submission is a duplicate of run %d, "
                      "already in the database.") % result['original_run']
        print >>out

    if not result['committed']:
        print >>out, "NOTE: This run was not committed!"
        print >>out

    if result['report_to_address']:
        print >>out, "Report emailed to: %r" % result['report_to_address']
        print >>out

    # Print the processing times.
    print >>out, "Processing Times"
    print >>out, "----------------"
    print >>out, "Load   : %.2fs" % result['load_time']
    print >>out, "Import : %.2fs" % result['import_time']
    print >>out, "Report : %.2fs" % result['report_time']
    print >>out, "Total  : %.2fs" % result['total_time']
    print >>out

    # Print the added database items.
    total_added = (result['added_machines'] + result['added_runs'] +
                   result['added_tests'] + result.get('added_samples', 0))
    if total_added:
        print >>out, "Imported Data"
        print >>out, "-------------"
        if result['added_machines']:
            print >>out, "Added Machines: %d" % result['added_machines']
        if result['added_runs']:
            print >>out, "Added Runs    : %d" % result['added_runs']
        if result['added_tests']:
            print >>out, "Added Tests   : %d" % result['added_tests']
        if result.get('added_samples', 0):
            print >>out, "Added Samples : %d" % result['added_samples']
        print >>out

    # Print the test results.
    test_results = result.get('test_results')
    if not test_results:
        return

    # List the parameter sets, if interesting.
    show_pset = len(test_results) > 1
    if show_pset:
        print >>out, "Parameter Sets"
        print >>out, "--------------"
        for i,info in enumerate(test_results):
            print >>out, "P%d: %s" % (i, info['pset'])
        print >>out

    total_num_tests = sum([len(item['results'])
                           for item in test_results])
    print >>out, "--- Tested: %d tests --" % total_num_tests
    test_index = 0
    for i,item in enumerate(test_results):
        pset = item['pset']
        pset_results = item['results']

        for name,test_status,perf_status in pset_results:
            test_index += 1

            # FIXME: Show extended information for performance changes, previous
            # samples, standard deviation, all that.
            #
            # FIXME: Think longer about mapping to test codes.
            result_info = None
            if test_status == runinfo.REGRESSED:
                result_string = 'FAIL'
            elif test_status == runinfo.IMPROVED:
                result_string = 'IMPROVED'
                result_info = "Test started passing."
            elif test_status == runinfo.UNCHANGED_FAIL:
                result_string = 'XFAIL'
            elif perf_status == None:
                # Missing perf status means test was just added or removed.
                result_string = 'PASS'
            elif perf_status == runinfo.REGRESSED:
                result_string = 'REGRESSED'
                result_info = 'Performance regressed.'
            elif perf_status == runinfo.IMPROVED:
                result_string = 'IMPROVED'
                result_info = 'Performance improved.'
            else:
                result_string = 'PASS'

            # Ignore passes unless in verbose mode.
            if not verbose and result_string == 'PASS':
                continue

            if show_pset:
                name = 'P%d :: %s' % (i, name)
            print >>out, "%s: %s (%d of %d)" % (result_string, name, test_index,
                                                total_num_tests)

            if result_info:
                print >>out, "%s TEST '%s' %s" % ('*'*20, name, '*'*20)
                print >>out, result_info
                print >>out, "*" * 20
