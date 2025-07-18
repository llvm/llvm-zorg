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
 - MacOS runners for HLSL managed by Microsoft.
 - GCP windows/linux runners managed by Google.
 - GCP linux runners setup for libcxx managed by Google.

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

We have two clusters to compose a high availability setup. The description
below describes an individual cluster, but they are largely identical.
Any relevant differences are explicitly enumerated.

Our runners are hosted on GCP Kubernetes clusters, and use the
[Action Runner Controller (ARC)](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller).
The clusters have 4 main pools:
  - llvm-premerge-linux
  - llvm-premerge-linux-service
  - llvm-premerge-windows
  - llvm-premerge-libcxx

**llvm-premerge-linux-service** is a fixed pool, only used to host the
services required to manage the premerge infra (controller, listeners,
monitoring). Today, this pool has three `e2-highcpu-4` machine.

**llvm-premerge-linux** is a auto-scaling pool with large `n2-standard-64`
VMs. This pool runs the Linux workflows. In the US West cluster, the machines
are `n2d-standard-64` due to quota limitations.

**llvm-premerge-windows** is a auto-scaling pool with large `n2-standard-32`
VMs. Similar to the Linux pool, but this time it runs Windows workflows. In the
US West cluster, the machines are `n2d-standard-32` due to quota limitations.

**llvm-premerge-libcxx** is a auto-scaling pool with large `n2-standard-32`
VMs. This is similar to the Linux pool but with smaller machines tailored
to the libcxx testing workflows. In the US West Cluster, the machines are
`n2d-standard-32` due to quota limitations.

### Service pool: llvm-premerge-linux-service

This pool runs all the services managing the presubmit infra.
  - Action Runner Controller
  - 1 listener for the Linux runners.
  - 1 listener for the windows runners.
  - Grafana Alloy to gather metrics.
  - metrics container.

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

### Worker pools : llvm-premerge-linux, llvm-premerge-windows, llvm-premerge-libcxx

To make sure each runner pod is scheduled on the correct pool (linux or
windows, avoiding the service pool), we use labels and taints.

The other constraints we define are the resource requirements. Without
information, Kubernetes is allowed to schedule multiple pods on the instance.
So if we do not enforce limits, the controller could schedule 2 runners on
the same instance, forcing containers to share resources.

Those bits are configures in the
[linux runner configuration](linux_runners_values.yaml),
[windows runner configuration](windows_runner_values.yaml), and
[libcxx runner configuration](libcxx_runners_values.yaml).

