.. _tests:

Test Producers
==============

On the client-side, LNT comes with a number of built-in test data producers.
This section focuses on the LLVM test-suite (aka nightly test) generator, since
it is the primary test run using the LNT infrastructure, but note that LNT also
includes tests for other interesting pieces of data, for example Clang
compile-time performance.

LNT also makes it easy to add new test data producers and includes examples of
custom data importers (e.g., to import buildbot build information into) and
dynamic test data generators (e.g., abusing the infrastructure to plot graphs,
for example).

Running a Local Server
----------------------

It is useful to set up a local LNT server to view the results of tests, either
for personal use or to preview results before submitting them to a public
server. To set up a one-off server for testing::

  # Create a new installation in /tmp/FOO.
  $ lnt create /tmp/FOO
  created LNT configuration in '/tmp/FOO'
  ...

  # Run a local LNT server.
  $ lnt runserver /tmp/FOO &> /tmp/FOO/runserver.log &
  [2] 69694

  # Watch the server log.
  $ tail -f /tmp/runserver.log
  * Running on http://localhost:8000/
  ...

Running Tests
-------------

The built-in tests are designed to be run via the ``lnt`` tool. The
following tools for working with built-in tests are available:

  ``lnt showtests``
    List the available tests.  Tests are defined with an extensible
    architecture. FIXME: Point at docs on how to add a new test.

  ``lnt runtest [<run options>] <test name> ... test arguments ...``
    Run the named test. The run tool itself accepts a number of options which
    are common to all tests. The most common option is ``--submit=<url>`` which
    specifies the server to submit the results to after testing is complete. See
    ``lnt runtest --help`` for more information on the available options.

    The remainder of the options are passed to the test tool itself. The options
    are specific to the test, but well behaved tests should respond to ``lnt
    runtest <test name> --help``. The following section provides specific
    documentation on the built-in tests.

Built-in Tests
--------------

None yet.
