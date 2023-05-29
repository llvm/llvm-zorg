# configure cloud storage backend to keep state information. This is shared 
# across all users and contains the previously configured parts. Accessing
# GCS requires that the environment variable `GOOGLE_CLOUD_KEYFILE_JSON` points
# to your credential file, e.g. 
# ~/.config/gcloud/legacy_credentials/<your email>/adc.json
terraform {
  backend "gcs" {
    bucket  = "buildbot_cluster_terraform_backend"
    prefix  = "terraform/state"
  }
}

# configure Google Cloud project
provider "google" {
  project  = var.gcp_config.project
  region   = var.gcp_config.region
}


# create a network for the cluster, required for Kubernetes on Windows 
# FIXME: rename to "buildbot-vpc-network", causes destruction of the cluster!
resource "google_compute_network" "vpc_network" {
  name = "vpc-network"
}

# Create the cluster runningn all Kubernetes services
resource "google_container_cluster" "primary" {
  name     = "buildbot-cluster"
  # maybe have a regional cluster for Kubernetes, as we depend on this...
  location = var.gcp_config.zone_a
  
  # configure local network, required for Kubernetes on Windows 
  network = google_compute_network.vpc_network.name
  # enable alias IP addresses, required for Kubernetes for Windows
  ip_allocation_policy {}

  # use newer Kubernetes version, otherwise Windows node pools can't be created
  min_master_version = "1.16"

  # one node is enough (at the moment)
  initial_node_count = 1

  node_config {
    # FIXME(kuhnel): turn this into a private cluster, without external IP
    # We need at least 2 vCPU to run all kubernetes services
    machine_type = "e2-medium"
    # use preemptible, as this saves costs
    preemptible = true
  }

}

resource "google_container_node_pool" "linux_16_core_pool" {
  name       = "linux-16-core-pool"
  # specify a zone here (e.g. "-a") to avoid a redundant deployment
  location   = var.gcp_config.zone_a
  cluster    = google_container_cluster.primary.name
  
  # use autoscaling to only create a machine when there is a deployment
  autoscaling {
    min_node_count = 0
    max_node_count = 2
  }
  
  node_config {
    # use preemptible, as this saves costs
    preemptible  = true
    #custom machine type: 16 core, 48 GB as tsan needs more RAM
    machine_type = "n2d-custom-16-49152"
    disk_size_gb = 100
    disk_type = "pd-ssd"

    # set the premissions required for the deployment later
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only",
    ]

    # add a label to all machines of this type, so we can select them 
    # during deployment
    labels = {
      pool = "linux-16-core-pool"
    }
  }
}
