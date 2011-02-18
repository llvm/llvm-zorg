"""Implements the command line 'llvmlab' tool."""

import hashlib
import os
import random
import shutil
import sys

import flask
import llvmlab.data

def action_create(name, args):
    """create a llvmlab installation"""

    import llvmlab
    from optparse import OptionParser, OptionGroup
    parser = OptionParser("%%prog %s [options] <path>" % name)
    parser.add_option("-f", "--force", dest="force", action="store_true",
                      help="overwrite existing files")

    group = OptionGroup(parser, "CONFIG OPTIONS")
    group.add_option("", "--admin-login", dest="admin_login",
                      help="administrator login [%default]", default='admin')
    group.add_option("", "--admin-name", dest="admin_name",
                      help="administrator name [%default]",
                      default='Administrator')
    group.add_option("", "--admin-password", dest="admin_password",
                      help="administrator password [%default]", default='admin')
    group.add_option("", "--admin-email", dest="admin_email",
                      help="administrator email [%default]",
                     default='admin@example.com')

    group.add_option("", "--debug-server", dest="debug_server",
                      help="run server in debug mode [%default]",
                     action="store_true", default=False)
    parser.add_option_group(group)

    (opts, args) = parser.parse_args(args)

    if len(args) != 1:
        parser.error("invalid number of arguments")

    basepath, = args
    basepath = os.path.abspath(basepath)
    cfg_path = os.path.join(basepath, 'lab.cfg')
    data_path = os.path.join(basepath, 'lab-data.json')

    if not os.path.exists(basepath):
        try:
            os.mkdir(basepath)
        except:
            parser.error("unable to create directory: %r" % basepath)
    elif not os.path.isdir(basepath):
        parser.error("%r exists but is not a directory" % basepath)

    if not opts.force:
        if os.path.exists(cfg_path):
            parser.error("%r exists (use --force to override)" % cfg_path)
        if os.path.exists(data_path):
            parser.error("%r exists (use --force to override)" % data_path)

    # Construct the config file.
    sample_cfg_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   "lab.cfg.sample")
    sample_cfg_file = open(sample_cfg_path, "rb")
    sample_cfg_data = sample_cfg_file.read()
    sample_cfg_file.close()

    # Fill in the sample config.
    secret_key = hashlib.sha1(str(random.getrandbits(256))).hexdigest()
    cfg_options = dict(opts.__dict__)
    cfg_options['admin_passhash'] = hashlib.sha256(
        opts.admin_password + secret_key).hexdigest()
    cfg_options['secret_key'] = secret_key
    cfg_options['data_path'] = data_path
    cfg_data = sample_cfg_data % cfg_options

    # Write the initial config file.
    cfg_file = open(cfg_path, 'w')
    cfg_file.write(cfg_data)
    cfg_file.close()
    
    # Create the inital data file.
    data = llvmlab.data.Data(users = [])

    # Write the initial (empty) data file.
    data_file = open(data_path, 'w')
    flask.json.dump(data.todata(), data_file, indent=2)
    print >>data_file
    data_file.close()

def action_runserver(name, args):
    """run a llvmlab instance"""

    import llvmlab
    from optparse import OptionParser, OptionGroup
    parser = OptionParser("%%prog %s [options] <path>" % name)
    (opts, args) = parser.parse_args(args)

    if len(args) != 0:
        parser.error("invalid number of arguments")

    from llvmlab.ui import app
    instance = app.App.create_standalone()
    instance.run()

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
        usage()

    cmd = sys.argv[1]
    commands[cmd](cmd, sys.argv[2:])
