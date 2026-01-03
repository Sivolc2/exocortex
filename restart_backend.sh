#!/bin/bash

echo "🔄 Restarting backend to load new dashboard code..."

# Kill existing uvicorn processes
pkill -f "uvicorn.*main:app" || echo "No existing backend found"

sleep 1

# Start backend
cd repo_src/backend
echo "Starting backend on port 8000..."
python -m uvicorn main:app --reload --port 8000 &

sleep 3

# Test the API
echo ""
echo "Testing dashboard API..."
curl -s http://localhost:8000/api/dashboard/metrics | python -c "
import sys, json
data=json.load(sys.stdin)
print('✅ Tasks:', data['overview'].get('tasks_extracted', 0))
print('✅ Interactions:', data['overview'].get('interactions_logged', 0))
print('✅ Files:', data['overview'].get('files_processed', 0))
" || echo "❌ API not responding yet, wait a moment and refresh browser"

echo ""
echo "Backend ready! Refresh your browser dashboard."
