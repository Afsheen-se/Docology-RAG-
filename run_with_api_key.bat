@echo off
echo Starting Docology with your Google API Key...

REM Set the API key
set GOOGLE_API_KEY=AIzaSyAdfz3NG0yUSmmqB0sLt-be_nzgHsGIJxU

REM Start Backend
echo Starting Backend...
start "Backend" cmd /k "cd backend && set GOOGLE_API_KEY=AIzaSyAdfz3NG0yUSmmqB0sLt-be_nzgHsGIJxU && python main.py"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start Frontend
echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo 🚀 Docology App is starting!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173 (or 5174)
echo.
echo Your Google API Key is configured!
echo.
pause

