terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.17.0"
    }
  }
}

provider "google" {
  project = "llvm-premerge-checks"
}

resource "random_id" "default" {
  byte_length = 8
}

resource "google_storage_bucket" "terraform_state_bucket" {
  name     = "${random_id.default.hex}-terraform-remote-backend"
  location = "US"

  force_destroy               = false
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "local_file" "terraform_state" {
  file_permission = "0644"
  filename        = "${path.module}/backend.tf"

  content = <<-EOT
  terraform {
    backend "gcs" {
      bucket = "${google_storage_bucket.terraform_state_bucket.name}"
    }
  }
  EOT
}

data "google_client_config" "current" {}

module "premerge_cluster" {
  source       = "./gke_cluster"
  cluster_name = "llvm-premerge-prototype"
  region       = "us-central1-a"
}

# TODO(boomanaiden154): Remove these moved blocks once we have finished
# updating everything to use the new module.
moved {
  from = google_container_cluster.llvm_premerge
  to   = module.premerge_cluster.google_container_cluster.llvm_premerge
}

moved {
  from = google_container_node_pool.llvm_premerge_linux
  to   = module.premerge_cluster.google_container_node_pool.llvm_premerge_linux
}

moved {
  from = google_container_node_pool.llvm_premerge_linux_service
  to   = module.premerge_cluster.google_container_node_pool.llvm_premerge_linux_service
}

moved {
  from = google_container_node_pool.llvm_premerge_windows
  to   = module.premerge_cluster.google_container_node_pool.llvm_premerge_windows
}

provider "helm" {
  kubernetes {
    host                   = module.premerge_cluster.endpoint
    token                  = data.google_client_config.current.access_token
    client_certificate     = base64decode(module.premerge_cluster.client_certificate)
    client_key             = base64decode(module.premerge_cluster.client_key)
    cluster_ca_certificate = base64decode(module.premerge_cluster.cluster_ca_certificate)
  }
  alias = "llvm-premerge-prototype"
}

data "google_secret_manager_secret_version" "github_app_id" {
  secret = "llvm-premerge-github-app-id"
}

data "google_secret_manager_secret_version" "github_app_installation_id" {
  secret = "llvm-premerge-github-app-installation-id"
}

data "google_secret_manager_secret_version" "github_app_private_key" {
  secret = "llvm-premerge-github-app-private-key"
}

data "google_secret_manager_secret_version" "grafana_token" {
  secret = "llvm-premerge-testing-grafana-token"
}

provider "kubernetes" {
  host  = "https://${module.premerge_cluster.endpoint}"
  token = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(
    module.premerge_cluster.cluster_ca_certificate
  )
  alias = "llvm-premerge-prototype"
}

module "premerge_cluster_resources" {
  source                     = "./premerge_resources"
  github_app_id              = data.google_secret_manager_secret_version.github_app_id.secret_data
  github_app_installation_id = data.google_secret_manager_secret_version.github_app_installation_id.secret_data
  github_app_private_key     = data.google_secret_manager_secret_version.github_app_private_key.secret_data
  cluster_name               = "llvm-premerge-prototype"
  grafana_token              = data.google_secret_manager_secret_version.grafana_token.secret_data
  providers = {
    kubernetes = kubernetes.llvm-premerge-prototype
    helm       = helm.llvm-premerge-prototype
  }
}

# TODO(boomanaiden154): Remove these moved blocks once we have finished
# updating everything to use the new module.
moved {
  from = kubernetes_namespace.llvm_premerge_controller
  to   = module.premerge_cluster_resources.kubernetes_namespace.llvm_premerge_controller
}

moved {
  from = kubernetes_namespace.llvm_premerge_linux_runners
  to   = module.premerge_cluster_resources.kubernetes_namespace.llvm_premerge_linux_runners
}

moved {
  from = kubernetes_secret.linux_github_pat
  to   = module.premerge_cluster_resources.kubernetes_secret.linux_github_pat
}

moved {
  from = kubernetes_namespace.llvm_premerge_windows_runners
  to   = module.premerge_cluster_resources.kubernetes_namespace.llvm_premerge_windows_runners
}

moved {
  from = kubernetes_secret.windows_github_pat
  to   = module.premerge_cluster_resources.kubernetes_secret.windows_github_pat
}

moved {
  from = helm_release.github_actions_runner_controller
  to   = module.premerge_cluster_resources.helm_release.github_actions_runner_controller
}

moved {
  from = helm_release.github_actions_runner_set_linux
  to   = module.premerge_cluster_resources.helm_release.github_actions_runner_set_linux
}

moved {
  from = helm_release.github_actions_runner_set_windows
  to   = module.premerge_cluster_resources.helm_release.github_actions_runner_set_windows
}

moved {
  from = kubernetes_namespace.grafana
  to   = module.premerge_cluster_resources.kubernetes_namespace.grafana
}

moved {
  from = helm_release.grafana-k8s-monitoring
  to   = module.premerge_cluster_resources.helm_release.grafana-k8s-monitoring
}

data "google_secret_manager_secret_version" "metrics_github_pat" {
  secret = "llvm-premerge-metrics-github-pat"
}

data "google_secret_manager_secret_version" "metrics_grafana_api_key" {
  secret = "llvm-premerge-metrics-grafana-api-key"
}

data "google_secret_manager_secret_version" "metrics_grafana_metrics_userid" {
  secret = "llvm-premerge-metrics-grafana-metrics-userid"
}

data "google_secret_manager_secret_version" "metrics_buildkite_token" {
  secret = "llvm-premerge-metrics-buildkite-graphql-token"
}

resource "kubernetes_namespace" "metrics" {
  metadata {
    name = "metrics"
  }
  provider = kubernetes.llvm-premerge-prototype
}

resource "kubernetes_secret" "metrics_secrets" {
  metadata {
    name      = "metrics-secrets"
    namespace = "metrics"
  }

  data = {
    "github-token"           = data.google_secret_manager_secret_version.metrics_github_pat.secret_data
    "grafana-api-key"        = data.google_secret_manager_secret_version.metrics_grafana_api_key.secret_data
    "grafana-metrics-userid" = data.google_secret_manager_secret_version.metrics_grafana_metrics_userid.secret_data
    "buildkite-token"        = data.google_secret_manager_secret_version.metrics_buildkite_token.secret_data
  }

  type     = "Opaque"
  provider = kubernetes.llvm-premerge-prototype
}

resource "kubernetes_manifest" "metrics_deployment" {
  manifest = yamldecode(file("metrics_deployment.yaml"))
  provider = kubernetes.llvm-premerge-prototype
}
