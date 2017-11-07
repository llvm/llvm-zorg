from pipes import quote
import inspect
import os
import subprocess
import sys
import textwrap

verbose = False


def _logged_catched(func, commandline, *args, **kwargs):
    commandline_string = commandline
    if isinstance(commandline, list) or isinstance(commandline, tuple):
        commandline_string = " ".join([quote(arg) for arg in commandline])

    if verbose:
        cwd = kwargs.get('cwd', None)
        if cwd is not None:
            sys.stderr.write("In Directory: %s\n" % cwd)
        sys.stderr.write("$ %s\n" % commandline_string)
    try:
        return func(commandline, *args, **kwargs)
    except subprocess.CalledProcessError as e:
        sys.stderr.write("Error while executing: $ %s\n" %
                         commandline_string)
        if e.output is not None:
            sys.stderr.write(str(e.output))
        sys.exit(e.returncode)
    except OSError as e:
        sys.stderr.write("Error while executing $ %s\n" % commandline_string)
        sys.stderr.write("Error: %s\n" % e)
        sys.exit(1)


def check_call(commandline, *args, **kwargs):
    """Opinionated version of subprocess.check_call: Logs commandline in
    verbose mode, and for returncode != 0 print a message and exit the
    application."""
    return _logged_catched(subprocess.check_call, commandline, *args, **kwargs)


def check_output(commandline, *args, **kwargs):
    """Opinionated version of subprocess.check_output: Logs commandline in
    verbose mode, and for returncode != 0 print a message and exit the
    application."""
    return _logged_catched(subprocess.check_output, commandline, *args,
                           **kwargs)


def call(commandline, *args, **kwargs):
    """Opinionated version of subprocess.check_output: Logs commandline in
    verbose mode, and exit with message the if command does not exist."""
    return _logged_catched(subprocess.call, commandline, *args, **kwargs)


def _print_help(commands, argv, docstring):
    if docstring:
        description = inspect.cleandoc(docstring)
        sys.stderr.write(description)
        sys.stderr.write("\n\n")
    sys.stderr.write("Usage:\n")
    twc = textwrap.TextWrapper(expand_tabs=True, initial_indent='        ',
                               subsequent_indent='        ', width=78)
    for name, func in sorted(commands.items(), key=lambda x: x[0]):
        sys.stderr.write("    %s %s [arg]...\n" %
                         (os.path.basename(argv[0]), name))
        if func.__doc__:
            docstring = inspect.cleandoc(func.__doc__)
            sys.stderr.write('\n'.join(twc.wrap(docstring)) + '\n')


def run_subcommand(commands, argv, docstring=None):
    if len(argv) < 2:
        _print_help(commands, argv, docstring)
        sys.stderr.write("\nError: No command specified!\n")
        sys.exit(1)

    commandname = argv[1]
    if commandname == 'help' or commandname == '--help':
        _print_help(commands, argv, docstring)
        sys.exit(0)

    command = commands.get(argv[1])
    if command is None:
        sys.stderr.write("Error: Unknown command '%s'\n" % argv[1])
        sys.exit(1)

    args = argv[2:]
    command(args)
