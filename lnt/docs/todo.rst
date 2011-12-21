.. _todo:

TODO
====

This is a TODO list of major and minor features for LNT.

Major Features
--------------

Too many to name!

Minor Features
--------------

Optimize test distribution format for common cases.

 1. We should left the test info higher in the format, so that it can easily be
 shared by a large number of samples.

 2. We should specify test samples in an array instead of objects, to avoid
 requiring repetitive 'Name' and 'Data' keys.

 3. We should support [test, sample] in addition to [test, [sample, ...]].

 4. If we changed the .success marker to be .failure, then having [test] be a
 shortcut for [test, 0] would be fairly nice, and in the visualization we would
 automatically get the right defaulting for absent tests.

These changes would significantly compact the archive format, which improves
performance across the board.

Other stuff:

 1. We should find ways to manage the SQLite databases better. Currently we:

    o Could benefit from having LNT manage when to run ANALYZE.

    o Could benefit from making LNT handle setting some of the page size
      pragmas, at some point.

    o Could benefit from finding a way to have LNT VACUUM, although this can be
      very expensive.

v0.4 Redesign
-------------

 - Kill parameter sets.

   o Is this actual worth doing? If we just bring up dual models for a while
     there is no reason to spend time on the old model.

   o Counter argument is that it might make migrating code more simple.

   o Another counter argument is that we want to remove these from some places
     that just migrating the schema won't touch (like the submission format).

 - Add schema version to test submission format (for future future proofing).

 - Schema redesign:

   o Plan on doing a dual submission model for bringup purposes.

   o Part of the planned schema design is to have proper attributes for the rows
     in the run table. Should we moved to a typed model?

   o See below.

 - Open question: UI rewrite at the same time? We are going to have to do a
   metric ton of rewrite work to adapt to the new schema anyway.

 - Open question: Introduce Mongo dependency? I would rather not, from a
   dependency perspective, but I also would really like to have mongo
   available. Also I am almost certainly going to want to move llvmlab to using
   mongo so it is an effective dependency on the server. Having it as a
   dependency for local use seems sucky though. Shame there isn't a local
   isolated mongo-as-a-library client.

   o CONCLUSION: Not for v0.4.

 - Run order redesign?

   o The current run order design is really unfortunate. It would be much better
     if we could provide a way for users to report all of the important
     revisions. Unfortunately, this places a lot of requirements on the server
     for understanding all the repositories, especially the git based ones.

Schema Resign
~~~~~~~~~~~~~

Primary Purpose
+++++++++++++++

The primary purpose of the schema redesign is to eliminate what Bill Karwin
calls the "Entity-Attribute-Value" anti-pattern in his book SQL
Antipatterns. This is where we basically store arbitrary dictionaries of
attributes in the various Info tables, which I have since discovered is a
terrible idea for all the reasons Karwin articulates.

The particular difficulty with following this within the other LNT design goals
is that we still have the desire to allow users to report very flexible
structured data.

Currently, the best idea to have to resolve this conflict is that we will
construct tables on the fly. I suspect many SQL experts might also regard that
as an anti- or scary- pattern, but it seems like the best option to me. If one
thinks of LNT as trying to be a general purpose product, then the idea of
creating tables is notionally related to the specialization (instantiation) of
the general purpose product for one's particular test suites.

However, we certainly also want to limit the degree to which we create or modify
tables. Having the test submission mechanism having to modify the table any time
a user reported a new key would certainly be superflous.

Thus, my current plan is to follow what Karwin calls the "Semistructured Data"
pattern. What we will do is add an arbitrary blob field (to be JSON or perhaps
BSON data). We will basically expect that any fields that are required (or
almost always used) to be put in the actual table schema, but any time we see
additional fields we can handle them by just placing them in the BLOB field.

We will probably allow users to migrate fields to and from the schema. This
gives us a good amount of flexibility (and an easy path to eliminate the JSON
field if need be). We may require users to do this before they can do anything
but just see the data associated with a run. For example, if they want to use
one of the reported fields as an axis.

Secondary Purpose
+++++++++++++++++

One additional painful part of the current schema design is that we use separate
tests to represent the status aspect of other tests. This is nice and flexible,
but makes the UI code very painful. Especially, some things like making a graph
of the test values for all tests which passed become incredibly complex.

The plan is to handle this problem by also constructing the Sample tables on the
fly, and allowing the test suite to define the keys that go into a sample. Thus,
any one sample will reflect *all* of the statistics that were reported for that
test.

This has many advantages:
 * We can start using types for the columns (e.g., easy to start reporting hash
   of produced binaries, for example).
 * The performance impact of adding new sample values should be much lower than
   in the old schema.
 * The database explicitly models the fact that sample values were produced from
   a single run, whereas before sample values and status could not technically
   be correlated correctly.
 * We eliminate the need to mangle subtest/test result key information into the
   test name, which is a big win.

The has some disadvantages, however:
 * Poorly models suites where different tests reported different test results.
 * Poorly models situations where we want to support a large number of test
   results and that set might change frequently or dynamically (e.g., suppose we
   reported one test for each LLVM Statistic counter).

However, at least for our current usage this scheme should work well enough and
be **substantially** faster than the old scheme.

This will probably mean that we have to do a bit of work (similar to what we had
to do for parameter sets) to handle what the UI for this should look
like. However, we should have better infrastructure for defining how the UI
should handle things in the metadata.

Other Antipatterns In Use
+++++++++++++++++++++++++

The "status kind" field uses and suffers from a view of the problems mentioned
in Chapter 11. 31 Flavors. It would probably be good to move being foreign key
references into an auxiliary table. This also reduces some of my reservations
about making that field required / part of every test.

Conveniently, this can also be done without actually changing the status kind
values, which makes migration easy.

Proposed Concepts
~~~~~~~~~~~~~~~~~

Test Suite
++++++++++

The major high level concept in the new schema is that of a test suite. This is
designed to correspond to some group of tests which users would browse
independently. Examples would be things like "LLVM Test Suite" or "PlumHall" or
"GCC Test Suite".

The test suite is the place that defines information about what is being tested
and the metadata on what information is reported by the runs and the tests.

Parameter Sets
++++++++++++++

This concept will be removed. Instead, the idea is that all the information
about how a test was run lives at the Run level. This corresponds much more to
how LNT is currently primarily used in production. Although there were tests
like the Clang tests which made use of parameter sets, the theory is that we
should only have one place for parameters, and a lot of them have to be in the
Run. The goal is that the UI will be enhanced to better support situations when
one group of tests was split up into multiple Runs. We should also eventually
support submitting multiple runs in one submission.

Proposed Migration Path
~~~~~~~~~~~~~~~~~~~~~~~

I would prefer to not do any coordinated changes to the non-DB side of things
while effecting the database changes (and generally, I like the test submission
format to be fairly stable).

For the most part, I think this can be done relatively easily, but there are a
few places that will require special care.

 - For parameter sets (TestInfo), we just discard them and reject any attempts
   to use them.

 - For MachineInfo, we just turn them into the Parameters BLOB or put them in
   the appropriate column.

 - For RunInfo, we just turn them into the Parameters BLOB or put them in the
   appropriate column.

   We will need to extract the run_order value and put it into the order table.

   This points out that we probably want the order table to be UNIQUE across all
   entries. Can we do that in SQLite3?

 - For the sample status field, we will need to convert the existing format,
   which encodes samples via multiple tests, into the new format.

   This is the one area where I really don't want to change the test data
   serialization format, so maybe this is even the right long term approach.

   In the new model of collapsing samples into a single row, this is going to
   mean that we will need to assume that tests mangled into subtest names are
   specified in the same order.

Unaddressed Issues
~~~~~~~~~~~~~~~~~~

There are couple design problems in the current system which I *am not*
intending to address as part of the v0.4 changes.

Machine Naming
++++++++++++++

LNT currently allows a "name" for machines, which is very arbitrary. It would be
nice to eliminate this field completely, but we should probably eliminate the
name from the UI completely first, and make sure that is workable.
