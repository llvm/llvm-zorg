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

Currently, we have 4 clusters:
 - `llvm-premerge-checks`: the cluster hosting BuildKite Linux runners.
 - `llvm-premerge-cluster-us-central`: The first cluster for GCP hosted runners.
 - `llvm-premerge-cluster-us-west`: The second cluster for GCP hosted runners.

`llvm-premerge-checks` is part of the old Buildkite
infrastructure. For the new infrastructure, we have two clusters,
`llvm-premerge-cluster-us-central` and `llvm-premerge-cluster-us-west` for GCP
hosted runners to form a high availability setup. They both load balance, and
if one fails then the other will pick up the work. This also enables seamless
migrations and upgrades.

To add a VM to a cluster, the VM has to come from a `pool`. A `pool` is
a group of nodes within a cluster that all have the same configuration.

For example:
A pool can say it contains at most 10 nodes, each using the `c2d-highcpu-32`
configuration (32 cores, 64GB ram).
In addition, a pool can `autoscale` [docs](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler).

If you click on `llvm-premerge-cluster-us-central`, and go to the `Nodes` tab, you
will see 3 node pools:
- llvm-premerge-linux
- llvm-premerge-linux-service
- llvm-premerge-windows-2022
- llvm-premerge-libcxx

Definitions for each pool are in [Architecture overview](architecture.md).

If you click on a pool, example `llvm-premerge-linux`, you will see one
instance group, and maybe several nodes.

Each created node must be attached to an instance group, which is used to
manage a group of instances. Because we use automated autoscale, and we have
a basic cluster, we have a single instance group per pool.

Then, we have the nodes. If you are looking at the panel during off hours,
you might see no nodes at all: when no presubmit is running, no VM is on.
If you are looking at the panel at peak time, you should see 8 instances.
(Today, autoscale is capped at 8 instances).

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
terraform apply -target module.premerge_cluster_us_central.google_container_node_pool.llvm_premerge_linux_service
terraform apply -target module.premerge_cluster_us_central.google_container_node_pool.llvm_premerge_linux
terraform apply -target module.premerge_cluster_us_central.google_container_node_pool.llvm_premerge_windows_2022
terraform apply -target module.premerge_cluster_us_central.google_container_node_pool.llvm_premerge_libcxx
terraform apply -target module.premerge_cluster_us_west.google_container_node_pool.llvm_premerge_linux_service
terraform apply -target module.premerge_cluster_us_west.google_container_node_pool.llvm_premerge_linux
terraform apply -target module.premerge_cluster_us_west.google_container_node_pool.llvm_premerge_windows_2022
terraform apply -target module.premerge_cluster_us_west.google_container_node_pool.llvm_premerge_libcxx
terraform apply
```

Setting the cluster up for the first time is more involved as there are certain
resources where terraform is unable to handle explicit dependencies. This means
that we have to set up the GKE cluster before we setup any of the Kubernetes
resources as otherwise the Terraform Kubernetes provider will error out. This
needs to be done for both clusters before running the standard
`terraform apply`.

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
execute them which could prevent failover in a HA cluster configuration like
ours.

### Uninstalling the Helm Charts

For the example commands below we will be modifying the cluster in
`us-central1-a`. You can replace `module.premerge_cluster_us_central_resources`
with `module.premerge_cluster_us_west_resources` to switch which cluster you
are working on.

To begin, start by uninstalling the helm charts by using resource targetting
on a kubernetes destroy command:

```bash
terraform destroy -target module.premerge_cluster_us_central_resources.helm_release.github_actions_runner_set_linux
terraform destroy -target module.premerge_cluster_us_central_resources.helm_release.github_actions_runner_set_windows_2022
terraform destroy -target module.premerge_cluster_us_central_resources.helm_release.github_actions_runner_set_libcxx
terraform destroy -target module.premerge_cluster_us_central_resources.helm_release.github_actions_runner_set_libcxx_release
terraform destroy -target module.premerge_cluster_us_central_resources.helm_release.github_actions_runner_set_libcxx_next
```

These should complete, but if they do not, we are still able to get things
cleaned up. If everything went smoothly, the commands should complete and leave
runner pods that are still in the process of executing jobs. You will need to
wait for them to complete before moving on. If they are stuck, you will need to
manually delete them with `kubectl delete`. Follow up the previous terraform
commands by deleting the kubernetes namespaces all the resources live in:

```bash
terraform destroy -target module.premerge_cluster_us_central_resources.kubernetes_namespace.llvm_premerge_linux_runners
terraform destroy -target module.premerge_cluster_us_central_resources.kubernetes_namespace.llvm_premerge_windows_2022_runners
terraform destroy -target module.premerge_cluster_us_central_resources.kubernetes_namespace.llvm_premerge_libcxx_runners
terraform destroy -target module.premerge_cluster_us_central_resources.kubernetes_namespace.llvm_premerge_libcxx_release_runners
terraform destroy -target module.premerge_cluster_us_central_resources.kubernetes_namespace.llvm_premerge_libcxx_next_runners
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
terraform destroy -target module.premerge_cluster_us_central_resources.helm_release.github_actions_runner_controller
```

Then delete the namespace to ensure there are no dangling resources
```bash
terraform destroy -target module.premerge_cluster_us_central_resources.kubernetes_namespace.llvm_premerge_controller
```

### Bumping the Version Number

This is necessary only for bumping the version of ARC. This involves simply
updating the `github_arc_version` field for premerge cluster resources in
`premerge/main.tf`. Each premerge cluster (`llvm-premerge-cluster-us-central`
and `llvm-premerge-cluster-us-west`) has a separate version. This allows for
updating them separately which allows for zero-downtime upgrades when the
system is operating at low capacity. Make sure to commit the changes and push
them to `llvm-zorg` to ensure others working on the terraform configuration
have an up to date state when they pull the repository.

### Bringing the Cluster Back Up

To get the cluster back up and accepting production jobs again, simply run
`terraform apply`. It will recreate all the resource previously destroyed and
ensure they are in a state consistent with the terraform IaC definitions.

### External Resources

[Strategies for Upgrading ARC](https://www.kenmuse.com/blog/strategies-for-upgrading-arc/)
outlines how ARC should be upgraded and why.

## Grafana tokens

The cluster has multiple services communicating with Grafana Cloud:
 - the metrics container
 - per-node monitoring  (Grafana Alloy, Prometheus node exporter)
 - per-cluster monitoring (Opencost, Alloy)

The full description of the services can be found on the [k8s-monitoring Helm
chart repository](https://github.com/grafana/k8s-monitoring-helm).

Authentication to Grafana Cloud is handled through `Cloud access policies`.
Currently, the cluster uses 2 kind of tokens:

 - `llvm-premerge-metrics-grafana-api-key`
    Used by: metrics container
    Scopes: `metrics:write`

 - `llvm-premerge-grafana-token`
   Used by: Alloy, Prometheus node exporter & other services.
   Scopes: `metrics:read`, `metrics:write`, `logs:write`

We've setup 2 cloud policies with matching names so scopes are already set up.
If you need to rotate tokens, you need to:

 1. Login to Grafana Cloud
 2. Navigate to `Home > Administration > Users and Access > Cloud Access Policies`
 3. Create a new token in the desired cloud access policy.
 4. Log in `GCP > Security > Secret Manager`
 5. Click on the secret to update.
 6. Click on `New version`
 7. Paste the token displayed in Grafana and tick `Disable all past versions`.

At this stage, you should have a **single** enabled secret on GCP. If you
display the value, you should see the Grafana token.

Then, go in the `llvm-zorg` repository. Make sure you pulled the last changes
in `main`, and then as usual, run `terraform apply`.

At this stage, you made sure newly created services will use the token, but
existing deployment still rely on the old tokens. You need to manually restart
the deployments on both `us-west1` and `us-central1-a` clusters.

Run:

``` bash
gcloud container clusters get-credentials llvm-premerge-cluster-us-west --location us-west1
kubectl scale --replicas=0 --namespace grafana deployments \
  grafana-k8s-monitoring-opencost \
  grafana-k8s-monitoring-kube-state-metrics \
  grafana-k8s-monitoring-alloy-events

gcloud container clusters get-credentials llvm-premerge-cluster-us-central --location us-central1-a
kubectl scale --replicas=0 --namespace grafana deployments \
  grafana-k8s-monitoring-opencost \
  grafana-k8s-monitoring-kube-state-metrics \
  grafana-k8s-monitoring-alloy-events
kubectl scale --replicas=0 --namespace metrics
```

:warning: metrics namespace only exists in the `us-central1-a` cluster.

Wait until the command `kubectl get deployments --namespace grafana` shows
all deployments have been scaled down to zero. Then run:

```bash
gcloud container clusters get-credentials llvm-premerge-cluster-us-west --location us-west1
kubectl scale --replicas=0 --namespace grafana deployments \
  grafana-k8s-monitoring-opencost \
  grafana-k8s-monitoring-kube-state-metrics \
  grafana-k8s-monitoring-alloy-events

gcloud container clusters get-credentials llvm-premerge-cluster-us-central --location us-central1-a
kubectl scale --replicas=1 --namespace grafana deployments \
  grafana-k8s-monitoring-opencost \
  grafana-k8s-monitoring-kube-state-metrics \
  grafana-k8s-monitoring-alloy-events
kubectl scale --replicas=1 --namespace metrics metrics
```

You can check the restarted service logs for errors. If the token is invalid
or the scope bad, you should see some `401` error codes.

```bash
kubectl logs -n metrics deployment/metrics
kubectl logs -n metrics deployment/grafana-k8s-monitoring-opencost
```

At this stage, all long-lived services should be using the new tokens.
**DO NOT DELETE THE OLD TOKEN YET**.
The existing CI jobs can be quite long-lived. We need to wait for them to
finish. New CI jobs will pick up the new tokens.

After 24 hours, log back in
`Administration > User and Access > Cloud Access policies` and expand the
token lists.
You should see the new tokens `Last used at` being about a dozen minutes at
most, while old tokens should remain unused for several hours.
If this is the case, congratulations, you've successfully rotated security
tokens! You can now safely delete the old unused tokens.
