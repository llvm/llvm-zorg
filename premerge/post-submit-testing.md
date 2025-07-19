# Post Submit Testing

## Introduction

While this infrastructure is focused on premerge testing, it is also important
to make sure that the specific configuration we are testing is tested post
commit as well. This document outlines the motivation for the need to test this
configuration post commit, why we are utilizing this design over others, and
how we plan on implementing this to ensure we get fast feedback scalably.

## Background/Motivation

It is important that we test the premerge configuration postcommit as well.
This enables easily checking the state of `main` at any given time and also
easily pinpointing where exactly `main` has broken which enables figuring
out which commit to revert/fix forward to get everything back to green.
Having information on the state of `main` is also important for certain kinds
of automation, like the planned premerge testing advisor that will let
contributors know if tests failing in their PR are already failing at `main`
and that it should be safe to merge despite the given failures.

Originally, we were looking at running postcommit testing through Github
Actions as well. This is primarily due to it being easy (a single line
change in the Github Actions workflow config) and also easy integration
with the Github API for implementation of the premerge testing advisor.
More detailed motivation for the doing postcommit testing directly through
Github is available in the [discourse RFC thread](https://discourse.llvm.org/t/rfc-running-premerge-postcommit-through-github-actions/86124)
where we proposed doing this. We eventually decided against implementation in
this way for a couple of reasons:

1. Nonstandard - The standard postcommit testing infrastructure for LLVM is
through Buildbot. Doing postcommit testing for the premerge configuration
through Github would represent a significant deparature from this. This means
we are leaving behind some common infrastructure and are also forcing a new
unfamiliar postcommit interface on LLVM contributors.
2. Notifications - This is the biggest issue. Github currently gives very
little control over the notifications that are sent out when the build
fails or gets cancelled. This is specifically a problem with Github sending
out notifications for build failures even if the previous build has failed.
This can easily create a lot of warning fatigue which is something we are
putting a lot of effort in to avoid so that the premerge system is
percieved as reliable, people trust its results, and most importantly,
people pay attention to failures when they do occur because they are
caused by the patch getting the notification and are actionable.
3. Customization - Buildbot can be customized around issues like notifications
whereas Github cannot. Github is not particularly responsive on feature
requests and their notification story has been poor for a while, so their
lack of customization is a strategic risk.

## Design

The overall design involves using an annotated builder that will be deployed
on both the central and west clusters for a HA configuration. The annotated
builder will consist of a script that runs builds inside kubernetes pods
to enable autoscaling.

In terms of the full flow, a commit pushed to the LLVM monorepo will get
detected by the buildbot master. The Buildbot master will invoke Buildbot
workers running on our clusters. These Buildbot workers will use annotated
builders to launch a build wrapped in a kubernetes pod and report the results
back to the buildbot master. When the job is finished, the pod will complete
and capacity will be available for another build, or if there is nothing
left to test GKE will see that there is nothing running on one of the nodes
and downscale the node pool.

### Annotated Builder

llvm-zorg has multiple types of builders. We plan on using an AnnotatedBuilder.
We need the flexibility of the AnnotatedBuilder (essentially a custom python
file that runs the build) to deploy jobs on the cluster. AnnotatedBuilder based
builders also enable deploying changes without needing to restart the buildbot
master. Without this, we have to wait for an administrator of the LLVM buildbot
master to restart it before our changes get deployed. This could significantly
delay updates or responses to incidents, especially before the system is fully
stable and we need to modify it relatively frequently.

### Build Distribution

We want to be able to take advantage of the autoscaling functionality of the
new cluster to efficiently utilize resources. To do this, we plan on having the
AnnotatedBuilder script launch builds as kubernetes pods. This allows for
kubernetes to assign the builds to nodes and also allows autoscaling through
the same mechanism that Github autoscales. This allows for us to quickly
process builds at peak times and not pay for extra capacity when commit
traffic is quiet. This is essentially for ensuring our resource use is
efficient while still providing fast feedback.

Using the kubernetes API inside of a python script to launch builds does add
some complexity. However, we do not believe we need too much added
complexity to achieve our goal here and this allows for vastly more efficient
resource usage.

### Testing Configuration

The testing configuration will be as close to the premerge configuration as
possible. We will be running all tests inside the same container with the
same scripts (the `monolithic-linux.sh` and `monolithic-windows.sh` scripts).
However, there will be one main difference between the premerge and postcommit
configuration. In the postcommit configuration we propose testing all projects
on every commit rather than only testing the projects that themselves changed
or had dependencies that changed. We propose this for two main reasons.
Firstly, Buildbot does not have support for heterogenous build configurations.
This means that testing a different set of projects in a single build
configuration depending upon what files changed could easily produce many
more notifications if certain configurations were failing and some were
passing which defeats the point of using Buildbot in the first place. For
example, if there is a MLIR change that fails, an unrelated clang-tidy change
that passes all tests that lands afterwards, and then another MLIR change, a 
notification will also be sent out on the second MLIR change because the
clang-tidy change turned the build back to green. We also explicitly do not
test certain projects even though their dependencies change, and while we do
this because we suspect interactions resulting in test failures would be quite
rare, it is possible, and having a postcommit configuration catch these rare
failures would be useful.
