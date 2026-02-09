@echo off
REM Quick verification script for Windows

echo ========================================
echo Real-Time Recommender MLOps - System Verification
echo ========================================
echo.

echo Checking dependencies...
echo.

REM Check Docker
docker --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Docker is installed
    docker --version
) else (
    echo [ERROR] Docker is NOT installed
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop
    goto :error
)

echo.

REM Check Docker Compose
docker-compose --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Docker Compose is installed
    docker-compose --version
) else (
    echo [ERROR] Docker Compose is NOT installed
    goto :error
)

echo.

REM Check Python (optional)
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Python is installed
    python --version
) else (
    echo [WARNING] Python is not installed (optional for local dev)
)

echo.

REM Check project structure
if exist "backend" (
    echo [OK] backend/ directory exists
) else (
    echo [ERROR] backend/ directory missing
    goto :error
)

if exist "frontend" (
    echo [OK] frontend/ directory exists
) else (
    echo [ERROR] frontend/ directory missing
    goto :error
)

if exist "docker-compose.yml" (
    echo [OK] docker-compose.yml exists
) else (
    echo [ERROR] docker-compose.yml missing
    goto :error
)

echo.
echo ========================================
echo [SUCCESS] System is ready!
echo ========================================
echo.
echo Quick Start:
echo   1. Run: docker-compose up -d
echo   2. Wait 30 seconds for initialization
echo   3. Visit: http://localhost:3000
echo.
echo Services:
echo   - Frontend: http://localhost:3000
echo   - Backend API: http://localhost:8000/docs
echo   - MLflow: http://localhost:5000
echo.
pause
exit /b 0

:error
echo.
echo ========================================
echo [ERROR] System verification failed
echo ========================================
echo Please fix the errors above and try again.
echo.
pause
exit /b 1
