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

resource "null_resource" "update_cluster" {
  # Add NVIDIA driver daemonset.
  depends_on = [google_container_cluster.primary]
  # Update kubectl context for the cluster and apply nvidia's daemonset.
  provisioner "local-exec" {
      command = <<EOT
        gcloud container clusters get-credentials cudabot
        kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml
      EOT
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
    max_node_count = 2
  }
  
  node_config {
    # use preemptible, as this saves costs
    preemptible  = true
    # FIXME upgrade to "n1-custom-24-32768"
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

resource "null_resource" "deployment-mlir-nvidia" {
  # Add NVIDIA driver daemonset.
  depends_on = [null_resource.update_cluster]
  triggers = {
    t4_contents = filemd5("${path.module}/deployment-mlir-nvidia-production.yaml")
  }
  # Add NVIDIA daemonset and deploy mlir-nvidia.
  # Using this workaround as terraform does not support GPUs on Google Cloud.
  # https://github.com/terraform-providers/terraform-provider-kubernetes/issues/149
  provisioner "local-exec" {
      command = "kubectl apply -f ${path.module}/deployment-mlir-nvidia-production.yaml"
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


resource "kubernetes_deployment" "clangd-ubuntu-clang" {
  metadata {
    name = "clangd-ubuntu-clang"
    labels = {
      app = "clangd-ubuntu-clang"
    }
  }

  spec {
    # create one instance of this container
    replicas = 1

    selector {
      match_labels = {
        app = "clangd-ubuntu-clang"
      }
    }
    strategy{
      rolling_update{
        # do not deploy more replicas, as the buildbot server 
        # can't handle multiple workers with the same credentials
        max_surge = 0
        # Allow to have 0 replicas during updates. 
        max_unavailable = 1
        }
      type = "RollingUpdate"
    }
    template {
      metadata {
        labels = {
          app = "clangd-ubuntu-clang"
        }
      }

      spec {
        container {
          image = "${var.gcp_config.gcr_prefix}/buildbot-clangd-ubuntu-clang:5"
          name  = "buildbot-clangd-ubuntu-clang"

          # reserve "<number of cores>-1" for this image, kubernetes also
          # needs <1 core for management tools
          resources {
            limits {
              cpu    = "15"
              memory = "45G"
            }
            requests {
              cpu    = "15"
              memory = "45G"
            }
          }

          # mount the secrets into a folder  
          volume_mount {
            mount_path = "/vol/secrets"
            name = "buildbot-token"
          }
          volume_mount {
            mount_path = "/vol/ccache"
            name = "ccache-vol"
          }
          volume_mount {
            mount_path = "/vol/worker"
            name = "worker-vol"
          }

          env {
            # connect to production environment, running at port 9990 
            # staging would be at 9994
            name = "BUILDBOT_PORT"
            value = "9990"          
          }          
        }
        # select which node pool to deploy to
        node_selector = {
          pool = "linux-16-core-pool"
        }
        # restart in case of any crashes
        restart_policy = "Always"
        
        # select the secret to be mounted
        volume {
          name = "buildbot-token"
            secret {
              optional = false
              secret_name = "password-clangd-ubuntu-clang"
            }
        }
        volume {
          name = "ccache-vol"
          empty_dir {}
        }
        volume {
          name = "worker-vol"
          empty_dir {}
        }

      }
    }
  }
}
