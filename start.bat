@echo off
REM ============================================================================
REM Timetable LLM - Quick Start Script for Windows
REM This script starts both backend and frontend servers
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo Timetable LLM - Application Startup
echo ============================================================================
echo.

REM Check if we're in the right directory
if not exist ".env" (
    echo ERROR: .env file not found. Please run this script from the project root.
    echo.
    exit /b 1
)

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from https://www.python.org
    exit /b 1
)
python --version

REM Check Node
echo.
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install from https://nodejs.org
    exit /b 1
)
node --version

echo.
echo ============================================================================
echo Starting services...
echo ============================================================================
echo.

REM Start Backend in a new window
echo Starting Backend (FastAPI on port 8000)...
start "Timetable LLM - Backend" cmd /k ^
    cd /d "%cd%\backend" && ^
    if not exist ".venv" (^
        echo Creating Python virtual environment... && ^
        python -m venv .venv^
    ) && ^
    call .venv\Scripts\activate.bat && ^
    echo Installing dependencies... && ^
    pip install -r requirements.txt -q && ^
    echo Running migrations... && ^
    alembic upgrade head && ^
    echo. && ^
    echo ============================================================================ && ^
    echo Backend is running on http://localhost:8000 && ^
    echo API Documentation: http://localhost:8000/api/docs && ^
    echo ============================================================================ && ^
    echo. && ^
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM Wait a moment before starting frontend
timeout /t 3 /nobreak

REM Start Frontend in a new window
echo Starting Frontend (Next.js on port 3000)...
start "Timetable LLM - Frontend" cmd /k ^
    cd /d "%cd%\frontend" && ^
    echo Installing dependencies... && ^
    npm install --silent && ^
    echo. && ^
    echo ============================================================================ && ^
    echo Frontend is running on http://localhost:3000 && ^
    echo ============================================================================ && ^
    echo. && ^
    npm run dev

REM Wait for both to start
timeout /t 2 /nobreak

echo.
echo ============================================================================
echo Services Started!
echo ============================================================================
echo.
echo Frontend:     http://localhost:3000
echo Backend API:  http://localhost:8000
echo API Docs:     http://localhost:8000/api/docs
echo Health Check: http://localhost:8000/health
echo.
echo IMPORTANT: Two new windows have been opened for Backend and Frontend
echo - Close those windows to stop the services
echo - Check those windows for any error messages
echo.
echo Next Steps:
echo 1. Open http://localhost:3000 in your browser
echo 2. Wait for both servers to fully start (~30-60 seconds)
echo 3. If you see errors, check the backend/frontend windows
echo.
echo ============================================================================
echo.
