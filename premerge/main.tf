terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.43.0"
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

locals {
  linux_runners_namespace_name                         = "llvm-premerge-linux-runners"
  linux_runners_kubernetes_service_account_name        = "linux-runners-ksa"
  windows_2022_runners_namespace_name                  = "llvm-premerge-windows-2022-runners"
  windows_2022_runners_kubernetes_service_account_name = "windows-runners-ksa"
}

module "premerge_cluster_us_central" {
  source                                               = "./gke_cluster"
  cluster_name                                         = "llvm-premerge-cluster-us-central"
  region                                               = "us-central1-a"
  libcxx_machine_type                                  = "n2d-standard-32"
  linux_machine_type                                   = "n2-standard-64"
  windows_machine_type                                 = "n2-standard-32"
  gcs_bucket_location                                  = "us-central1"
  linux_runners_namespace_name                         = local.linux_runners_namespace_name
  linux_runners_kubernetes_service_account_name        = local.linux_runners_kubernetes_service_account_name
  windows_2022_runners_namespace_name                  = local.windows_2022_runners_namespace_name
  windows_2022_runners_kubernetes_service_account_name = local.windows_2022_runners_kubernetes_service_account_name
}

# We explicitly specify a single zone for the service node pool locations as
# terraform by default will create node_count nodes per zone. We only want
# node_count nodes rather than (node_count * zone count) nodes, so we
# explicitly enumerate a specific region.
module "premerge_cluster_us_west" {
  source                                               = "./gke_cluster"
  cluster_name                                         = "llvm-premerge-cluster-us-west"
  region                                               = "us-west1"
  libcxx_machine_type                                  = "n2d-standard-32"
  linux_machine_type                                   = "n2d-standard-64"
  windows_machine_type                                 = "n2d-standard-32"
  service_node_pool_locations                          = ["us-west1-a"]
  gcs_bucket_location                                  = "us-west1"
  linux_runners_namespace_name                         = local.linux_runners_namespace_name
  linux_runners_kubernetes_service_account_name        = local.linux_runners_kubernetes_service_account_name
  windows_2022_runners_namespace_name                  = local.windows_2022_runners_namespace_name
  windows_2022_runners_kubernetes_service_account_name = local.windows_2022_runners_kubernetes_service_account_name
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

# Buildbot here refers specifically to the LLVM Buildbot postcommit
# testing infrastructure. These machines are used specifically for testing
# commits after they have landed in main.
data "google_secret_manager_secret_version" "us_central_linux_buildbot_password" {
  secret = "llvm-buildbot-linux-us-central"
}

data "google_secret_manager_secret_version" "us_central_windows_buildbot_password" {
  secret = "llvm-buildbot-windows-us-central"
}

data "google_secret_manager_secret_version" "us_west_linux_buildbot_password" {
  secret = "llvm-buildbot-linux-us-west"
}

data "google_secret_manager_secret_version" "us_west_windows_buildbot_password" {
  secret = "llvm-buildbot-windows-us-west"
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
  source                                                   = "./premerge_resources"
  github_app_id                                            = data.google_secret_manager_secret_version.github_app_id.secret_data
  github_app_installation_id                               = data.google_secret_manager_secret_version.github_app_installation_id.secret_data
  github_app_private_key                                   = data.google_secret_manager_secret_version.github_app_private_key.secret_data
  cluster_name                                             = "llvm-premerge-cluster-us-central"
  grafana_token                                            = data.google_secret_manager_secret_version.grafana_token.secret_data
  runner_group_name                                        = "llvm-premerge-cluster-us-central"
  linux_runners_namespace_name                             = local.linux_runners_namespace_name
  linux_runners_kubernetes_service_account_name            = local.linux_runners_kubernetes_service_account_name
  windows_2022_runners_namespace_name                      = local.windows_2022_runners_namespace_name
  windows_2022_runners_kubernetes_service_account_name     = local.windows_2022_runners_kubernetes_service_account_name
  linux_object_cache_gcp_service_account_email             = module.premerge_cluster_us_central.linux_object_cache_gcp_service_account_email
  windows_2022_object_cache_gcp_service_account_email      = module.premerge_cluster_us_central.windows_2022_object_cache_gcp_service_account_email
  github_arc_version                                       = "0.13.0"
  linux_buildbot_name_template                             = "premerge-us-central-linux"
  linux_buildbot_password                                  = data.google_secret_manager_secret_version.us_central_linux_buildbot_password.secret_data
  windows_buildbot_name_template                           = "premerge-us-central-windows"
  windows_buildbot_password                                = data.google_secret_manager_secret_version.us_central_windows_buildbot_password.secret_data
  linux_object_cache_buildbot_service_account_email        = module.premerge_cluster_us_central.linux_object_cache_buildbot_service_account_email
  windows_2022_object_cache_buildbot_service_account_email = module.premerge_cluster_us_central.windows_2022_object_cache_buildbot_service_account_email
  providers = {
    kubernetes = kubernetes.llvm-premerge-us-central
    helm       = helm.llvm-premerge-us-central
  }
}

module "premerge_cluster_us_west_resources" {
  source                                                   = "./premerge_resources"
  github_app_id                                            = data.google_secret_manager_secret_version.github_app_id.secret_data
  github_app_installation_id                               = data.google_secret_manager_secret_version.github_app_installation_id.secret_data
  github_app_private_key                                   = data.google_secret_manager_secret_version.github_app_private_key.secret_data
  cluster_name                                             = "llvm-premerge-cluster-us-west"
  grafana_token                                            = data.google_secret_manager_secret_version.grafana_token.secret_data
  runner_group_name                                        = "llvm-premerge-cluster-us-west"
  linux_runners_namespace_name                             = local.linux_runners_namespace_name
  linux_runners_kubernetes_service_account_name            = local.linux_runners_kubernetes_service_account_name
  windows_2022_runners_namespace_name                      = local.windows_2022_runners_namespace_name
  windows_2022_runners_kubernetes_service_account_name     = local.windows_2022_runners_kubernetes_service_account_name
  linux_object_cache_gcp_service_account_email             = module.premerge_cluster_us_west.linux_object_cache_gcp_service_account_email
  windows_2022_object_cache_gcp_service_account_email      = module.premerge_cluster_us_west.windows_2022_object_cache_gcp_service_account_email
  github_arc_version                                       = "0.13.0"
  linux_buildbot_name_template                             = "premerge-us-west-linux"
  linux_buildbot_password                                  = data.google_secret_manager_secret_version.us_west_linux_buildbot_password.secret_data
  windows_buildbot_name_template                           = "premerge-us-west-windows"
  windows_buildbot_password                                = data.google_secret_manager_secret_version.us_west_windows_buildbot_password.secret_data
  linux_object_cache_buildbot_service_account_email        = module.premerge_cluster_us_west.linux_object_cache_buildbot_service_account_email
  windows_2022_object_cache_buildbot_service_account_email = module.premerge_cluster_us_west.windows_2022_object_cache_buildbot_service_account_email
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

# Resources for collecting LLVM operational metrics data

# Service accounts and bindings to grant access to the
# BigQuery API for our cronjob
resource "google_service_account" "operational_metrics_gsa" {
  account_id   = "operational-metrics-gsa"
  display_name = "Operational Metrics GSA"
}

resource "google_project_iam_member" "operational_metrics_gsa_bq_jobuser_member" {
  project = google_service_account.operational_metrics_gsa.project
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.operational_metrics_gsa.email}"

  depends_on = [google_service_account.operational_metrics_gsa]
}

resource "kubernetes_namespace" "operational_metrics" {
  metadata {
    name = "operational-metrics"
  }
  provider = kubernetes.llvm-premerge-us-central
}

resource "kubernetes_service_account" "operational_metrics_ksa" {
  metadata {
    name      = "operational-metrics-ksa"
    namespace = "operational-metrics"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.operational_metrics_gsa.email
    }
  }

  depends_on = [kubernetes_namespace.operational_metrics]

  provider = kubernetes.llvm-premerge-us-central
}

resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.operational_metrics_gsa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${google_service_account.operational_metrics_gsa.project}.svc.id.goog[operational-metrics/operational-metrics-ksa]",
  ]

  depends_on = [
    google_service_account.operational_metrics_gsa,
    kubernetes_service_account.operational_metrics_ksa,
  ]
}

resource "kubernetes_secret" "operational_metrics_secrets" {
  metadata {
    name      = "operational-metrics-secrets"
    namespace = "operational-metrics"
  }

  data = {
    "github-token" = data.google_secret_manager_secret_version.metrics_github_pat.secret_data
  }

  type       = "Opaque"
  provider   = kubernetes.llvm-premerge-us-central
  depends_on = [kubernetes_namespace.operational_metrics]
}

resource "kubernetes_manifest" "operational_metrics_cronjob" {
  manifest = yamldecode(file("operational_metrics_cronjob.yaml"))
  provider = kubernetes.llvm-premerge-us-central

  depends_on = [
    kubernetes_namespace.operational_metrics,
    kubernetes_secret.operational_metrics_secrets,
    kubernetes_service_account.operational_metrics_ksa,
  ]
}

# BigQuery dataset and table resources
resource "google_bigquery_dataset" "operational_metrics_dataset" {
  dataset_id  = "operational_metrics"
  description = "Dataset for retaining operational data regarding LLVM commit trends."
}

resource "google_bigquery_table" "llvm_commits_table" {
  dataset_id  = google_bigquery_dataset.operational_metrics_dataset.dataset_id
  table_id    = "llvm_commits"
  description = "LLVM commit data, including pull request and review activity per commit."

  schema = file("./bigquery_schema/llvm_commits_table_schema.json")

  depends_on = [google_bigquery_dataset.operational_metrics_dataset]
}

resource "google_bigquery_dataset_iam_binding" "operational_metrics_dataset_editor_binding" {
  dataset_id = google_bigquery_dataset.operational_metrics_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"

  members = [
    "serviceAccount:${google_service_account.operational_metrics_gsa.email}",
  ]

  depends_on = [google_bigquery_dataset.operational_metrics_dataset, google_service_account.operational_metrics_gsa]
}
