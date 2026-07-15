locals {
  # The Cloud Run service and the migrate job both run as the project's default
  # compute service account. That is the identity that reads the secrets.
  runtime_service_account = "${var.project_number}-compute@developer.gserviceaccount.com"

  # Sensitive values moved out of the Cloud Run revision config into Secret
  # Manager. Each entry is a Secret Manager secret id; the VALUE is seeded
  # out-of-band (see seed-secrets.sh) and never lives in Terraform state.
  secret_ids = [
    "database-url",
    "secret-key",
    "email-smtp-password",
    "google-vision-api-key",
    "gemini-api-key",
    "gemini-api-keys",
    "enrich-gemini-api-keys",
    "chat-gemini-api-keys",
  ]
}

# Secret containers only — no versions/values here.
resource "google_secret_manager_secret" "app" {
  for_each  = toset(local.secret_ids)
  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

# Let the Cloud Run runtime SA read each secret. Least privilege: granted per
# secret, not project-wide.
resource "google_secret_manager_secret_iam_member" "runtime_accessor" {
  for_each  = google_secret_manager_secret.app
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.runtime_service_account}"
}
