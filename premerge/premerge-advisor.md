# Premerge Advisor

## Introduction

While the premerge infrastructure is generally reliable, tests that are broken
at HEAD, or tests that are flaky can significantly degrade the user experience.
Failures unrelated to the PR being worked on can lead to warning fatigue which
can compound this problem when people land failing tests into main that they
believe are unrelated. The premerge advisor is designed to run after premerge
testing and signal to the user whether the failures can be safely ignored because
they are flaky or broken at head, or whether they should be investigated further.

## Background/Motivation

The usefulness of the premerge system is significantly impacted by how much
people trust it. People trust the system less when the issues reported to them
are unrelated to the changes that they are currently working on. False positives
occur regularly whether due to flaky tests, or due to main being broken. Efforts
to fix these issues at the source and keep main always green and deflake tests
are laudable, but not a scalable solution to the problem of false positive
failures. It is also not reasonable to expect PR authors to spend time
familiarizing themselves with all known flaky tests and dig through postcommit
testing logs to see if the failures in their premerge run also occur in main.
These alternatives are further explored in the section on
[alternatives considered](#alternatives-considered). Having tooling to
automatically run through the steps that one would otherwise need to perform
manually would ensure the analysis on every failed premerge run is thorough and
likely to be correct.

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
addition to having an endpoint to accept uploads will have an endpoint that will
accept test failure information (logs and filenames) and return whether or not
they are broken at `main`, flaky, or novel test failures due to the PR.

For the premerge jobs running through Github Actions, we plan on using the
existing `generate_test_report` scripts that are currently used for generating
summaries on job failures. When the job ends and there is a failure, there would
be a script that runs, utilizing the `generate_test_report` library to extract
failure information, and then uploading the information to the web server.
Information on how the premerge jobs will query the server and display results
about flaky/already broken tests is in
[the section below](#informing-the-user). We plan on having both the premerge
and postcommit jobs upload failure information to the web server. This enables
the web server to know about failures that are not the result of mid-air
collisions before postcommit testing has been completed. Postcommit testing can
take upwards of 30 minutes, during which the premerge advisor would not be able
to advise that these failures are due to a broken `main`.

We plan on implementing the web server in python with the `flask` library. All
contributors to the premerge infrastructure are already familiar with Python,
building web servers in Python with `flask` is relatively easy, and we do not
need high performance or advanced features. For storage, we plan on using SQLite
as it has support built in to Python, does not require any additional complexity
in terms of infrastructure setup, and is reliable.

Given we have two identical clusters that need to be able to function
independently of each other, we also need to duplicate the web server for the
premerge advisor. Queries and failure information uploads will go to the
cluster-local premerge advisor web server. Periodically (eg once every thirty
seconds), the web server will query the web server on the other cluster to see
if there is any new data that has not been propgated back to the other side yet.
It is easy to figure out what one side is missing as Github workflow runs are
numbered sequentially and git commits are also explicitly ordered. One side just
needs to send the latest commit SHA and workflow run it has all previous data
for, and the other side can reply with the data that it has past that point.
Explicitly synchronizing everytime without assumptions about the state of the
other side has benefits over just writing through, like ensuring that a cluster
that has been down for a significant amount of time is seamlessly able to
recover. Synchronization does not need to be perfect as test failures that are
flaky or broken at head will almost certainly show up in both clusters
relatively quickly, and minor discrepancies for queries between the clusters are
not a big deal.

### Informing the User

Once a workflow has completed, no actions related to the premerge advisor will
be performed if there are no failures. If there are failures, they will be
uploaded to the web server. Afterwards, the premerge workflow then makes a
request to the server asking if it can explain the failures as either existing
in `main` or as flaky.

After the response from the server has been recieved, the workflow will then
construct a comment. It will contain the failure information, and if relevant,
information/links showing the tests are flaky (and the flakiness rate) or are
broken in `main`. If all of the test failures are due to flakes or failures in
`main`, the comment will indicate to the user that they can safely merge their
PR despite the test failures. We plan to construct the comment in a manner
similar to the code formatting action. We will create one comment on the first
workflow failure and then update that comment everytime we get new data. This
prevents creating much noise. This does mean that the comment might get buried
in long running reviews, but those are not the common case and people should
learn to expect to look for the comment earlier in the thread in such cases.

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
existing practices for the same reason requiring premerge checks to be run
before landing are not.

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
