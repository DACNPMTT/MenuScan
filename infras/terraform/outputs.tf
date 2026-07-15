output "artifact_registry_repo" {
  description = "Full resource name of the Docker repository."
  value       = google_artifact_registry_repository.cloud_run_source_deploy.name
}

output "cloudsql_connection_name" {
  description = "Cloud SQL connection name (project:region:instance) for the socket path."
  value       = google_sql_database_instance.menuscan_db.connection_name
}

output "deploy_service_account" {
  description = "Email of the CI/CD deploy service account."
  value       = google_service_account.github_actions_deploy.email
}

output "wif_provider" {
  description = "Full resource name of the Workload Identity provider used by GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "dashboard_url" {
  description = "Console URL of the MenuScan monitoring dashboard."
  value       = "https://console.cloud.google.com/monitoring/dashboards/builder/${reverse(split("/", google_monitoring_dashboard.menuscan.id))[0]}?project=${var.project_id}"
}
