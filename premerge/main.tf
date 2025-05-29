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

module "premerge_cluster_us_central" {
  source               = "./gke_cluster"
  cluster_name         = "llvm-premerge-cluster-us-central"
  region               = "us-central1-a"
  linux_machine_type   = "n2-standard-64"
  windows_machine_type = "n2-standard-32"
}

# We explicitly specify a single zone for the service node pool locations as
# terraform by default will create node_count nodes per zone. We only want
# node_count nodes rather than (node_count * zone count) nodes, so we
# explicitly enumerate a specific region.
module "premerge_cluster_us_west" {
  source                      = "./gke_cluster"
  cluster_name                = "llvm-premerge-cluster-us-west"
  region                      = "us-west1"
  linux_machine_type          = "n2d-standard-64"
  windows_machine_type        = "n2d-standard-32"
  service_node_pool_locations = ["us-west1-a"]
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

provider "helm" {
  kubernetes {
    host                   = module.premerge_cluster_us_west.endpoint
    token                  = data.google_client_config.current.access_token
    client_certificate     = base64decode(module.premerge_cluster_us_west.client_certificate)
    client_key             = base64decode(module.premerge_cluster_us_west.client_key)
    cluster_ca_certificate = base64decode(module.premerge_cluster_us_west.cluster_ca_certificate)
  }
  alias = "llvm-premerge-us-west"
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

provider "kubernetes" {
  host                   = "https://${module.premerge_cluster_us_west.endpoint}"
  token                  = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(module.premerge_cluster_us_west.cluster_ca_certificate)
  alias                  = "llvm-premerge-us-west"
}

module "premerge_cluster_us_central_resources" {
  source                     = "./premerge_resources"
  github_app_id              = data.google_secret_manager_secret_version.github_app_id.secret_data
  github_app_installation_id = data.google_secret_manager_secret_version.github_app_installation_id.secret_data
  github_app_private_key     = data.google_secret_manager_secret_version.github_app_private_key.secret_data
  cluster_name               = "llvm-premerge-cluster-us-central"
  grafana_token              = data.google_secret_manager_secret_version.grafana_token.secret_data
  runner_group_name          = "llvm-premerge-cluster-us-central"
  providers = {
    kubernetes = kubernetes.llvm-premerge-us-central
    helm       = helm.llvm-premerge-us-central
  }
}

module "premerge_cluster_us_west_resources" {
  source                     = "./premerge_resources"
  github_app_id              = data.google_secret_manager_secret_version.github_app_id.secret_data
  github_app_installation_id = data.google_secret_manager_secret_version.github_app_installation_id.secret_data
  github_app_private_key     = data.google_secret_manager_secret_version.github_app_private_key.secret_data
  cluster_name               = "llvm-premerge-cluster-us-west"
  grafana_token              = data.google_secret_manager_secret_version.grafana_token.secret_data
  runner_group_name          = "llvm-premerge-cluster-us-west"
  providers = {
    kubernetes = kubernetes.llvm-premerge-us-west
    helm       = helm.llvm-premerge-us-west
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

  type       = "Opaque"
  provider   = kubernetes.llvm-premerge-us-central
  depends_on = [kubernetes_namespace.metrics]
}

resource "kubernetes_manifest" "metrics_deployment" {
  manifest = yamldecode(file("metrics_deployment.yaml"))
  provider = kubernetes.llvm-premerge-us-central

  depends_on = [kubernetes_namespace.metrics, kubernetes_secret.metrics_secrets]
}
