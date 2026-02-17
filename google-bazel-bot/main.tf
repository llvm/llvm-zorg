terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.43.0"
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
