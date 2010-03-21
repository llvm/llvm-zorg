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
              and for submitting plist to the server.

 lnt/test - Tests for the infrastructure; they currently assume they are running
            on a system with a live instance available at
            'http://localhost/zorg/'.

 lnt/viewer - The LNT web-app itself.


Installation Instructions
-------------------------

External Dependencies: SQLAlchemy, Quixote, mod_wsgi, SQLite,
                       MySQL (optional), urllib2_file

Internal Dependencies: MooTools

These are the steps to get a working LNT installation:

 1. Figure it out yourself, write installation instructions, add to README.txt.

 2. M-x revert-buffer, goto 1.
