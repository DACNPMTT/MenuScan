resource "google_sql_database_instance" "menuscan_db" {
  project          = var.project_id
  name             = "menuscan-db"
  region           = var.region
  database_version = "POSTGRES_18"

  # Terraform-side guard: keep true so `terraform destroy` can never drop the
  # live database.
  deletion_protection = true

  settings {
    tier              = "db-custom-1-3840"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"
    activation_policy = "ALWAYS"

    # Matches the live instance (GCP-side delete guard is ON).
    deletion_protection_enabled = true

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      # The live instance already enforces TLS (ssl_mode = ENCRYPTED_ONLY); this
      # keeps the file in sync and satisfies Trivy AVD-GCP-0015. Public IP is
      # kept on purpose (AVD-GCP-0017 is suppressed in .trivyignore).
      ssl_mode     = "ENCRYPTED_ONLY"
      ipv4_enabled = true
    }
  }

  lifecycle {
    # The instance's detailed live settings — PITR, backup location, database
    # flags (cloudsql.iam_authentication), authorized networks, maintenance
    # window, password policy, dataplex, etc. — are managed outside Terraform
    # (console/gcloud). Ignore the whole settings block so an apply can NEVER
    # strip or overwrite that live configuration; Terraform still tracks the
    # instance's existence and identity.
    ignore_changes = [settings]
  }

  depends_on = [google_project_service.enabled]
}

# The application database. The auto-created `postgres` database and the SQL
# users/passwords are intentionally NOT managed here — credentials stay out of
# Terraform state (they live in Secret Manager, see secrets.tf).
resource "google_sql_database" "menuscan" {
  project  = var.project_id
  name     = "menuscan"
  instance = google_sql_database_instance.menuscan_db.name
}
