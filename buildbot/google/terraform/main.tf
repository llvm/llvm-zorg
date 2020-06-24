
# configure Google Cloud project
provider "google" {
  project  = var.gcp_config.project
  region   = var.gcp_config.region
}

# Create the cluster runningn all Kubernetes services
resource "google_container_cluster" "primary" {
  name     = "buildbot-cluster"
  # maybe have a regional cluster for Kubernetes, as we depend on this...
  location = var.gcp_config.zone_a

  # one node is enough (at the moment)
  initial_node_count = 1

  node_config {
    # FIXME(kuhnel): turn this into a private cluster, without external IP
    # We need at least 2 vCPU to run all kubernetes services
    machine_type = "n1-standard-2"
    # use preemptible, as this saves costs
    preemptible = true
  }
}

# Create machines for mlir-nvidia
# Note: The buildbot mlir-nividia is deployed using a kubernetes file. See
# the README.md for details on GPUs.

resource "google_container_node_pool" "nvidia_16core_pool_nodes" {
  name       = "nvidia-16core-pool"
  # specify a zone here (e.g. "-a") to avoid a redundant deployment
  location   = var.gcp_config.zone_a
  cluster    = google_container_cluster.primary.name
  
  # use autoscaling to only create a machine when there is a deployment
  autoscaling {
    min_node_count = 0
    max_node_count = 1
  }
  
  node_config {
    # use preemptible, as this saves costs
    preemptible  = true
    machine_type = "n1-highcpu-16"
    disk_size_gb = 100
    # FIXME: test if SSDs are actually faster than HDDs for our use case
    disk_type = "pd-ssd"
    guest_accelerator {
      type = "nvidia-tesla-t4"
      count= 1
    }

    # set the premissions required for the deployment later
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only",
    ]

    # add a label to all machines of this type, so we can select them 
    # during deployment
    labels = {
      pool = "nvidia-16core-pool"
    }
  }
}
