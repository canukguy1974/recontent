variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }
variable "raw_bucket" { type = string default = "recontent-raw" }
variable "processed_bucket" { type = string default = "recontent-processed" }
variable "published_bucket" { type = string default = "recontent-published" }
variable "sql_instance_name" { type = string default = "recontent-sql" }
variable "db_name" { type = string default = "recontent" }
variable "db_user" { type = string default = "recontent" }
variable "db_tier" { type = string default = "db-custom-1-3840" } # 1 vCPU, 3.75GB
