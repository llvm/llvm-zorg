import re, time

from lnt import formats
from lnt.viewer import PerfDB
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
    toAddress = None
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
        success,run = PerfDB.importDataFromDict(db, data)
    except KeyboardInterrupt:
        raise
    except:
        import traceback
        result['error'] = "import failure: %s" % traceback.format_exc()
        return result

    result['db_import_time'] = time.time() - importStartTime
    if not success:
        # Record the original run this is a duplicate of.
        result['original_run'] = run.id

    if not disable_email and toAddress is not None:
        result['report_to_address'] = toAddress
        NTEmailReport.emailReport(db, run,
                                  "%s/db_%s/" % (config.zorgURL, db_name),
                                  email_config.host, email_config.from_address,
                                  toAddress, success, commit)

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

    result['import_time'] = time.time() - startTime

    result['success'] = True
    return result
