# CloudFlare Tunnel Setup Guide for IntelliRAG

**Status**: ✅ Active
**Created**: 2025-11-16
**Purpose**: Expose local KServe endpoints to GKE via secure CloudFlare Tunnel
**Prerequisites**: Local server with minikube and KServe running

---

## 📋 Overview

This guide provides step-by-step instructions for setting up CloudFlare Tunnel (cloudflared) to securely expose your local KServe model serving endpoints to the GKE cluster.

**What You'll Achieve**:
- Secure HTTPS endpoints for local models (no port forwarding)
- CloudFlare Edge network protection (DDoS, rate limiting)
- Zero Trust access control (optional)
- End-to-end encryption

**Architecture**:
```
GKE FastAPI → CloudFlare Edge → Tunnel → Local cloudflared → Minikube KServe
```

---

## 🎯 Prerequisites Checklist

Before starting, ensure you have:

- [ ] CloudFlare account (free tier is sufficient)
- [ ] Domain registered and using CloudFlare DNS
- [ ] Local server with Ubuntu 22.04
- [ ] Minikube running with KServe installed
- [ ] KServe InferenceServices deployed and accessible on `localhost:8080`
- [ ] Root or sudo access on local server

**Recommended Setup**:
- Domain: `intellirag.example.com` (replace with your actual domain)
- Subdomain for GPU: `gpu.intellirag.example.com`
- Local KServe gateway: `http://localhost:8080`

---

## 📥 Step 1: Install cloudflared

### On Ubuntu 22.04

**Method 1: Download and install .deb package (Recommended)**

```bash
# Download latest cloudflared for Linux
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install package
sudo dpkg -i cloudflared-linux-amd64.deb

# Verify installation
cloudflared --version
# Expected: cloudflared version 2025.x.x (built ...)
```

**Method 2: Manual installation**

```bash
# Download binary
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64

# Make executable and move to PATH
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Verify
cloudflared --version
```

---

## 🔐 Step 2: Authenticate with CloudFlare

### Login to CloudFlare Account

```bash
# Authenticate (opens browser)
cloudflared tunnel login
```

**What Happens**:
1. Browser opens to CloudFlare login page
2. Login with your CloudFlare account
3. Select the domain you want to use (e.g., `intellirag.example.com`)
4. Authorization cert saved to `~/.cloudflared/cert.pem`

**Verify Authentication**:
```bash
# Check cert file exists
ls -la ~/.cloudflared/cert.pem

# Should output:
# -rw------- 1 user user 2484 Nov 16 10:00 /home/user/.cloudflared/cert.pem
```

---

## 🚇 Step 3: Create Tunnel

### Create Named Tunnel

```bash
# Create tunnel named "intellirag-gpu"
cloudflared tunnel create intellirag-gpu
```

**Output**:
```
Tunnel credentials written to /home/user/.cloudflared/<TUNNEL_ID>.json
Created tunnel intellirag-gpu with id <TUNNEL_ID>
```

**Save the Tunnel ID**: You'll need it for configuration.

### List Tunnels

```bash
# Verify tunnel created
cloudflared tunnel list

# Output:
# ID                                   NAME             CREATED              CONNECTIONS
# <TUNNEL_ID>                          intellirag-gpu   2025-11-16T10:00:00Z  0
```

---

## ⚙️ Step 4: Configure Tunnel Routing

### Create Configuration File

Create tunnel config at `~/.cloudflared/config.yml`:

```bash
# Create config directory if not exists
mkdir -p ~/.cloudflared

# Create config file
nano ~/.cloudflared/config.yml
```

### Configuration Template

**Option A: Single Hostname (Recommended for IntelliRAG)**

```yaml
# ~/.cloudflared/config.yml

# Tunnel identifier (replace with your actual tunnel ID)
tunnel: <TUNNEL_ID>

# Path to tunnel credentials file
credentials-file: /home/user/.cloudflared/<TUNNEL_ID>.json

# Ingress rules (order matters - first match wins)
ingress:
  # Route gpu.intellirag.example.com to local KServe gateway
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false

  # Catch-all rule (required as last rule)
  - service: http_status:404
```

**Replace**:
- `<TUNNEL_ID>`: Your actual tunnel ID from Step 3
- `/home/user/`: Your actual home directory path
- `gpu.intellirag.example.com`: Your actual subdomain

**Option B: Multiple Hostnames (For Advanced Use)**

```yaml
# ~/.cloudflared/config.yml

tunnel: <TUNNEL_ID>
credentials-file: /home/user/.cloudflared/<TUNNEL_ID>.json

ingress:
  # LLM endpoint
  - hostname: llm.intellirag.example.com
    service: http://localhost:8080
    path: /v1/chat/completions

  # Embedding endpoint
  - hostname: embedding.intellirag.example.com
    service: http://localhost:8080
    path: /v1/embeddings

  # Health check endpoint
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
    path: /health

  # Catch-all
  - service: http_status:404
```

### Validate Configuration

```bash
# Validate config syntax
cloudflared tunnel ingress validate

# Expected output:
# Validating rules from /home/user/.cloudflared/config.yml
# OK
```

---

## 🌐 Step 5: Configure DNS Records

### Route DNS to Tunnel

```bash
# Create DNS route for subdomain
cloudflared tunnel route dns intellirag-gpu gpu.intellirag.example.com
```

**Output**:
```
Created CNAME record for gpu.intellirag.example.com which will route to tunnel <TUNNEL_ID>
```

### Verify DNS (Optional)

**Method 1: Via CloudFlare Dashboard**
1. Go to CloudFlare Dashboard → DNS → Records
2. Look for CNAME record: `gpu.intellirag.example.com`
3. Target should be: `<TUNNEL_ID>.cfargotunnel.com`

**Method 2: Via Command Line**
```bash
# Query DNS
dig gpu.intellirag.example.com CNAME +short

# Expected output:
# <TUNNEL_ID>.cfargotunnel.com
```

---

## 🚀 Step 6: Run Tunnel

### Test Run (Foreground)

Before setting up as a service, test the tunnel:

```bash
# Run tunnel in foreground
cloudflared tunnel --config ~/.cloudflared/config.yml run intellirag-gpu
```

**Expected Output**:
```
2025-11-16T10:00:00Z INF Starting tunnel tunnelID=<TUNNEL_ID>
2025-11-16T10:00:00Z INF Connection registered connIndex=0 location=LAX
2025-11-16T10:00:00Z INF Connection registered connIndex=1 location=ORD
2025-11-16T10:00:00Z INF Connection registered connIndex=2 location=IAD
2025-11-16T10:00:00Z INF Connection registered connIndex=3 location=DFW
```

**Test the Tunnel** (in another terminal):
```bash
# From local server
curl https://gpu.intellirag.example.com/health

# Expected: 200 OK with response from KServe
```

### Press Ctrl+C to Stop

---

## 🔧 Step 7: Setup as Systemd Service

### Create Service User

```bash
# Create dedicated user for cloudflared
sudo useradd -r -s /bin/false cloudflared

# Copy config to system directory
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo cp ~/.cloudflared/<TUNNEL_ID>.json /etc/cloudflared/<TUNNEL_ID>.json

# Set ownership
sudo chown -R cloudflared:cloudflared /etc/cloudflared
sudo chmod 600 /etc/cloudflared/<TUNNEL_ID>.json
```

### Create Systemd Service File

```bash
# Create service file
sudo nano /etc/systemd/system/cloudflared.service
```

**Service File Template**:
```ini
[Unit]
Description=CloudFlare Tunnel for IntelliRAG
After=network.target

[Service]
Type=simple
User=cloudflared
Group=cloudflared
ExecStart=/usr/local/bin/cloudflared tunnel --config /etc/cloudflared/config.yml --no-autoupdate run intellirag-gpu
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/etc/cloudflared

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable cloudflared

# Start service
sudo systemctl start cloudflared

# Check status
sudo systemctl status cloudflared
```

**Expected Status**:
```
● cloudflared.service - CloudFlare Tunnel for IntelliRAG
     Loaded: loaded (/etc/systemd/system/cloudflared.service; enabled)
     Active: active (running) since Wed 2025-11-16 10:00:00 UTC
   Main PID: 12345 (cloudflared)
      Tasks: 8
     Memory: 20.0M
     CGroup: /system.slice/cloudflared.service
             └─12345 /usr/local/bin/cloudflared tunnel --config /etc/cloudflared/config.yml run intellirag-gpu
```

---

## ✅ Step 8: Test End-to-End Connectivity

### Test from Local Server

```bash
# 1. Test health endpoint
curl -v https://gpu.intellirag.example.com/health

# 2. Test LLM endpoint
curl https://gpu.intellirag.example.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "max_tokens": 50
  }'

# 3. Test embedding endpoint
curl https://gpu.intellirag.example.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-m3",
    "input": "This is a test sentence"
  }'
```

### Test from GKE Pod

```bash
# Create debug pod in GKE
kubectl run -n app -it --rm debug \
  --image=curlimages/curl \
  --restart=Never \
  -- sh

# Inside the pod, test tunnel
curl -v https://gpu.intellirag.example.com/health

curl https://gpu.intellirag.example.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "Hello from GKE!"}]
  }'
```

**Expected Result**: Successful responses from both tests ✅

---

## 🔐 Step 9: Optional - Setup CloudFlare Access (Zero Trust)

### Enable CloudFlare Access

**Why Use CloudFlare Access?**
- Restrict access to specific IPs or service accounts
- Add extra authentication layer
- Audit access logs
- Free for up to 50 users

### Configure Access Policy

**Via CloudFlare Dashboard**:
1. Go to Zero Trust → Access → Applications
2. Click "Add an application" → "Self-hosted"
3. Configure application:
   - **Application name**: IntelliRAG GPU Endpoints
   - **Session duration**: 24 hours
   - **Application domain**: `gpu.intellirag.example.com`
4. Create access policy:
   - **Policy name**: Allow GKE
   - **Action**: Allow
   - **Include**:
     - IP ranges: `<GKE_NAT_IP>/32` (get from GKE)
     - OR Service Auth: Create service token
5. Save application

### Get GKE NAT IP

```bash
# From GKE, check egress IP
kubectl run -n app --rm -it egress-test \
  --image=curlimages/curl \
  --restart=Never \
  -- curl -s https://api.ipify.org

# Output: <GKE_NAT_IP>
```

### Test with Access Policy

```bash
# From GKE pod (should work)
curl https://gpu.intellirag.example.com/health

# From random internet IP (should get 403 Forbidden)
curl https://gpu.intellirag.example.com/health
# Output: {"error": "Access denied"}
```

---

## 🔐 Step 10: Optional - Add API Key Authentication

For additional security, add API key validation at the FastAPI layer.

### Update FastAPI Config

```python
# app/config.py

class Settings(BaseSettings):
    MODEL_API_KEY: str = ""  # Set via environment variable

    @property
    def llm_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.MODEL_API_KEY:
            headers["Authorization"] = f"Bearer {self.MODEL_API_KEY}"
        return headers
```

### Update LLM Client

```python
# app/services/llm_client.py

async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.LLM_ENDPOINT,
            headers=settings.llm_headers,  # Includes API key
            json={
                "model": "qwen",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0
        )
        return response.json()
```

### Set API Key in GKE

```bash
# Create secret in GKE
kubectl create secret generic intellirag-secrets \
  -n app \
  --from-literal=MODEL_API_KEY=your-secret-api-key-here
```

```yaml
# Update Deployment to use secret
env:
  - name: MODEL_API_KEY
    valueFrom:
      secretKeyRef:
        name: intellirag-secrets
        key: MODEL_API_KEY
```

---

## 📊 Monitoring & Logging

### View Tunnel Logs

```bash
# Real-time logs
sudo journalctl -u cloudflared -f

# Last 100 lines
sudo journalctl -u cloudflared -n 100

# Logs from last hour
sudo journalctl -u cloudflared --since "1 hour ago"
```

### Key Log Events to Monitor

```bash
# Successful connections
sudo journalctl -u cloudflared | grep "Connection registered"

# Errors
sudo journalctl -u cloudflared | grep -i "error"

# Request logs
sudo journalctl -u cloudflared | grep "request"
```

### CloudFlare Dashboard Analytics

**Via CloudFlare Dashboard**:
1. Go to Analytics & Logs → Traffic
2. Filter by hostname: `gpu.intellirag.example.com`
3. View metrics:
   - Total requests
   - Bandwidth
   - Status codes
   - Edge response time

---

## 🔧 Troubleshooting

### Issue 1: Tunnel Not Connecting

**Symptoms**: `cloudflared` service fails to start or shows "connection refused"

**Debug**:
```bash
# Check service status
sudo systemctl status cloudflared

# Check logs for errors
sudo journalctl -u cloudflared -n 50

# Test tunnel manually
sudo -u cloudflared cloudflared tunnel --config /etc/cloudflared/config.yml run intellirag-gpu
```

**Common Fixes**:
```bash
# Verify credentials file exists
ls -la /etc/cloudflared/<TUNNEL_ID>.json

# Check permissions
sudo chown cloudflared:cloudflared /etc/cloudflared/<TUNNEL_ID>.json
sudo chmod 600 /etc/cloudflared/<TUNNEL_ID>.json

# Verify config syntax
cloudflared tunnel ingress validate --config /etc/cloudflared/config.yml

# Restart service
sudo systemctl restart cloudflared
```

---

### Issue 2: DNS Not Resolving

**Symptoms**: `curl https://gpu.intellirag.example.com` fails with "Could not resolve host"

**Debug**:
```bash
# Check DNS records
dig gpu.intellirag.example.com CNAME +short

# Check CloudFlare DNS
nslookup gpu.intellirag.example.com 1.1.1.1
```

**Fixes**:
```bash
# Re-create DNS route
cloudflared tunnel route dns intellirag-gpu gpu.intellirag.example.com

# Or manually create CNAME in CloudFlare Dashboard:
# Name: gpu
# Target: <TUNNEL_ID>.cfargotunnel.com
# Proxied: Yes (orange cloud)
```

---

### Issue 3: Connection Timeout / 502 Error

**Symptoms**: Tunnel connects but requests timeout or return 502 Bad Gateway

**Debug**:
```bash
# Test local KServe gateway directly
curl http://localhost:8080/health

# Check if minikube is running
minikube status

# Check KServe pods
kubectl get pods -n kserve
```

**Fixes**:
```bash
# Ensure minikube is running
minikube start

# Ensure KServe InferenceServices are ready
kubectl get inferenceservices -n kserve

# Increase timeout in config.yml
ingress:
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
    originRequest:
      connectTimeout: 60s  # Increase from 30s
      noTLSVerify: false

# Restart cloudflared
sudo systemctl restart cloudflared
```

---

### Issue 4: High Latency

**Symptoms**: Requests succeed but take >500ms

**Debug**:
```bash
# Test direct connection (bypass tunnel)
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen", "messages": [{"role": "user", "content": "test"}]}'

# Test via tunnel
curl -w "@curl-format.txt" -o /dev/null -s https://gpu.intellirag.example.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen", "messages": [{"role": "user", "content": "test"}]}'
```

**curl-format.txt**:
```
    time_namelookup:  %{time_namelookup}s\n
       time_connect:  %{time_connect}s\n
    time_appconnect:  %{time_appconnect}s\n
   time_pretransfer:  %{time_pretransfer}s\n
      time_redirect:  %{time_redirect}s\n
 time_starttransfer:  %{time_starttransfer}s\n
                    ----------\n
         time_total:  %{time_total}s\n
```

**Analysis**:
- Direct: ~80ms → vLLM is fast ✅
- Tunnel: ~150ms → +70ms tunnel overhead ⚠️

**Optimizations**:
```yaml
# In config.yml, enable HTTP/2
ingress:
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false
      http2Origin: true  # Enable HTTP/2
```

---

## 📋 Configuration Reference

### Complete config.yml Template

```yaml
# /etc/cloudflared/config.yml

# Tunnel identifier (UUID from tunnel create)
tunnel: <TUNNEL_ID>

# Credentials file path
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

# Metrics endpoint (optional, for monitoring)
metrics: localhost:9090

# Log level (debug, info, warn, error)
loglevel: info

# Ingress rules (processed top-to-bottom, first match wins)
ingress:
  # Main GPU endpoint for KServe
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
    originRequest:
      # Connection settings
      connectTimeout: 30s
      tcpKeepAlive: 30s
      keepAliveTimeout: 90s

      # TLS settings
      noTLSVerify: false
      originServerName: localhost

      # HTTP/2
      http2Origin: true

      # Disable chunked encoding for streaming
      disableChunkedEncoding: false

  # Catch-all (required as last rule)
  - service: http_status:404
```

### Environment Variables

```bash
# ~/.bashrc or /etc/environment

# Tunnel configuration
export TUNNEL_ID="<your-tunnel-id>"
export TUNNEL_TOKEN="<your-tunnel-token>"

# CloudFlare credentials
export CLOUDFLARE_TUNNEL_CREDENTIALS=/etc/cloudflared/${TUNNEL_ID}.json
```

---

## 🎯 Next Steps

After successful CloudFlare Tunnel setup:

1. ✅ **Verify tunnel is running**: `sudo systemctl status cloudflared`
2. ✅ **Test endpoints from GKE**: Deploy debug pod and test
3. 🚀 **Update FastAPI configuration**: Set `LLM_ENDPOINT` and `EMBEDDING_ENDPOINT` to CloudFlare Tunnel URLs
4. 🚀 **Deploy FastAPI to GKE**: See [Phase 2: GKE Application Deployment](../plans/phase-1-application-deployment.md)
5. 🧪 **End-to-end testing**: Test ingestion and query flows

---

## 📚 Additional Resources

**Official CloudFlare Documentation**:
- [CloudFlare Tunnel Overview](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Kubernetes Deployment Guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/deployment-guides/kubernetes/)
- [Tunnel Configuration](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/configuration/)

**Related IntelliRAG Documentation**:
- [Hybrid Deployment Architecture](../architecture/hybrid-deployment-architecture.md)
- [Local KServe Setup Guide](./local-kserve-setup-guide.md)
- [Post-GKE Deployment Checklist](./post-gke-deployment-checklist.md) *(to be created)*

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Maintainer**: IntelliRAG Team
**Status**: ✅ Production-Ready Guide
