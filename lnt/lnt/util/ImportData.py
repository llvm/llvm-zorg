import re, time

from lnt import formats
from lnt.viewer import PerfDB
from lnt.util import NTEmailReport

def import_and_report(config, db_name, db, file, log, format, commit=False,
                      show_sample_count=False, disable_email=False):
    """
    import_and_report(config, db_name, db, file, log, format,
                      [commit], [show_sample_count],
                      [disable_email]) -> (success, run)

    Import a test data file into an LNT server and generate a test report. On
    success, run is the newly imported run. Note that success is uneffected by
    the value of commit, this merely changes whether the run (on success) is
    committed to the database.
    """
    numMachines = db.getNumMachines()
    numRuns = db.getNumRuns()
    numTests = db.getNumTests()

    # If the database gets fragmented, count(*) in SQLite can get really slow!?!
    if show_sample_count:
        numSamples = db.getNumSamples()

    print >>log, 'IMPORT: %s' % file
    startTime = time.time()
    try:
        data = formats.read_any(file, format)
    except KeyboardInterrupt:
        raise
    except:
        import traceback
        print >>log, 'ERROR: %r: load failed' % file
        print >>log, traceback.format_exc()
        return (False, None)
    print >>log, '  LOAD TIME: %.2fs' % (time.time() - startTime,)

    # Check if this is a nightlytest run.
    tag = data.get('Run',{}).get('Info',{}).get('tag',None)
    is_nt = tag is None or tag == 'nightlytest'

    # Find the email address for this machine's results.
    toAddress = None
    if is_nt and config.ntEmailEnabled:
        if isinstance(config.ntEmailTo, str):
            toAddress = config.ntEmailTo
        else:
            # Find the machine name.
            machineName = str(data.get('Machine',{}).get('Name'))
            for pattern,addr in config.ntEmailTo:
                if re.match(pattern, machineName):
                    toAddress = addr
                    break
            else:
                print >>log,("ERROR: unable to match machine name "
                             "for test results email address!")
                return (False, None)

    importStartTime = time.time()
    try:
        success,run = PerfDB.importDataFromDict(db, data)
    except KeyboardInterrupt:
        raise
    except:
        import traceback
        print >>log, 'ERROR: %r: import failed' % file
        print >>log, traceback.format_exc()
        return (False, None)

    print >>log, '  IMPORT TIME: %.2fs' % (time.time() - importStartTime,)
    if not success:
        print >>log, "  IGNORING DUPLICATE RUN"
        print >>log, "    MACHINE: %d" % (run.machine_id, )
        print >>log, "    START  : %s" % (run.start_time, )
        print >>log, "    END    : %s" % (run.end_time, )
        for ri in run.info.values():
            print >>log, "    INFO   : %r = %r" % (ri.key, ri.value)

    if not disable_email and toAddress is not None:
        print >>log, "\nMAILING RESULTS TO: %r\n" % toAddress
        NTEmailReport.emailReport(db, run,
                                  "%s/db_%s/nightlytest/" % (config.zorgURL,
                                                             db_name),
                                  config.ntEmailHost, config.ntEmailFrom,
                                  toAddress, success, commit)

    print >>log, "ADDED: %d machines" % (db.getNumMachines() - numMachines,)
    print >>log, "ADDED: %d runs" % (db.getNumRuns() - numRuns,)
    print >>log, "ADDED: %d tests" % (db.getNumTests() - numTests,)
    if show_sample_count:
        print >>log, "ADDED: %d samples" % (db.getNumSamples() - numSamples)

    if commit:
        print >>log, 'COMMITTING RESULT:',
        db.commit()
        print >>log, 'DONE'
    else:
        print >>log, 'DISCARDING RESULT:',
        db.rollback()
        print >>log, 'DONE'

    print >>log, 'TOTAL IMPORT TIME: %.2fs' % (time.time() - startTime,)

    return (success, run)
