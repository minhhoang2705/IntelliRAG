# Observability Stack Resource Allocation

## Cluster Capacity
- **Total CPU**: 8 cores (8000m)
- **Total Memory**: 22GB
- **Node**: Single Minikube node

## Resource Allocation Plan

### Prometheus Stack
| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Prometheus Operator | 50m | 300m | 192Mi | 384Mi |
| Prometheus Server | 500m | 1500m | 1536Mi | 3Gi |
| Alertmanager | 100m | 500m | 128Mi | 512Mi |
| Node Exporter | ~50m | - | ~50Mi | - |
| Kube State Metrics | ~100m | - | ~100Mi | - |
| **Subtotal** | **~800m** | **~2300m** | **~2Gi** | **~4Gi** |

### Loki Stack
| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Loki SingleBinary | 500m | 1000m | 1Gi | 1536Mi |
| Loki Gateway | ~50m | ~100m | ~64Mi | ~128Mi |
| Loki Chunks Cache | - | - | 512Mi | 512Mi |
| Loki Results Cache | - | - | 256Mi | 256Mi |
| Promtail | ~100m | ~200m | ~128Mi | ~256Mi |
| **Subtotal** | **~650m** | **~1300m** | **~2Gi** | **~2.5Gi** |

### Jaeger Stack
| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Jaeger Agent | 50m | 200m | 128Mi | 256Mi |
| Jaeger Collector | 200m | 500m | 256Mi | 512Mi |
| Jaeger Query | 100m | 300m | 192Mi | 384Mi |
| Elasticsearch | 500m | 1000m | 1Gi | 2Gi |
| **Subtotal** | **850m** | **2000m** | **~1.6Gi** | **~3Gi** |

## Total Observability Stack
- **CPU Requests**: ~2300m (29% of 8000m)
- **CPU Limits**: ~5600m (70% of 8000m)
- **Memory Requests**: ~5.6Gi (26% of 22Gi)
- **Memory Limits**: ~9.5Gi (43% of 22Gi)

## Available for Application Workloads
- **Available CPU**: ~5700m (71%)
- **Available Memory**: ~16Gi (74%)

## Notes
- All storage volumes reduced to 20Gi for dev/testing
- Elasticsearch: Single replica (not HA, for dev only)
- Retention periods reduced:
  - Prometheus: 15 days (was 30)
  - Loki: 7 days
  - Jaeger: 7 days
- Caches optimized for lower memory usage
- Autoscaling disabled on most components

## Recommendations for Production
If moving to production GKE:
1. Increase Elasticsearch to 3 replicas (HA)
2. Enable Jaeger Collector autoscaling (2-5 replicas)
3. Increase retention periods
4. Increase storage volumes (50Gi+)
5. Use dedicated node pools for observability

