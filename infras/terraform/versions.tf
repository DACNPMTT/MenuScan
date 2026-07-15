terraform {
  # >= 1.5 is required for the `import {}` blocks used in imports.tf.
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # State is local by default (see .gitignore). For a shared/durable state,
  # bootstrap a bucket once:
  #   gcloud storage buckets create gs://menuscan-tf-state \
  #     --location=asia-southeast1 --uniform-bucket-level-access \
  #     --project=menuscan-500911
  # then uncomment this block and run `terraform init -migrate-state`.
  #
  # backend "gcs" {
  #   bucket = "menuscan-tf-state"
  #   prefix = "platform"
  # }
}
