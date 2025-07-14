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
    name = "llvm-premerge-linux-runners"
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

resource "kubernetes_namespace" "llvm_premerge_windows_runners" {
  metadata {
    name = "llvm-premerge-windows-runners"
  }
}

resource "kubernetes_namespace" "llvm_premerge_windows_2022_runners" {
  metadata {
    name = "llvm-premerge-windows-2022-runners"
  }
}

resource "kubernetes_secret" "linux_github_pat" {
  metadata {
    name      = "github-token"
    namespace = "llvm-premerge-linux-runners"
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

resource "kubernetes_secret" "windows_github_pat" {
  metadata {
    name      = "github-token"
    namespace = "llvm-premerge-windows-runners"
  }

  data = {
    "github_app_id"              = var.github_app_id
    "github_app_installation_id" = var.github_app_installation_id
    "github_app_private_key"     = var.github_app_private_key
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.llvm_premerge_windows_runners]
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
  version    = "0.11.0"
  chart      = "gha-runner-scale-set-controller"

  depends_on = [
    kubernetes_namespace.llvm_premerge_controller
  ]
}

resource "helm_release" "github_actions_runner_set_linux" {
  name       = "llvm-premerge-linux-runners"
  namespace  = "llvm-premerge-linux-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = "0.11.0"
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("linux_runners_values.yaml", { runner_group_name : var.runner_group_name })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_linux_runners,
    helm_release.github_actions_runner_controller,
    kubernetes_secret.linux_github_pat,
  ]
}

resource "helm_release" "github_actions_runner_set_windows" {
  name       = "llvm-premerge-windows-runners"
  namespace  = "llvm-premerge-windows-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = "0.11.0"
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("windows_runner_values.yaml", { runner_group_name : var.runner_group_name })}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_windows_runners,
    kubernetes_secret.windows_github_pat,
    helm_release.github_actions_runner_controller,
  ]
}

resource "helm_release" "github_actions_runner_set_windows_2022" {
  name       = "llvm-premerge-windows-2022-runners"
  namespace  = "llvm-premerge-windows-2022-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  version    = "0.11.0"
  chart      = "gha-runner-scale-set"

  values = [
    "${templatefile("windows_2022_runner_values.yaml", { runner_group_name : var.runner_group_name })}"
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
  version    = "0.11.0"
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
  version    = "0.11.0"
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
  version    = "0.11.0"
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
