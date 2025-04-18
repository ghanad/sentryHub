@echo off
rem This batch file activates a Python virtual environment and runs the Django development server

rem Set the paths based on your provided information
set VENV_PATH=C:\codes\python_codes\prometheus_alerts\venv
set PROJECT_PATH=C:\codes\python_codes\prometheus_alerts\sentryHub

rem Activate the virtual environment
echo Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

rem Check if virtual environment was activated successfully
if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment!
    pause
    exit /b %ERRORLEVEL%
)

rem Navigate to the project directory
echo Navigating to project directory...
cd /d "%PROJECT_PATH%"

rem Run the Django development server
echo Starting Django development server...
python manage.py shell

rem Keep the window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo An error occurred while running the Django server.
    pause
    exit /b %ERRORLEVEL%
)

echo Django server stopped.