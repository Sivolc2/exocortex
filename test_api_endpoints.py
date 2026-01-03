"""Test the insights API endpoints"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from repo_src.backend.main import app

def test_insights_api():
    client = TestClient(app)

    print("\n" + "="*60)
    print("🧪 TESTING INSIGHTS API ENDPOINTS")
    print("="*60 + "\n")

    # Test 1: Get all tasks
    print("📋 Test 1: GET /api/insights/tasks")
    response = client.get("/api/insights/tasks")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        tasks = response.json()
        print(f"   ✅ Retrieved {len(tasks)} tasks")
        if tasks:
            print(f"   Sample: {tasks[0]['raw_text']}")
    print()

    # Test 2: Get open tasks only
    print("📋 Test 2: GET /api/insights/tasks?status=open")
    response = client.get("/api/insights/tasks?status=open")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        open_tasks = response.json()
        print(f"   ✅ Retrieved {len(open_tasks)} open tasks")
    print()

    # Test 3: Get task statistics
    print("📊 Test 3: GET /api/insights/tasks/stats")
    response = client.get("/api/insights/tasks/stats")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✅ Stats: {stats}")
    print()

    # Test 4: Get all interactions
    print("👥 Test 4: GET /api/insights/interactions")
    response = client.get("/api/insights/interactions")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        interactions = response.json()
        print(f"   ✅ Retrieved {len(interactions)} interactions")
        if interactions:
            print(f"   Sample: {interactions[0]['person_name']} (sentiment: {interactions[0]['sentiment_score']})")
    print()

    # Test 5: Get people with last interaction
    print("🔍 Test 5: GET /api/insights/interactions/people")
    response = client.get("/api/insights/interactions/people")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        people = response.json()
        print(f"   ✅ Retrieved {len(people)} people")
        for person in people:
            print(f"   - {person['person_name']}: {person['days_since']} days ago")
    print()

    # Test 6: Get daily metrics
    print("📈 Test 6: GET /api/insights/metrics/daily")
    response = client.get("/api/insights/metrics/daily")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        metrics = response.json()
        print(f"   ✅ Retrieved {len(metrics)} daily metrics")
        if metrics:
            print(f"   Sample: {metrics[0]['date']} - Mood: {metrics[0]['mood_score']}")
    print()

    # Test 7: Get metrics summary
    print("📊 Test 7: GET /api/insights/metrics/summary")
    response = client.get("/api/insights/metrics/summary?days=30")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        summary = response.json()
        print(f"   ✅ Summary: {summary}")
    print()

    # Test 8: Get processing status
    print("🔄 Test 8: GET /api/insights/processing/status")
    response = client.get("/api/insights/processing/status")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        status = response.json()
        print(f"   ✅ Retrieved {len(status)} processing logs")
    print()

    # Test 9: Get processing stats
    print("📊 Test 9: GET /api/insights/processing/stats")
    response = client.get("/api/insights/processing/stats")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✅ Stats: {stats}")
    print()

    print("="*60)
    print("✅ ALL API TESTS COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_insights_api()
