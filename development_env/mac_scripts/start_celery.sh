#!/bin/zsh

# This shell script starts redis-server, activates a Python virtual environment, and runs a Celery worker on macOS

# Set the paths based on your provided information
VENV_PATH="$HOME/codes/sentryHub/venv"
PROJECT_PATH="$HOME/codes/sentryHub/sentryHub"

# --- Start Redis Server ---
echo "Checking for redis-server..."
if ! command -v redis-server &> /dev/null; then
    echo "Error: redis-server not found. Please install Redis using 'brew install redis'."
    exit 1
fi

echo "Starting redis-server in the background..."
redis-server --daemonize yes
if [ $? -ne 0 ]; then
    echo "Error: Failed to start redis-server."
    exit 1
fi

# Get the Redis server PID (most recent redis-server process)
REDIS_PID=$(pgrep -u $USER redis-server)
if [ -z "$REDIS_PID" ]; then
    echo "Error: Could not find redis-server process ID."
    exit 1
fi
echo "redis-server started with PID $REDIS_PID"

# Function to stop redis-server
stop_redis() {
    if [ -n "$REDIS_PID" ]; then
        echo "Stopping redis-server (PID $REDIS_PID)..."
        redis-cli shutdown
        if [ $? -eq 0 ]; then
            echo "redis-server stopped successfully."
        else
            echo "Error: Failed to stop redis-server."
        fi
    fi
}

# Trap script exit (normal exit, Ctrl+C, or errors) to stop redis-server
trap stop_redis EXIT INT TERM

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
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: VIRTUAL_ENV variable not set. Activation might have failed."
fi

# Navigate to the project directory
echo "Navigating to project directory..."
cd "$PROJECT_PATH"

# Check if navigation was successful
if [ $? -ne 0 ]; then
    echo "Failed to navigate to project directory: $PROJECT_PATH"
    exit 1
fi

# Run the Celery worker
echo "Running Celery worker..."
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