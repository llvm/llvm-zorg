# Past Issues

This document lists past issues that could be of interest if you encounter
issues with the cluser/presubmit.

## Workflows are failing: DNS resolution of github.com fails.

### Date: 2025-01-27

### Symptoms:

We noticed GitHub jobs were failing, and the logs showed `hostname lookup
failed for github.com`.

### Investigation

Initial steps were to check the github status page. No outages.
Then, we checked internal incident page. No outages.

Then we looked at the instance logs.
When a node fails, GCP removes it, meaning the logs are not accessible from
the node page anymore, but can be retrieved either in the global logs.

Looking at the logs, we discovered other services failing to resolve
hostname, like the metrics container.

In Kubernetes, each cluster runs a `kube-dns` service/pod, which is used
by other pods to do DNS requests.
This pod was crashing.

Looking at the node this pod was running on showed a RAM usage close to the
VM limits.
At the time, the service instances were running on `e2-small` VMs, which only
have 2GB of RAM.
In addition, we recently added more runner nodes by adding a new Windows pool.
This meant cluster size increased. This caused the cluster management services
to take more resources to run, and pushed us just above the 2GB limit.

This causes the kube-dns service to be OOM killed, and then caused various DNS
failures in the cluster.

### Solution

Change the shape of the service pool to be `e2-highcpu-4`, doubling the RAM
and CPU budget. We also increased the pool size from 2 to 3.

## LLVM dashboard graphs are empty for presubmits

### Date: 2025-01-28

### Symptoms

The LLVM dashboard was showing empty graphs for the presubmit job runtime and
queue time. Autoscaling graphs were still working.

### Investigation

The graphs were empty because no new metrics were received, but other GCP
metrics were still showing.
Our dashboard has multiple data source:
 - the GCP cluster.
 - the metrics container.

Because we had GCP metrics, it meant the Grafana instance was working, and
the Grafana Alloy component running in the cluster was also fine.

It was probably the metrics container.
We checked the heartbeat metric: `metrics_container_heartbeat`.
This is a simple ping recorded every minutes by the container. If this
metrics stops emitting, it means something is wrong with the job.
This metric was still being recorded.

A recent change was made to add the windows version of the premerge check.
This caused the job name to change, and thus changed the recorded metric
names from `llvm_premerge_checks_linux_run_time` to
`llvm_premerge_checks_premerge_checks_linux_run_time`.

### Solution

Change the dashboards to read the new metric name instead of the previous
name, allowing new data to be shown.
SLO definitions and alerts also had to be adjusted to look at the new metrics.

## LLVM dashboard graphs are empty for run/queue times

### Date: 2025-01-10

### Symptoms

The LLVM dashboard was showing empty graphs for the presubmit job runtime and
queue time. Autoscaling graphs were still working.

### Investigation

Grafana was still recording GCP metrics, but no new data coming from the
metrics container.

A quick look at the google cloud console showed the metrics container pod was
crashing.
Looking at the logs, we saw the script failed to connect to GitHub to get
the workflow status. Reason was a bad GitHub token.

Because we have no admin access to the GitHub admin organization, we cannot
emit LLVM owned tokens. A Googler had used its personal account to setup a
PAT token. This token expired in December, causing the metrics container
to fail since.

### Solution

Another Googler generated a new token, and replaced it in `Menu > Security > Secrets Manager > llvm-premerge-github-pat`.
Note: this secret is in the general secret manager, not in `Kubernetes Engine > Secrets & ConfigMaps`.

Once the secret updated, the metrics container had to be restarted:
- `Menu > Kubernetes Engine > Workflows`
- select `metrics`.
- click `Rolling update`
- set all thresholds to `100%`, the click update.

This will allow GCP to delete the only metrics container pod, and recreate it
using the new secret value.
Because we have a single metrics container instance running, we have to but
all thresholds to `100%`.

In addition, we added a heartbeat metric to the container, and Grafana
alerting to make sure we detect this kind of failure early.

## Linux Runner Set Not Scaling

### Date: 2025-03-31

### Symptoms

The LLVM dashboard showed that there was a large queue of linux jobs but
only two runners actively processing jobs rather than the runner count limit
of 8.

### Investigation

Initial investigation involved checking the cluster, which also showed only
two runner pods working. The logs of the linux runner scale set controller
were inspected which showed it was only scaling up to two pods. The runner
scale set controller pod was then deleted to try and rectify the situation
along with a version upgrade of the ARC Helm charts. This resulted in the
linux controller not coming back up.

### Solution

The Linux runner scale set was uninstalled using the
[instructions](cluster-management.md#upgradingresetting-github-arc). This
resulted in all Linux runners quickly coming back online. The windows runner
set had also stopped accepting jobs at this point, presumed to be due to
prodding while investigating the Linux issues. The issue on the Windows
side was fixed in the same way, by uninstalling the helm charts, deleting
dangling resources, deleting the namespaces, and then reinstalling the
helm charts.
