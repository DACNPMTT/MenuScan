resource "google_sql_database_instance" "menuscan_db" {
  project          = var.project_id
  name             = "menuscan-db"
  region           = var.region
  database_version = "POSTGRES_18"

  # Terraform-side guard: keep true so `terraform destroy` can never drop the
  # live database. (This is separate from the GCP-side flag below.)
  deletion_protection = true

  settings {
    tier              = "db-custom-1-3840"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    # activation_policy is toggled by hand — ALWAYS for demos, NEVER to stop
    # billing between them. It is ignored below so the manual start/stop is not
    # flagged as drift on every plan.
    activation_policy = "ALWAYS"

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled = true
    }

    deletion_protection_enabled = false
  }

  lifecycle {
    ignore_changes = [settings[0].activation_policy]
  }

  depends_on = [google_project_service.enabled]
}

# The application database. The auto-created `postgres` database and the SQL
# users/passwords are intentionally NOT managed here — credentials stay out of
# Terraform state (they belong in Secret Manager, see the deploy TODO).
resource "google_sql_database" "menuscan" {
  project  = var.project_id
  name     = "menuscan"
  instance = google_sql_database_instance.menuscan_db.name
}
