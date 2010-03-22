import os, sys, time

from lnt import formats
from lnt.viewer import Config, PerfDB
from lnt.util import ImportData

def action_import(name, args):
    """import test data into a database"""

    from optparse import OptionParser, OptionGroup

    parser = OptionParser("%%prog %s [options] <path|config-file> file+" %name)
    parser.add_option("", "--database", dest="database", default="default",
                      help="database to write to [%default]")
    parser.add_option("", "--format", dest="format",
                      choices=formats.format_names + ['<auto>'],
                      default='<auto>')
    parser.add_option("", "--commit", dest="commit", type=int,
                      default=False)
    parser.add_option("", "--show-sql", dest="showSQL", action="store_true",
                      default=False)
    parser.add_option("", "--show-sample-count", dest="showSampleCount",
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
    db = PerfDB.PerfDB(db_entry.path, echo=opts.showSQL)
    for file in args:
        success, run = ImportData.import_and_report(
            config, opts.database, db, file, sys.stdout,
            opts.format, opts.commit, opts.showSampleCount,
            opts.noEmail)
