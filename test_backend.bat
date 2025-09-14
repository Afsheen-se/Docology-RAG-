@echo off
echo Testing Backend Endpoints...
echo.

echo 1. Testing root endpoint:
curl -s http://localhost:8000/
echo.
echo.

echo 2. Testing health endpoint:
curl -s http://localhost:8000/health
echo.
echo.

echo 3. Testing documents endpoint:
curl -s http://localhost:8000/documents
echo.
echo.

echo 4. Testing API docs:
echo Open http://localhost:8000/docs in your browser
echo.

pause
