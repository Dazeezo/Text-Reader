@echo off
setlocal

cd /d "%~dp0"

echo Text Reader - Installing dependencies
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH.
    echo Install Python 3 from https://www.python.org/downloads/ ^(check "Add python.exe to PATH"^) and run this script again.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists, reusing it.
)

echo.
echo Installing packages from requirements.txt...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Dependency installation failed. See the errors above.
    pause
    exit /b 1
)

echo.
echo Done. Double-click TextReader.bat to launch the app.
pause
