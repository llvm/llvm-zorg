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
  $ tail -f /tmp/FOO/runserver.log
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

LLVM test-suite (aka LLVM nightly test)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``nt`` built-in test runs the LLVM test-suite execution and performance
tests, in the "nightly test" configuration. This test allows running many
different applications and benchmarks (e.g., SPEC), with various compile
options, and in several different configurations (for example, using an LLVM
compiler like ``clang`` or ``llvm-gcc``, running under the LLVM JIT compiler
using the LLVM ``lli`` bit-code interpreter, or testing new code generator
passes).

The ``nt`` test requires that the LLVM test-suite repository, a working LLVM
compiler, and a LLVM source and build tree are available. Currently, the LLVM
build tree is expected to have been built-in the Release+Asserts configuration.
Unlike the prior ``NewNightlyTest.pl``, the ``nt`` tool does not checkout or build
any thing, it is expected that users manage their own LLVM source and build
trees. Ideally, each of the components should be based on the same LLVM revision
(except perhaps the LLVM test-suite), but this is not required.

The test runs the LLVM test-suite builds and execution inside a user specificed
sandbox directory. By default, each test run will be done in a timestamped
directory inside the sandbox, and the results left around for post-mortem
analysis. Currently, the user is responsible for cleaning up these directories
to manage disk space.

The tests are always expected to be run using out-of-tree builds -- this is a
more robust model and allow sharing the same source trees across many test
runs. One current limitation is that the LLVM test-suite repository will not
function correctly if an in-tree build is done, followed by an out-of-tree
build. It is very important that the LLVM test-suite repository be left
pristine.

The following command shows an example of running the ``nt`` test suite on a
local build::

  $ rm -rf /tmp/BAR
  $ lnt runtest nt \
       --sandbox /tmp/BAR \
       --cc ~/llvm.obj.64/Release+Asserts/bin/clang \
       --cxx ~/llvm.obj.64/Release+Asserts/bin/clang++ \
       --llvm-src ~/llvm \
       --llvm-obj ~/llvm.obj.64 \
       --test-suite ~/llvm-test-suite \
       TESTER_NAME \
        -j 16
  2010-04-17 23:46:40: using nickname: 'TESTER_NAME__clang_DEV__i386'
  2010-04-17 23:46:40: creating sandbox: '/tmp/BAR'
  2010-04-17 23:46:40: starting test in '/private/tmp/BAR/test-2010-04-17_23-46-40'
  2010-04-17 23:46:40: configuring...
  2010-04-17 23:46:50: testing...
  2010-04-17 23:51:04: loading test data...
  2010-04-17 23:51:05: generating report: '/private/tmp/BAR/test-2010-04-17_23-46-40/report.json'

The first seven arguments are all required -- they specify the sandbox path, the
compilers to test, and the paths to the required sources and builds. The
``TESTER_NAME`` argument is used to derive the name for this tester (in
conjunction which some inferred information about the compiler under test). This
name is used as a short identifier for the test machine; generally it should be
the hostname of the machine or the name of the person who is responsible for the
tester. The ``-j 16`` argument is optional, in this case it specifies that tests
should be run in parallel using up to 16 processes.

In this case, we can see from the output that the test created a new sandbox
directory, then ran the test in a subdirectory in that sandbox. The test outputs
a limited about of summary information as testing is in progress. The full
information can be found in .log files within the test build directory (e.g.,
``configure.log`` and ``test.log``).

The final test step was to generate a test report inside the test
directory. This report can now be submitted directly to an LNT server. For
example, if we have a local server running as described earlier, we can run::

  $ lnt submit --commit=1 http://localhost:8000/submitRun \
      /tmp/BAR/test-2010-04-17_23-46-40/report.json
  STATUS: 0

  OUTPUT:
  IMPORT: /tmp/FOO/lnt_tmp/data-2010-04-17_16-54-35ytpQm_.plist
    LOAD TIME: 0.34s
    IMPORT TIME: 5.23s
  ADDED: 1 machines
  ADDED: 1 runs
  ADDED: 1990 tests
  COMMITTING RESULT: DONE
  TOTAL IMPORT TIME: 5.57s

and view the results on our local server.

LNT-based NT test modules
+++++++++++++++++++++++++

In order to support more complicated tests, or tests which are not easily
integrated into the more strict SingleSource or MultiSource layout of the LLVM
test-suite module, the ``nt`` built-in test provides a mechanism for LLVM
test-suite tests that just define an extension test module. These tests are
passed the user configuration parameters for a test run and expected to return
back the test results in the LNT native format.

For more information, see the example tests in the LLVM test-suite repository
under the ``LNT/Examples`` directory.
