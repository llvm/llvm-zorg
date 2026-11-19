# configure cloud storage backend to keep state information. This is shared 
# across all users and contains the previously configured parts. Accessing
# GCS requires that the environment variable `GOOGLE_CLOUD_KEYFILE_JSON` points
# to your credential file, e.g. 
# ~/.config/gcloud/legacy_credentials/<your email>/adc.json
terraform {
  backend "gcs" {
    bucket = "buildbot_cluster_terraform_backend"
    prefix = "terraform/state"
  }
}

# configure Google Cloud project
provider "google" {
  project = var.gcp_config.project
  region  = var.gcp_config.region
}

# create a network for the cluster, required for Kubernetes on Windows 
# FIXME: rename to "buildbot-vpc-network", causes destruction of the cluster!
resource "google_compute_network" "vpc_network" {
  name = "vpc-network"
}

# Create the cluster runningn all Kubernetes services
resource "google_container_cluster" "primary" {
  name = "buildbot-cluster"
  # maybe have a regional cluster for Kubernetes, as we depend on this...
  location = var.gcp_config.zone_a

  # configure local network, required for Kubernetes on Windows 
  network = google_compute_network.vpc_network.name
  # enable alias IP addresses, required for Kubernetes for Windows
  ip_allocation_policy {}

  # Keep around for now to avoid updates to the cluster.
  enable_shielded_nodes = false

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
  name = "linux-16-core-pool"
  # specify a zone here (e.g. "-a") to avoid a redundant deployment
  location = var.gcp_config.zone_a
  cluster  = google_container_cluster.primary.name

  # use autoscaling to only create a machine when there is a deployment
  autoscaling {
    min_node_count = 0
    max_node_count = 2
  }

  node_config {
    # use preemptible, as this saves costs
    preemptible = true
    #custom machine type: 16 core, 48 GB as tsan needs more RAM
    machine_type = "n2d-custom-16-49152"
    disk_size_gb = 100
    disk_type    = "pd-ssd"

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

# Despite the name, this secret is shared and still used by clang-debian-cpp20.
data "google_secret_manager_secret_version" "password_clangd_ubuntu_clang" {
  secret = "password-clangd-ubuntu-clang"
}

data "google_client_config" "current" {}

provider "kubernetes" {
  host  = "https://${google_container_cluster.primary.endpoint}"
  token = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(
    google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  )
}

resource "kubernetes_secret_v1" "clangd_ubuntu_clang_password" {
  metadata {
    name = "password-clangd-ubuntu-clang"
  }

  data = {
    "token" = data.google_secret_manager_secret_version.password_clangd_ubuntu_clang.secret_data
  }

  type = "Opaque"
}

resource "kubernetes_manifest" "clang_debian_cpp20" {
  manifest = yamldecode(file("${path.module}/deployment-clang-debian-cpp20.yaml"))
}

data "google_compute_zones" "available" {
  region = var.gcp_config.region
  status = "UP"
}

resource "google_container_node_pool" "linux_32_core_pool" {
  name           = "linux-32-core-pool"
  location       = var.gcp_config.zone_a
  cluster        = google_container_cluster.primary.name
  node_locations = data.google_compute_zones.available.names

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 10
    location_policy      = "ANY"
  }

  node_config {
    preemptible  = true
    machine_type = "n2d-standard-32"
    disk_size_gb = 100
    disk_type    = "pd-ssd"

    labels = {
      pool = "linux-32-core-pool"
    }
  }
}

module "profcheck" {
  source                   = "./buildbot_set"
  buildbot_names           = ["profcheck-b1", "profcheck-b2"]
  deployment_template_path = "${path.module}/profcheck_deployment.yaml"
}

module "google_integrate" {
  source                   = "./buildbot_set"
  buildbot_names           = ["google-integrate-b1", "google-integrate-b2"]
  deployment_template_path = "${path.module}/google_integrate_deployment.yaml"
}

module "ml_opt_rel" {
  source                   = "./buildbot_set"
  buildbot_names           = ["ml-opt-rel-x86-64-b1", "ml-opt-rel-x86-64-b2"]
  deployment_template_path = "${path.module}/ml_opt_rel.yaml"
}

module "ml_opt_dev" {
  source                   = "./buildbot_set"
  buildbot_names           = ["ml-opt-dev-x86-64-b1", "ml-opt-dev-x86-64-b2"]
  deployment_template_path = "${path.module}/ml_opt_dev.yaml"
}

module "ml_opt_devrel" {
  source                   = "./buildbot_set"
  buildbot_names           = ["ml-opt-devrel-x86-64-b1", "ml-opt-devrel-x86-64-b2"]
  deployment_template_path = "${path.module}/ml_opt_dev.yaml"
}
