LLVM "Nightly Test" Infrastructure
==================================

This directory and its subdirectories contain the LLVM nightly test
infrastructure. This is technically version "3.0" of the LLVM nightly test
architecture.

LNT is written in Python and implements a WSGI web app on top of Quixote, along
with utilities for submitting data via LLVM's NewNightlyTest.pl in conjunction
with LLVM's test-suite repository.

The infrastructure has the following layout:

 $ROOT/lnt - Top-level source module

 $ROOT/lnt/import - Utilities for converting to the LNT plist format for test
                    data, and for submitting plists to the server.

 $ROOT/lnt/viewer - The LNT web-app itself.

 $ROOT/db - Database schema, utilities, and examples of the LNT plist format.

 $ROOT/tests - Tests for the infrastructure; they currently assume they are
                  running on a system with a live instance available at
                  'http://localhost/zorg/'.


Installation Instructions
-------------------------

External Dependencies: SQLAlchemy, Quixote, mod_wsgi, SQLite, MySQL (optional)

Internal Dependencies: MooTools

These are the rough steps to get a working LNT installation:

 1. Install LNT:

      python setup.py install

    It is recommended that you install LNT into a virtualenv.

 2. Create a new LNT installation:

      lnt create path/to/install-dir

    This will create the LNT configuration file, the default database, and a
    .wsgi wrapper to create the application. You can execute the generated app
    directly to run with the builtin web server, or use 'lnt runserver' with the
    path the config file.

 3. Edit the generated 'lnt.cfg' file if necessary, for example to:

    a. Update the databases list.

    b. Update the zorgURL.

    c. Update the nt_emailer configuration.

 4. Add the zorg.wsgi app to your Apache configuration. You should set also
    configure the WSGIDaemonProcess and WSGIProcessGroup variables if not
    already done.

    If running in a virtualenv you will need to configure that as well; see the
    `modwsgi wiki <http://code.google.com/p/modwsgi/wiki/VirtualEnvironments>`_.


Development Instructions
------------------------

Developing LNT should be done under a virtualenv (most likely in 'develop'
mode). Currently, the tests require:

 1. 'lit', the LLVM test runner, is available.

 2. The hosted application is live at http://localhost/perf/.

 3. lnt/tests/lit.cfg should be modified to have the correct '%email_host' and
    '%email_to' substitutions.

To run the tests, use, e.g.,

  lit -sv $ROOT/lnt/tests

or

  lit -sv $ZORG_ROOT/test

to run the zorg and LNT tests all at once.

Note that currently the email test will actually send you email.
