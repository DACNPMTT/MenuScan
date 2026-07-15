# Observability for the Cloud Run service. These resources are NEW (there is no
# import block for them) — the first `terraform apply` creates them.

# ── Where alerts go ─────────────────────────────────────────────────────────
resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "MenuScan alerts (email)"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# ── Uptime checks ───────────────────────────────────────────────────────────
# /health = the process is up and serving HTTP (no dependencies).
resource "google_monitoring_uptime_check_config" "health" {
  project      = var.project_id
  display_name = "menuscan-api /health"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.service_host
    }
  }
}

# /ready = the process can reach its dependencies (DB, email, storage). This is
# what catches the Cloud SQL instance being STOPPED at runtime — /health would
# still pass, but /ready returns 5xx.
resource "google_monitoring_uptime_check_config" "ready" {
  project      = var.project_id
  display_name = "menuscan-api /ready"
  timeout      = "10s"
  period       = "300s"

  http_check {
    path         = "/ready"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.service_host
    }
  }
}

# ── Alert policies ──────────────────────────────────────────────────────────
# Service down: /health uptime check failing.
resource "google_monitoring_alert_policy" "service_down" {
  project      = var.project_id
  display_name = "menuscan-api is DOWN (/health failing)"
  combiner     = "OR"

  conditions {
    display_name = "/health uptime check failing"
    condition_threshold {
      filter = join(" AND ", [
        "resource.type = \"uptime_url\"",
        "metric.type = \"monitoring.googleapis.com/uptime_check/check_passed\"",
        "metric.label.check_id = \"${google_monitoring_uptime_check_config.health.uptime_check_id}\"",
      ])
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "60s"

      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.project_id", "resource.label.host"]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content = "The /health uptime check is failing — the Cloud Run service is not serving HTTP. Check the latest revision and its logs."
  }
}

# Dependencies down: /ready uptime check failing (typically Cloud SQL STOPPED).
resource "google_monitoring_alert_policy" "dependencies_down" {
  project      = var.project_id
  display_name = "menuscan-api dependencies UNHEALTHY (/ready failing)"
  combiner     = "OR"

  conditions {
    display_name = "/ready uptime check failing"
    condition_threshold {
      filter = join(" AND ", [
        "resource.type = \"uptime_url\"",
        "metric.type = \"monitoring.googleapis.com/uptime_check/check_passed\"",
        "metric.label.check_id = \"${google_monitoring_uptime_check_config.ready.uptime_check_id}\"",
      ])
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "60s"

      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.project_id", "resource.label.host"]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content = "The /ready check is failing while /health may still pass — a dependency is down. Most often this is the Cloud SQL instance `menuscan-db` being STOPPED (activation_policy NEVER). Re-enable it with: gcloud sql instances patch menuscan-db --activation-policy=ALWAYS --project menuscan-500911"
  }
}

# High server-error rate on the service.
resource "google_monitoring_alert_policy" "high_5xx" {
  project      = var.project_id
  display_name = "menuscan-api high 5xx rate"
  combiner     = "OR"

  conditions {
    display_name = "5xx responses > 0.1/s for 5m"
    condition_threshold {
      filter = join(" AND ", [
        "resource.type = \"cloud_run_revision\"",
        "resource.label.service_name = \"menuscan-api\"",
        "metric.type = \"run.googleapis.com/request_count\"",
        "metric.label.response_code_class = \"5xx\"",
      ])
      comparison      = "COMPARISON_GT"
      threshold_value = 0.1 # ~6 server errors per minute, sustained
      duration        = "300s"

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["resource.label.service_name"]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content = "menuscan-api is returning 5xx responses above the threshold. Inspect Cloud Run logs for the failing revision."
  }
}

# ── Dashboard ───────────────────────────────────────────────────────────────
resource "google_monitoring_dashboard" "menuscan" {
  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "MenuScan API"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          xPos = 0, yPos = 0, width = 6, height = 4
          widget = {
            title = "Request latency p95 (ms)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.label.service_name=\"menuscan-api\" metric.type=\"run.googleapis.com/request_latencies\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_PERCENTILE_95"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          xPos = 6, yPos = 0, width = 6, height = 4
          widget = {
            title = "Request count by response class"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.label.service_name=\"menuscan-api\" metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.response_code_class"]
                    }
                  }
                }
              }]
            }
          }
        },
        {
          xPos = 0, yPos = 4, width = 6, height = 4
          widget = {
            title = "Container instance count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.label.service_name=\"menuscan-api\" metric.type=\"run.googleapis.com/container/instance_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          xPos = 6, yPos = 4, width = 6, height = 4
          widget = {
            title = "Uptime check pass ratio"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"uptime_url\" metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" metric.label.host=\"${var.service_host}\""
                    aggregation = {
                      alignmentPeriod    = "300s"
                      perSeriesAligner   = "ALIGN_FRACTION_TRUE"
                      crossSeriesReducer = "REDUCE_MEAN"
                      groupByFields      = ["metric.label.check_id"]
                    }
                  }
                }
              }]
            }
          }
        },
      ]
    }
  })

  depends_on = [google_project_service.enabled]
}
