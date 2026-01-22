# Phase 6: Helm Charts AWS Adaptation

## Context Links
- [Current Helm Chart](../../helm/intellirag-app/values.yaml)
- [Phase 4: EKS Infrastructure](./phase-04-terraform-eks-infrastructure.md)
- [IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

## Overview

**Priority**: P1 (Critical Path)
**Status**: Pending
**Effort**: 4 hours
**Depends On**: Phase 4, Phase 5

Update Helm charts to work with AWS EKS, IRSA, and S3 configuration.

## Key Insights

- Replace GKE Workload Identity with AWS IRSA
- Update service account annotations for AWS
- Change storage config from GCS to S3
- Update MLFlow artifacts path
- Keep CloudFlare Tunnel URLs unchanged

## Requirements

### Functional
- Service account with IRSA annotation
- ConfigMap with S3 settings
- Environment variables for AWS SDK
- Image pull secrets for ghcr.io
- Resource limits tuned for t3.xlarge

### Non-Functional
- Single node deployment
- Memory limit ~4GB for app
- Support both dev (LocalStack) and prod (AWS) configs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Helm Deployment                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    ServiceAccount                           │ │
│  │  annotations:                                               │ │
│  │    eks.amazonaws.com/role-arn: arn:aws:iam::...:role/...   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Deployment                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │                    Pod                                  │ │ │
│  │  │  ┌───────────────┐  ┌───────────────┐                  │ │ │
│  │  │  │   ConfigMap   │  │    Secrets    │                  │ │ │
│  │  │  │  (S3 config)  │  │  (API keys)   │                  │ │ │
│  │  │  └───────────────┘  └───────────────┘                  │ │ │
│  │  │                                                         │ │ │
│  │  │  ┌───────────────────────────────────────────────────┐ │ │ │
│  │  │  │              intellirag-api                       │ │ │ │
│  │  │  │  STORAGE_PROVIDER=s3                              │ │ │ │
│  │  │  │  S3_BUCKET_NAME=intellirag-documents-dev          │ │ │ │
│  │  │  │  AWS_REGION=us-east-1                             │ │ │ │
│  │  │  └───────────────────────────────────────────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Files to Modify
| File | Changes |
|------|---------|
| `helm/intellirag-app/values.yaml` | AWS config, IRSA, S3 settings |
| `helm/intellirag-app/templates/serviceaccount.yaml` | IRSA annotation |
| `helm/intellirag-app/templates/configmap.yaml` | S3 environment vars |
| `helm/intellirag-app/templates/deployment.yaml` | Image pull secrets |
| `helm/mlflow/values.yaml` | S3 artifact store |

### Files to Create
| File | Purpose |
|------|---------|
| `helm/intellirag-app/values-aws.yaml` | AWS-specific overrides |
| `helm/intellirag-app/values-localstack.yaml` | LocalStack dev overrides |

## Implementation Steps

### Step 1: Update values.yaml with AWS Config

```yaml
# helm/intellirag-app/values.yaml
replicaCount: 2

image:
  repository: ghcr.io/minhhoang2705/intellirag/intellirag-api
  pullPolicy: Always
  tag: "latest"

imagePullSecrets:
  - name: ghcr-secret

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations:
    # AWS IRSA annotation (replace with actual ARN from Terraform output)
    eks.amazonaws.com/role-arn: ""  # Set via --set or values-aws.yaml
  name: "intellirag-app"

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  fsGroupChangePolicy: "OnRootMismatch"
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true

service:
  type: ClusterIP
  port: 8000
  targetPort: 8000

ingress:
  enabled: false
  className: "nginx"
  annotations: {}
  hosts:
    - host: api.intellirag.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1536Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}
tolerations: []
affinity: {}

# Application Configuration - AWS/S3
config:
  appName: "IntelliRAG"
  appVersion: "0.2.0"
  debug: "false"
  environment: "development"

  # Storage Provider Configuration
  storageProvider: "s3"  # Options: gcs, s3, local

  # AWS S3 Configuration
  s3BucketName: "intellirag-documents-dev"
  s3Region: "us-east-1"
  awsEndpointUrl: ""  # Empty for real AWS, set for LocalStack

  # Qdrant Configuration
  qdrantUrl: "http://qdrant.database.svc.cluster.local:6333"
  qdrantCollectionName: "intellirag_collection"

  # vLLM Configuration (Hybrid Architecture - Local GPU Server)
  vllmBaseUrl: "https://llm.blockchainradar.xyz/v1"
  vllmModel: "Qwen/Qwen3-0.6B"

  # Embedding Service Configuration (Hybrid Architecture)
  embeddingServiceUrl: "https://embed.blockchainradar.xyz"
  embeddingUseRemote: "true"
  embeddingDimension: "1024"
  embeddingDevice: "cpu"
  embeddingBatchSize: "32"

  # Document Processing Configuration
  maxFileSizeMb: "50"
  allowedFileTypes: "pdf,docx,txt,csv,md"
  chunkSize: "512"
  chunkOverlap: "50"

  # RAG Configuration
  ragTopK: "5"
  ragTemperature: "0.7"
  ragMaxTokens: "512"

  # Observability Configuration
  jaegerHost: "jaeger-collector.observability.svc.cluster.local"
  jaegerPort: "6831"

livenessProbe:
  httpGet:
    path: /
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 8
  failureThreshold: 3

secrets: {}
```

### Step 2: Update ServiceAccount Template

```yaml
# helm/intellirag-app/templates/serviceaccount.yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "intellirag-app.serviceAccountName" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "intellirag-app.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
```

### Step 3: Update ConfigMap Template

```yaml
# helm/intellirag-app/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "intellirag-app.fullname" . }}-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "intellirag-app.labels" . | nindent 4 }}
data:
  # Application
  APP_NAME: {{ .Values.config.appName | quote }}
  APP_VERSION: {{ .Values.config.appVersion | quote }}
  DEBUG: {{ .Values.config.debug | quote }}
  ENVIRONMENT: {{ .Values.config.environment | quote }}

  # Storage Provider
  STORAGE_PROVIDER: {{ .Values.config.storageProvider | quote }}

  # AWS S3 Configuration
  S3_BUCKET_NAME: {{ .Values.config.s3BucketName | quote }}
  S3_REGION: {{ .Values.config.s3Region | quote }}
  {{- if .Values.config.awsEndpointUrl }}
  AWS_ENDPOINT_URL: {{ .Values.config.awsEndpointUrl | quote }}
  {{- end }}

  # Legacy GCS Configuration (for backward compatibility during migration)
  {{- if .Values.config.gcsProjectId }}
  GCS_PROJECT_ID: {{ .Values.config.gcsProjectId | quote }}
  GCS_BUCKET_NAME: {{ .Values.config.gcsBucketName | quote }}
  {{- end }}

  # Qdrant
  QDRANT_URL: {{ .Values.config.qdrantUrl | quote }}
  QDRANT_COLLECTION_NAME: {{ .Values.config.qdrantCollectionName | quote }}

  # vLLM (CloudFlare Tunnel to local GPU)
  VLLM_BASE_URL: {{ .Values.config.vllmBaseUrl | quote }}
  VLLM_MODEL: {{ .Values.config.vllmModel | quote }}

  # Embedding Service (CloudFlare Tunnel to local GPU)
  EMBEDDING_SERVICE_URL: {{ .Values.config.embeddingServiceUrl | quote }}
  EMBEDDING_USE_REMOTE: {{ .Values.config.embeddingUseRemote | quote }}
  EMBEDDING_DIMENSION: {{ .Values.config.embeddingDimension | quote }}
  EMBEDDING_DEVICE: {{ .Values.config.embeddingDevice | quote }}
  EMBEDDING_BATCH_SIZE: {{ .Values.config.embeddingBatchSize | quote }}

  # Document Processing
  MAX_FILE_SIZE_MB: {{ .Values.config.maxFileSizeMb | quote }}
  ALLOWED_FILE_TYPES: {{ .Values.config.allowedFileTypes | quote }}
  CHUNK_SIZE: {{ .Values.config.chunkSize | quote }}
  CHUNK_OVERLAP: {{ .Values.config.chunkOverlap | quote }}

  # RAG
  RAG_TOP_K: {{ .Values.config.ragTopK | quote }}
  RAG_TEMPERATURE: {{ .Values.config.ragTemperature | quote }}
  RAG_MAX_TOKENS: {{ .Values.config.ragMaxTokens | quote }}

  # Observability
  JAEGER_HOST: {{ .Values.config.jaegerHost | quote }}
  JAEGER_PORT: {{ .Values.config.jaegerPort | quote }}
```

### Step 4: Update Deployment Template

```yaml
# helm/intellirag-app/templates/deployment.yaml (partial - key changes)
spec:
  template:
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "intellirag-app.serviceAccountName" . }}
      # ... rest of spec
```

### Step 5: Create AWS-specific Values Override

```yaml
# helm/intellirag-app/values-aws.yaml
# AWS production overrides
# Usage: helm upgrade --install intellirag ./helm/intellirag-app -f values-aws.yaml

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::ACCOUNT_ID:role/intellirag-irsa-role"

config:
  storageProvider: "s3"
  s3BucketName: "intellirag-documents-dev"
  s3Region: "us-east-1"
  awsEndpointUrl: ""  # Empty = use real AWS
  environment: "production"
```

### Step 6: Create LocalStack Values Override

```yaml
# helm/intellirag-app/values-localstack.yaml
# LocalStack development overrides
# Usage: helm upgrade --install intellirag ./helm/intellirag-app -f values-localstack.yaml

replicaCount: 1

serviceAccount:
  annotations: {}  # No IRSA for LocalStack

config:
  storageProvider: "s3"
  s3BucketName: "intellirag-documents"
  s3Region: "us-east-1"
  awsEndpointUrl: "http://localstack:4566"
  environment: "development"
  debug: "true"

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 250m
    memory: 512Mi

autoscaling:
  enabled: false
```

### Step 7: Update MLFlow Helm Chart

```yaml
# helm/mlflow/values.yaml (key changes)
mlflow:
  backendStoreUri: "sqlite:///mlflow/mlflow.db"
  # Change from GCS to S3
  defaultArtifactRoot: "s3://intellirag-documents-dev/mlflow-artifacts"
  serveArtifacts: true
  host: "0.0.0.0"
  port: 5000

serviceAccount:
  annotations:
    # AWS IRSA for MLFlow S3 access
    eks.amazonaws.com/role-arn: "arn:aws:iam::ACCOUNT_ID:role/intellirag-irsa-role"
```

### Step 8: Create Deployment Script

```bash
#!/bin/bash
# scripts/helm-deploy-aws.sh
set -e

# Get IRSA role ARN from Terraform
cd terraform/aws/eks
IRSA_ROLE_ARN=$(terraform output -raw irsa_role_arn)
cd -

echo "Deploying IntelliRAG to EKS..."
echo "IRSA Role: ${IRSA_ROLE_ARN}"

helm upgrade --install intellirag ./helm/intellirag-app \
  --namespace app \
  --create-namespace \
  -f ./helm/intellirag-app/values-aws.yaml \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="${IRSA_ROLE_ARN}" \
  --wait \
  --timeout 10m

echo "Deployment complete!"
kubectl get pods -n app
```

## Todo List

- [ ] Update helm/intellirag-app/values.yaml with S3 config
- [ ] Update helm/intellirag-app/templates/serviceaccount.yaml
- [ ] Update helm/intellirag-app/templates/configmap.yaml
- [ ] Update helm/intellirag-app/templates/deployment.yaml
- [ ] Create helm/intellirag-app/values-aws.yaml
- [ ] Create helm/intellirag-app/values-localstack.yaml
- [ ] Update helm/mlflow/values.yaml for S3 artifacts
- [ ] Create scripts/helm-deploy-aws.sh
- [ ] Test with LocalStack values
- [ ] Test with AWS values
- [ ] Verify IRSA permissions (pod can access S3)
- [ ] Verify CloudFlare Tunnel connectivity

## Success Criteria

- [ ] Helm deploys successfully to EKS
- [ ] ServiceAccount has IRSA annotation
- [ ] ConfigMap contains S3 settings
- [ ] Pod can read/write to S3 bucket
- [ ] MLFlow can store artifacts in S3
- [ ] CloudFlare Tunnel connectivity works
- [ ] All probes pass (health, ready)

## Testing Commands

```bash
# Test IRSA permissions
kubectl run -it --rm aws-cli \
  --image=amazon/aws-cli \
  --serviceaccount=intellirag-app \
  --namespace=app \
  -- s3 ls s3://intellirag-documents-dev/

# Test application
kubectl port-forward -n app svc/intellirag-app 8000:8000
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| IRSA misconfiguration | Test S3 access from pod |
| Missing env vars | ConfigMap validation |
| Wrong bucket name | Terraform output reference |

## Security Considerations

- IRSA provides pod-level IAM (no node credentials)
- S3 bucket policy restricts access
- No AWS credentials in ConfigMap
- Secrets via Kubernetes secrets or Secrets Manager

## Next Steps

After completing this phase:
1. Full end-to-end testing
2. Document operational procedures
3. Archive GCP-specific configurations
4. Update README with AWS deployment instructions
