Create two Cloud Build triggers (optional):

- recontent-api: uses infra/cloudbuild/build-api.yaml
- recontent-worker: uses infra/cloudbuild/build-worker.yaml

Add Secret Manager secret recontent-db-pass with your DB password from Terraform output to avoid plaintext env vars.
