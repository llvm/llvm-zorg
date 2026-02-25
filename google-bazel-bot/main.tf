terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.43.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.35.1"
    }
  }
}

provider "google" {
  project = "llvm-bazel"
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

resource "google_container_cluster" "llvm_bazel_cluster" {
  name     = "llvm-bazel-cluster"
  location = "us-central1-c"

  remove_default_node_pool = true
  initial_node_count       = 1

  workload_identity_config {
    workload_pool = "llvm-bazel.svc.id.goog"
  }
}

resource "google_container_node_pool" "bazel_ci" {
  name               = "bazel-ci"
  location           = "us-central1-c"
  cluster            = google_container_cluster.llvm_bazel_cluster.name
  initial_node_count = 2

  node_config {
    machine_type = "n2-standard-64"
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

resource "google_service_account" "bazel_cache_gsa" {
  account_id   = "bazel-cache"
  display_name = "Service account for accessing bazel cache."
}

resource "google_project_iam_binding" "vertex_ai_user_binding" {
  project = "llvm-bazel"
  role    = "roles/aiplatform.user"

  members = [
    "serviceAccount:${google_service_account.bazel_cache_gsa.email}",
  ]

  depends_on = [google_service_account.bazel_cache_gsa]
}

resource "google_storage_bucket" "bazel_cache_bucket" {
  name     = "llvm-bazel-cache"
  location = "us-central1-c"

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # Disable soft deletion. Soft deletion keeps the file around for the
  # specified duration (or deletes immediately if set to zero) after it is
  # requested to be deleted.
  soft_delete_policy {
    retention_duration_seconds = 0
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 7
    }
  }
}

resource "google_storage_bucket_iam_binding" "cache_bucket_binding" {
  bucket = google_storage_bucket.bazel_cache_bucket.name
  role   = "roles/storage.objectUser"
  members = [
    format("serviceAccount:%s", google_service_account.bazel_cache_gsa.email)
  ]

  depends_on = [
    google_service_account.bazel_cache_gsa
  ]
}

data "google_client_config" "current" {}

provider "kubernetes" {
  host  = "https://${google_container_cluster.llvm_bazel_cluster.endpoint}"
  token = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(
    google_container_cluster.llvm_bazel_cluster.master_auth[0].cluster_ca_certificate
  )
}

data "google_secret_manager_secret_version" "buildkite_agent_token" {
  secret = "buildkite-agent-token"
}

data "google_secret_manager_secret_version" "github_api_token" {
  secret = "github-api-token"
}

data "google_secret_manager_secret_version" "buildkite_api_token" {
  secret = "buildkite-api-token"
}

resource "kubernetes_namespace" "bazel_ci" {
  metadata {
    name = "bazel-ci"
  }
}

resource "kubernetes_secret" "buildkite_agent_token" {
  metadata {
    name      = "buildkite-agent-token"
    namespace = kubernetes_namespace.bazel_ci.metadata[0].name
  }

  data = {
    "token" = data.google_secret_manager_secret_version.buildkite_agent_token.secret_data
  }

  type       = "Opaque"
  depends_on = [kubernetes_namespace.bazel_ci]
}

resource "kubernetes_secret" "github_api_token" {
  metadata {
    name      = "github-api-token"
    namespace = kubernetes_namespace.bazel_ci.metadata[0].name
  }

  data = {
    "token" = data.google_secret_manager_secret_version.github_api_token.secret_data
  }

  type       = "Opaque"
  depends_on = [kubernetes_namespace.bazel_ci]
}

resource "kubernetes_secret" "buildkite_api_token" {
  metadata {
    name      = "buildkite-api-token"
    namespace = kubernetes_namespace.bazel_ci.metadata[0].name
  }

  data = {
    "token" = data.google_secret_manager_secret_version.buildkite_api_token.secret_data
  }

  type       = "Opaque"
  depends_on = [kubernetes_namespace.bazel_ci]
}

resource "kubernetes_service_account" "bazel_cache_ksa" {
  metadata {
    name      = "bazel-cache-ksa"
    namespace = kubernetes_namespace.bazel_ci.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.bazel_cache_gsa.email
    }
  }

  depends_on = [kubernetes_namespace.bazel_ci]
}

resource "google_service_account_iam_binding" "bazel_cache_gsa_binding" {
  service_account_id = google_service_account.bazel_cache_gsa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${google_service_account.bazel_cache_gsa.project}.svc.id.goog[bazel-ci/bazel-cache-ksa]"
  ]

  depends_on = [
    google_service_account.bazel_cache_gsa
  ]
}

resource "kubernetes_manifest" "bazel_buildkite" {
  manifest = yamldecode(file("bazel-buildkite.yaml"))
  depends_on = [
    kubernetes_namespace.bazel_ci,
    kubernetes_secret.buildkite_agent_token,
    kubernetes_service_account.bazel_cache_ksa
  ]
}

resource "kubernetes_manifest" "bazel_fixer_bot" {
  manifest = yamldecode(file("bazel-fixer-bot.yaml"))
  depends_on = [
    kubernetes_namespace.bazel_ci,
    kubernetes_secret.github_api_token,
    kubernetes_secret.buildkite_api_token,
    kubernetes_service_account.bazel_cache_ksa
  ]
}
