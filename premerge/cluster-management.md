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

## Upgrading/Resetting Github ARC

Updating and resetting the Github Actions Runner Controller (ARC) within the
cluster involves largely the same process. Some special considerations need
to be made with how ARC interacts with kubernetes. The process involves
uninstalling the runner scale set charts, deleting the namespaces to ensure
everything is properly cleaned up, optionally bumping the version number if
this is a version upgrade, and then reinstalling the charts to get the cluster
back to accepting production jobs.

It is important to not just blindly delete controller pods or namespaces as
this (at least empirically) can interrupt the state and custom resources that
ARC manages, then requiring a costly full uninstallation and reinstallation of
at least a runner scale set.

When upgrading/resetting the cluster, jobs will not be lost, but instead remain
queued on the Github side. Running build jobs will complete after the helm charts
are uninstalled unless they are forcibly killed. Note that best practice dictates
the helm charts should just be uninstalled rather than also setting `maxRunners`
to zero beforehand as that can cause ARC to accept some jobs but not actually
execute them which could prevent failover in HA cluster configurations.

### Uninstalling the Helm Charts

To begin, start by uninstalling the helm charts by using resource targetting
on a kubernetes destroy command:

```bash
terraform destroy -target helm_release.github_actions_runner_set_linux
terraform destroy -target helm_release.github_actions_runner_set_windows
```

These should complete, but if they do not, we are still able to get things
cleaned up. If everything went smoothly, the commands should complete and leave
runner pods that are still in the process of executing jobs. You will need to
wait for them to complete before moving on. If they are stuck, you will need to
manually delete them with `kubectl delete`. Follow up the previous terraform
commands by deleting the kubernetes namespaces all the resources live in:

```bash
terraform destroy -target kubernetes_namespace.llvm_premerge_linux_runners
terraform destroy -target kubernetes_namespace.llvm_premerge_windows_runners
```

If things go smoothly, these should complete quickly. If they do not complete,
there is most likely dangling resources in the namespaces that need to have their
finalizers removed before they can be updated. You can confirm this by running
`kubectl get namespaces`. If the namespace is listed as `Terminating`, you most
likely need to manually intervene. To find a list of dangling resources that
did not get cleaned up properly, you can run the following command, making sure
to fill in `<namespace>` with the actual namespace of interest:

```bash
kubectl api-resources --verbs=list --namespaced -o name \
  | xargs -n 1 kubectl get --show-kind --ignore-not-found -n <namespace>
```

This will return the stuck resources. Then you can copy each resource, and edit
the YAML configuration of the kubernetes object to remove the finalizers:

```bash
kubectl edit <resource name> -n <namespace name>
```

Just deleting the finalizers key along with any entries should be sufficient.
After rerunning the command to find dangling resources, you should see it get
removed. After doing this for all dangling resources, the namespace should
then delete automatically. This can be confirmed by running
`kubectl get namespaces`.

If you are performing these steps as part of an incident response, you can
skip to the section [Bringing the Cluster Back Up](#bringing-the-cluster-back-up).
If you are bumping the version you still need to uninstall the controller and
bump the version number beforehand.

### Uninstalling the Controller Helm Chart

Next, the controller helm chart needs to be uninstalled. If you are performing
these steps as part of dealing with an incident, you most likely do not need to
perform this step. Usually it is sufficient to destroy and recreate the runner
scale sets to resolve incidents. Uninstalling the controller is necessary for
version upgrades however.

Start by destroying the helm chart:
```bash
terraform destroy -target helm_release.github_actions_runner_controller
```

Then delete the namespace to ensure there are no dangling resources
```bash
terraform destroy -target kubernetes_namespace.llvm_premerge_controller
```

### Bumping the Version Number

This is not necessary only for bumping the version of ARC. This involves simply
updating the version field for the `helm_release` objects in `main.tf`. Make sure
to commit the changes and push them to `llvm-zorg` to ensure others working on
the terraform configuration have an up to date state when they pull the repository.

### Bringing the Cluster Back Up

To get the cluster back up and accepting production jobs again, simply run
`terraform apply`. It will recreate all the resource previously destroyed and
ensure they are in a state consistent with the terraform IaC definitions.

### External Resources

[Strategies for Upgrading ARC](https://www.kenmuse.com/blog/strategies-for-upgrading-arc/)
outlines how ARC should be upgraded and why.
