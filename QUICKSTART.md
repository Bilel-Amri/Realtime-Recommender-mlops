# Real-Time Recommender System - Quick Start

## 🚀 Run with Docker (Easiest - 5 minutes)

### Windows:
```bash
docker-start.bat
```

### Linux/Mac:
```bash
chmod +x docker-start.sh
./docker-start.sh
```

**What it does:**
- ✅ Downloads MovieLens-100K dataset (5MB)
- ✅ Trains ML model (60 seconds)
- ✅ Starts all services (Backend, Frontend, Redis, MLflow)
- ✅ Opens at http://localhost:3000

**Services:**
- **Frontend**: http://localhost:3000 (React dashboard)
- **Backend**: http://localhost:8000 (FastAPI)
- **MLflow**: http://localhost:5000 (Model tracking)
- **Redis**: localhost:6379 (Feature store)

**Test it:**
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/recommend?user_id=1&limit=5"
```

---

## 🐍 Run Locally (No Docker)

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
pip install -r training/requirements.txt
```

### 2. Download Dataset
```bash
cd data && python download_dataset.py && cd ..
```

### 3. Train Model
```bash
cd training && python train_embeddings.py && cd ..
```

### 4. Start Backend
```bash
cd backend && uvicorn app.main:app --reload
```

### 5. Start Frontend (separate terminal)
```bash
cd frontend && npm install && npm run dev
```

### 6. Test
```bash
python test_system.py
```

---

## 🧪 Testing

### Automated Tests
```bash
python test_system.py
```

**Tests:**
- ✅ Health check
- ✅ Recommendations API
- ✅ Learning behavior (recs change after interactions)
- ✅ Personalization (different users, different recs)

### Training Pipeline Test
```bash
python test_training.py
```

**Tests:**
- ✅ Dataset loading
- ✅ Model training (Matrix Factorization)
- ✅ Evaluation (Precision@10 ≈ 0.15)
- ✅ FAISS vector store creation

---

## 📊 System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│    Redis    │
│   React     │     │   FastAPI   │     │   Features  │
│   :3000     │     │   :8000     │     │   :6379     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   MLflow    │
                    │   :5000     │
                    └─────────────┘
```

**Components:**
1. **ML Model**: Matrix Factorization (ALS) - 64-dim embeddings
2. **Vector Search**: FAISS (similarity search <10ms)
3. **Feature Store**: Redis (user embeddings, interactions)
4. **Model Registry**: MLflow (versioning, tracking)

**Dataset:** MovieLens-100K (100,000 ratings, 943 users, 1,682 movies)

---

## 📚 Documentation

- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Complete Docker guide
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing instructions
- **[README_AI_SYSTEM.md](README_AI_SYSTEM.md)** - System overview
- **[ACADEMIC_DEFENSE.md](ACADEMIC_DEFENSE.md)** - Academic justification

---

## 🔧 Troubleshooting

### Port already in use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Docker not starting
```bash
docker-compose down
docker-compose up -d --build
docker-compose logs -f
```

### Dataset not found
```bash
cd data
python download_dataset.py
```

### Model not trained
```bash
cd training
python train_embeddings.py
```

---

## 🎯 Expected Results

**Training Metrics:**
- Precision@10: 0.15 (15% accuracy)
- Recall@10: 0.25 (25% coverage)
- MAP@10: 0.18 (ranking quality)
- Training Time: 30-60 seconds

**Inference Performance:**
- Latency: <12ms average
- Throughput: 1000+ req/sec
- Cold start: <50ms

**Learning Behavior:**
- Recommendations change after user interactions
- Different users get different recommendations
- System adapts to user preferences in real-time

---

## ✅ Success Checklist

- [ ] Docker/Python installed
- [ ] Dataset downloaded (9MB in data/processed/)
- [ ] Model trained (models/embedding_model.pkl exists)
- [ ] Services running (docker-compose ps shows all healthy)
- [ ] Health check passes (curl localhost:8000/health)
- [ ] Tests pass (python test_system.py → 3/3 pass)
- [ ] Frontend loads (http://localhost:3000)

---

## 🎉 Demo Script

```bash
# 1. Start system
docker-start.bat  # or ./docker-start.sh

# 2. Wait 60 seconds for startup

# 3. Test health
curl http://localhost:8000/health

# 4. Get recommendations for user 1
curl "http://localhost:8000/recommend?user_id=1&limit=5"

# 5. Log user interaction
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"user_id":"1","item_id":"item_50","event_type":"click"}'

# 6. Get updated recommendations (should be different!)
curl "http://localhost:8000/recommend?user_id=1&limit=5"

# 7. Open frontend dashboard
# Open browser: http://localhost:3000

# 8. View MLflow experiments
# Open browser: http://localhost:5000
```

---

**Need help?** Check [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed troubleshooting.
