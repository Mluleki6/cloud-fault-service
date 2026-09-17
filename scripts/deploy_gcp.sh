#!/usr/bin/env bash
# Deploy the Fault Reporting Service to Cloud Run.
# Requires: gcloud CLI authenticated, an approved GCP project with
# billing enabled, and scripts/provision_gcp.sh already run once (creates
# the Cloud SQL instance, service account, and DATABASE_URL secret).
#
# Fill in the placeholders below (or export them as env vars) before
# running. Never commit real values -- this script only reads them from
# the environment, and the database credential is pulled from Secret
# Manager at deploy time, never passed as plain text.
set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT to your approved project ID}"
: "${GCP_REGION:=africa-south1}"
: "${SERVICE_NAME:=fault-reporting-service}"
: "${SQL_CONNECTION_NAME:?Set SQL_CONNECTION_NAME to the Cloud SQL instance connection name (project:region:instance), printed by provision_gcp.sh}"
: "${SECRET_NAME:=fault-service-database-url}"

gcloud config set project "$GCP_PROJECT"

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GCP_REGION" \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances "$SQL_CONNECTION_NAME" \
  --set-secrets "DATABASE_URL=${SECRET_NAME}:latest" \
  --service-account "fault-service-runner@${GCP_PROJECT}.iam.gserviceaccount.com"

echo "Deployed. Fetch logs with:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${GCP_REGION}"
echo "Tear down with:"
echo "  gcloud run services delete ${SERVICE_NAME} --region ${GCP_REGION}"
