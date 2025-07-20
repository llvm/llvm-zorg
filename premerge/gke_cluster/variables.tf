variable "cluster_name" {
  description = "The name of the cluster"
  type        = string
}

variable "region" {
  description = "The region to run the cluster in"
  type        = string
}

variable "gcs_bucket_location" {
  description = "The location to use for the GCS buckets"
  type        = string
}

variable "linux_machine_type" {
  description = "The type of machine to use for Linux instances"
  type        = string
}

variable "windows_machine_type" {
  description = "The type of machine to use for Windows instances"
  type        = string
}

variable "libcxx_machine_type" {
  description = "The type of machine to use for libcxx instances (linux)"
  type        = string
}

variable "service_node_pool_locations" {
  description = "The location to run the service node pool in"
  type        = list(any)
  default     = null
}
