@echo off
title EduCast
cd /d "%~dp0"

echo ============================================
echo   EduCast Startup
echo ============================================
echo.

:: Check prerequisites
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

:: 1. Check backend deps
echo [1/5] Checking backend deps...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing...
    pip install -r backend\requirements.txt -q
) else (
    echo       Ready
)

:: 2. Check frontend deps
echo [2/5] Checking frontend deps...
if not exist frontend\node_modules (
    echo       Installing...
    cd frontend && call npm install --silent && cd ..
) else (
    echo       Ready
)

:: 3. Check database
echo [3/5] Checking database...
if not exist backend\educast.db (
    echo       Creating database...
    cd backend && python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())" >nul 2>&1 && cd ..
    echo       Database created
) else (
    echo       Database exists
)

:: 4. Start backend
echo [4/5] Starting backend (port 8000)...
start "EduCast Backend" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: 5. Start frontend
echo [5/5] Starting frontend (port 5173)...
start "EduCast Frontend" cmd /k "cd frontend && npm run dev"

:: Wait for services
timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Close the two command windows to stop services.
