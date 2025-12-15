# Premerge Advisor

## Introduction

While the premerge testing infrastructure is generally reliable, tests that are
broken at HEAD, or tests that are flaky can significantly degrade the user
experience. Reporting failures unrelated to the PR being worked on can lead to
warning fatigue. Warning fatigue can self reinforce when people land failing
tests into main that they believe are unrelated. This causes more false positive
failures on other premerge testing invocations, leading to more warning
fatigure. To address these issues we propose to implement a "premerge advisor".
The premerge advisor is designed to run after premerge testing and signal to the
user whether the failures can be safely ignored because they are flaky or broken
at head, or whether they should be investigated further.

## Background/Motivation

The usefulness of the premerge system is significantly impacted by how much
people trust it. People trust the system less when the issues reported to them
are unrelated to the changes that they are currently working on. False positives
occur regularly whether due to flaky tests, or due to tests already being broken
at head (perhaps by a previous commit). Efforts to fix these issues at the
source and keep main always green and deflake tests are ongoing, but not a
scalable solution to the problem of false positive failures. It is also not
reasonable to expect PR authors to spend time familiarizing themselves with all
known flaky tests and dig through postcommit testing logs to see if the failures
in their premerge run also occur in main. These alternatives are further
explored in the section on [alternatives considered](#alternatives-considered).
Having tooling to automatically run through the steps that one would otherwise
need to perform manually would ensure the analysis on every failed premerge run
is thorough and likely to be correct.

## Design

The premerge advisor will consist of three main parts: jobs uploading failure
information, a web server and database to store and query failure information,
and tooling to write out a verdict about the failures to comments on Github.
When a job runs premerge or postcommit and there are build/test failures, it
will upload information to the web server containing information on the failure
like the test/build action that failed and the exact log. The web server will
then store this information in a format that makes it easy to query for later.
Every premerge run that encounters build/test failures will then query the web
server to see if there are any matching build/test failures for the version of
`main` that the PR has been merged into. If there are, the web server can
respond with the failure information and signal that the failures can be safely
ignored for that premerge run. If the failures are novel, then the web server
can signal that the failures should be investigated more thoroughly. If there
are failures, the premerge advisor can then write out a comment on the PR
explaining its findings.

### Processing and Storing Failures

A key part of the premerge advisor is infrastructure to store and process build
failure information so that it can be queried later. We plan on having jobs
extract failure logs and upload them to a web server. This web server in
addition to having an endpoint to accept uploads of failure information without
returning any analysis will have an explanation endpoint that will accept test
failure information (logs and filenames) and return whether or not they are
broken at `main`, flaky, or novel test failures due to the PR.

For the premerge jobs running through Github Actions, we plan on using the
existing `generate_test_report` scripts that are currently used for generating
summaries on job failures. When the job ends and there is a failure, there would
be a script that runs, utilizing the `generate_test_report` library to extract
failure information, and then uploads the information to the web server.
Information on how the premerge jobs will query the server and display results
about flaky/already broken tests is in [the section below](#informing-the-user).
We plan on having both the premerge and [postcommit
jobs](post-submit-testing.md) upload failure information to the web server. This
enables the web server to know about failures that are not the result of mid-air
collisions before postcommit testing has been completed. Postcommit testing can
take upwards of 30 minutes, during which the premerge advisor would not be able
to advise that these failures are due to a broken `main`. Data from both
postcommit and premerge testing will be associated with a commit SHA for the
base commit in main. Premerge testing data will additionally have a PR
associated with it to enable disambiguating between failures occurring in `main`
at a specific commit and failures only occurring in a PR. All failure
information will be stored in the database. When testing for a PR is completed
and there are failures, premerge will then be able to query the advisor to
explain any outstanding failures. The advisor will compare the logs from the
premerge run to the database and return its results, namely whether or not any
of the failures exist at `HEAD` or are known flakes.

We plan on implementing the web server in python with the `flask` library. All
contributors to the premerge infrastructure are already familiar with Python,
building web servers in Python with `flask` is relatively easy, and we do not
need high performance or advanced features. For storage, we plan on using SQLite
as it has support built in to Python, does not require any additional complexity
in terms of infrastructure setup, and is reliable.

Given we have two identical clusters that need to be able to function
independently of each other, we also need to duplicate the web server for the
premerge advisor. Queries will go to the cluster-local premerge advisor web
server. Failure uploads will directly write to both premerge advisor containers.
This could lead to situations where uploading to one server succeeds while it
fails writing to the other one, resulting in inconsistent state between the
clusters. This is not a major concern because in the rare event we do end up
with inconsistent states, the only major concern would be inconsistent results
returned between the clusters. Uploading directly to both premerge containers
and explicitly allowing inconsistent state means we do not need to maintain any
state replication/consistency machinery, which would add significant complexity
and maintenance costs.

For the database, we will have two tables, one called `failures` to store
failure information, and one called `commits` that will be used to map commit
SHAs to SVN like indices. The `commits` table will simply have two columns,
mapping SHAs to indices. The failure table is designed to have rows describing
individual test failures, and the schema looks like the following:

* `source_type` - Whether the failure information comes from a postcommit run or
  from a premerge run.
* `base_commit_sha` - The SHA of the base commit. For premerge runs, this is the
  commit in `main` (or the user branch) that the PR is based on top of. For
  postcommit runs, this is simply the SHA of the commit being tested.
* `commit_index` - The index of the base commit, assuming the base commit is in
  `main`.
* `source_id` - The ID of the source. For buildbot runs, this is the buldbot run
  number. For premerge runs, this is the Github Actions workflow run ID.
* `test_file` - The test file/compilation unit where the failure occurred.
* `failure_message` - Any failure message text associated with the failure.
* `platform` - The platform (including OS and architecture) where the failure
  occurred.

### Classifying Test Failures

When the web server is sent a request to explain a list of failures, it needs to
be able to determine whether a failure has occurred previously. To do this, the
web server will keep a list of currently active failures in `main` and a list of
flaky tests. The list of flaky tests will be computed from historical data on
startup from a rolling window of data. The exact heuristic is left to
implementation as it will likely require some experimentation, but will look at
whether or not the test has been failing periodically over a long period of
time. The list of currently active failures will initially be taken from the
last known postcommit run. If a new postcommit run shows additional failures
that are not in the flake list, they will be added to the currently active
failure list. Failures in the currently active list not present in the latest
postcommit run will be removed from the currently active list. In the future, we
want to look at information from PRs to improve the latency of failures/passes
making their way into the system due to postcommit testing currently having a
minimum latency of 30 minutes.

Failures will be identified as being the same through a combination of the
test name and likely a fuzzy match of the test error output. The exact details
are left to implementation as they will likely require some experimentation
to get right.

These tradeoffs do leave open the possibility that we incorrectly identify tests
as being broken at head in certain extenuating circumstances. Consider a
situation where someone lands commit A breaking a test, immediately after lands
commit B fixing that test, and then opens a PR, C, that also breaks the test in
the same way around the same time. If commit B was directly pushed, or merged
without waiting for premerge to finish, then the test failure will still be in
the currently active failure list. The failure for PR C will then be marked as
failing at HEAD despite it not actually failing at HEAD. Given the low
probability of this occurring due to the same test needing to be broken, the
error message needing to be extremely similar, and the exact timing
requirements, we deem this an acceptable consequence of the current design. To
alleviate this issue, we would end up marking many more failures broken at main
as true failures due to the latency of postcommit testing.

### Informing the User

Once a workflow has completed, no actions related to the premerge advisor will
be performed if there are no failures. If there are failures, they will be
uploaded to the web server. Afterwards, the premerge workflow then makes a
request to the server asking if it can explain the failures as either existing
in `main` or as flaky.

After the response from the server has been recieved, the workflow will then
construct a comment. It will contain the failure information, and if relevant,
information/links showing the tests are flaky (and the flakiness rate) or are
broken in `main`. We plan to construct the comment in a manner similar to the
code formatting action. We will create one comment on the first workflow failure
and then update that comment everytime we get new data. This prevents creating
too much noise. This does mean that the comment might get buried in long running
reviews, but those are not the common case and people should learn to expect to
look for the comment earlier in the thread in such cases.

If all of the failures in the workflow were successfully explained by the
premerge advisor as flaky or already broken in `main`, then the premerge
workflow will be marked as successful despite the failure. This will be
achieved by having the build/test step always marked as successful. The
premerge advisor will then exit with a non-zero exit code if it comes
across non-explainable failures.

## Alternatives Considered

There are two main alternatives to this work. One would be to do nothing and let
users figure out these failures on their own, potentially with documentation to
better inform them of the process. The other alternative would be to work on
keeping `main` green all the time and deflake tests rather than work on a
premerge advisor. Both of these alternatives are considered below.

### Deflaking Tests and Keeping Main Green

Instead of putting effort into building the premerge advisor, we could also be
putting effort into deflaking tests and making process changes to ensure `main`
is not broken. These fixes have the bonus of being useful for more than just
premerge, also improving reliability for buildbots and any downstream testing.
While we probably could achieve this at least temporarily with process changes
and a concentrated deflaking effort, we do not believe this is feasible or
scalable.

In order to ensure that main is not broken by new patches, we need to ensure
that every commit is tested directly on top of `main` before landing. This is
not feasible given LLVM's current processes where pushing directly to main is a
critical component of several developer's workflows. We would also need to
reduce the risk of "mid-air collisions", patches that pass premerge testing, but
fail on `main` when landed due to the patch in its original state not being
compatible with the new state of main. This would most likely involve merge
queues which would introduce new CI load and are also not compatible with LLVM's
existing practices.

Doing an initial effort for deflaking tests is also not scalable from an
engineering effort perspective. While we might be able to deflake existing
tests, additional flaky tests will get added in the future, and it is likely not
feasible to dedicate enough resources to deflake them. Policy improvements
around reverting patches that introduce flaky tests might make this more
scalable, but relies on quick detection of flaky tests, which might be difficult
for tests that experience flaky failures very rarely.

### Not Doing Anything

Alternatively, we could not implement this at all. This system adds quite a bit
of complexity and adds new failure modes. False positive failures also are not
that frequent. However, even a relatively small percentage of failures like we
are observing significantly impacts trust in the premerge system, which
compounds the problem. People learn not to trust the results, ignore true
failures caused by their patch, and then land it, causing many downstream
failures. The frequency of these incidents (typically multiple times per week)
means that it is pretty likely most LLVM developers will run into this class of
issue sooner or later.

The complexity is also well confined to the components specific to this new
infrastructure, and the new failure modes can be mitigated through proper error
handling at the interface between the existing premerge system and the new
premerge advisor infrastructure.

### Using an Existing System

There are several different platforms that offer post workflow test analysis
around issues like flaky tests. These platforms include [trunk.io](trunk.io),
[mergify](mergify.com), and
[DataDog Test Optimization](docs.datadoghq.com/tests/). However, only one of
these platforms, trunk.io, supports marking jobs as green if the only tests that
failed were flaky through their
[quarantining feature](docs.trunk.io/flaky-tests/quarantining). However, it
supports little customization over commenting on PRs (either is always on, even
successful runs, or always off), and our notification story is of high
importance. We want the signal to noise ratio of premerge notifications to be
high. The system should simply say nothing if everything has gone well.

In addition to being able to mark jobs as green if only flaky tests failed,
we also need to be able to keep track of failures in `main` and not block
merging on them. None of the systems considered support this functionality,
making the assumption that `main` should always be green (through mechanisms
like a merge queue), or should be fixed quickly. Due to the scale and
contribution norms in LLVM, keeping `main` always green is hard to enforce
at scale, so we need to support this feature.

The cost of using these systems is also nontrivial given how frequently
the premerge pipeline gets run and the number of tests that get run. These
systems are typically priced based on a number of "test spans" (a single
test invocation), with both mergify trunk.io and DataDog pricing ingesting
1M test spans at $3. We run ~300k tests per premerge run. Using a
conservative estimate of 400 premerge runs per weekday, no runs on weekends,
we end up with a cost of almost $100k per year, not including any potential
open source discounts.
