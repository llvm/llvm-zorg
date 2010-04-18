.. _tools:

The ``lnt`` Tool
================

The ``lnt`` command line utility provides the following commands for client-side
use and server-side use. The following is a list of commands and the most
importat options, use ``lnt <toolname> --help`` for more information on any
particular tool.

Client-Side Tools
-----------------

  ``lnt checkformat [<file>]``
    Checks the syntax of an LNT test report file. In addition to verifying that
    LNT can read the raw format (e.g., JSON or property list), this also creates
    a temporary in-memory database instance and ensures that the test report
    file can be imported correctly.

    If run without arguments, this expects to read the input file from ``stdin``.

  ``lnt convert <input path> [<output path>]``
    Convert between LNT test report formats. By default, this will convert to
    the property list format. You can use ``-`` for either the input (to read
    from ``stdin) or the output (to write to ``stdout``).

  ``lnt submit [--commit=1] <server url> <file>+``
    Submits one or more files to the given server. The ``<server url>`` should
    be the url to the actual ``submitRun`` page on the server; the database
    being submitted to is effectively a part of this URL.

    By default, this only submits the report to the server but does not actually
    commit the data. When testing, you should verify that the server returns an
    acceptable response before committing runs.

  ``lnt showtests``
    List available built-in tests. See the :ref:`tests` documentation for more
    details on this tool.

  ``lnt runtest [<run options>] <test name> ... test arguments ...``
    Run a built-in test. See the :ref:`tests` documentation for more
    details on this tool.

Server-Side Tools
-----------------

The following tools are used to interact with an LNT server:

  ``lnt create <path>``
    Creates a new LNT server instance. This command has a number of parameters
    to tweak the generated server, but they can all be modified after the fact
    in the LNT configuration file.

    The default server will have one database named *default*.

  ``lnt createdb <path>``
    Creates a new LNT sqlite3 database at the specified path.

  ``lnt import <path | config file> <file>+``
    Import an LNT data file into a database. You can use ``--database`` to
    select the database to write to. Note that by default this will also
    generate report emails if enabled in the configuration, you can use
    ``--no-email`` to disable this.

  ``lnt runserver <path | config file>``
    Start the LNT server using a development WSGI server. Additional options can
    be used to control the server host and port, as well as useful development
    features such as automatic reloading.
