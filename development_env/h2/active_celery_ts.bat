@echo off
rem This batch file activates a Python virtual environment and runs a Celery worker

rem Set the paths based on your provided information
set VENV_PATH=D:\codes\sentryHub\venv311
set PROJECT_PATH=D:\codes\sentryHub\sentryHub

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

rem Run the Celery worker
echo Running Celery worker...
celery -A sentryHub worker --loglevel=info

rem Keep the window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo An error occurred while running the Celery worker.
    pause
    exit /b %ERRORLEVEL%
)

echo Process completed successfully.