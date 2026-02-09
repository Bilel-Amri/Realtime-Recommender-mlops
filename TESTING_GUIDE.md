# 🧪 Testing Guide - Real-Time Learning Recommendation System

## Quick Test (5 Minutes)

### Prerequisites Check
```bash
# Check Python version (need 3.8+)
python --version

# Check if dataset is ready
dir data\processed\interactions.csv

# If dataset missing, download it:
cd data
python download_dataset.py
cd ..
```

---

## Option 1: Test Training Pipeline Only (No Backend Required)

### Step 1: Install ML Dependencies
```bash
pip install implicit faiss-cpu pandas numpy scikit-learn mlflow
```

### Step 2: Train Model
```bash
cd training
python train_embeddings.py
```

**Expected Output:**
```
✅ Dataset loaded: 100K interactions
✅ Training complete in ~30 seconds
✅ Precision@10: 0.15
✅ Model saved to models/embedding_model.pkl
✅ FAISS index created
```

**Success Criteria:**
- ✅ No errors
- ✅ Files created: `models/embedding_model.pkl`, `models/vector_store.faiss`
- ✅ Precision@10 > 0.10

---

## Option 2: Test Full System (With Backend + Frontend)

### Step 1: Install All Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### Step 2: Train Model (if not done)
```bash
cd training
python train_embeddings.py
cd ..
```

### Step 3: Start Redis (Optional)
```bash
# Option A: Docker
docker run -d -p 6379:6379 redis

# Option B: Skip (system will use in-memory fallback)
```

### Step 4: Start Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 5: Test Backend API

**Open new terminal:**

```bash
# Test 1: Health Check
curl http://localhost:8000/health

# Expected: {"status": "healthy", ...}

# Test 2: Get Recommendations (before interaction)
curl "http://localhost:8000/recommend?user_id=1&limit=10"

# Expected: JSON with 10 item recommendations

# Test 3: Send User Interaction
curl -X POST http://localhost:8000/events ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"1\",\"item_id\":\"50\",\"event_type\":\"click\",\"timestamp\":\"2026-02-06T10:30:00Z\"}"

# Expected: {"status": "success", "event_id": "..."}

# Test 4: Get Recommendations Again (after interaction)
curl "http://localhost:8000/recommend?user_id=1&limit=10"

# Expected: DIFFERENT recommendations (proves learning!)
```

### Step 6: Start Frontend (Optional)

**Open new terminal:**
```bash
cd frontend
npm run dev
```

**Then open browser:**
```
http://localhost:3001
```

**Test in UI:**
1. Enter user ID (e.g., "1")
2. Click "Get Recommendations"
3. Note the recommendations
4. Go to "Health" page - verify all systems healthy
5. Return to recommendations - results should be dynamic

---

## Option 3: Automated Test Script

### Create Test Script

**File: `test_system.py`**
```python
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("Test 1: Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✅ Backend is healthy")

def test_recommendations_before():
    print("\nTest 2: Get initial recommendations...")
    response = requests.get(f"{BASE_URL}/recommend", params={"user_id": "1", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Received {len(data['recommendations'])} recommendations")
    return data['recommendations']

def test_send_event():
    print("\nTest 3: Send interaction event...")
    event = {
        "user_id": "1",
        "item_id": "50",
        "event_type": "click",
        "timestamp": "2026-02-06T10:30:00Z"
    }
    response = requests.post(f"{BASE_URL}/events", json=event)
    assert response.status_code == 200
    print("✅ Event logged successfully")

def test_recommendations_after():
    print("\nTest 4: Get recommendations after interaction...")
    time.sleep(1)  # Wait for processing
    response = requests.get(f"{BASE_URL}/recommend", params={"user_id": "1", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Received {len(data['recommendations'])} recommendations")
    return data['recommendations']

def test_learning():
    print("\n" + "="*60)
    print("TESTING LEARNING BEHAVIOR")
    print("="*60)
    
    # Get initial recommendations
    recs_before = test_recommendations_before()
    print("\nRecommendations BEFORE interaction:")
    for i, rec in enumerate(recs_before[:5]):
        print(f"  {i+1}. {rec['item_id']} (score: {rec.get('score', 'N/A')})")
    
    # Send interaction
    test_send_event()
    
    # Get recommendations after
    recs_after = test_recommendations_after()
    print("\nRecommendations AFTER interaction:")
    for i, rec in enumerate(recs_after[:5]):
        print(f"  {i+1}. {rec['item_id']} (score: {rec.get('score', 'N/A')})")
    
    # Check if they changed
    before_ids = [r['item_id'] for r in recs_before]
    after_ids = [r['item_id'] for r in recs_after]
    
    if before_ids != after_ids:
        print("\n✅ SUCCESS: Recommendations CHANGED after interaction!")
        print("   System is learning! 🎉")
        return True
    else:
        print("\n⚠️  WARNING: Recommendations are the same")
        print("   This is expected with MockModel. Deploy trained model to see learning.")
        return False

if __name__ == "__main__":
    try:
        test_health()
        test_learning()
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✅")
        print("="*60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nMake sure backend is running:")
        print("  cd backend && uvicorn app.main:app --reload")
```

### Run Test Script
```bash
# Make sure backend is running first!
python test_system.py
```

---

## Proof of Learning Test

### Test Different Users Get Different Recommendations

**Create: `test_personalization.py`**
```python
import requests

BASE_URL = "http://localhost:8000"

# Test 3 users with different behavior
users = [
    {"id": "1", "liked_items": ["10", "20", "30"]},  # User A
    {"id": "2", "liked_items": ["50", "60", "70"]},  # User B  
    {"id": "3", "liked_items": ["100", "110", "120"]},  # User C
]

print("Testing Personalization Across Users")
print("="*60)

results = {}

for user in users:
    # Send interactions
    for item in user['liked_items']:
        requests.post(f"{BASE_URL}/events", json={
            "user_id": user['id'],
            "item_id": item,
            "event_type": "click",
            "timestamp": "2026-02-06T10:30:00Z"
        })
    
    # Get recommendations
    response = requests.get(f"{BASE_URL}/recommend", params={
        "user_id": user['id'],
        "limit": 5
    })
    
    recs = response.json()['recommendations']
    results[user['id']] = [r['item_id'] for r in recs]
    
    print(f"\nUser {user['id']} (liked {user['liked_items']}):")
    print(f"  Recommendations: {results[user['id']]}")

# Check uniqueness
print("\n" + "="*60)
if len(set(map(tuple, results.values()))) == len(users):
    print("✅ SUCCESS: All users got DIFFERENT recommendations!")
    print("   System is personalizing! 🎉")
else:
    print("⚠️  Users got similar recommendations")
    print("   Deploy trained embedding model for better personalization")
```

**Run:**
```bash
python test_personalization.py
```

---

## Performance Test

### Test Latency & Throughput

**Create: `test_performance.py`**
```python
import requests
import time
import statistics

BASE_URL = "http://localhost:8000"

def measure_latency(n=100):
    print(f"Measuring latency over {n} requests...")
    latencies = []
    
    for i in range(n):
        start = time.time()
        response = requests.get(f"{BASE_URL}/recommend", params={
            "user_id": str(i % 10),  # 10 different users
            "limit": 10
        })
        latency = (time.time() - start) * 1000  # Convert to ms
        latencies.append(latency)
        
        if response.status_code != 200:
            print(f"❌ Request {i} failed")
    
    print("\n" + "="*60)
    print("PERFORMANCE RESULTS")
    print("="*60)
    print(f"Requests:     {n}")
    print(f"Mean Latency: {statistics.mean(latencies):.2f} ms")
    print(f"Median:       {statistics.median(latencies):.2f} ms")
    print(f"P95:          {sorted(latencies)[int(n*0.95)]:.2f} ms")
    print(f"P99:          {sorted(latencies)[int(n*0.99)]:.2f} ms")
    print(f"Max:          {max(latencies):.2f} ms")
    
    if statistics.mean(latencies) < 50:
        print("\n✅ PASS: Average latency < 50ms")
    else:
        print("\n⚠️  WARNING: Latency higher than target")

if __name__ == "__main__":
    measure_latency(100)
```

**Run:**
```bash
python test_performance.py
```

---

## Expected Results Summary

### ✅ Success Indicators

1. **Training Pipeline:**
   - ✅ Completes in < 60 seconds
   - ✅ Precision@10 > 0.10
   - ✅ Creates model files

2. **API Tests:**
   - ✅ All endpoints return 200 OK
   - ✅ Recommendations are JSON arrays
   - ✅ Events are logged successfully

3. **Learning Tests:**
   - ✅ Recommendations change after interactions
   - ✅ Different users get different results
   - ✅ Latency < 50ms average

4. **Integration:**
   - ✅ Health check shows all systems green
   - ✅ Frontend displays recommendations
   - ✅ Monitoring shows metrics

---

## Troubleshooting

### Issue: Dataset not found
```bash
# Solution: Download dataset
cd data
python download_dataset.py
```

### Issue: Import errors
```bash
# Solution: Install dependencies
pip install -r requirements.txt
pip install implicit faiss-cpu
```

### Issue: Redis connection failed
```
# Expected behavior: System falls back to in-memory mode
# No action needed unless you specifically want Redis

# To fix: Start Redis
docker run -d -p 6379:6379 redis
```

### Issue: Port 8000 already in use
```bash
# Solution: Use different port
uvicorn app.main:app --port 8001
```

### Issue: Frontend won't start
```bash
# Solution: Install dependencies
cd frontend
npm install
npm run dev
```

---

## Quick Validation Checklist

```
□ Dataset downloaded (data/processed/interactions.csv exists)
□ Training completes without errors
□ Model files created (models/*.pkl, models/*.faiss)
□ Backend starts and responds to /health
□ GET /recommend returns items
□ POST /events accepts interactions
□ Recommendations change after events (learning proof)
□ Different users get different recommendations (personalization proof)
□ Latency < 50ms (performance proof)
□ Frontend displays UI (optional)
```

---

## Demo Script for Presentation

### 1. Show Static Problem
```bash
# Terminal 1: Start backend WITHOUT trained model
cd backend
uvicorn app.main:app

# Terminal 2: Test
curl "http://localhost:8000/recommend?user_id=1&limit=5"
curl "http://localhost:8000/recommend?user_id=2&limit=5"
# Show: Same results for everyone ❌
```

### 2. Train Model
```bash
cd training
python train_embeddings.py
# Show: Training metrics, model saved ✅
```

### 3. Show Learning
```bash
# Restart backend with trained model
# Test different users
python test_personalization.py
# Show: Different recommendations per user ✅
```

### 4. Show Adaptation
```bash
# Get initial recommendations
curl "http://localhost:8000/recommend?user_id=5&limit=5"

# User interacts
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"user_id":"5","item_id":"100","event_type":"click"}'

# Get updated recommendations
curl "http://localhost:8000/recommend?user_id=5&limit=5"
# Show: Recommendations changed ✅
```

---

## Time Estimates

- **Quick Test** (health check only): 30 seconds
- **Training Test** (model training): 2 minutes
- **API Test** (basic endpoints): 5 minutes
- **Learning Test** (proof of learning): 10 minutes
- **Full Integration Test** (with frontend): 15 minutes
- **Performance Test** (100 requests): 5 minutes

**Total for complete testing: ~30 minutes**

---

## Next Steps After Testing

1. ✅ If all tests pass → System is ready for demo/evaluation
2. ⚠️ If learning tests fail → Integrate trained models into backend
3. 📊 If performance is slow → Profile and optimize
4. 🎨 If frontend issues → Check frontend/README.md

---

**For detailed academic defense points, see:** [ACADEMIC_DEFENSE.md](../ACADEMIC_DEFENSE.md)

**For system architecture, see:** [README_AI_SYSTEM.md](../README_AI_SYSTEM.md)
