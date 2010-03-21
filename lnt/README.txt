LLVM "Nightly Test" Infrastructure
==================================

This directory and its subdirectories contain the LLVM nightly test
infrastructure. This is technically version "3.0" of the LLVM nightly test
architecture.

LNT is written in Python and implements a (old-school) Quixote web-app,
available by CGI and WSGI, and utilities for submitting data via LLVM's
NewNightlyTest.pl in conjunction with LLVM's test-suite repository.

The infrastructure has the following layout:

 lnt/db - Database schema, utilities, and examples of the LNT plist format.

 lnt/import - Utilities for converting to the LNT plist format for test data,
              and for submitting plists to the server.

 lnt/test - Tests for the infrastructure; they currently assume they are running
            on a system with a live instance available at
            'http://localhost/zorg/'.

 lnt/viewer - The LNT web-app itself.


Installation Instructions
-------------------------

External Dependencies: SQLAlchemy, Quixote, mod_wsgi, SQLite,
                       MySQL (optional), urllib2_file

Internal Dependencies: MooTools

These are the rough steps to get a working LNT installation:

 1. Install external dependencies. FIXME: Elaborate.

 2. Choose a data directory and create the initial SQLite or MySQL
    databases. SQLite databases need to be writable by the Apache user, as does
    the directory they are contained in.

 3. Copy viewer/zorg.cfg.sample to viewer/zorg.cfg, and modify for your
    installation.

    a. Update the databases list.

    b. Update the zorgURL.

    c. Update the nt_emailer configuration.

 4. Add the zorg.wsgi app to your Apache configuration. You should set also
    configure the WSGIDaemonProcess and WSGIProcessGroup variables if not
    already done.

 5. Add a link or copy of the zorg.cgi app in the appropriate place if you want
    to use the CGI script. The WSGI app is significantly faster, but currently
    can't handle submissions.

 6. Create a zorg/lnt/viewer/resources/graphs directory, which the app uses to
    hold temporary files, and make sure it is writable by the Apache user.
