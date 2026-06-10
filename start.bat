@echo off
title EduCast
cd /d "%~dp0"

echo ============================================
echo   EduCast Startup
echo ============================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] python not found. Please install Python 3.11+
    pause
    exit /b 1
)
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] node not found. Please install Node.js
    pause
    exit /b 1
)

echo [1/4] Checking backend deps...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing...
    pip install -r backend\requirements.txt -q
) else (
    echo       Ready
)

echo [2/4] Checking frontend deps...
if not exist frontend\node_modules (
    echo       Installing...
    cd frontend && call npm install --silent && cd ..
) else (
    echo       Ready
)

echo [3/4] Starting backend (port 8000)...
start "EduCast Backend" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [4/4] Starting frontend (port 5173)...
start "EduCast Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Waiting for services...
timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Close the two command windows to stop services.
