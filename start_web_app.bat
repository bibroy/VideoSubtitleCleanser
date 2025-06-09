@echo off
setlocal enabledelayedexpansion

echo ===============================================================
echo VideoSubtitleCleanser Web Application
echo ===============================================================
echo.
echo This will start the web server and open your browser.
echo Press Ctrl+C in this window to stop the server when done.
echo.

:: Set the absolute paths
set "PROJECT_ROOT=%~dp0"
set "VENV_PATH=%PROJECT_ROOT%.venv"
set "PYTHON_EXE=%VENV_PATH%\Scripts\python.exe"
set "WEB_SERVER=%PROJECT_ROOT%web_server.py"

:: Create necessary directories
if not exist "%PROJECT_ROOT%uploads" mkdir "%PROJECT_ROOT%uploads"
if not exist "%PROJECT_ROOT%outputs" mkdir "%PROJECT_ROOT%outputs"

echo Checking environment...

:: Check if virtual environment exists
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Error: Virtual environment not found at .venv
    echo Please create a virtual environment with: python -m venv .venv
    echo Then install requirements with: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

:: Start the web server (browser will open automatically)
echo Starting web server on http://localhost:5000
echo.
"%PYTHON_EXE%" "%WEB_SERVER%"

if %errorlevel% neq 0 (
    echo.
    echo Error: Web server failed to start or was terminated unexpectedly
    echo Check the error message above for details
    pause
    exit /b 1
)

pause
