terraform {
  backend "gcs" {
    bucket = "intellirag-aide1-capstone-terraform-state"
    prefix = "gke/prod"
  }
}
