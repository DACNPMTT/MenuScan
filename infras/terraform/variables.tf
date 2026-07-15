variable "project_id" {
  description = "GCP project ID."
  type        = string
  default     = "menuscan-500911"
}

variable "project_number" {
  description = "GCP project number (used in Workload Identity resource names)."
  type        = string
  default     = "754814183582"
}

variable "region" {
  description = "Primary region for regional resources."
  type        = string
  default     = "asia-southeast1"
}

variable "github_repository" {
  description = "owner/name of the GitHub repo allowed to impersonate the deploy SA via WIF."
  type        = string
  default     = "DACNPMTT/MenuScan"
}

variable "service_host" {
  description = "Public hostname of the Cloud Run service (no scheme) for uptime checks."
  type        = string
  default     = "menuscan-api-vv7wxllnta-as.a.run.app"
}

variable "alert_email" {
  description = "Email address that receives monitoring alerts."
  type        = string
  default     = "hahuynhdai@gmail.com"
}
