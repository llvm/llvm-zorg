# LLVM Premerge infra - GCP runners

This document describes how the GCP based presubmit infra is working, and
explains common maintenance actions.

## Overview

Presubmit tests are using GitHub workflows. Executing GitHub workflows can be
done in two ways:
 - using GitHub provided runners.
 - using self-hosted runners on GCP.

GitHub provided runners are not very powerful, and have limitations, but they
are **FREE**.
Self hosted runners are large virtual machines, very powerful, but they are
**expensive**.

To balance cost/performance, we keep both runners.
 - simple jobs like `clang-format` shall run on GitHub runners.
 - building & testing LLVM shall be done on self-hosted runners.

The choice between self-hosted & GitHub runners is done in the workflow
definition:

```
jobs:
  my_job_name:
    # Runs on expensive GCP VMs.
    runs-on: llvm-premerge-linux-runners
```

Our self hosted runners come in two flavors:
  - linux
  - windows

## GCP runners - Architecture overview

Our runners are hosted on a GCP Kubernetes cluster, and use the [Action Runner Controller (ARC)](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller).
The cluster has 3 nodes:
  - llvm-premerge-linux
  - llvm-premerge-linux-service
  - llvm-premerge-windows

**llvm-premerge-linux-service** is a fixed node, only used to host the
services required to manage the premerge infra (controller, listeners,
monitoring). Today, this node has only one e2-small machine.

**llvm-premerge-linux** is a auto-scaling node with large c2d-highcpu-56 VMs.
This node runs the linux workflows.

**llvm-premerge-windows** is a auto-scaling node with large c2d-highcpu-56 VMs.
Similar to the linux node, but this time it runs Windows workflows.

### Service node: llvm-premerge-linux-service

This node runs all the services managing the presubmit infra.
  - Action Runner Controller
  - 1 listener for the linux runners.
  - 1 listener for the windows runners.
  - Grafana Alloy to gather metrics.


The Action Runner Controller listens on the LLVM repository job queue.
Individual jobs are then handled by the listeners.

How a job is run:
 - The controller informs GitHub the self-hosted runner is live.
 - A PR is uploaded on GitHub
 - The listener finds a linux job to run.
 - The listener creates a new runner pod to be scheduled by Kubernetes.
 - Kubernetes adds one instance to the linux node to schedule new pod.
 - The runner starts executing on the new node.
 - Once finished, the runner dies, meaning the pod dies.
 - If the instance is not reused in the next 10 minutes, Kubernetes will scale
   down the instance.

To make sure each pod is scheduled on the correct node (linux or windows,
avoiding the service node), we use labels & tains.
Those tains are configured in the [ARC runner templates](premerge/linux_runners_values.yaml).

