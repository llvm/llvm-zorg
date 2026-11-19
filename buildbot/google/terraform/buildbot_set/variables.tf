variable "buildbot_names" {
  description = "Set of buildbot instance names (also used as Secret Manager secret IDs)."
  type        = set(string)
}

variable "deployment_template_path" {
  description = "Path to the Kubernetes deployment YAML template file."
  type        = string
}
