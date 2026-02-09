@echo off
REM Quick start script for Windows
REM Checks prerequisites and launches system

echo ============================================
echo Real-Time Recommender System
echo ============================================
echo.

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found
    echo Install from: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

REM Check if already running
docker ps | findstr "recommender-backend" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] System is already running!
    echo.
    goto :show_urls
)

REM Download dataset if needed
if not exist "data\processed\interactions.csv" (
    echo [1/4] Downloading dataset...
    python data\download_dataset.py
) else (
    echo [1/4] Dataset found
)

REM Train model if needed
if not exist "models\embedding_model.pkl" (
    echo [2/4] Training model - 60 seconds...
    cd training
    python train_embeddings.py
    cd ..
) else (
    echo [2/4] Model found
)

REM Build images
echo [3/4] Building Docker images...
docker-compose build

REM Start services
echo [4/4] Starting services...
docker-compose up -d

echo.
echo Waiting for services to start (30 seconds)...
timeout /t 30 /nobreak >nul

:show_urls
echo.
echo ============================================
echo System is READY!
echo ============================================
echo.
echo Open in your browser:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000/docs
echo   MLflow:    http://localhost:5000
echo.
echo Test API:
echo   curl http://localhost:8000/health
echo.
echo View logs:
echo   docker-compose logs -f
echo.
echo Stop system:
echo   docker-compose down
echo.
pause
