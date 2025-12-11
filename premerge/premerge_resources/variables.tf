variable "github_app_id" {
  description = "The Github app ID to use for authentication"
  type        = string
}

variable "github_app_installation_id" {
  description = "The Github app installation ID for authentication"
  type        = string
}

variable "github_app_private_key" {
  description = "The Github app private key for authentication"
  type        = string
}

variable "cluster_name" {
  type = string
}

variable "grafana_token" {
  type = string
}

variable "github_arc_version" {
  type = string
}

variable "externalservices_prometheus_host" {
  type    = string
  default = "https://prometheus-prod-13-prod-us-east-0.grafana.net"
}

variable "externalservices_prometheus_basicauth_username" {
  type    = number
  default = 1716097
}

variable "externalservices_loki_host" {
  type    = string
  default = "https://logs-prod-006.grafana.net"
}

variable "externalservices_loki_basicauth_username" {
  type    = number
  default = 957850
}

variable "externalservices_tempo_host" {
  type    = string
  default = "https://tempo-prod-04-prod-us-east-0.grafana.net:443"
}

variable "externalservices_tempo_basicauth_username" {
  type    = number
  default = 952165
}

variable "runner_group_name" {
  type = string
}

variable "linux_runners_namespace_name" {
  description = "The name of the namespace containing the Linux runners"
  type        = string
}

variable "linux_runners_kubernetes_service_account_name" {
  description = "The name of the kubernetes service account used to access the Linux object cache GCS bucket"
  type        = string
}

variable "windows_2022_runners_namespace_name" {
  description = "The name of the namespace containing the Windows runners"
  type        = string
}

variable "windows_2022_runners_kubernetes_service_account_name" {
  description = "The name of the kubernetes service account used to access the Windows object cache GCS bucket"
  type        = string
}

variable "linux_object_cache_gcp_service_account_email" {
  description = "The email associated with the service account for accessing the object cache on Linux."
  type        = string
}

variable "windows_2022_object_cache_gcp_service_account_email" {
  description = "The email associated with the service account for accessing the object cache on Windows."
  type        = string
}

variable "linux_buildbot_name_template" {
  description = "The name of the linux buildbot that will run tests postcommit."
  type        = string
}

variable "linux_buildbot_password" {
  description = "The password for the linux buildbot that will run tests postcommit."
  type        = string
}

variable "windows_buildbot_name_template" {
  description = "The name of the windows buildbot that will run tests postcommit."
  type        = string
}

variable "windows_buildbot_password" {
  description = "The password for the windows buildbot that will run tests postcommit."
  type        = string
}

variable "linux_object_cache_buildbot_service_account_email" {
  description = "The email associated with the service account for the buildbot worker accessing the object cache on Linux."
  type        = string
}

variable "windows_2022_object_cache_buildbot_service_account_email" {
  description = "The email associated with the service account for the buildbot worker accessing the object cache on Windows."
  type        = string
}
