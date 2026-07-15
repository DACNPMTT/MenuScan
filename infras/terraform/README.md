# MenuScan infrastructure (Terraform)

Infrastructure-as-Code for the **platform layer** of MenuScan on GCP project
`menuscan-500911`.

## Scope — and the deliberate boundary

This Terraform manages the stable platform:

- Enabled project APIs (`apis.tf`)
- Artifact Registry Docker repo (`artifact_registry.tf`)
- Cloud SQL instance + `menuscan` database (`cloudsql.tf`)
- Deploy service account + its project roles (`iam.tf`)
- Workload Identity pool + provider for keyless GitHub Actions auth (`wif.tf`)
- Observability: uptime checks, alert policies, dashboard (`monitoring.tf`)
- Secret Manager secret containers + runtime read access (`secrets.tf`)

It intentionally does **not** manage the Cloud Run service (`menuscan-api`) or the
migration job (`menuscan-migrate`). Those are owned by the CD pipeline
(`.github/workflows/cd-deploy.yml`), which changes their image and env on every
push. Managing them here too would make Terraform and CD fight over the same
resource on every deploy. The rule: **Terraform owns the platform, CD owns the
app.**

SQL users/passwords are also out of scope — credentials do not belong in
Terraform state (they should move to Secret Manager; see the CD TODO).

## Prerequisites

- Terraform >= 1.5 (for `import {}` blocks)
- `gcloud auth application-default login` as a principal with viewer/admin on
  the project

## First run — import existing infra (SAFE)

Everything here already exists in GCP. `imports.tf` maps the live resources into
state so Terraform adopts them instead of trying to recreate them.

```bash
cd infras/terraform
terraform init
terraform plan      # review carefully — see "Reading the plan" below
```

### Reading the plan — the safety gate

A correct first plan imports the existing platform resources AND creates the
new resources that don't exist yet:

```
Plan: N to import, M to add, 0 to change, 0 to destroy.
```

- The **"to add"** items must be ONLY the new-by-design resources: the
  `monitoring.tf` set (notification channel, 2 uptime checks, 3 alert policies,
  1 dashboard) and the `secrets.tf` set (8 secret containers + 8 IAM bindings +
  the Secret Manager API). If any *existing* platform resource (SQL, registry,
  SA, WIF...) shows up as "to add", it failed to import — investigate.
- **1 expected change**: `google_sql_database_instance.menuscan_db` will show a
  change to `settings.ip_configuration.ssl_mode` → `ENCRYPTED_ONLY`. This is an
  intentional hardening (enforce TLS); the Cloud SQL Auth Proxy already uses SSL
  so it does not break the app. Any *other* change should be investigated.
- **0 to destroy / 0 to replace** is mandatory. If you see a destroy or replace,
  STOP — the `.tf` does not match reality. Fix the config (not the cloud) and
  re-plan.
- **A few "to change"** are usually harmless normalisations (e.g. an optional
  field Terraform wants to set to its default). Inspect each; adjust the `.tf`
  to match the live value if you want a truly no-op plan.

Only once the plan is clean:

```bash
terraform apply     # writes state only; makes no real infra change
```

After the first successful apply the `import {}` blocks are inert — you may
delete `imports.tf`.

## Secrets (Secret Manager)

Terraform creates the secret **containers** and grants the Cloud Run runtime
service account read access — it never stores the **values**. The deploy
pipeline (`cd-deploy.yml`) reads them at runtime via `--set-secrets`, so
secrets are no longer written into the Cloud Run revision config.

### Rollout order — do NOT skip

The `cd-deploy.yml` change references `--set-secrets ...:latest`. If a deploy
runs before the secrets have a value, Cloud Run fails to start the revision.
So the very first time, in this order:

1. `terraform apply` — creates the (empty) secret containers + IAM.
2. Seed the values from a local env file (held only in memory, never committed):
   ```bash
   ./seed-secrets.sh ../../env/.env.local
   ```
   Verify: `gcloud secrets versions list database-url --project=menuscan-500911`
3. Only now merge/push the `cd-deploy.yml` change so the next deploy uses
   `--set-secrets`.

### Rotating a key

Update the value in your env file and re-run `seed-secrets.sh` (it adds a new
version; `:latest` picks it up on the next deploy). No Terraform change needed.

Once seeded, the matching `DEV_*` GitHub secrets are only still used for the
non-secret config in `env.yaml` (frontend URL, SMTP username) — the sensitive
`DEV_DATABASE_URL`, `DEV_SECRET_KEY`, `DEV_*_API_KEYS`, `DEV_EMAIL_SMTP_PASSWORD`
can be removed from GitHub if you want Secret Manager to be the sole source.

## Day-2 usage

From then on, change infrastructure by editing the `.tf` files and running
`terraform plan` / `apply`. Keep `activation_policy` changes (starting/stopping
Cloud SQL to save credit) on the CLI — Terraform ignores that field on purpose.

## Remote state (recommended)

State is local by default and git-ignored. To share it / make it durable,
bootstrap a bucket and enable the GCS backend (commented in `versions.tf`):

```bash
gcloud storage buckets create gs://menuscan-tf-state \
  --location=asia-southeast1 --uniform-bucket-level-access \
  --project=menuscan-500911
# uncomment the backend "gcs" block in versions.tf, then:
terraform init -migrate-state
```
