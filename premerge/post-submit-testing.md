# Post Submit Testing

## Introduction

While this infrastructure is focused on premerge testing, it is also important
to make sure that the specific configuration we are testing is tested post
commit as well. This document outlines the motivation for the need to test this
configuration post commit how we plan on implementing this to ensure we get fast
feedback scalably, and why we are utilizing this design over others.

## Background/Motivation

LLVM has two types of testing upstream: premerge and postcommit. The premerge
testing is performed using Github Actions every time a pull request (PR) is
updated before it is merged. Premerge testing is performed using this
infrastructure (specifically the `./premerge` folder in llvm-zorg). Landing a PR
consists of squashing the changes into a single commit and adding that commit to
the `main` branch in the LLVM monorepo. We care specifically about the state of
the `main` branch because it is what the community considers to be the canonical
tree. Currently, commits can also be added to the `main` branch by directly
pushing to the main branch. Commits pushed directly to `main` are not tested
through the premerge pipeline as they skip the PR merge process. After a new
commit lands in the `main` branch, postcommit testing is performed. Most
postcommit testing is performed through the Buildbot infrastructure. The main
Buildbot instance for LLVM has a web instance hosted at
[lab.llvm.org](https://lab.llvm.org/buildbot/#/builders). When a new commit
lands in `main` the Buildbot instance (sometimes referred to as the Buildbot
master) will trigger many different builds, base on the configurations
defined in the llvm-zorg repository under the `buildbot/` folder. These
configurations are run on Buildbot workers that are hosted by the community.
Some builders build too slowly to keep up with the pace of commits to `main`,
so test batches of commits. This often results in a large number of
erroneous notifications due to the list of possible culprits for a breakage
being more than a single commit.

For premerge testing, we do not want to notify LLVM developers about failures
already happening in `main` irrelevant to their changes. This requires knowing
the state of `main` at the time the premerge testing for a PR was started. We
also want information on the current state of `main` to empower the community
with information that they need to revert or forward-fix problematic commits.
Problematic commits can occur without being caught by the premerge system due to
someone directly pushing a commit to `main`, or if multiple PRs become
problematic only when combined. This means we need to test the premerge
configuration postcommit as well so that we can determine the state of `main`
(in terms of whether the build passed/failed and what tests failed, if any) at
any given point in time.

## Design

The LLVM Premerge system has two clusters, namely the central cluster in the
Google Cloud Platform (GCP) zone `us-central1-a` and the west cluster in the GCP
zone `us-west1`. We run two clusters in different zones for redundancy so that
if one fails, we can still run jobs on the other cluster. For postcommit
testing, we plan on setting up builders attached to the Buildbot master
described above. We will run one builder on the central cluster and one in the
west cluster. This ensures the configuration is highly available (able to
tolerate an entire cluster going down), similar to the premerge testing. The
builders will be configured to use a script that will launch testing on each
commit to `main` as if it was being run through the premerge testing pipeline, with some small but significant differences. The post submit
testing is intended to be close to the premerge configuration. but will be
different in some key ways. The differences and motivation for them is described
more thoroughly in the [testing configuration](#testing-configuration) section.
These builds will be run inside containers that are distributed onto the cluster
inside kubernetes pods (the fundamental schedulable unit inside kubernetes).
This allows for kubernetes to handle details like what machine a build should
run on. Allowing kubernetes to handle these details also enables Google
Kubernetes Engine (GKE) to autoscale the node pools so we are not paying for
unneeded capacity. Launching builds inside pods also allows for each builder to
handle multiple builds at the same time.

In terms of the full flow, any commit (which can be from direct pushes or
merging pull requests) pushed to the LLVM monorepo will get detected by the
buildbot master. The Buildbot master will invoke Buildbot workers running on our
clusters. These Buildbot workers will use custom builders to launch a build
wrapped in a kubernetes pod and report the results back to the buildbot master.
When the job is finished, the pod will complete and capacity will be available
for another build, or if there is nothing left to test GKE will see that there
is nothing running on one of the nodes and downscale the node pool.

### Annotated Builder

llvm-zorg has multiple types of builders. We plan on using an AnnotatedBuilder.
AnnotatedBuilders allow for the build to be driven using a custom python script
rather than directly dictating the shell commands that should be run to perform
the build. We need the flexibility of the AnnotatedBuilder to deploy jobs on the
cluster. AnnotatedBuilder based builders also enable deploying changes without
needing to restart the buildbot master. Without this, we have to wait for an
administrator of the LLVM buildbot master to restart it before our changes get
deployed. This could significantly delay updates or responses to incidents,
especially before the system is fully stable.

### Build Distribution

We want to be able to take advantage of the autoscaling functionality of the new
cluster to efficiently utilize resources. To do this, we plan on having the
AnnotatedBuilder script launch builds as kubernetes pods. This allows for
kubernetes to assign the builds to nodes and also allows autoscaling through the
same mechanism that Github Actions Runner Controller (ARC) uses to autoscale.
This enables us to quickly process builds at peak times and not pay for extra
capacity when commit traffic is quiet, ensuring our resource use is efficient
while still providing fast feedback.

Using the kubernetes API inside of a python script (our AnnotatedBuilder
implementation) to launch builds does add some complexity. However, we belive
the additional complexity is justified as it allows us to achieve our goals
while maintaining efficient resource usage.

### Testing Configuration

By testing configuration, we mean both the environment that the tests run in,
and the set of tests that run. The testing configuration will be as close to the
premerge configuration as possible. We will be running all tests inside the same
container with the same scripts (the `monolithic-linux.sh` and
`monolithic-windows.sh` scripts). However, there will be one main difference
between the premerge and postcommit testing configurations. In the postcommit
configuration we propose testing all projects on every commit rather than only
testing the projects that themselves changed or had dependencies that changed.
We propose this for two main reasons. Firstly, Buildbot does not have support
for heterogenous build configurations. This means that testing a different set
of projects within a single builder depending upon the contents of the commit
could easily cause problems. More notifications could be produced if certain
projects (that were only triggered by some files) were failing and some were
passing which would significantly increase false positive notifications. For
example, supposed that we have three commits that land in `main` and run through
postcommit testing: commit A that touches MLIR, commit B that touches
clang-tidy, and commit C that modifies MLIR. Commit A lands, then commit B, then
commit C. If commit A introduces MLIR test failures into an otherwise clean
slate, we would see the following events:

1. Commit A lands. Because it touches MLIR, the buildbot worker runs the MLIR
   tests. Some of the tests fail. The buildbot "turns red" and a notification is
   sent out to the PR author.
2. Commit B lands. Since it touches clang-tidy, the buildbot worker runs the
   clang-tidy tests. All of the tests pass. The buildbot "turns green". No
   notifications are sent out since everything is passing.
3. Commit C lands. Since it touches MLIR, the buildbot workers runs the MLIR
   tests. The problem introduced in commit A still exists, so some tests fail.
   No new tests fail. Since the buildbot was previously green due to the
   interspersed clang-tidy commit, a notification is still sent out to the
   author of commit C.

When running premerge tests on a PR, we also explicitly do not test certain
projects even though their dependencies change. While we do this because we
suspect interactions resulting in test failures would be quite rare, it is
possible, and having a postcommit configuration catch these rare failures would
be useful.

### Data Storage

The hosted Buildbot master instance at [lab.llvm.org](https://lab.llvm.org)
contains results for all recent postcommit runs. We plan on querying the results
from the buildbot master because they are already available and that is where
they will natively be reported after the infrastructure is set up. Buildbot
supports a [REST API](https://docs.buildbot.net/latest/developer/rest.html) that
would allow for easily querying the state of a commit in `main`.

For the proposed premerge advisor that tells the user what tests/build failures
they can safely ignore, we need to know what is currently failing on `main`.
Each pull request is tested as if it was merged into main, which means the
commit underneath the PR is very recent. If a premerge run fails, the premerge
advisor will find the commit from `main` the PR is being tested on. It will then
query the Buildbot master using the REST API for the status of that commit.
It can then report the appropriate status to the user. Having the status will
let the premerge advisor ignore pestering LLVM developers with failures
unrelated to their changes.

## Alternatives Considered

Originally, we were looking at running postcommit testing through Github
Actions, like the premerge tests. This is primarily due to it being easy to
implement (a single line change in the Github Actions workflow config) and also
easy to integrate with the Github API for implementation of the premerge testing
advisor. More detailed motivation for the doing postcommit testing directly
through Github is available in the
[discourse RFC thread](https://discourse.llvm.org/t/rfc-running-premerge-postcommit-through-github-actions/86124)
where we proposed doing this. We eventually decided against implementation in
this way for a couple of reasons:

1. Nonstandard - The standard postcommit testing infrastructure for LLVM is
   through Buildbot. Doing postcommit testing for the premerge configuration
   through Github would represent a significant departure from this. This means
   we are leaving behind some common infrastructure and are also forcing a new
   unfamiliar postcommit interface on LLVM contributors.
2. Notifications - This is the biggest issue. Github currently gives very little
   control over the notifications that are sent out when the build fails or gets
   cancelled. This is specifically a problem with Github sending out
   notifications for build failures even if the previous build has failed. This
   can easily create a lot of warning fatigue which is something we are putting
   a lot of effort in to avoid. We want the premerge systemto be perceived as
   reliable, have people trust its results, and most importantly, have people
   pay attention to failures when they do occur. They are significantly more
   likely to pay attention when they are the author of the patch getting the
   notification and the feedback is actionable.
3. Customization - Buildbot can be customized around issues like notifications
   whereas Github cannot. Github is not particularly responsive on feature
   requests and their notification story has been poor for a while, so their
   lack of customization is a strategic risk.
