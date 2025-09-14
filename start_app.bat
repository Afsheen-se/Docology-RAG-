@echo off
echo Starting Docology RAG Document Q&A App...

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy "env.example" ".env"
    echo Please edit .env file and add your GOOGLE_API_KEY
)

REM Start Backend
echo Starting Backend (FastAPI)...
start "Backend" cmd /k "cd backend && set GOOGLE_API_KEY=test_key && python main.py"

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Start Frontend  
echo Starting Frontend (React + Vite)...
start "Frontend" cmd /k "cd frontend && npm run dev"

REM Wait a moment
timeout /t 2 /nobreak >nul

echo.
echo 🚀 Docology App is starting up!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo ⚠️  Don't forget to add your real Google API key to the .env file!
echo.
pause

