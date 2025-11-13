terraform {
  required_version = ">= 1.5.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region

  deletion_protection      = false
  remove_default_node_pool = true
  initial_node_count       = 1  # still required for API, but default pool will be removed

  # Temporary default node pool config (used only during bootstrap)
  node_config {
    machine_type = "e2-medium"   # small & cheap, any valid type is fine
    disk_type    = "pd-standard" # avoid SSD quota
    disk_size_gb = 20            # small disk; enough for system pods
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name     = "${var.cluster_name}-node-pool"
  location = var.region
  cluster  = google_container_cluster.primary.name

  autoscaling {
    min_node_count = var.min_nodes  # 1
    max_node_count = var.max_nodes  # 2
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.machine_type  # "e2-standard-2"
    disk_size_gb = 80
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    tags = ["gke-node", "${var.cluster_name}"]
  }
}


# Service Account for Workload Identity (GCS access)
resource "google_service_account" "gke_workload" {
  account_id   = "${var.cluster_name}-workload-sa"
  display_name = "GKE Workload Service Account"
  project      = var.project_id
}

# IAM binding for GCS access
resource "google_project_iam_member" "gcs_access" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# IAM binding for Workload Identity
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.gke_workload.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[app/intellirag-app]"
  depends_on         = [google_container_cluster.primary]
}
