# Day 4: NGINX Ingress Controller & TLS

**Duration**: 5-6 hours
**Prerequisites**: Domain name ready, DNS access, GKE cluster running
**Output**: HTTPS endpoint with TLS certificate, NGINX Ingress configured

---

## 🎯 Objectives

1. Deploy NGINX Ingress Controller on GKE
2. Configure DNS A record for production domain
3. Install cert-manager and issue Let's Encrypt certificate
4. Enable HTTPS with automatic HTTP→HTTPS redirect
5. Configure security headers, CORS, and rate limiting

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 4.1 Install NGINX Ingress | 1 hour | LoadBalancer with external IP |
| 4.2 Configure DNS | 30 min | A record pointing to Ingress |
| 4.3 Install cert-manager | 1 hour | cert-manager pods running |
| 4.4 Create Ingress with TLS | 1 hour | TLS certificate issued |
| 4.5 Configure Security | 1 hour | Security headers, CORS, rate limiting |
| 4.6 Verify & Test | 30 min | HTTPS endpoint validated |

---

## Task 4.1: Install NGINX Ingress Controller (1 hour)

### Add Helm Repository

```bash
# Switch to GKE context
kubectl config use-context <your-gke-context>

# Add NGINX Helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```

### Install NGINX Ingress

```bash
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.service.externalTrafficPolicy=Local \
  --set controller.metrics.enabled=true \
  --set controller.metrics.serviceMonitor.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"=10254 \
  --set controller.resources.requests.cpu=500m \
  --set controller.resources.requests.memory=512Mi \
  --set controller.resources.limits.cpu=1000m \
  --set controller.resources.limits.memory=1Gi \
  --timeout 10m \
  --wait

# Verify installation
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx

# Expected: 1 controller pod Running, 1 LoadBalancer service
```

### Get External IP

```bash
# Wait for external IP (can take 2-5 minutes)
kubectl get svc -n ingress-nginx ingress-nginx-controller -w

# Once EXTERNAL-IP shows (not <pending>), save it
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ingress External IP: $INGRESS_IP"

# Save for DNS configuration
echo $INGRESS_IP > /tmp/ingress-ip.txt
```

**Success Criteria**:
- ✅ NGINX Ingress Controller pod Running
- ✅ LoadBalancer service has external IP
- ✅ IP address saved

---

## Task 4.2: Configure DNS (30 minutes)

### Option A: Manual DNS Configuration (Any Provider)

1. Log into your DNS provider (CloudFlare, Route53, Google Domains, etc.)
2. Navigate to DNS management
3. Create A record:
   - **Name**: `api` (for api.intellirag.example.com)
   - **Type**: `A`
   - **Value**: `<INGRESS_IP>`
   - **TTL**: `120` (2 minutes for faster propagation)
4. Save changes

### Option B: CloudFlare API (Automated)

```bash
# Set credentials
CF_API_TOKEN="your-cloudflare-api-token"
CF_ZONE_ID="your-zone-id"  # Get from CloudFlare dashboard
DOMAIN="api.intellirag.example.com"
INGRESS_IP=$(cat /tmp/ingress-ip.txt)

# Create DNS A record
curl -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "api.intellirag.example.com",
    "content": "'$INGRESS_IP'",
    "ttl": 120,
    "proxied": false
  }' | jq .

# Verify DNS record created
curl -X GET "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records?name=$DOMAIN" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq '.result[] | {name, type, content}'
```

### Verify DNS Propagation

```bash
# Wait for DNS to propagate (2-10 minutes)
echo "Waiting for DNS propagation..."

while true; do
  RESOLVED_IP=$(dig +short api.intellirag.example.com @8.8.8.8)
  if [ "$RESOLVED_IP" == "$INGRESS_IP" ]; then
    echo "✅ DNS propagated successfully!"
    break
  else
    echo "Still waiting... (resolved: $RESOLVED_IP, expected: $INGRESS_IP)"
    sleep 10
  fi
done

# Verify from multiple DNS servers
dig api.intellirag.example.com @8.8.8.8        # Google DNS
dig api.intellirag.example.com @1.1.1.1        # CloudFlare DNS
nslookup api.intellirag.example.com
```

**Success Criteria**:
- ✅ DNS A record created
- ✅ `dig` resolves to correct IP
- ✅ Propagation verified from multiple DNS servers

---

## Task 4.3: Install cert-manager (1 hour)

### Install CRDs

```bash
# Install cert-manager Custom Resource Definitions
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.crds.yaml

# Verify CRDs installed
kubectl get crd | grep cert-manager
```

### Install cert-manager via Helm

```bash
# Add Jetstack repo
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=false \
  --set prometheus.enabled=true \
  --set webhook.timeoutSeconds=30

# Wait for pods to be ready
kubectl wait --for=condition=Available --timeout=300s \
  deployment/cert-manager -n cert-manager
kubectl wait --for=condition=Available --timeout=300s \
  deployment/cert-manager-webhook -n cert-manager
kubectl wait --for=condition=Available --timeout=300s \
  deployment/cert-manager-cainjector -n cert-manager

# Verify all pods running
kubectl get pods -n cert-manager
```

### Create Let's Encrypt ClusterIssuer

Create `kubernetes/cert-manager/letsencrypt-prod.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@intellirag.example.com  # REPLACE with your email
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

Apply:
```bash
kubectl apply -f kubernetes/cert-manager/letsencrypt-prod.yaml

# Verify ClusterIssuer is ready
kubectl get clusterissuer letsencrypt-prod
kubectl describe clusterissuer letsencrypt-prod
```

**Success Criteria**:
- ✅ 3 cert-manager pods Running
- ✅ ClusterIssuer status: Ready

---

## Task 4.4: Create Ingress Resource with TLS (1 hour)

### Create Ingress Manifest

Create `kubernetes/app/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: intellirag-ingress
  namespace: app
  annotations:
    # cert-manager
    cert-manager.io/cluster-issuer: "letsencrypt-prod"

    # SSL/TLS
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"

    # Security headers
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";

    # Rate limiting
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/limit-rps: "20"
    nginx.ingress.kubernetes.io/limit-connections: "100"
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "3"

    # Timeouts
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"

spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.intellirag.example.com
    secretName: intellirag-tls  # cert-manager will create this
  rules:
  - host: api.intellirag.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: intellirag-app
            port:
              number: 8000
```

### Apply Ingress

```bash
kubectl apply -f kubernetes/app/ingress.yaml

# Watch certificate being issued (takes 1-3 minutes)
kubectl get certificate -n app -w

# Check certificate status
kubectl describe certificate intellirag-tls -n app

# Expected events:
# - Requested new certificate
# - Created HTTP-01 challenge
# - Presented challenge using ingress
# - Validated challenge
# - Issued certificate
```

### Verify Certificate

```bash
# Check secret created
kubectl get secret intellirag-tls -n app

# View certificate details
kubectl get certificate intellirag-tls -n app -o yaml

# Expected status.conditions:
# - type: Ready, status: "True"
```

**Success Criteria**:
- ✅ Certificate status: Ready=True
- ✅ Secret `intellirag-tls` exists
- ✅ No errors in certificate description

---

## Task 4.5: Configure Security Headers & CORS (1 hour)

### Add CORS Configuration

Update `kubernetes/app/ingress.yaml` annotations:

```yaml
metadata:
  annotations:
    # ... existing annotations ...

    # CORS
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://intellirag.example.com, https://app.intellirag.example.com"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"
    nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "3600"
```

### Apply Updates

```bash
kubectl apply -f kubernetes/app/ingress.yaml

# Verify changes applied
kubectl get ingress intellirag-ingress -n app -o yaml | grep -A 10 annotations
```

### Update Application Service Type

Since we now have Ingress, change service from LoadBalancer to ClusterIP:

```bash
# Edit Helm values
# In helm/intellirag-app/values.yaml:
# service:
#   type: ClusterIP  # Changed from LoadBalancer
#   port: 8000

# Upgrade Helm release
helm upgrade intellirag-app ./helm/intellirag-app \
  --namespace app \
  --set service.type=ClusterIP \
  --wait

# Verify service is ClusterIP
kubectl get svc -n app intellirag-app
```

---

## Task 4.6: Verification & Testing (30 minutes)

### Test 1: HTTPS Access

```bash
# Test HTTPS endpoint
curl -v https://api.intellirag.example.com/

# Expected: 200 OK, TLS handshake successful

# Test readiness endpoint
curl https://api.intellirag.example.com/ready

# Expected: JSON response with service health
```

### Test 2: HTTP to HTTPS Redirect

```bash
# Test HTTP (should redirect to HTTPS)
curl -v http://api.intellirag.example.com/

# Expected: 308 Permanent Redirect → https://api.intellirag.example.com/
```

### Test 3: TLS Certificate Validation

```bash
# Check certificate details
openssl s_client -connect api.intellirag.example.com:443 -servername api.intellirag.example.com < /dev/null 2>&1 | openssl x509 -noout -text

# Verify certificate info
echo | openssl s_client -connect api.intellirag.example.com:443 -servername api.intellirag.example.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates

# Expected:
# subject: CN=api.intellirag.example.com
# issuer: C=US, O=Let's Encrypt, CN=R3
# notBefore: [date]
# notAfter: [date + 90 days]
```

### Test 4: Security Headers

```bash
curl -I https://api.intellirag.example.com/

# Expected headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### Test 5: CORS

```bash
# Test CORS preflight
curl -H "Origin: https://app.intellirag.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -X OPTIONS \
  -I https://api.intellirag.example.com/api/v1/query

# Expected:
# Access-Control-Allow-Origin: https://app.intellirag.example.com
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
# Access-Control-Allow-Headers: ... Authorization ...
```

### Test 6: Rate Limiting

```bash
# Test rate limit (100 requests/min per IP)
for i in {1..150}; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://api.intellirag.example.com/)
  echo "$i: $HTTP_CODE"

  # If we hit 429, rate limit is working
  if [ "$HTTP_CODE" == "429" ]; then
    echo "✅ Rate limit triggered at request $i"
    break
  fi

  sleep 0.1
done

# Expected: 429 Too Many Requests after ~100 requests
```

### SSL Labs Test (Optional)

```bash
# Check SSL configuration quality
# Visit: https://www.ssllabs.com/ssltest/
# Enter: api.intellirag.example.com
# Expected grade: A or A+
```

### Create Documentation

Create `docs/phase-3/reports/day4-nginx-tls-verification.md`:

```markdown
# Day 4: NGINX Ingress & TLS Verification

**Date**: 2025-11-21

## Deployment Summary

- **NGINX Ingress**: v1.x.x
- **cert-manager**: v1.13.3
- **Domain**: api.intellirag.example.com
- **External IP**: XXX.XXX.XXX.XXX

## Certificate Details

- **Issuer**: Let's Encrypt (R3)
- **Valid From**: YYYY-MM-DD
- **Valid Until**: YYYY-MM-DD (90 days)
- **SANs**: api.intellirag.example.com

## Test Results

| Test | Status | Details |
|------|--------|---------|
| HTTPS Access | ✅ | 200 OK |
| HTTP Redirect | ✅ | 308 → HTTPS |
| TLS Certificate | ✅ | Valid, trusted |
| Security Headers | ✅ | All present |
| CORS | ✅ | Properly configured |
| Rate Limiting | ✅ | Triggers at 100 req/min |

## SSL Labs Grade

**Grade**: A / A+
[Include screenshot or link]

## Configuration Files

- `kubernetes/app/ingress.yaml`
- `kubernetes/cert-manager/letsencrypt-prod.yaml`

## Next Steps

- Day 5: Configure HPA with optimal thresholds
- Day 6: Add network policies for Ingress traffic
```

---

## ✅ Day 4 Completion Checklist

- [ ] NGINX Ingress Controller installed on GKE
- [ ] External IP assigned to LoadBalancer
- [ ] DNS A record created and propagated
- [ ] cert-manager installed and running
- [ ] Let's Encrypt ClusterIssuer created
- [ ] Ingress resource created with TLS annotation
- [ ] TLS certificate issued successfully
- [ ] HTTPS endpoint accessible
- [ ] HTTP redirects to HTTPS
- [ ] Security headers present
- [ ] CORS configured correctly
- [ ] Rate limiting functional
- [ ] Application service changed to ClusterIP
- [ ] Verification tests passed
- [ ] Documentation created

**Success Criteria**:
- HTTPS endpoint returns 200 OK
- TLS certificate valid (Let's Encrypt)
- All security headers present
- Rate limiting triggers at expected threshold
- SSL Labs grade A or better

---

## 🔧 Troubleshooting

### Issue: Certificate stuck in "False" state

```bash
# Check certificate status
kubectl describe certificate intellirag-tls -n app

# Common issues:
# 1. DNS not propagated
dig api.intellirag.example.com +short
# Wait 10 more minutes if incorrect

# 2. HTTP-01 challenge failing
kubectl get challenges -n app
kubectl describe challenge <challenge-name> -n app

# 3. cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager --tail=50

# 4. Rate limit hit (Let's Encrypt)
# Wait 1 hour and retry:
kubectl delete certificate intellirag-tls -n app
kubectl apply -f kubernetes/app/ingress.yaml
```

### Issue: 502 Bad Gateway on HTTPS

```bash
# Check application pods
kubectl get pods -n app
kubectl logs -n app -l app.kubernetes.io/name=intellirag-app

# Check Ingress backend
kubectl describe ingress intellirag-ingress -n app

# Check service
kubectl get svc intellirag-app -n app
kubectl get endpoints intellirag-app -n app
```

### Issue: Rate limiting not working

```bash
# Verify annotations applied
kubectl get ingress intellirag-ingress -n app -o yaml | grep rate-limit

# Check NGINX config
kubectl exec -n ingress-nginx <nginx-pod> -- cat /etc/nginx/nginx.conf | grep limit_req

# Test from different IP (rate limit is per-IP)
```

---

## 📚 Resources

- [NGINX Ingress Controller Docs](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)

---

**Next**: [Day 5: HPA & Resource Management](./day5-hpa-resources.md)

**Last Updated**: 2025-11-21
