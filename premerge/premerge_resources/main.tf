terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.35.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "2.17.0"
    }
  }
}

resource "kubernetes_namespace" "llvm_premerge_controller" {
  metadata {
    name = "llvm-premerge-controller"
  }
}

resource "kubernetes_namespace" "llvm_premerge_linux_runners" {
  metadata {
    name = var.linux_runners_namespace_name
  }
}

resource "kubernetes_namespace" "llvm_premerge_libcxx_runners" {
  metadata {
    name = "llvm-premerge-libcxx-runners"
  }
}

resource "kubernetes_namespace" "llvm_premerge_libcxx_release_runners" {
  metadata {
    name = "llvm-premerge-libcxx-release-runners"
  }
}

resource "kubernetes_namespace" "llvm_premerge_libcxx_next_runners" {
  metadata {
    name = "llvm-premerge-libcxx-next-runners"
  }
}

resource "kubernetes_namespace" "llvm_premerge_windows_2022_runners" {
  metadata {
    name = var.windows_2022_runners_namespace_name
  }
}

resource "kubernetes_namespace" "llvm_premerge_linux_buildbot" {
  metadata {
    name = "llvm-premerge-linux-buildbot"
  }
}

resource "kubernetes_namespace" "llvm_premerge_windows_2022_buildbot" {
  metadata {
    name = "llvm-premerge-windows-2022-buildbot"
  }
}

resource "kubernetes_secret" "linux_buildbot_password" {
  metadata {
    name      = "linux-buildbot-password"
    namespace = "llvm-premerge-linux-buildbot"
  }

  data = {
    "password" = var.linux_buildbot_password
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_linux_buildbot]
}

resource "kubernetes_secret" "windows_buildbot_password" {
  metadata {
    name      = "windows-buildbot-password"
    namespace = "llvm-premerge-windows-buildbot"
  }

  data = {
    "password" = var.windows_buildbot_password
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_windows_2022_buildbot]
}

resource "kubernetes_secret" "linux_github_pat" {
  metadata {
    name      = "github-token"
    namespace = var.linux_runners_namespace_name
  }

  data = {
    "github_app_id"              = var.github_app_id
    "github_app_installation_id" = var.github_app_installation_id
    "github_app_private_key"     = var.github_app_private_key
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_secret" "libcxx_github_pat" {
  metadata {
    name      = "github-token"
    namespace = "llvm-premerge-libcxx-runners"
  }

  data = {
    "github_app_id"              = var.github_app_id
    "github_app_installation_id" = var.github_app_installation_id
    "github_app_private_key"     = var.github_app_private_key
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_libcxx_runners]
}

resource "kubernetes_secret" "libcxx_release_github_pat" {
  metadata {
    name      = "github-token"
    namespace = "llvm-premerge-libcxx-release-runners"
  }

  data = {
    "github_app_id"              = var.github_app_id
    "github_app_installation_id" = var.github_app_installation_id
    "github_app_private_key"     = var.github_app_private_key
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_libcxx_release_runners]
}

resource "kubernetes_secret" "libcxx_next_github_pat" {
  metadata {
    name      = "github-token"
    namespace = "llvm-premerge-libcxx-next-runners"
  }

  data = {
    "github_app_id"              = var.github_app_id
    "github_app_installation_id" = var.github_app_installation_id
    "github_app_private_key"     = var.github_app_private_key
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_libcxx_next_runners]
}

resource "kubernetes_secret" "windows_2022_github_pat" {
  metadata {
    name      = "github-token"
    namespace = "llvm-premerge-windows-2022-runners"
  }

  data = {
    "github_app_id"              = var.github_app_id
    "github_app_installation_id" = var.github_app_installation_id
    "github_app_private_key"     = var.github_app_private_key
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_windows_2022_runners]
}

resource "helm_release" "github_actions_runner_controller" {
  name       = "llvm-premerge-controller"
  namespace  = "llvm-premerge-controller"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = var.github_arc_version
  chart      = "gha-runner-scale-set-controller"

  depends_on = [
    kubernetes_namespace.llvm_premerge_controller
  ]
}

resource "helm_release" "github_actions_runner_set_linux" {
  name       = "llvm-premerge-linux-runners"
  namespace  = var.linux_runners_namespace_name
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = var.github_arc_version
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("linux_runners_values.yaml", { runner_group_name : var.runner_group_name, cache_gcs_bucket : format("%s-object-cache-linux", var.cluster_name) })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_linux_runners,
    helm_release.github_actions_runner_controller,
    kubernetes_secret.linux_github_pat,
  ]
}

resource "helm_release" "github_actions_runner_set_windows_2022" {
  name       = "llvm-premerge-windows-2022-runners"
  namespace  = var.windows_2022_runners_namespace_name
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = var.github_arc_version
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("windows_2022_runner_values.yaml", { runner_group_name : var.runner_group_name, cache_gcs_bucket : format("%s-object-cache-windows", var.cluster_name) })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_windows_2022_runners,
    kubernetes_secret.windows_2022_github_pat,
    helm_release.github_actions_runner_controller,
  ]
}

resource "helm_release" "github_actions_runner_set_libcxx" {
  name       = "llvm-premerge-libcxx-runners"
  namespace  = "llvm-premerge-libcxx-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = var.github_arc_version
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("libcxx_runners_values.yaml", { runner_group_name : var.runner_group_name, runner_image : var.libcxx_runner_image })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_libcxx_runners,
    helm_release.github_actions_runner_controller,
    kubernetes_secret.libcxx_github_pat,
  ]
}

resource "helm_release" "github_actions_runner_set_libcxx_release" {
  name       = "llvm-premerge-libcxx-release-runners"
  namespace  = "llvm-premerge-libcxx-release-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = var.github_arc_version
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("libcxx_runners_values.yaml", { runner_group_name : var.runner_group_name, runner_image : var.libcxx_release_runner_image })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_libcxx_release_runners,
    helm_release.github_actions_runner_controller,
    kubernetes_secret.libcxx_release_github_pat,
  ]
}

resource "helm_release" "github_actions_runner_set_libcxx_next" {
  name       = "llvm-premerge-libcxx-next-runners"
  namespace  = "llvm-premerge-libcxx-next-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = var.github_arc_version
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("libcxx_runners_values.yaml", { runner_group_name : var.runner_group_name, runner_image : var.libcxx_next_runner_image })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_libcxx_next_runners,
    helm_release.github_actions_runner_controller,
    kubernetes_secret.libcxx_next_github_pat,
  ]
}

resource "kubernetes_manifest" "linux_buildbot_deployment" {
  manifest = yamldecode(templatefile("buildbot_deployment.yaml", { buildbot_name : var.linux_buildbot_name, buildbot_namespace : "llvm-premerge-linux-buildbot", secret_name : "linux-buildbot-password" }))

  depends_on = [kubernetes_namespace.llvm_premerge_linux_buildbot, kubernetes_secret.linux_buildbot_password]
}

resource "kubernetes_manifest" "windows_buildbot_deployment" {
  manifest = yamldecode(templatefile("buildbot_deployment.yaml", { buildbot_name : var.windows_buildbot_name, buildbot_namespace : "llvm-premerge-windows-buildbot", secret_name : "windows-buildbot-password" }))

  depends_on = [kubernetes_namespace.llvm_premerge_windows_2022_buildbot, kubernetes_secret.windows_buildbot_password]
}

resource "kubernetes_service_account" "linux_object_cache_ksa" {
  metadata {
    name      = var.linux_runners_kubernetes_service_account_name
    namespace = var.linux_runners_namespace_name
    annotations = {
      "iam.gke.io/gcp-service-account" = var.linux_object_cache_gcp_service_account_email
    }
  }

  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_service_account" "windows_2022_object_cache_ksa" {
  metadata {
    name      = var.windows_2022_runners_kubernetes_service_account_name
    namespace = var.windows_2022_runners_namespace_name
    annotations = {
      "iam.gke.io/gcp-service-account" = var.windows_2022_object_cache_gcp_service_account_email
    }
  }

  depends_on = [kubernetes_namespace.llvm_premerge_windows_2022_runners]
}

# We set up pod disruption budgets here. We need one per namespace and we need
# to set the min pod count to the maximum number of runner pods that can
# possibly exist so we never have a number of disruptible pods greater than
# zero.

resource "kubernetes_manifest" "linux_runners_disruption_budget" {
  manifest   = yamldecode(templatefile("pod_disruption_budget.yaml", { runner_set_name : "llvm-premerge-linux-runners", min_pod_count : 16 }))
  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_manifest" "windows_2022_runners_disruption_budget" {
  manifest   = yamldecode(templatefile("pod_disruption_budget.yaml", { runner_set_name : "llvm-premerge-windows-2022-runners", min_pod_count : 16 }))
  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_manifest" "libcxx_runners_disruption_budget" {
  manifest   = yamldecode(templatefile("pod_disruption_budget.yaml", { runner_set_name : "llvm-premerge-libcxx-runners", min_pod_count : 32 }))
  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_manifest" "libcxx_release_runners_disruption_budget" {
  manifest   = yamldecode(templatefile("pod_disruption_budget.yaml", { runner_set_name : "llvm-premerge-libcxx-release-runners", min_pod_count : 32 }))
  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_manifest" "libcxx_next_runners_disruption_budget" {
  manifest   = yamldecode(templatefile("pod_disruption_budget.yaml", { runner_set_name : "llvm-premerge-libcxx-next-runners", min_pod_count : 32 }))
  depends_on = [kubernetes_namespace.llvm_premerge_linux_runners]
}

resource "kubernetes_namespace" "grafana" {
  metadata {
    name = "grafana"
  }
}

resource "helm_release" "grafana-k8s-monitoring" {
  name             = "grafana-k8s-monitoring"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "k8s-monitoring"
  namespace        = "grafana"
  create_namespace = true
  atomic           = true
  timeout          = 300
  # TODO(boomanaiden154); This needs to be upgraded to v2.x.x at some point.
  version = "1.6.14"

  values = [file("${path.module}/grafana_values.yaml")]

  set {
    name  = "cluster.name"
    value = var.cluster_name
  }

  set {
    name  = "externalServices.prometheus.host"
    value = var.externalservices_prometheus_host
  }

  set_sensitive {
    name  = "externalServices.prometheus.basicAuth.username"
    value = var.externalservices_prometheus_basicauth_username
  }

  set_sensitive {
    name  = "externalServices.prometheus.basicAuth.password"
    value = var.grafana_token
  }

  set {
    name  = "externalServices.loki.host"
    value = var.externalservices_loki_host
  }

  set_sensitive {
    name  = "externalServices.loki.basicAuth.username"
    value = var.externalservices_loki_basicauth_username
  }

  set_sensitive {
    name  = "externalServices.loki.basicAuth.password"
    value = var.grafana_token
  }

  set {
    name  = "externalServices.tempo.host"
    value = var.externalservices_tempo_host
  }

  set_sensitive {
    name  = "externalServices.tempo.basicAuth.username"
    value = var.externalservices_tempo_basicauth_username
  }

  set_sensitive {
    name  = "externalServices.tempo.basicAuth.password"
    value = var.grafana_token
  }

  set {
    name  = "opencost.opencost.exporter.defaultClusterId"
    value = var.cluster_name
  }

  set {
    name  = "opencost.opencost.prometheus.external.url"
    value = format("%s/api/prom", var.externalservices_prometheus_host)
  }

  depends_on = [kubernetes_namespace.grafana]
}

resource "kubernetes_manifest" "sysctl-daemonset" {
  manifest = yamldecode(file("sysctl_daemonset.yaml"))
}
