---
title: "GCP to AWS Migration Plan"
description: "Migrate IntelliRAG from GCP to AWS with ephemeral EKS infrastructure pattern"
status: pending
priority: P1
effort: 32h
issue: null
branch: main
tags: [infra, aws, migration, terraform, cicd]
created: 2025-12-26
---

# GCP to AWS Migration Plan

## Overview

Migrate IntelliRAG from Google Cloud Platform to Amazon Web Services with cost-optimized ephemeral infrastructure pattern. Target budget: $100-200.

## Architecture Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Kubernetes | EKS (ephemeral) | Provision/destroy pattern saves ~$60/month |
| Node | t3.xlarge spot (single) | 4 vCPU, 16GB RAM for full stack |
| Registry | ghcr.io | Free, GitHub-native |
| Storage | S3 | AWS-native, free tier eligible |
| Qdrant | Fresh start | No persistence overhead |
| GPU Tunnel | CloudFlare (unchanged) | Keep existing architecture |
| Observability | Full stack | Prometheus, Grafana, Jaeger, Loki |

## Cost Estimate

| Phase | Scenario | Monthly Cost |
|-------|----------|--------------|
| Development | Ephemeral (80 hrs/month) | ~$15 |
| Production | 24/7 | ~$115 |

## Phases

| # | Phase | Status | Effort | Link |
|---|-------|--------|--------|------|
| 1 | Abstract Storage Layer | Pending | 6h | [phase-01](./phase-01-abstract-storage-layer.md) |
| 2 | Local Development Setup | Pending | 4h | [phase-02-local-development-setup.md](./phase-02-local-development-setup.md) |
| 3 | AWS Foundation | Pending | 6h | [phase-03-aws-foundation.md](./phase-03-aws-foundation.md) |
| 4 | Terraform EKS Infrastructure | Pending | 8h | [phase-04-terraform-eks-infrastructure.md](./phase-04-terraform-eks-infrastructure.md) |
| 5 | CI/CD Pipeline Update | Pending | 4h | [phase-05-cicd-pipeline-update.md](./phase-05-cicd-pipeline-update.md) |
| 6 | Helm Charts AWS Adaptation | Pending | 4h | [phase-06-helm-charts-aws-adaptation.md](./phase-06-helm-charts-aws-adaptation.md) |

## GCP Dependencies Inventory

### Application Code (Must Modify)

| File | Dependency | Action |
|------|------------|--------|
| `app/services/gcs_storage.py` | `gcloud-aio-storage` | Replace with abstract interface + S3 impl |
| `app/services/gcs_loader.py` | LangChain GCS loaders | Replace with S3 loaders |
| `app/services/orchestrator.py` | GCSLoaderService | Update to use abstract loader |
| `app/api/v1/upload.py` | GCSStorageService | Update to use abstract storage |
| `app/config.py` | GCS config vars | Add S3 config vars |
| `app/models/schemas.py` | GCS-specific models | Generalize to cloud-agnostic |

### Infrastructure (Must Rewrite)

| Component | Current | Target |
|-----------|---------|--------|
| `terraform/main.tf` | GKE | EKS |
| `terraform/variables.tf` | GCP vars | AWS vars |
| `terraform/backend.tf` | GCS backend | S3 backend |
| `.github/workflows/cd-app.yml` | GCR + GKE | ghcr.io + EKS |
| `helm/intellirag-app/values.yaml` | GKE annotations | IRSA annotations |
| `helm/mlflow/values.yaml` | GCS artifacts | S3 artifacts |

### Dependencies (pyproject.toml)

| Remove | Add |
|--------|-----|
| `gcloud-aio-storage` | `aioboto3` |
| - | `boto3` |

## Success Criteria

- [ ] All tests pass with S3 storage
- [ ] LocalStack development environment works
- [ ] EKS cluster provisions in <15 minutes
- [ ] EKS cluster destroys in <10 minutes
- [ ] CI/CD deploys to EKS successfully
- [ ] CloudFlare Tunnel connectivity verified
- [ ] Full observability stack functional
- [ ] Monthly cost under $20 for development

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| EKS provision time | LOW | MEDIUM | Pre-baked AMIs, parallel init |
| Spot instance termination | MEDIUM | HIGH | Graceful shutdown, state in S3 |
| IAM misconfiguration | MEDIUM | HIGH | Least privilege, IRSA validation |
| Cost overrun | LOW | MEDIUM | Budget alerts, destroy scripts |

## Dependencies

- AWS account with $100+ credits
- GitHub repository access (for ghcr.io)
- CloudFlare Tunnel (unchanged)
- Local GPU server (unchanged)
