import os
from optparse import OptionParser, OptionGroup

import lnt.server.config
from lnt.testing.util.commands import note, warning, error, fatal

def action_updatedb(name, args):
    """modify a database"""

    from optparse import OptionParser, OptionGroup

    parser = OptionParser("%%prog %s [options] <path|config-file> <file>+"%name)
    parser.add_option("", "--database", dest="database", default="default",
                      help="database to modify [%default]")
    parser.add_option("", "--testsuite", dest="testsuite",
                      help="testsuite to modify")
    parser.add_option("", "--commit", dest="commit", type=int,
                      default=False)
    parser.add_option("", "--show-sql", dest="show_sql", action="store_true",
                      default=False)
    parser.add_option("", "--delete-machine", dest="delete_machines",
                      action="append", default=[])
    parser.add_option("", "--delete-run", dest="delete_runs",
                      action="append", default=[], type=int)
    (opts, args) = parser.parse_args(args)

    if len(args) != 1:
        parser.error("invalid number of arguments")

    if opts.testsuite is None:
        parser.error("--testsuite is required")
        
    config, = args

    # Accept paths to config files, or to directories containing 'lnt.cfg'.
    if os.path.isdir(config):
        tmp = os.path.join(config, 'lnt.cfg')
        if os.path.exists(tmp):
            config = tmp

    # Load the config file.
    config_data = {}
    exec open(config) in config_data
    config = lnt.server.config.Config.fromData(config, config_data)

    # Get the database and test suite.
    db = config.get_database(opts.database, echo=opts.show_sql)
    ts = db.testsuite[opts.testsuite]

    # Compute a list of all the runs to delete.
    runs_to_delete = list(opts.delete_runs)
    if opts.delete_machines:
        runs_to_delete.extend(
            id
            for id, in ts.query(ts.Run.id).\
                join(ts.Machine).\
                filter(ts.Machine.name.in_(opts.delete_machines)))

    # Delete all samples associated with those runs.
    ts.query(ts.Sample).\
        filter(ts.Sample.run_id.in_(runs_to_delete)).\
        delete(synchronize_session=False)

    # Delete all those runs.
    ts.query(ts.Run).\
        filter(ts.Run.id.in_(runs_to_delete)).\
        delete(synchronize_session=False)

    # Delete the machines.
    for name in opts.delete_machines:
        num_deletes = ts.query(ts.Machine).filter_by(name=name).delete()
        if num_deletes == 0:
            warning("unable to find machine named: %r" % name)

    if opts.commit:
        db.commit()
    else:
        db.rollback()
