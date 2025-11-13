variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "asia-southeast1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "intellirag-cluster"
}

variable "machine_type" {
  description = "Machine type for nodes"
  type        = string
  default     = "e2-standard-2"
}

variable "min_nodes" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "max_nodes" {
  description = "Maximum number of nodes"
  type        = number
  default     = 2
}
