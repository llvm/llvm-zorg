# LLVM Premerge infra - GCP runners

This document describes how the GCP based presubmit infra is working, and
explains common maintenance actions.

## Overview

Presubmit tests are using GitHub workflows. Executing GitHub workflows can be
done in two ways:
 - using GitHub provided runners.
 - using self-hosted runners.

GitHub provided runners are not very powerful, and have limitations, but they
are **FREE**.
Self hosted runners are self-hosted, meaning they can be large virtual
machines running on GCP, very powerful, but **expensive**.

To balance cost/performance, we keep both types.
 - simple jobs like `clang-format` shall run on GitHub runners.
 - building & testing LLVM shall be done on self-hosted runners.

LLVM has several flavor of self-hosted runners:
 - libcxx runners.
 - MacOS runners for HLSL managed by Microsoft.
 - GCP windows/linux runners managed by Google.

This document only focuses on Google's GCP hosted runners.

Choosing on which runner a workflow runs is done in the workflow definition:

```
jobs:
  my_job_name:
    # Runs on expensive GCP VMs.
    runs-on: llvm-premerge-linux-runners
```

Our self hosted runners come in two flavors:
  - Linux
  - Windows

## GCP runners - Architecture overview

Our runners are hosted on a GCP Kubernetes cluster, and use the [Action Runner Controller (ARC)](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller).
The cluster has 3 pools:
  - llvm-premerge-linux
  - llvm-premerge-linux-service
  - llvm-premerge-windows

**llvm-premerge-linux-service** is a fixed pool, only used to host the
services required to manage the premerge infra (controller, listeners,
monitoring). Today, this pool has three `e2-highcpu-4` machine.

**llvm-premerge-linux** is a auto-scaling pool with large `n2-standard-64`
VMs. This pool runs the Linux workflows.

**llvm-premerge-windows** is a auto-scaling pool with large `n2-standard-64`
VMs. Similar to the Linux pool, but this time it runs Windows workflows.

### Service pool: llvm-premerge-linux-service

This pool runs all the services managing the presubmit infra.
  - Action Runner Controller
  - 1 listener for the Linux runners.
  - 1 listener for the windows runners.
  - Grafana Alloy to gather metrics.

The Action Runner Controller listens on the LLVM repository job queue.
Individual jobs are then handled by the listeners.

How a job is run:
 - The controller informs GitHub the self-hosted runner set is live.
 - A PR is uploaded on GitHub
 - The listener finds a Linux job to run.
 - The listener creates a new runner pod to be scheduled by Kubernetes.
 - Kubernetes adds one instance to the Linux pool to schedule new pod.
 - The runner starts executing on the new node.
 - Once finished, the runner dies, meaning the pod dies.
 - If the instance is not reused in the next 10 minutes, the autoscaler
   will turn down the instance, freeing resources.

### Worker pools : llvm-premerge-linux, llvm-premerge-windows

To make sure each runner pod is scheduled on the correct pool (linux or
windows, avoiding the service pool), we use labels & taints.
Those taints are configured in the
[ARC runner templates](linux_runners_values.yaml).

The other constraints we define are the resource requirements. Without
information, Kubernetes is allowed to schedule multiple pods on the instance.
So if we do not enforce limits, the controller could schedule 2 runners on
the same instance, forcing containers to share resources.
Resource limits are defined in 2 locations:
 - [runner configuration](linux_runners_values.yaml)
 - [container template](linux_container_pod_template.yaml)

