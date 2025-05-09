variable "cluster_name" {
  description = "The name of the cluster"
  type        = string
}

variable "region" {
  description = "The region to run the cluster in"
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