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

output "linux_object_cache_gcp_service_account_email" {
  value = google_service_account.object_cache_linux_gsa.email
}

output "windows_2022_object_cache_gcp_service_account_email" {
  value = google_service_account.object_cache_windows_gsa.email
}

output "linux_object_cache_buildbot_service_account_email" {
  value = google_service_account.object_cache_linux_buildbot_gsa.email
}

output "windows_2022_object_cache_buildbot_service_account_email" {
  value = google_service_account.object_cache_windows_buildbot_gsa.email
}
