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

variable "libcxx_runner_image" {
  type = string
  default = "ghcr.io/llvm/libcxx-linux-builder:b060022103f551d8ca1dad84122ef73927c86512"
}

variable "libcxx_release_runner_image" {
  type = string
  default = "ghcr.io/llvm/libcxx-linux-builder:b060022103f551d8ca1dad84122ef73927c86512"
}

# Same value as libcxx_runner_image at this time.
variable "libcxx_next_runner_image" {
  type = string
  default = "ghcr.io/llvm/libcxx-linux-builder:b060022103f551d8ca1dad84122ef73927c86512"
}
