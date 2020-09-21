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

# node pool for windows machines
resource "google_container_node_pool" "windows_32core_pool_nodes" {
  name       = "windows-32core-pool"
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
    machine_type = "e2-highcpu-32"
    # Windows deployments tend to require more disk space, so using 300GB here.
    disk_size_gb = 300
    # FIXME: test if SSDs are actually faster than HDDs for our use case
    disk_type = "pd-ssd"

    # Configure Windows image. As Windows is picky about the combination of
    # host and container OS versions, this must be compatible with the version
    # in your container. Recommondation: Use LTSC for long-term stability.
    # For details see
    # https://docs.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility
    # https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-cluster-windows#choose_your_windows_server_node_image
    image_type = "WINDOWS_LTSC"

    # set the premissions required for the deployment later
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only",
    ]

    # add a label to all machines of this type, so we can select them 
    # during deployment
    labels = {
      pool = "win-32core-pool"
    }
  }
}

# Deployment for the buildbot windows10_vs2019 running on Windows rather than
# Linux. 
# Note: Deploying this takes significantly longer (~35 min) than on Linux 
# as the images tend to be larger (~18GB) and IO performance is lower.
resource "kubernetes_deployment" "windows10_vs2019" {
  metadata {
    name = "windows10-vs2019"
    labels = {
      app = "windows10_vs2019"
    }
  }

  spec {
    # create one instance of this container
    replicas = 1

    selector {
      match_labels = {
        app = "windows10_vs2019"
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
          app = "windows10_vs2019"
        }
      }

      spec {
        container {
          image = "${var.gcp_config.gcr_prefix}/buildbot-windows10-vs2019:15"
          name  = "windows10-vs2019"

          # reserve "<number of cores>-1" for this image, kubernetes also
          # needs <1 core for management tools
          resources {
            limits {
              cpu    = "31"
              memory = "20Gi"
            }
            requests {
              cpu    = "31"
              memory = "20Gi"
            }
          }

          # mount the secrets into a folder  
          volume_mount {
            mount_path = "c:\\volumes\\secrets"
            name = "buildbot-token"
          }
          volume_mount {
            mount_path = "c:\\volumes\\sccache"
            name = "sccache-vol"
          }
          volume_mount {
            mount_path = "c:\\volumes\\buildbot"
            name = "buildbot-vol"
          }
        }
        # select which node pool to deploy to
        node_selector = {
          pool = "win-32core-pool"
        }
        # restart in case of any crashes
        restart_policy = "Always"
        
        # select the secret to be mounted
        volume {
          name = "buildbot-token"
            secret {
              optional = false
              secret_name = "password-windows10-vs2019"
            }
        }
        volume {
          name = "sccache-vol"
          empty_dir {}
        }
        volume {
          name = "buildbot-vol"
          empty_dir {}
        }

        # Windows nodes from the node pool are marked with the taint 
        # "node.kubernetes.io/os=windows". So we need to "tolerate" this to
        # deploy to such nodes.
        toleration {
          effect    = "NoSchedule"
          key       = "node.kubernetes.io/os"
          operator  = "Equal"
          value     = "windows"
        }
      }
    }
  }
}
