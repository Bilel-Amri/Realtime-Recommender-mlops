@echo off
REM Quick System Restart and Test Script for Windows
REM Run this after fixes are applied

echo.
echo ================================================================================
echo                    SYSTEM RESTART AND VERIFICATION
echo ================================================================================
echo.

echo Step 1: Stopping Docker containers...
docker-compose down
timeout /t 3 /nobreak >nul

echo.
echo Step 2: Starting Docker containers...
docker-compose up -d

echo.
echo Step 3: Waiting for services to be ready (60 seconds)...
echo (You can press Ctrl+C if containers are already healthy)
timeout /t 60

echo.
echo Step 4: Checking Docker container status...
docker-compose ps

echo.
echo ================================================================================
echo                         RUNNING VERIFICATION
echo ================================================================================
echo.

python verify_system.py

echo.
echo ================================================================================
echo                    VERIFICATION COMPLETE
echo ================================================================================
echo.

echo If all checks passed, you can now run:
echo   - python run_defense_demo.py       (Generate demo activity)
echo   - Open http://localhost:3000       (View application)
echo   - Open http://localhost:3000/dashboard  (View metrics)
echo.

pause
