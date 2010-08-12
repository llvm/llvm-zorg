import os, pprint, sys, time

from lnt import formats
from lnt.viewer import Config, PerfDB
from lnt.util import ImportData

def action_import(name, args):
    """import test data into a database"""

    from optparse import OptionParser, OptionGroup

    parser = OptionParser("%%prog %s [options] <path|config-file> <file>+"%name)
    parser.add_option("", "--database", dest="database", default="default",
                      help="database to write to [%default]")
    parser.add_option("", "--format", dest="format",
                      choices=formats.format_names + ['<auto>'],
                      default='<auto>')
    parser.add_option("", "--commit", dest="commit", type=int,
                      default=False)
    parser.add_option("", "--show-sql", dest="show_sql", action="store_true",
                      default=False)
    parser.add_option("", "--show-sample-count", dest="show_sample_count",
                      action="store_true", default=False)
    parser.add_option("", "--show-raw-result", dest="show_raw_result",
                      action="store_true", default=False)
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="show verbose test results",
                      action="store_true", default=False)
    parser.add_option("", "--no-email", dest="noEmail",
                      action="store_true", default=False)
    (opts, args) = parser.parse_args(args)

    if len(args) < 2:
        parser.error("invalid number of arguments")

    config = args.pop(0)

    # Accept paths to config files, or to directories containing 'lnt.cfg'.
    if os.path.isdir(config):
        tmp = os.path.join(config, 'lnt.cfg')
        if os.path.exists(tmp):
            config = tmp

    # Load the config file.
    config_data = {}
    exec open(config) in config_data
    config = Config.Config.fromData(config, config_data)

    # Get the database entry to use.
    db_entry = config.databases.get(opts.database)
    if db_entry is None:
        parser.error("invalid database name")

    # Load the database.
    db = PerfDB.PerfDB(db_entry.path, echo=opts.show_sql)
    for file in args:
        result = ImportData.import_and_report(
            config, opts.database, db, file,
            opts.format, opts.commit, opts.show_sample_count,
            opts.noEmail)

        if opts.show_raw_result:
            pprint.pprint(result)
        else:
            ImportData.print_report_result(result, sys.stdout, opts.verbose)

