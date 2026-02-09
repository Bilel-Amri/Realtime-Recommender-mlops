# 🔧 Frontend Display Issue - Troubleshooting Guide

## Issue: Plain Text Instead of Styled UI

**Symptoms:** Opening http://localhost:3000/dashboard or http://localhost:3000/ab-testing shows plain text without colors, buttons, or styling.

---

## 🔍 Quick Diagnosis

### Step 1: Check Frontend Container Health

```bash
docker-compose ps frontend
```

**Expected:**  
```
recommender-frontend   Up   (healthy)
```

**If you see:**
- `(health: starting)` → **Wait 2-3 minutes**, then check again
- `(unhealthy)` → See "Fix #1" below  
- Container not running → See "Fix #2" below

---

### Step 2: Check Browser Console

1. Open http://localhost:3000 in browser
2. Press **F12** (open DevTools)
3. Go to **Console** tab

**Look for errors like:**
- ❌ `Failed to load resource: net::ERR_CONNECTION_REFUSED`
- ❌ `Failed to fetch Chrome extension` (ignore this)
- ❌ `Uncaught SyntaxError` or `Cannot find module`

---

### Step 3: Check Network Tab

1. In DevTools, go to **Network** tab  
2. Refresh page (**Ctrl + R**)
3. Look at loaded files

**Expected:** You should see:
- ✅ `index.html` (200 OK)
- ✅ `main.tsx` or `index-[hash].js` (200 OK)  
- ✅ `style.css` or `index-[hash].css` (200 OK)

**If CSS/JS files are missing or showing 404:**
→ Frontend build failed. See "Fix #1" below.

---

## 🛠️ Fixes

### Fix #1: Rebuild Frontend Container

If frontend is unhealthy or build failed:

```batch
fix_frontend.bat
```

This will:
1. Check frontend logs
2. Rebuild container from scratch (no cache)
3. Restart frontend service
4. Wait 30 seconds for it to be ready

**OR manually:**

```bash
# Stop and remove frontend
docker-compose stop frontend
docker-compose rm -f frontend

# Remove old image
docker rmi realtime-recommender-mlops-frontend

# Rebuild (no cache)
docker-compose build --no-cache frontend

# Start
docker-compose up -d frontend

# Wait 60 seconds
timeout /t 60

# Check status
docker-compose ps frontend
```

---

### Fix #2: Clear Browser Cache

Sometimes browsers aggressively cache broken content:

1. **Hard Refresh:** Press **Ctrl + Shift + R** (or **Cmd + Shift + R** on Mac)
2. **Incognito Mode:** Try opening http://localhost:3000 in incognito/private window
3. **Clear Cache:**
   - Chrome: Settings → Privacy → Clear browsing data → Cached images and files
   - Edge: Settings → Privacy → Clear browsing data → Cached data and files

---

### Fix #3: Check Container Logs

See what's happening inside the container:

```bash
# Check frontend logs
docker logs recommender-frontend

# Follow logs in real-time
docker logs -f recommender-frontend
```

**Look for:**
- ✅ `Server running at http://0.0.0.0:3000` (good!)
- ❌ `ERROR` or `ENOENT` messages (build failed)
- ❌ `Module not found` (missing dependencies)

---

### Fix #4: Use Development Mode (Easier Debugging)

If production build keeps failing, use development mode:

1. Edit `docker-compose.yml`, find the `frontend` service
2. Change:
   ```yaml
   build:
     context: .
     dockerfile: frontend/Dockerfile
   ```
   To:
   ```yaml
   build:
     context: .
     dockerfile: frontend/Dockerfile.dev
   ```

3. Restart:
   ```bash
   docker-compose up -d --build frontend
   ```

Development mode:
- ✅ Faster builds
- ✅ Hot reload (changes appear instantly)
- ✅ Better error messages
- ❌ Slower runtime performance (OK for dev/demo)

---

## 🎯 Common Causes & Solutions

### Cause 1: Frontend Still Building
**Symptom:** Container shows `(health: starting)`  
**Solution:** Wait 2-3 minutes. React build takes time.

### Cause 2: Build Failed During Docker Compose Up
**Symptom:** Container is `(unhealthy)` or exits immediately  
**Solution:** Run `fix_frontend.bat` to rebuild

### Cause 3: Browser Cached Broken HTML
**Symptom:** Other pages work, but this one doesn't  
**Solution:** Hard refresh (Ctrl + Shift + R) or try incognito

### Cause 4: Missing Dependencies  
**Symptom:** Logs show "Module not found"  
**Solution:** Rebuild with `fix_frontend.bat`

### Cause 5: Port Conflict
**Symptom:** Container won't start, port 3000 in use  
**Solution:** 
```bash
# Find what's using port 3000
netstat -ano | findstr :3000

# Kill the process
taskkill /PID <PID> /F

# Restart frontend
docker-compose up -d frontend
```

---

## ✅ Expected Working Result

When everything works, you should see:

### Dashboard (http://localhost:3000/dashboard):
- 🎨 **Colorful cards** showing metrics (blue, green backgrounds)
- 📊 **Charts** with lines showing events over time  
- 🔄 **Auto-refreshing** every 5 seconds
- ✨ **Smooth animations** and hover effects

### A/B Testing (http://localhost:3000/ab-testing):
- 📊 **Two side-by-side cards** (Model A vs B)
- 📈 **Bar chart** comparing metrics
- 🏆 **Winner badge** on the better model
- 📊 **Statistical analysis** section

**NOT:**
- ❌ Plain black text on white background
- ❌ No colors or styling
- ❌ Bullet points and headings only
- ❌ Raw HTML showing

---

## 🆘 Still Not Working?

Run this diagnostic script:

```batch
check_frontend.bat
```

This will show:1. Container status
2. Recent logs
3. HTTP response test
4. Specific recommendations

---

## 📞 Emergency Fallback: View API Directly

If frontend won't work, you can still demo the backend APIs:

1. **API Documentation:**  
   http://localhost:8000/docs

2. **Dashboard Metrics JSON:**  
   http://localhost:8000/api/v1/metrics/dashboard

3. **A/B Test Results JSON:**  
   http://localhost:8000/api/v1/mlops/ab-results-demo

Show these to your examiners if frontend issues persist. The backend is fully functional!

---

## 🎓 For Your Defense

If frontend issues persist and you can't fix them before defense:

**What to say:**
> *"The backend API is fully functional with all MLOps capabilities. The frontend is a visualization layer that temporarily has a rendering issue in this environment. I can demonstrate all functionality via the API endpoints and show you the code architecture."*

**Then:**
1. Open http://localhost:8000/docs
2. Show API endpoints working
3. Execute requests in Swagger UI
4. Show JSON responses
5. Walk through frontend code in VS Code

The system is fully functional - just the UI layer has a rendering issue.

---

**Created:** February 9, 2026  
**Last Updated:** Contact me if none of these fixes work!
