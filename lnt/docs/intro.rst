.. _intro:

Introduction
============

LNT consists of two main parts, a server side web application for accessing and
visualizing performance data, and client side utilities for easily generating
and submitting data.

LNT uses a simple and extensible format for interchanging data between the
clients and the server; this allows the LNT server to receive and store data for
a wide variety of applications. The web app currently contains a specialized
viewer for LLVM nightly test data, and a generic viewer for visualizing
arbitrary test reports.

Both the LNT client and server are written in Python, however the test data
itself can be passed in one of several formats, including property lists and
JSON. This makes it easy to produce test results from almost any language.


Installation
------------

These are the (current) rough steps to get a working LNT client:

 1. Install LNT:

      python setup.py install

    It is recommended that you install LNT into a virtualenv.

If you want to run an LNT server, you will need to perform the following
additional steps:

 2. Create a new LNT installation:

      lnt create path/to/install-dir

    This will create the LNT configuration file, the default database, and a
    .wsgi wrapper to create the application. You can execute the generated app
    directly to run with the builtin web server, or use 

      lnt runserver path/to/install-dir

    which provides additional command line options. Neither of these servers is
    recommended for production use.

 3. Edit the generated 'lnt.cfg' file if necessary, for example to:

    a. Update the databases list.

    b. Update the zorgURL.

    c. Update the nt_emailer configuration.

 4. Add the 'zorg.wsgi' app to your Apache configuration. You should set also
    configure the WSGIDaemonProcess and WSGIProcessGroup variables if not
    already done.

    If running in a virtualenv you will need to configure that as well; see the
    `modwsgi wiki <http://code.google.com/p/modwsgi/wiki/VirtualEnvironments>`_.


Development
-----------

Developing LNT should be done under a virtualenv (most likely in 'develop'
mode). Currently, the tests require:

 1. 'lit', the LLVM test runner, is available.

 2. If inside a virtualenv, the virtualenv will need to be activated because the
 tests want to run Python directly. This should be fixed to substitute in the
 Python that was used to run lit, so the venv doesn't have to be active.

To run the tests, use, e.g.,

  lit -sv $ROOT/lnt/tests

or

  lit -sv $ZORG_ROOT/test

to run the zorg and LNT tests all at once. You can use

  python setup.py test

if you prefer 'unittest' style output (this still requires that 'lit' be
installed).


Architecture
------------

The LNT web app is currently implemented as a Flask WSGI web app, with Jinja2
for the templating engine. My hope is to eventually move to a more AJAXy web
interface.

The database layer uses SQLAlchemy for its ORM, and is typically backed by
SQLite, although I have tested on MySQL on the past, and supporting other
databases should be trivial. My plan is to always support SQLite as this allows
the possibility of developers easily running their own LNT installation for
viewing nightly test results, and to run with whatever DB makes the most sense
on the server.
