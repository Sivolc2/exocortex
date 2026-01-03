#!/bin/bash

cd "$(dirname "$0")"

echo "🔄 Starting Exocortex Backend..."
echo "Working directory: $(pwd)"

# Kill any existing backend
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend
PYTHONPATH="$(pwd):$PYTHONPATH" python -m uvicorn repo_src.backend.main:app --reload --port 8000 &

# Wait for startup
sleep 5

# Test
echo ""
echo "Testing API..."
curl -s 'http://localhost:8000/api/dashboard/metrics?force_refresh=true' | python3 -c "
import sys, json
try:
    d=json.load(sys.stdin)
    o=d['overview']
    print('✅ Backend is running!')
    print(f\"   Tasks: {o.get('tasks_extracted', 0)}\")
    print(f\"   Interactions: {o.get('interactions_logged', 0)}\")
    print(f\"   Files: {o.get('files_processed', 0)}\")
except:
    print('⏳ Backend starting up, wait a moment...')
"

echo ""
echo "Backend running on http://localhost:8000"
echo "Logs: tail -f /tmp/backend_clean.log"
