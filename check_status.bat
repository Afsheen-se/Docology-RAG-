@echo off
echo Checking Docology App Status...
echo.

echo Backend Status:
curl -s http://localhost:8000/health 2>nul
if %errorlevel%==0 (
    echo ✅ Backend is running on http://localhost:8000
) else (
    echo ❌ Backend is NOT running
)
echo.

echo Frontend Status:
curl -s http://localhost:5173 2>nul
if %errorlevel%==0 (
    echo ✅ Frontend is running on http://localhost:5173
) else (
    echo ❌ Frontend is NOT running on port 5173
)

curl -s http://localhost:5174 2>nul
if %errorlevel%==0 (
    echo ✅ Frontend is running on http://localhost:5174
) else (
    echo ❌ Frontend is NOT running on port 5174
)
echo.

echo Check these URLs in your browser:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:5173 or http://localhost:5174
echo - API Docs: http://localhost:8000/docs
echo.

pause

