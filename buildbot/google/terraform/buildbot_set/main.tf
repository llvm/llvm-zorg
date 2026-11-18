data "google_secret_manager_secret_version" "password" {
  for_each = var.buildbot_names
  secret   = each.value
}

resource "kubernetes_secret_v1" "password" {
  for_each = var.buildbot_names

  metadata {
    name = "password-${each.value}"
  }

  data = {
    "password" = data.google_secret_manager_secret_version.password[each.value].secret_data
  }

  type = "Opaque"
}

removed {
  from = kubernetes_secret.password
  lifecycle {
    destroy = false
  }
}

resource "kubernetes_manifest" "deployment" {
  for_each = var.buildbot_names

  manifest = yamldecode(
    templatefile(var.deployment_template_path, {
      buildbot_name = each.value
      secret_name   = kubernetes_secret_v1.password[each.value].metadata[0].name
    })
  )

  depends_on = [
    kubernetes_secret_v1.password
  ]
}
