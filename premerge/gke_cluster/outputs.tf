output "endpoint" {
  value = google_container_cluster.llvm_premerge.endpoint
}

output "client_certificate" {
  value = google_container_cluster.llvm_premerge.master_auth.0.client_certificate
}

output "client_key" {
  value = google_container_cluster.llvm_premerge.master_auth.0.client_key
}

output "cluster_ca_certificate" {
  value = google_container_cluster.llvm_premerge.master_auth.0.cluster_ca_certificate
}