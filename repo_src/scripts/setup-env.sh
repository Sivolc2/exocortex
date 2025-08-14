#!/bin/bash

# Parse command line arguments
FORCE_MODE=false
if [[ "$1" == "-f" || "$1" == "--force" ]]; then
    FORCE_MODE=true
    echo "Force mode enabled: will overwrite existing files"
fi

echo "Setting up environment files..."

# Define backend .env directory and file
BACKEND_ENV_DIR="repo_src/backend"
BACKEND_ENV_FILE="${BACKEND_ENV_DIR}/.env"

# Define frontend .env directory and file
FRONTEND_ENV_DIR="repo_src/frontend"
FRONTEND_ENV_FILE="${FRONTEND_ENV_DIR}/.env"

# Create backend .env file with default environment variables
if [ ! -f "$BACKEND_ENV_FILE" ] || [ "$FORCE_MODE" = true ]; then
    if [ "$FORCE_MODE" = true ] && [ -f "$BACKEND_ENV_FILE" ]; then
        echo "Overwriting ${BACKEND_ENV_FILE} with default environment variables..."
    else
        echo "Creating ${BACKEND_ENV_FILE} with default environment variables..."
    fi

    cat > "$BACKEND_ENV_FILE" << EOF
# Database configuration
DATABASE_URL=sqlite:///./app_dev.db

# API settings
PORT=8000
LOG_LEVEL=info

# --- OpenRouter Configuration ---
# Get your key from https://openrouter.ai/keys
OPENROUTER_API_KEY="sk-or-v1-..."

# Recommended model. See https://openrouter.ai/models for more.
OPENROUTER_MODEL_NAME="anthropic/claude-3.5-sonnet"

# Optional: For OpenRouter analytics/tracking
YOUR_SITE_URL="http://localhost:5173"
YOUR_APP_NAME="AI-Friendly Repo Chat"

# --- Data Source API Keys (Optional) ---
# Get your key from https://www.notion.so/my-integrations
NOTION_API_KEY="secret_..."

# Get your bot token from the Discord Developer Portal
DISCORD_BOT_TOKEN="your_discord_bot_token_here"
EOF

    echo "${BACKEND_ENV_FILE} created."
else
    echo "${BACKEND_ENV_FILE} already exists. Skipping."
fi

# Create or update frontend .env file with default environment variables
if [ ! -f "$FRONTEND_ENV_FILE" ] || [ "$FORCE_MODE" = true ]; then
    if [ "$FORCE_MODE" = true ] && [ -f "$FRONTEND_ENV_FILE" ]; then
        echo "Overwriting ${FRONTEND_ENV_FILE} with default environment variables..."
    else
        echo "Creating ${FRONTEND_ENV_FILE} with default environment variables..."
    fi
    cat > "$FRONTEND_ENV_FILE" << EOF
# API URL (for direct API calls, not via proxy)
VITE_API_URL=http://localhost:8000
EOF
    
    echo "${FRONTEND_ENV_FILE} created."
else
    echo "${FRONTEND_ENV_FILE} already exists. Skipping."
fi

echo "Environment file setup complete."
echo "Please review the .env files in ${BACKEND_ENV_DIR} and ${FRONTEND_ENV_DIR} and customize if necessary."
echo "IMPORTANT: You must add your OPENROUTER_API_KEY to repo_src/backend/.env for the chat to work."
echo ""
echo "Usage: $0 [-f|--force]"
echo "  -f, --force    Overwrite existing .env files"