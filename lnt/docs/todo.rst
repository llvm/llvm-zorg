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

It is obvious that we need to move the "test status" indication into the sample
field. However, this raises the question of what *else* should move into the
status field. Is there a more general problem here?

Also, just moving the test status in introduces other modeling problem, for
example what about tests for which there is no meaningful notion of status? For
example, an aggregate test that may produce a large number of results on
success. Does it make sense to think about all those tests as succeeding? It
seems ok, but not quite accurate.

The only other option I can think of at the moment would be to allow multiple
kinds of samples. This might be worth considering, because it also solves other
problems like associating types with samples (instead of just requiring every
sample to be a float).

In particular, one thing I would very much like would be to be able to report
the hash of the generated exutable along whenever we compile something (and
eventually dispatch them to an archival server).

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

Proposed Table Design
~~~~~~~~~~~~~~~~~~~~~

Global
++++++
StatusKind
 - ID
 - Name

TestSuite
 - ID
 - Name
 - DBKeyName

   The name we use to prefix the per test suite databases.

 - Version

   The version of the schema used for the per-test suite databases (probably
   encoded as LNT version).

TestSuiteMachineKeys
 - ID INTEGER PRIMARY KEY
 - TestSuite FOREIGN KEY TestSuite(ID)
 - Name VARCHAR(512)
 - Type?
 - Default?
 - InfoKey

   This is used for migration purposes (possibly permanent), it is the key name
   to expect this field to be present as in a submitted info dictionary.

TestSuiteOrderKeys
 - ID INTEGER PRIMARY KEY
 - TestSuite FOREIGN KEY TestSuite(ID)
 - Name VARCHAR(512)
 - Index INTEGER

   The ordinal index this order key should appear in.

 - Type?
 - Default?

TestSuiteRunKeys
 - ID INTEGER PRIMARY KEY
 - TestSuite FOREIGN KEY TestSuite(ID)
 - Name VARCHAR(512)
 - Type?
 - Default?
 - InfoKey

   This is used for migration purposes (possibly permanent), it is the key name
   to expect this field to be present as in a submitted info dictionary.

Per Test Suite
++++++++++++++

<TS>_Machine
 - ID INTEGER PRIMARY KEY
 - Name VARCHAR(512)
 - Number INTEGER
 - ... additional keys here are defined by TestSuite(MachineKeys) relation ...

   Examples would be things like "uname", "CPU". These are all specified by the
   test suite.

 - Parameters JSON BLOB
 - Indices::
   
     CREATE INDEX [<TS>_Machine_ID_IDX] ON Machine(ID);
     CREATE INDEX [<TS>_Machine_Name_IDX] ON Machine(Name);

<TS>_Run
 - ID INTEGER PRIMARY KEY
 - Machine FOREIGN KEY <TS>_Machine(ID)
 - StartTime DATETIME
 - EndTime DATETIME
 - Order FOREIGN KEY <TS>_Order(ID)

   This is the order of the tested products. The schema doesn't explicitly
   record any information about what the actual products under test are, though,
   so we just refer to this as the "order" of the run.

 - ... additional keys here are defined by TestSuite(RunKeys) relation ...

   Examples would be things like "optimization level", "architecture",
   etc. These are all specified by the test suite.

 - Parameters JSON BLOB

   Additional information a client might want to report in a run, but this will
   only be used for display on a per-Run basis. It is not information that we
   should ever attempt to construct queries on.

 - Indices::
   
     CREATE INDEX [<TS>_Run_ID_IDX] ON <TS>_Run(ID);

<TS>_Test
 - ID INTEGER PRIMARY KEY
 - Name VARCHAR(512)
 - Indices::

     CREATE INDEX [<TS>_Tests_ID_IDX] ON <TS>_Tests(ID);
     CREATE INDEX [<TS>_Tests_Name_IDX] ON <TS>_Tests(Name);

<TS>_Sample
 - ID INTEGER PRIMARY KEY
 - Run FOREIGN Key <TS>_Run(ID)
 - Test FOREIGN KEY <TS>_Test(ID)
 - Value REAL
 - Status FOREIGN KEY StatusKind(ID)
 - Indices::

     CREATE INDEX [<TS>_Samples_RunID_IDX] ON <TS>_Sample(RunID);
     CREATE INDEX [<TS>_Samples_TestID_IDX] ON <TS>_Sample(TestID);
     CREATE INDEX [<TS>_Samples_TestIDRunID_IDX] ON <TS>_Sample(TestID, RunID);

<TS>_Order
 - ID
 - ... keys here are defined by TestSuite(OrderKeys) relation ...

   Examples would be LLVMRevision, ClangRevision, etc. Eventually we could also
   support the use of git hashes to support users who have other test components
   or software in git repositories (the server would handle using those git
   hashes to construct an ordering).

   The order of these keys is the lexicographic ordering that defines the total
   ordering.

 - Indices::

     CREATE INDEX [<TS>_Order_ID_IDX] ON <TS>_Order(ID);

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

Unaddressed Issues
~~~~~~~~~~~~~~~~~~

There are couple design problems in the current system which I *am not*
intending to address as part of the v0.4 changes.

Test / Subtest Relationships
++++++++++++++++++++++++++++

We currently impose a certain amount of structure on the tests and mangle it
into the name (e.g., as "<test_name>.compile" or "<test_name>.exec", not to
mention the status indicators). The status indicators are going to go away in
the redesign, but we will still have the distinction between ".compile" and
".exec".

This works ok up to the point where we want to do things in the UI based on the
test structure (for example, separate out compile time results from execution
results). At the moment we have gross code in the UI which just happens to
"know" these manglings, but it would be much better to have this be explicit in
the schema.

While I don't have a plan to solve this in the current iteration, I can imagine
one way to solve this is to allow the test suite to define additional metadata
that is present in the Test table. We would allow that metadata to specify how
tests should be displayed, their units, etc.

This could be more important problem going forward if we wanted to start
reporting large numbers of additional statistics (like number of spills, etc.).

Machine Naming
++++++++++++++

LNT currently allows a "name" for machines, which is very arbitrary. It would be
nice to eliminate this field completely, but we should probably eliminate the
name from the UI completely first, and make sure that is workable.
