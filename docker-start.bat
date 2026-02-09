@echo off
REM Docker deployment script for Real-Time Recommender System (Windows)

echo ============================================
echo Real-Time Recommender System - Docker Setup
echo ============================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed
    echo Install Docker from: https://docs.docker.com/get-docker/
    exit /b 1
)
echo [OK] Docker is installed

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose is not installed
        echo Install Docker Compose from: https://docs.docker.com/compose/install/
        exit /b 1
    )
)
echo [OK] Docker Compose is installed

REM Check if dataset exists
if not exist "data\processed\interactions.csv" (
    echo [WARNING] Dataset not found
    echo Downloading and preprocessing dataset...
    
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed
        echo Install Python or manually place dataset in data\processed\
        exit /b 1
    )
    
    python data\download_dataset.py
    echo [OK] Dataset downloaded
) else (
    echo [OK] Dataset found
)

REM Check if model exists
if not exist "models\embedding_model.pkl" (
    echo [WARNING] Trained model not found
    echo Training model - this will take 30-60 seconds...
    cd training
    python train_embeddings.py
    cd ..
    echo [OK] Model trained
) else (
    echo [OK] Trained model found
)

REM Stop any existing containers
echo.
echo Stopping existing containers...
docker-compose down 2>nul

REM Build images
echo.
echo Building Docker images (this may take a few minutes)...
docker compose build 2>nul || docker-compose build

REM Start services
echo.
echo Starting services...
docker compose up -d 2>nul || docker-compose up -d

REM Wait for services
echo.
echo Waiting for services to be ready...
echo This may take 30-60 seconds for first startup...
timeout /t 30 /nobreak >nul

REM Print status
echo.
echo ============================================
echo System is running!
echo ============================================
echo.

echo Services:
echo   * Frontend:  http://localhost:3000
echo   * Backend:   http://localhost:8000
echo   * MLflow:    http://localhost:5000
echo   * Redis:     localhost:6379
echo.

echo API Endpoints:
echo   * Health:          http://localhost:8000/health
echo   * Recommendations: http://localhost:8000/recommend?user_id=1^&limit=10
echo   * Events:          http://localhost:8000/events (POST)
echo   * Metrics:         http://localhost:8000/metrics
echo.

echo Useful commands:
echo   docker-compose logs -f           # View all logs
echo   docker-compose logs -f backend   # View backend logs
echo   docker-compose ps                # Check service status
echo   docker-compose down              # Stop all services
echo   docker-compose restart backend   # Restart backend
echo.

echo Test the system:
echo   curl http://localhost:8000/health
echo   curl "http://localhost:8000/recommend?user_id=1&limit=5"
echo.

echo Setup complete!
pause
