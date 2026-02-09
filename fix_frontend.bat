@echo off
REM Frontend Diagnostic and Rebuild Script

echo.
echo ================================================================================
echo                    FRONTEND DIAGNOSTIC AND FIX
echo ================================================================================
echo.

echo Step 1: Checking frontend container logs...
echo.
docker logs recommender-frontend --tail 50

echo.
echo ================================================================================
echo Step 2: Rebuilding frontend container...
echo ================================================================================
echo.

echo Stopping frontend...
docker-compose stop frontend

echo.
echo Removing old frontend container and image...
docker-compose rm -f frontend
docker rmi realtime-recommender-mlops-frontend 2>nul

echo.
echo Rebuilding frontend (this may take 2-3 minutes)...
docker-compose build --no-cache frontend

echo.
echo Starting frontend...
docker-compose up -d frontend

echo.
echo ================================================================================
echo Step 3: Waiting for frontend to be ready (30 seconds)...
echo ================================================================================
timeout /t 30 /nobreak

echo.
echo Step 4: Checking frontend status...
docker-compose ps frontend

echo.
echo Step 5: Testing frontend...
curl -I http://localhost:3000 2>nul

echo.
echo ================================================================================
echo                         DIAGNOSTIC COMPLETE
echo ================================================================================
echo.

echo Now try opening in your browser:
echo   http://localhost:3000
echo.
echo If you still see plain text:
echo   1. Press F12 in browser (open DevTools)
echo   2. Check Console tab for errors
echo   3. Check Network tab - are CSS/JS files loading?
echo.

pause
