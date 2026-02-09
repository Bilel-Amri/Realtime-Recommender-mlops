# Docker Deployment Guide

Complete guide to running the Real-Time Recommender System with Docker.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Services](#services)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
   - Windows/Mac: https://docs.docker.com/get-docker/
   - Linux: https://docs.docker.com/engine/install/
   - Minimum version: 20.10+

2. **Docker Compose**
   - Included with Docker Desktop
   - Linux: https://docs.docker.com/compose/install/
   - Minimum version: 2.0+

3. **Python 3.11+** (for dataset download and model training)
   - Only needed for initial setup
   - Download: https://www.python.org/downloads/

### System Requirements

```
Disk Space:  5 GB minimum
RAM:         4 GB minimum (8 GB recommended)
CPU:         2 cores minimum (4 cores recommended)
OS:          Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
```

---

## Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**
```bash
docker-start.bat
```

**Linux/Mac:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

This script will:
1. ✅ Check Docker installation
2. ✅ Download dataset (if needed)
3. ✅ Train model (if needed)
4. ✅ Build Docker images
5. ✅ Start all services
6. ✅ Wait for services to be healthy

**Expected time:** 3-5 minutes

---

### Option 2: Manual Setup

**Step 1: Download Dataset**
```bash
cd data
python download_dataset.py
cd ..
```

**Step 2: Train Model**
```bash
cd training
python train_embeddings.py
cd ..
```

**Step 3: Build and Start**
```bash
docker-compose build
docker-compose up -d
```

**Step 4: Verify**
```bash
docker-compose ps
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Docker Network                     │
│                                                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ Frontend │   │ Backend  │   │  Redis   │        │
│  │  React   │◄──┤  FastAPI │◄──┤  Cache   │        │
│  │  :3000   │   │  :8000   │   │  :6379   │        │
│  └──────────┘   └──────────┘   └──────────┘        │
│                       │                              │
│                  ┌────▼─────┐                        │
│                  │  MLflow  │                        │
│                  │  :5000   │                        │
│                  └──────────┘                        │
│                                                       │
└─────────────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │ Browser │   │  Models │   │  Data   │
    │  User   │   │ Volume  │   │ Volume  │
    └─────────┘   └─────────┘   └─────────┘
```

---

## Services

### 1. **Frontend** (React + Vite + Nginx)

**Purpose:** User interface for recommendations and monitoring

**Container:** `recommender-frontend`
**Port:** 3000
**URL:** http://localhost:3000

**Features:**
- Recommendations dashboard
- Real-time monitoring
- Performance metrics
- Health status

**Tech Stack:**
- React 18
- TypeScript
- Vite (build tool)
- Nginx (web server)

---

### 2. **Backend** (FastAPI + ML Models)

**Purpose:** API server with ML recommendation engine

**Container:** `recommender-backend`
**Port:** 8000
**URL:** http://localhost:8000

**API Endpoints:**
```
GET  /health                          # Health check
GET  /recommend?user_id=X&limit=10    # Get recommendations
POST /events                           # Log user interactions
GET  /metrics                          # System metrics
```

**Tech Stack:**
- FastAPI
- Matrix Factorization (ALS)
- FAISS vector search
- Redis feature store

**Environment Variables:**
```bash
REDIS_HOST=redis
REDIS_PORT=6379
MLFLOW_TRACKING_URI=http://mlflow:5000
MODEL_PATH=/app/models/embedding_model.pkl
VECTOR_STORE_PATH=/app/models/vector_store
LOG_LEVEL=INFO
```

---

### 3. **Redis** (In-Memory Feature Store)

**Purpose:** Real-time feature storage and caching

**Container:** `recommender-redis`
**Port:** 6379

**Features:**
- User embeddings (64-dim vectors)
- Recent interactions (last 100 per user)
- Item popularity scores
- User statistics (views, clicks, purchases)

**Configuration:**
```
Max Memory:  512 MB
Eviction:    allkeys-lru (least recently used)
Persistence: AOF (append-only file)
```

---

### 4. **MLflow** (Model Registry & Tracking)

**Purpose:** ML experiment tracking and model versioning

**Container:** `recommender-mlflow`
**Port:** 5000
**URL:** http://localhost:5000

**Features:**
- Experiment tracking
- Model versioning
- Metrics logging
- Artifact storage

**Storage:**
- Backend: SQLite
- Artifacts: Local filesystem
- Volume: `mlflow-data`

---

## Usage

### Start System

```bash
docker-compose up -d
```

**Verify all services are running:**
```bash
docker-compose ps
```

Expected output:
```
NAME                      STATUS         PORTS
recommender-backend       Up (healthy)   0.0.0.0:8000->8000/tcp
recommender-frontend      Up (healthy)   0.0.0.0:3000->3000/tcp
recommender-redis         Up (healthy)   0.0.0.0:6379->6379/tcp
recommender-mlflow        Up (healthy)   0.0.0.0:5000->5000/tcp
```

---

### View Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f redis
docker-compose logs -f mlflow
```

**Last 100 lines:**
```bash
docker-compose logs --tail=100 backend
```

---

### Test System

**1. Health Check:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-02-06T10:30:00Z",
  "version": "1.0.0"
}
```

**2. Get Recommendations:**
```bash
curl "http://localhost:8000/recommend?user_id=1&limit=5"
```

Expected response:
```json
{
  "user_id": "1",
  "recommendations": [
    {"item_id": "item_123", "score": 0.89, "title": "Product X"},
    {"item_id": "item_456", "score": 0.87, "title": "Product Y"}
  ],
  "latency_ms": 12
}
```

**3. Log User Event:**
```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1",
    "item_id": "item_123",
    "event_type": "click",
    "timestamp": "2025-02-06T10:30:00Z"
  }'
```

**4. Run Automated Tests:**
```bash
python test_system.py
```

---

### Stop System

**Stop all services:**
```bash
docker-compose down
```

**Stop and remove volumes (⚠️ deletes data):**
```bash
docker-compose down -v
```

**Stop specific service:**
```bash
docker-compose stop backend
```

---

### Restart Services

**Restart all:**
```bash
docker-compose restart
```

**Restart specific service:**
```bash
docker-compose restart backend
```

---

### Scale Services

**Run multiple backend instances:**
```bash
docker-compose up -d --scale backend=3
```

**Note:** Requires load balancer configuration for production use.

---

### Update Code

**Backend changes:**
```bash
# Code is mounted as volume, changes reflect immediately
# Restart to apply:
docker-compose restart backend
```

**Rebuild after dependency changes:**
```bash
docker-compose build backend
docker-compose up -d backend
```

**Frontend changes:**
```bash
# Rebuild required (Nginx serves static files)
docker-compose build frontend
docker-compose up -d frontend
```

---

### Access Containers

**Open shell in container:**
```bash
docker exec -it recommender-backend bash
docker exec -it recommender-frontend sh
```

**Run command in container:**
```bash
docker exec recommender-backend python -c "print('Hello')"
```

**Access Redis CLI:**
```bash
docker exec -it recommender-redis redis-cli
```

Redis commands:
```bash
PING                              # Test connection
KEYS *                            # List all keys
GET user:123:embedding            # Get user embedding
LRANGE user:123:interactions 0 9  # Get last 10 interactions
```

---

## Troubleshooting

### Issue 1: Port Already in Use

**Error:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**Solution:**
```bash
# Windows (find process on port 8000)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**Or change port in docker-compose.yml:**
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

---

### Issue 2: Service Not Healthy

**Check logs:**
```bash
docker-compose logs backend
```

**Common causes:**
1. **Model not found** → Train model: `python training/train_embeddings.py`
2. **Redis connection failed** → Check Redis is running: `docker-compose ps redis`
3. **Out of memory** → Increase Docker memory limit in Docker Desktop settings

**Restart service:**
```bash
docker-compose restart backend
```

---

### Issue 3: Build Fails

**Error:**
```
ERROR [internal] load metadata for docker.io/library/python:3.11-slim
```

**Solution:**
```bash
# Pull base images manually
docker pull python:3.11-slim
docker pull node:20-alpine
docker pull nginx:alpine
docker pull redis:7-alpine

# Rebuild
docker-compose build --no-cache
```

---

### Issue 4: Frontend Can't Reach Backend

**Check network:**
```bash
docker network inspect realtime-recommender-mlops_recommender-network
```

**Verify backend is accessible from frontend:**
```bash
docker exec recommender-frontend wget -O- http://backend:8000/health
```

**Check Nginx proxy configuration:**
```bash
docker exec recommender-frontend cat /etc/nginx/conf.d/default.conf
```

---

### Issue 5: Slow Startup

**Cause:** Docker downloading images, building, starting services

**Expected times:**
- First build: 5-10 minutes
- Subsequent starts: 30-60 seconds

**Speed up:**
```bash
# Use cached layers
docker-compose build

# Parallel build (if multiple services changed)
docker-compose build --parallel
```

---

### Issue 6: Out of Disk Space

**Check Docker disk usage:**
```bash
docker system df
```

**Clean up:**
```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes (⚠️ deletes data)
docker volume prune

# Remove everything (⚠️ nuclear option)
docker system prune -a --volumes
```

---

### Issue 7: Can't Access MLflow UI

**Check if MLflow is running:**
```bash
docker-compose ps mlflow
```

**Check logs:**
```bash
docker-compose logs mlflow
```

**Test connection:**
```bash
curl http://localhost:5000/health
```

**Restart:**
```bash
docker-compose restart mlflow
```

---

## Performance Optimization

### 1. Build Optimization

**Use multi-stage builds** (already implemented):
- Reduces image size
- Faster deployments
- Smaller attack surface

**Layer caching:**
```dockerfile
# Copy requirements first (changes less often)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code last (changes more often)
COPY app/ .
```

---

### 2. Resource Limits

**Add to docker-compose.yml:**
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

### 3. Health Check Tuning

**Adjust health check intervals:**
```yaml
healthcheck:
  interval: 10s      # How often to check
  timeout: 5s        # Max time for check
  retries: 3         # Failures before unhealthy
  start_period: 60s  # Grace period on startup
```

---

### 4. Redis Performance

**Increase memory:**
```yaml
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

**Persistent storage:**
```yaml
command: redis-server --appendonly yes --save 60 1000
```

---

## Production Deployment

### Security Hardening

1. **Use secrets for sensitive data:**
```yaml
secrets:
  redis_password:
    external: true
```

2. **Enable TLS/SSL:**
```yaml
environment:
  - REDIS_TLS=true
  - REDIS_TLS_CERT_FILE=/certs/redis.crt
```

3. **Run as non-root user** (already implemented)

4. **Scan for vulnerabilities:**
```bash
docker scan recommender-backend
```

---

### Monitoring

**Add Prometheus + Grafana:**
```yaml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "4000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

### Logging

**Use logging driver:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Centralized logging (ELK stack):**
```yaml
logging:
  driver: "gelf"
  options:
    gelf-address: "udp://logstash:12201"
```

---

## Summary

**Start System:**
```bash
./docker-start.sh  # or docker-start.bat on Windows
```

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- MLflow: http://localhost:5000

**Test:**
```bash
python test_system.py
```

**Stop:**
```bash
docker-compose down
```

**Logs:**
```bash
docker-compose logs -f
```

---

**🎉 You're now running the system in Docker!**

For more details, see:
- [README_AI_SYSTEM.md](README_AI_SYSTEM.md) - System overview
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing instructions
- [ACADEMIC_DEFENSE.md](ACADEMIC_DEFENSE.md) - Academic justification
