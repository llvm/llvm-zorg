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
}

resource "google_container_node_pool" "bazel_ci" {
  name               = "bazel-ci"
  location           = "us-central1-c"
  cluster            = google_container_cluster.llvm_bazel_cluster.name
  initial_node_count = 2

  node_config {
    machine_type = "n2-standard-64"
  }
}

data "google_client_config" "current" {}

provider "kubernetes" {
  host  = "https://${llvm_bazel_cluster.endpoint}"
  token = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(
    google_container_cluster.llvm_bazel_cluster.cluster_ca_certificate
  )
  alias = "llvm-bazel-cluster"
}

data "google_secret_manager_secret_version" "buildkite_agent_token" {
  secret = "buildkite-agent-token"
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

resource "kubernetes_manifest" "bazel_buildkite" {
  manifest = yamldecode(file("bazel-buildkite.yaml"))
  depends_on = [
    kubernetes_namespace.bazel_ci,
    kubernetes_secret.buildkite_agent_token
  ]
}
