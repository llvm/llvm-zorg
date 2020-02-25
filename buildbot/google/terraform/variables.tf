# configuration parameter for Google Cloud
variable "gcp_config" {
  type = object({
    project     = string
    region      = string
    zone_a      = string
    gcr_prefix  = string
   })
  default = {
    project     = "sanitizer-bots"
    region      = "us-central1"
    zone_a      = "us-central1-a"
    gcr_prefix  = "gcr.io/sanitizer-bots"
  }
}
