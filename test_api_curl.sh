#!/bin/bash

echo "============================================================"
echo "🧪 TESTING INSIGHTS API ENDPOINTS WITH CURL"
echo "============================================================"
echo ""

BASE_URL="http://localhost:8000"

echo "📋 Test 1: GET /api/insights/tasks"
curl -s "$BASE_URL/api/insights/tasks" | jq '.[:2] | .[] | {raw_text, status, context_tags}' 2>/dev/null || echo "Server not running or jq not installed"
echo ""

echo "📊 Test 2: GET /api/insights/tasks/stats"
curl -s "$BASE_URL/api/insights/tasks/stats" | jq '.' 2>/dev/null || echo "Server not running"
echo ""

echo "👥 Test 3: GET /api/insights/interactions"
curl -s "$BASE_URL/api/insights/interactions" | jq '.[] | {person_name, sentiment_score, summary}' 2>/dev/null || echo "Server not running"
echo ""

echo "🔍 Test 4: GET /api/insights/interactions/people"
curl -s "$BASE_URL/api/insights/interactions/people" | jq '.' 2>/dev/null || echo "Server not running"
echo ""

echo "📈 Test 5: GET /api/insights/metrics/daily"
curl -s "$BASE_URL/api/insights/metrics/daily" | jq '.' 2>/dev/null || echo "Server not running"
echo ""

echo "📊 Test 6: GET /api/insights/metrics/summary"
curl -s "$BASE_URL/api/insights/metrics/summary?days=30" | jq '.' 2>/dev/null || echo "Server not running"
echo ""

echo "🔄 Test 7: GET /api/insights/processing/stats"
curl -s "$BASE_URL/api/insights/processing/stats" | jq '.' 2>/dev/null || echo "Server not running"
echo ""

echo "============================================================"
echo "✅ API TESTS COMPLETE"
echo "============================================================"
