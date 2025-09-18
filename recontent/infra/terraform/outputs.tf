output "notes" {
  value = "After deploying Cloud Run worker, create a Pub/Sub push subscription to https://<worker-url>/pubsub using 'gcloud pubsub subscriptions create jobs-sub --topic=jobs --push-endpoint=... --push-auth-service-account=<worker-sa>'"
}
