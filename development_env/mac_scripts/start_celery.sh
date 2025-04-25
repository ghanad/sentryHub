#!/bin/zsh

# This shell script activates a Python virtual environment and runs a Celery worker on macOS

# Set the paths based on your provided information
VENV_PATH="$HOME/codes/sentryHub/venv"
PROJECT_PATH="$HOME/codes/sentryHub/sentryHub"

# --- Basic Checks ---
# Check if venv activation script exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo "Error: Virtual environment activation script not found at $VENV_PATH/bin/activate"
  exit 1
fi

# Check if project directory exists
if [ ! -d "$PROJECT_PATH" ]; then
  echo "Error: Project directory not found at $PROJECT_PATH"
  exit 1
fi
# --- End Basic Checks ---


# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Check if virtual environment was activated successfully
# Note: The 'source' command itself doesn't always set $? reliably on failure in all shells/cases.
# A common check is to see if a command from the venv is now available, like 'python' or 'pip'.
# We'll primarily rely on the subsequent cd and celery commands failing if activation didn't work.
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: VIRTUAL_ENV variable not set. Activation might have failed."
    # You could add a stricter check here if needed, e.g., checking `which python`
fi


# Navigate to the project directory
echo "Navigating to project directory..."
cd "$PROJECT_PATH"

# Check if navigation was successful
if [ $? -ne 0 ]; then
    echo "Failed to navigate to project directory: $PROJECT_PATH"
    exit 1 # Exit with a non-zero status code
fi


# Run the Celery worker
echo "Running Celery worker..."
# The '-A sentryHub' assumes your Celery app instance is discoverable via 'sentryHub'.
# Make sure this matches your Django project structure and Celery configuration.
celery -A sentryHub worker --loglevel=info -P solo

# Capture the exit code after Celery stops/exits
CELERY_EXIT_CODE=$?

# Report final status based on Celery's exit code
if [ $CELERY_EXIT_CODE -ne 0 ]; then
    echo "Celery worker exited with error code $CELERY_EXIT_CODE."
    exit $CELERY_EXIT_CODE
else
    echo "Celery worker finished successfully."
    exit 0
fi