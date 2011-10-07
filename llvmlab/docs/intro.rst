.. _intro:

Introduction
============

Installation
------------

These are the (current) rough steps to get a working llvmlab server:

 1. Install llvmlab::

      python setup.py install

    It is recommended that you install llvmlab into a virtualenv. If you are
    developing the software, you presumably want to use::

      python setup.py develop

 2. Create a new llvmlab installation::

      llvmlab create \
        --master-url http://example.com:8010 \
        --plugin-module zorg.llvmlab
        path/to/install-dir

    This will create the llvmlab configuration file, the default database, and a
    .wsgi wrapper to create the application. If using this instance for
    development, you may want to add the ``--debug-server`` argument to default
    to running the server in debug mode.

    The ``--master-url`` should be used to point the lab at the buildbot
    installation it is intended to monitor. You can monitor ``lab.llvm.org`` for
    quick testing purposes, but **please** do not leave this running for an
    extended time, as it puts a certain amount of load on the buildbot
    installation. If you want to run longer tests, please run a local buildbot
    master and monitor that.

    The ``--plugin-module`` argument is required in order for the dashboard to
    work, it is how the dashboard loads the information about the buildbot
    configuration. The module path is expected to be importable, so you may need
    to extend the PYTHONPATH to support that (e.g.,
    ``PYTHONPATH=/path/to/zorg/repo`` would allow the default ``lab.llvm.org``
    plugin named above to be imported).

    If using this instance for deployment, you *certainly* want to provide the
    ``--admin-email`` and ``--admin-password`` arguments to override the
    defaults. You may also need to modify the generated ``app.cfg`` file to
    change the default SMTP relay server (used for mailing error messages).

    You can execute the generated WSGI app directly to run with the builtin web
    server, or use::

      env LLVMLAB_CONFIG=/path/to/instance/lab.cfg llvmlab runserver

    which may eventually provide additional command line options. Neither of
    these servers is recommended for production use.

 3. Add the 'app.wsgi' app to your Apache configuration. You should set also
    configure the WSGIDaemonProcess and WSGIProcessGroup variables if not
    already done.

    If running in a virtualenv you will need to configure that as well; see the
    `modwsgi wiki <http://code.google.com/p/modwsgi/wiki/VirtualEnvironments>`_.


Architecture
------------

The llvmlab web app is currently implemented as a WSGI web app using Flask.
