resource "google_service_account" "github_actions_deploy" {
  project      = var.project_id
  account_id   = "github-actions-deploy"
  display_name = "github-actions-deploy"
}

# Project roles the CD pipeline needs: push images, deploy Cloud Run
# services/jobs, connect to Cloud SQL, and act as the runtime service account.
locals {
  deploy_sa_roles = [
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/cloudsql.client",
    "roles/iam.serviceAccountUser",
  ]
}

resource "google_project_iam_member" "deploy_sa" {
  for_each = toset(local.deploy_sa_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.github_actions_deploy.email}"
}

# Let the GitHub repo (through the WIF pool) impersonate the deploy SA. This is
# what makes keyless auth from GitHub Actions work.
resource "google_service_account_iam_member" "wif_impersonation" {
  service_account_id = google_service_account.github_actions_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}
