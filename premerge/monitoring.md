# Monitoring

Presubmit monitoring is provided by Grafana.
The dashboard link is [https://llvm.grafana.net/dashboards](https://llvm.grafana.net/dashboards).

Grafana pulls its data from 2 sources: the GCP Kubernetes cluster & GitHub.
Grafana instance access is restricted, but there is a publicly visible dashboard:
- [Public dashboard](https://llvm.grafana.net/public-dashboards/6a1c1969b6794e0a8ee5d494c72ce2cd)


## GCP monitoring

Cluster metrics are gathered through Grafana alloy.
This service is deployed using Helm, as described [HERE](main.tf)

## Github monitoring

Github CI queue and job status is fetched using a custom script which pushes
metrics to grafana.
The script itself lives in the llvm-project repository: [LINK](https://github.com/llvm/llvm-project/blob/main/.ci/metrics/metrics.py).
The deployment configuration if in the [metrics_deployment file](metrics_deployment.yaml).
