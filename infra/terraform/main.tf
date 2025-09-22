terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "> 5.40" }
    random = { source = "hashicorp/random", version = "> 3.6" }
  }
}

provider "google" { 
  project = var.project_id 
  region  = var.region 
}

resource "google_storage_bucket" "raw" {
  name = var.raw_bucket
  location = var.region
  uniform_bucket_level_access = true
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 60 }
  }
}

resource "google_storage_bucket" "processed" {
  name = var.processed_bucket
  location = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "published" {
  name = var.published_bucket
  location = var.region
  uniform_bucket_level_access = true
}

resource "google_pubsub_topic" "jobs" { name = "jobs" }

# Service Accounts
resource "google_service_account" "api" {
  account_id   = "recontent-api-sa"
  display_name = "recontent API service account"
}

resource "google_service_account" "worker" {
  account_id   = "recontent-worker-sa"
  display_name = "recontent Worker service account"
}

# IAM (minimal; tighten in production)
resource "google_project_iam_member" "api_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "worker_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "api_pubsub_pub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "worker_pubsub_sub" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "vertex_api" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "cloudsql_client_api" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Cloud SQL (Postgres 15)
resource "google_sql_database_instance" "pg" {
  name             = var.sql_instance_name
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = false

  settings {
    tier = var.db_tier
    availability_type = "ZONAL"
    backup_configuration { enabled = true }
    ip_configuration {
      # Using the connector from Cloud Run; public IP is fine with connector
      ipv4_enabled = true
    }
  }
}

resource "google_sql_database" "db" {
  name     = var.db_name
  instance = google_sql_database_instance.pg.name
}

resource "random_password" "db_password" { 
  length  = 20 
  special = true 
}

resource "google_sql_user" "dbuser" {
  name     = var.db_user
  instance = google_sql_database_instance.pg.name
  password = random_password.db_password.result
}

output "instance_connection_name" { 
  value = google_sql_database_instance.pg.connection_name 
}

output "db_user" { 
  value = google_sql_user.dbuser.name 
}

output "db_password" { 
  value     = random_password.db_password.result 
  sensitive = true 
}

output "pubsub_topic" { 
  value = google_pubsub_topic.jobs.name 
}

output "buckets" {
  value = {
    raw       = google_storage_bucket.raw.name
    processed = google_storage_bucket.processed.name
    published = google_storage_bucket.published.name
  }
}
