#!/bin/zsh

# macOS Shell Script to Activate Virtual Environment and Run Django Server
# -----------------------------------------------------------------------
# This script automates the process of starting the Django development server
# for a project on macOS using the zsh shell.

# --- Configuration ---
# Set the path to your virtual environment's root directory
# Uses $HOME which represents the current user's home directory
VENV_PATH="$HOME/codes/sentryHub/venv"

# Set the path to your Django project directory (where manage.py is located)
PROJECT_PATH="$HOME/codes/sentryHub/sentryHub"
# --- End Configuration ---


# --- Script Execution ---
echo "Starting Django development server setup..."

# 1. Check if Virtual Environment Activation Script Exists
# -------------------------------------------------------
ACTIVATE_SCRIPT="$VENV_PATH/bin/activate"
if [ ! -f "$ACTIVATE_SCRIPT" ]; then
  echo "Error: Virtual environment activation script not found!"
  echo "Expected location: $ACTIVATE_SCRIPT"
  exit 1 # Exit with a non-zero status code indicating failure
fi
echo "Found virtual environment activation script."

# 2. Activate Virtual Environment
# -------------------------------
echo "Activating virtual environment..."
source "$ACTIVATE_SCRIPT"

# Optional: Check if activation seems successful by checking the VIRTUAL_ENV variable
if [ -z "$VIRTUAL_ENV" ]; then
    # Note: This check isn't foolproof but often works.
    echo "Warning: VIRTUAL_ENV environment variable not set after activation."
    echo "Activation might have failed silently. Proceeding with caution..."
fi

# 3. Check if Project Directory Exists
# ------------------------------------
if [ ! -d "$PROJECT_PATH" ]; then
  echo "Error: Project directory not found!"
  echo "Expected location: $PROJECT_PATH"
  exit 1 # Exit with failure status
fi
echo "Found project directory."

# 4. Check if manage.py Exists in Project Directory
# -------------------------------------------------
MANAGE_PY_PATH="$PROJECT_PATH/manage.py"
if [ ! -f "$MANAGE_PY_PATH" ]; then
  echo "Error: manage.py not found in project directory!"
  echo "Expected location: $MANAGE_PY_PATH"
  exit 1 # Exit with failure status
fi
echo "Found manage.py."


# 5. Navigate to Project Directory
# --------------------------------
echo "Navigating to project directory: $PROJECT_PATH"
cd "$PROJECT_PATH"

# Check if navigation was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to navigate to project directory!"
    exit 1 # Exit with failure status
fi
echo "Successfully changed directory."

# 6. Run Django Development Server
# --------------------------------
echo "Starting Django development server..."
echo "Command: python manage.py runserver"
echo "(Server will run on http://127.0.0.1:8000/ by default)"
echo "(Press Ctrl+C to stop the server)"

# Execute the Django runserver command. The script will wait here until the server stops.
python manage.py runserver

# Capture the exit code of the runserver command
SERVER_EXIT_CODE=$?

# 7. Report Final Status
# ----------------------
# This part will only be reached after the server process terminates (e.g., via Ctrl+C).
if [ $SERVER_EXIT_CODE -ne 0 ]; then
    echo "Django server exited with error code: $SERVER_EXIT_CODE."
    exit $SERVER_EXIT_CODE # Exit the script with the server's error code
else
    echo "Django server stopped successfully (exit code 0)."
    exit 0 # Exit the script successfully
fi

# --- End Script Execution ---
