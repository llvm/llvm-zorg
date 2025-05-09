terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.35.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.17.0"
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

resource "kubernetes_namespace" "llvm_premerge_windows_runners" {
  metadata {
    name = "llvm-premerge-windows-runners"
  }
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
    "${file("linux_runners_values.yaml")}"
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
    "${file("windows_runner_values.yaml")}"
  ]

  depends_on = [
    kubernetes_namespace.llvm_premerge_windows_runners,
    kubernetes_secret.windows_github_pat,
    helm_release.github_actions_runner_controller,
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
