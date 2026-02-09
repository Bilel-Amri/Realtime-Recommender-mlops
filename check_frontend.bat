@echo off
REM Quick Frontend Check Script

echo.
echo ================================================================================
echo                    FRONTEND STATUS CHECK
echo ================================================================================
echo.

echo Checking frontend container status...
docker-compose ps frontend

echo.
echo Checking frontend logs (last 30 lines)...
echo ================================================================================
docker logs recommender-frontend --tail 30

echo.
echo ================================================================================
echo Testing HTTP response from frontend...
echo ================================================================================
curl -v http://localhost:3000/ 2>&1 | findstr /C:"HTTP" /C:"Content-Type" /C:"200"

echo.
echo ================================================================================
echo                         RECOMMENDATIONS
echo ================================================================================
echo.

echo If you saw "health: starting" (not "healthy"):
echo   → Wait 1-2 more minutes for frontend to finish building
echo   → Run: docker-compose ps frontend
echo   → Wait until status shows "(healthy)"
echo.

echo If you saw errors in logs:
echo   → Run: fix_frontend.bat (rebuilds from scratch)
echo.

echo If you saw "200 OK" and "text/html":
echo   → Try hard refresh in browser: Ctrl + Shift + R
echo   → Clear browser cache
echo   → Try incognito/private window
echo.

echo After frontend is healthy, open:
echo   http://localhost:3000
echo.

pause
