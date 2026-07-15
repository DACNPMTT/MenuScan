resource "google_artifact_registry_repository" "cloud_run_source_deploy" {
  project       = var.project_id
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  description   = "Cloud Run Source Deployments"
  format        = "DOCKER"
  mode          = "STANDARD_REPOSITORY"

  depends_on = [google_project_service.enabled]
}
