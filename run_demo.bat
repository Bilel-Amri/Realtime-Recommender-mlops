@echo off
REM Quick Demo Script - Run this if Docker is already running
REM This generates demo activity and creates the report

echo.
echo ================================================================================
echo                    GENERATING DEMO ACTIVITY
echo ================================================================================
echo.

echo Opening dashboard in browser...
start http://localhost:3000/dashboard

echo.
echo Running demo script...
echo (This will take about 2 minutes)
echo.

python run_defense_demo.py

echo.
echo ================================================================================
echo                         DEMO COMPLETE
echo ================================================================================
echo.

echo Generated files:
echo   - DEMO_REPORT.txt (demo summary)
echo.

echo Open these URLs in your browser:
echo   - Dashboard:     http://localhost:3000/dashboard
echo   - A/B Testing:   http://localhost:3000/ab-testing
echo   - Main App:      http://localhost:3000
echo   - MLflow:        http://localhost:5000
echo.

echo Review DEFENSE_CHEAT_SHEET.md for your presentation guide!
echo.

pause
