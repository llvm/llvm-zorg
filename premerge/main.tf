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

# TODO(boomanaiden154): Rename this to llvm-premerge-cluster-us-central when
# commit traffic is low.
module "premerge_cluster_us_central" {
  source       = "./gke_cluster"
  cluster_name = "llvm-premerge-prototype"
  region       = "us-central1-a"
}

# TODO(boomanaiden154): Remove these statements after the changes have been
# applied.

moved {
  from = module.premerge_cluster
  to   = module.premerge_cluster_us_central
}

provider "helm" {
  kubernetes {
    host                   = module.premerge_cluster_us_central.endpoint
    token                  = data.google_client_config.current.access_token
    client_certificate     = base64decode(module.premerge_cluster_us_central.client_certificate)
    client_key             = base64decode(module.premerge_cluster_us_central.client_key)
    cluster_ca_certificate = base64decode(module.premerge_cluster_us_central.cluster_ca_certificate)
  }
  alias = "llvm-premerge-us-central"
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
  host  = "https://${module.premerge_cluster_us_central.endpoint}"
  token = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(
    module.premerge_cluster_us_central.cluster_ca_certificate
  )
  alias = "llvm-premerge-us-central"
}

module "premerge_cluster_resources" {
  source                     = "./premerge_resources"
  github_app_id              = data.google_secret_manager_secret_version.github_app_id.secret_data
  github_app_installation_id = data.google_secret_manager_secret_version.github_app_installation_id.secret_data
  github_app_private_key     = data.google_secret_manager_secret_version.github_app_private_key.secret_data
  cluster_name               = "llvm-premerge-prototype"
  grafana_token              = data.google_secret_manager_secret_version.grafana_token.secret_data
  providers = {
    kubernetes = kubernetes.llvm-premerge-us-central
    helm       = helm.llvm-premerge-us-central
  }
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
  provider = kubernetes.llvm-premerge-us-central
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
  provider = kubernetes.llvm-premerge-us-central
}

resource "kubernetes_manifest" "metrics_deployment" {
  manifest = yamldecode(file("metrics_deployment.yaml"))
  provider = kubernetes.llvm-premerge-us-central
}
