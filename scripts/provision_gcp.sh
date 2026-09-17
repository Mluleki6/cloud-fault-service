#!/usr/bin/env bash
# One-time GCP provisioning for the Fault Reporting Service.
#
# Creates the pieces deploy_gcp.sh assumes already exist: enabled APIs, a
# least-privilege runner service account, a Cloud SQL (Postgres) instance,
# and the DATABASE_URL stored in Secret Manager (never printed in plain
# text, never committed).
#
# Run this ONCE per project, after billing is confirmed enabled. It creates
# real, billable resources (Cloud SQL in particular) -- see
# architecture/cost-worksheet.md before running.
#
# Usage:
#   GCP_PROJECT=your-project-id ./scripts/provision_gcp.sh
set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT to your GCP project ID}"
: "${GCP_REGION:=africa-south1}"
: "${SQL_INSTANCE:=fault-service-db}"
: "${DB_NAME:=faultservice}"
: "${DB_USER:=faultservice}"
: "${SERVICE_ACCOUNT_NAME:=fault-service-runner}"
: "${SECRET_NAME:=fault-service-database-url}"
: "${SQL_TIER:=db-f1-micro}"

SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"

echo "== Setting active project =="
gcloud config set project "$GCP_PROJECT"

echo "== Enabling required APIs (idempotent) =="
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com

echo "== Creating runner service account (idempotent) =="
if ! gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name "Fault Reporting Service runner"
else
  echo "Service account $SA_EMAIL already exists, skipping."
fi

echo "== Granting least-privilege roles =="
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client" \
  --quiet
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter" \
  --quiet

echo "== Creating Cloud SQL instance (this is the billable step -- ${SQL_TIER}) =="
if ! gcloud sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1; then
  gcloud sql instances create "$SQL_INSTANCE" \
    --database-version=POSTGRES_16 \
    --tier="$SQL_TIER" \
    --region="$GCP_REGION" \
    --storage-size=10GB \
    --storage-auto-increase
else
  echo "Cloud SQL instance $SQL_INSTANCE already exists, skipping create."
fi

DB_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"

echo "== Creating database and user =="
gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE" || echo "Database $DB_NAME may already exist, continuing."
gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASSWORD" || {
  echo "User $DB_USER may already exist -- resetting password so we know the current value."
  gcloud sql users set-password "$DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASSWORD"
}

CONNECTION_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

echo "== Storing DATABASE_URL in Secret Manager (never printed, never committed) =="
if ! gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
  printf '%s' "$DATABASE_URL" | gcloud secrets create "$SECRET_NAME" --data-file=-
else
  printf '%s' "$DATABASE_URL" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
fi

echo
echo "Provisioning complete."
echo "  Cloud SQL instance:   $SQL_INSTANCE ($CONNECTION_NAME)"
echo "  Service account:      $SA_EMAIL"
echo "  Secret:                $SECRET_NAME (holds DATABASE_URL)"
echo
echo "Next: run scripts/deploy_gcp.sh with:"
echo "  GCP_PROJECT=$GCP_PROJECT GCP_REGION=$GCP_REGION SQL_CONNECTION_NAME=$CONNECTION_NAME ./scripts/deploy_gcp.sh"
