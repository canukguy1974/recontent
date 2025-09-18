# Initialize & apply

terraform init
terraform apply -var="project_id=recontent-472506" -var="region=us-central1"

Outputs include:

- instance_connection_name (for Cloud Run --add-cloudsql-instances)
- db_user and db_password (use as env vars DB_USER/DB_PASSWORD on Cloud Run)
- bucket names and topic

Create Pub/Sub push subscription after you deploy the worker:

gcloud pubsub subscriptions create jobs-sub       --topic=jobs       --push-endpoint="https://<worker-url>/pubsub"       --push-auth-service-account="recontent-worker-sa@recontent-472506.iam.gserviceaccount.com"
