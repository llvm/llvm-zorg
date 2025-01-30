# Cluster configuration

The cluster is managed using Terraform. The main configuration is
[main.tf](main.tf).

---
NOTE: As of today, only Googlers can administrate the cluster.
---

Terraform is a tool to automate infrastructure deployment. Basic usage is to
change this configuration and to call `terraform apply` make the required
changes.
Terraform won't recreate the whole cluster from scratch every time, instead
it tries to only apply the new changes. To do so, **Terraform needs a state**.

**If you apply changes without this state, you might break the cluster.**

The current configuration stores its state into a GCP bucket.


## Accessing Google Cloud Console

This web interface is the easiest way to get a quick look at the infra.

---
IMPORTANT: cluster state is managed with terraform. Please DO NOT change
shapes/scaling, and other settings using the cloud console. Any change not
done through terraform will be at best overridden by terraform, and in the
worst case cause an inconsistent state.
---

The main part you want too look into is `Menu > Kubernetes Engine > Clusters`.

Currently, we have 3 clusters:
 - `llvm-premerge-checks`: the cluster hosting BuildKite Linux runners.
 - `windows-cluster`: the cluster hosting BuildKite Windows runners.
 - `llvm-premerge-prototype`: the cluster for those GCP hoster runners.

Yes, it's called `prototype`, but that's the production cluster.
We should rename it at some point.

To add a VM to the cluster, the VM has to come from a `pool`. A `pool` is
a group of nodes withing a cluster that all have the same configuration.

For example:
A pool can say it contains at most 10 nodes, each using the `c2d-highcpu-32`
configuration (32 cores, 64GB ram).
In addition, a pool can `autoscale` [docs](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler).

If you click on `llvm-premerge-prototype`, and go to the `Nodes` tab, you
will see 3 node pools:
- llvm-premerge-linux
- llvm-premerge-linux-service
- llvm-premerge-windows

Definitions for each pool is in [Architecture overview](architecture.md).

If you click on a pool, example `llvm-premerge-linux`, you will see one
instance group, and maybe several nodes.

Each created node must be attached to an instance group, which is used to
manage a group of instances. Because we use automated autoscale, and we have
a basic cluster, we have a single instance group per pool.

Then, we have the nodes. If you are looking at the panel during off hours,
you might see no nodes at all: when no presubmit is running, no VM is on.
If you are looking at the panel at peak time, you should see 4 instances.
(Today, autoscale is capped at 4 instances).

If you click on a node, you'll see the CPU usage, memory usage, and can access
the logs for each instance.

As long as you don't click on actions like `Cordon`, `Edit`, `Delete`, etc,
navigating the GCP panel should not cause any harm. So feel free to look
around to familiarize yourself with the interface.

## Setup

- install terraform (https://developer.hashicorp.com/terraform/install?product_intent=terraform)
- get the GCP tokens: `gcloud auth application-default login`
- initialize terraform: `terraform init`

To apply any changes to the cluster:
- setup the cluster: `terraform apply`
- terraform will list the list of proposed changes.
- enter 'yes' when prompted.

## Setting the cluster up for the first time

```
terraform apply -target google_container_node_pool.llvm_premerge_linux_service
terraform apply -target google_container_node_pool.llvm_premerge_linux
terraform apply -target google_container_node_pool.llvm_premerge_windows
terraform apply
```

Setting the cluster up for the first time is more involved as there are certain
resources where terraform is unable to handle explicit dependencies. This means
that we have to set up the GKE cluster before we setup any of the Kubernetes
resources as otherwise the Terraform Kubernetes provider will error out.
