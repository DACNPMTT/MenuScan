# Import blocks map the ALREADY-EXISTING GCP resources into Terraform state.
#
# Workflow (see README):
#   terraform plan   -> preview; every resource here should show "import" and
#                       the plan should report NO destroy/replace. Reconcile the
#                       .tf files until the plan is clean.
#   terraform apply  -> writes state only (no real infra change) once clean.
#
# After the first successful apply, these blocks are inert and may be deleted.

import {
  to = google_project_service.enabled["run.googleapis.com"]
  id = "menuscan-500911/run.googleapis.com"
}
import {
  to = google_project_service.enabled["sqladmin.googleapis.com"]
  id = "menuscan-500911/sqladmin.googleapis.com"
}
import {
  to = google_project_service.enabled["artifactregistry.googleapis.com"]
  id = "menuscan-500911/artifactregistry.googleapis.com"
}
import {
  to = google_project_service.enabled["iam.googleapis.com"]
  id = "menuscan-500911/iam.googleapis.com"
}
import {
  to = google_project_service.enabled["iamcredentials.googleapis.com"]
  id = "menuscan-500911/iamcredentials.googleapis.com"
}
import {
  to = google_project_service.enabled["compute.googleapis.com"]
  id = "menuscan-500911/compute.googleapis.com"
}
import {
  to = google_project_service.enabled["monitoring.googleapis.com"]
  id = "menuscan-500911/monitoring.googleapis.com"
}

import {
  to = google_artifact_registry_repository.cloud_run_source_deploy
  id = "projects/menuscan-500911/locations/asia-southeast1/repositories/cloud-run-source-deploy"
}

import {
  to = google_sql_database_instance.menuscan_db
  id = "menuscan-500911/menuscan-db"
}
import {
  to = google_sql_database.menuscan
  id = "menuscan-500911/menuscan-db/menuscan"
}

import {
  to = google_service_account.github_actions_deploy
  id = "projects/menuscan-500911/serviceAccounts/github-actions-deploy@menuscan-500911.iam.gserviceaccount.com"
}

import {
  to = google_project_iam_member.deploy_sa["roles/run.admin"]
  id = "menuscan-500911 roles/run.admin serviceAccount:github-actions-deploy@menuscan-500911.iam.gserviceaccount.com"
}
import {
  to = google_project_iam_member.deploy_sa["roles/artifactregistry.writer"]
  id = "menuscan-500911 roles/artifactregistry.writer serviceAccount:github-actions-deploy@menuscan-500911.iam.gserviceaccount.com"
}
import {
  to = google_project_iam_member.deploy_sa["roles/cloudsql.client"]
  id = "menuscan-500911 roles/cloudsql.client serviceAccount:github-actions-deploy@menuscan-500911.iam.gserviceaccount.com"
}
import {
  to = google_project_iam_member.deploy_sa["roles/iam.serviceAccountUser"]
  id = "menuscan-500911 roles/iam.serviceAccountUser serviceAccount:github-actions-deploy@menuscan-500911.iam.gserviceaccount.com"
}

import {
  to = google_service_account_iam_member.wif_impersonation
  id = "projects/menuscan-500911/serviceAccounts/github-actions-deploy@menuscan-500911.iam.gserviceaccount.com roles/iam.workloadIdentityUser principalSet://iam.googleapis.com/projects/754814183582/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/DACNPMTT/MenuScan"
}

import {
  to = google_iam_workload_identity_pool.github
  id = "projects/menuscan-500911/locations/global/workloadIdentityPools/github-actions-pool"
}
import {
  to = google_iam_workload_identity_pool_provider.github
  id = "projects/menuscan-500911/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider"
}
