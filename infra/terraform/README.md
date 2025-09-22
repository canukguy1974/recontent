# Initialize & apply

## Prerequisites: Install Terraform

### 1. Install Terraform

Choose one of the following methods based on your operating system:

#### Option A: Using Package Manager (Recommended)

**Ubuntu/Debian:**
```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

**macOS:**
```bash
brew install terraform
```

**Windows (using Chocolatey):**
```bash
choco install terraform
```

#### Option B: Manual Installation

1. Download the appropriate package from [terraform.io/downloads](https://www.terraform.io/downloads.html)
2. Unzip the package
3. Move the `terraform` binary to a directory in your PATH (e.g., `/usr/local/bin`)
4. Make it executable: `chmod +x /usr/local/bin/terraform`

### 2. Verify Installation

```bash
terraform version
```

### 3. Initialize Terraform

Navigate to your infrastructure directory and initialize:

```bash
cd /home/canuk/projects/recontent/infra/terraform
terraform init
```

This command:
- Downloads required provider plugins
- Initializes the backend for state storage
- Prepares the working directory for other Terraform commands

### 4. Plan and Apply

After successful initialization, you can proceed with:

```bash
terraform plan -var="project_id=recontent-472506" -var="region=us-central1"
```
terraform apply -var="project_id=recontent-472506" -var="region=us-central1"

Outputs include:

- instance_connection_name (for Cloud Run --add-cloudsql-instances)
- db_user and db_password (use as env vars DB_USER/DB_PASSWORD on Cloud Run)
- bucket names and topic

Create Pub/Sub push subscription after you deploy the worker:

gcloud pubsub subscriptions create jobs-sub       --topic=jobs       --push-endpoint="https://<worker-url>/pubsub"       --push-auth-service-account="recontent-worker-sa@recontent-472506.iam.gserviceaccount.com"
