resource "google_container_cluster" "llvm_premerge" {
  name     = var.cluster_name
  location = var.region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  # Set the networking mode to VPC Native to enable IP aliasing, which is required
  # for adding windows nodes to the cluster.
  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {}

  # Set the workload identity config so that we can authenticate with Google
  # Cloud APIs using workload identity federation as described in
  # https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity.
  workload_identity_config {
    workload_pool = "llvm-premerge-checks.svc.id.goog"
  }

  # We prefer that maintenance is done on weekends between 02:00 and 08:00
  # UTC when commit traffic is low to avoid interruptions.
  maintenance_policy {
    recurring_window {
      start_time = "2025-07-24T02:00:00Z"
      end_time   = "2025-07-24T08:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA,SU"
    }
  }
}

resource "google_container_node_pool" "llvm_premerge_linux_service" {
  name           = "llvm-premerge-linux-service"
  location       = var.region
  cluster        = google_container_cluster.llvm_premerge.name
  node_count     = 3
  node_locations = var.service_node_pool_locations

  node_config {
    machine_type = "e2-highcpu-4"

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

resource "google_container_node_pool" "llvm_premerge_linux" {
  name               = "llvm-premerge-linux"
  location           = var.region
  cluster            = google_container_cluster.llvm_premerge.name
  initial_node_count = 0

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 16
  }

  node_config {
    machine_type = var.linux_machine_type
    taint {
      key    = "premerge-platform"
      value  = "linux"
      effect = "NO_SCHEDULE"
    }
    labels = {
      "premerge-platform" : "linux"
    }
    disk_size_gb = 200

    # Enable workload identity federation for this pool so that we can access
    # GCS buckets.
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# Buildbot here refers specifically to the LLVM Buildbot postcommit
# testing infrastructure. These machines are used specifically for testing
# commits after they have landed in main.
resource "google_container_node_pool" "llvm_buildbot_linux" {
  name               = "llvm-buildbot-linux"
  location           = var.region
  cluster            = google_container_cluster.llvm_premerge.name
  initial_node_count = 0

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 3
  }

  node_config {
    machine_type = var.linux_machine_type
    taint {
      key    = "buildbot-platform"
      value  = "linux"
      effect = "NO_SCHEDULE"
    }
    labels = {
      "buildbot-platform" : "linux"
    }
    disk_size_gb = 200

    # Enable workload identity federation for this pool so that we can access
    # GCS buckets.
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

resource "google_container_node_pool" "llvm_premerge_libcxx" {
  name               = "llvm-premerge-libcxx"
  location           = var.region
  cluster            = google_container_cluster.llvm_premerge.name
  initial_node_count = 0

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 32
  }

  node_config {
    machine_type = var.libcxx_machine_type
    taint {
      key    = "premerge-platform-libcxx"
      value  = "linux-libcxx"
      effect = "NO_SCHEDULE"
    }
    labels = {
      "premerge-platform-libcxx" : "linux-libcxx"
    }
    disk_size_gb = 200
  }
}

resource "google_container_node_pool" "llvm_premerge_windows_2022" {
  name               = "llvm-premerge-windows-2022"
  location           = var.region
  cluster            = google_container_cluster.llvm_premerge.name
  initial_node_count = 0

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 16
  }

  # We do not set a taint for the windows nodes as kubernetes by default sets
  # a node.kubernetes.io/os taint for windows nodes.
  node_config {
    machine_type = var.windows_machine_type
    labels = {
      "premerge-platform" : "windows-2022"
    }
    image_type = "WINDOWS_LTSC_CONTAINERD"
    windows_node_config {
      osversion = "OS_VERSION_LTSC2022"
    }
    # Add a script that runs on the initial boot to disable Windows Defender.
    # Windows Defender causes an increase in test times by approximately an
    # order of magnitude.
    metadata = {
      "sysprep-specialize-script-ps1" = "Set-MpPreference -DisableRealtimeMonitoring $true"
      # Terraform wants to recreate the node pool everytime whe running
      # terraform apply unless we explicitly set this.
      # TODO(boomanaiden154): Look into why terraform is doing this so we do
      # not need this hack.
      "disable-legacy-endpoints" = "true"
    }
    disk_size_gb = 200
    disk_type    = "pd-ssd"

    # Enable workload identity federation for this pool so that we can access
    # GCS buckets.
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# Buildbot here refers specifically to the LLVM Buildbot postcommit
# testing infrastructure. These machines are used specifically for testing
# commits after they have landed in main.
resource "google_container_node_pool" "llvm_buildbot_window_2022" {
  name               = "llvm-buildbot-windows-2022"
  location           = var.region
  cluster            = google_container_cluster.llvm_premerge.name
  initial_node_count = 0

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 3
  }

  # We do not set a taint for the windows nodes as kubernetes by default sets
  # a node.kubernetes.io/os taint for windows nodes.
  node_config {
    # Use the Linux machine type here as we want to keep the windows machines
    # symmetric with the Linux machines for faster builds. Throughput is not
    # as much of a concern postcommit.
    machine_type = var.linux_machine_type
    labels = {
      "buildbot-platform" : "windows-2022"
    }
    image_type = "WINDOWS_LTSC_CONTAINERD"
    windows_node_config {
      osversion = "OS_VERSION_LTSC2022"
    }
    # Add a script that runs on the initial boot to disable Windows Defender.
    # Windows Defender causes an increase in test times by approximately an
    # order of magnitude.
    metadata = {
      "sysprep-specialize-script-ps1" = "Set-MpPreference -DisableRealtimeMonitoring $true"
      # Terraform wants to recreate the node pool everytime whe running
      # terraform apply unless we explicitly set this.
      # TODO(boomanaiden154): Look into why terraform is doing this so we do
      # not need this hack.
      "disable-legacy-endpoints" = "true"
    }
    disk_size_gb = 200
    disk_type    = "pd-ssd"

    # Enable workload identity federation for this pool so that we can access
    # GCS buckets.
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

resource "google_storage_bucket" "object_cache_linux" {
  name     = format("%s-object-cache-linux", var.cluster_name)
  location = var.gcs_bucket_location

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 0
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 1
    }
  }
}

resource "google_storage_bucket" "object_cache_windows" {
  name     = format("%s-object-cache-windows", var.cluster_name)
  location = var.gcs_bucket_location

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 0
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 1
    }
  }
}

resource "google_service_account" "object_cache_linux_gsa" {
  account_id   = format("%s-linux-gsa", var.region)
  display_name = format("%s Linux Object Cache Service Account", var.region)
}

resource "google_service_account" "object_cache_windows_gsa" {
  account_id   = format("%s-windows-gsa", var.region)
  display_name = format("%s Windows Object Cache Service Account", var.region)
}

resource "google_storage_bucket_iam_binding" "linux_bucket_binding" {
  bucket = google_storage_bucket.object_cache_linux.name
  role   = "roles/storage.objectUser"
  members = [
    format("serviceAccount:%s", google_service_account.object_cache_linux_gsa.email),
  ]

  depends_on = [
    google_storage_bucket.object_cache_linux,
    google_service_account.object_cache_linux_gsa,
  ]
}

resource "google_storage_bucket_iam_binding" "windows_bucket_binding" {
  bucket = google_storage_bucket.object_cache_windows.name
  role   = "roles/storage.objectUser"
  members = [
    format("serviceAccount:%s", google_service_account.object_cache_windows_gsa.email),
  ]

  depends_on = [
    google_storage_bucket.object_cache_windows,
    google_service_account.object_cache_windows_gsa
  ]
}

resource "google_service_account_iam_binding" "linux_bucket_gsa_workload_binding" {
  service_account_id = google_service_account.object_cache_linux_gsa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${google_service_account.object_cache_linux_gsa.project}.svc.id.goog[${var.linux_runners_namespace_name}/${var.linux_runners_kubernetes_service_account_name}]",
  ]

  depends_on = [
    google_service_account.object_cache_linux_gsa,
  ]
}

resource "google_service_account_iam_binding" "windows_bucket_gsa_workload_binding" {
  service_account_id = google_service_account.object_cache_windows_gsa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${google_service_account.object_cache_windows_gsa.project}.svc.id.goog[${var.windows_2022_runners_namespace_name}/${var.windows_2022_runners_kubernetes_service_account_name}]",
  ]

  depends_on = [
    google_service_account.object_cache_windows_gsa,
  ]
}
