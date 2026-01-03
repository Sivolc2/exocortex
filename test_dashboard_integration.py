"""Test that dashboard metrics integration is working with real ETL data"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from repo_src.backend.database.connection import SessionLocal
from repo_src.backend.pipelines.dashboard_metrics import compute_dashboard_metrics

async def test_dashboard():
    print("\n" + "="*60)
    print("🧪 TESTING DASHBOARD INTEGRATION")
    print("="*60 + "\n")

    db = SessionLocal()

    try:
        print("📊 Computing dashboard metrics with real ETL data...")
        metrics = await compute_dashboard_metrics(db)

        print(f"\n✅ Dashboard Metrics Computed Successfully!")
        print(f"   Computation time: {metrics.computation_time_ms}ms")
        print(f"   Last updated: {metrics.last_updated}")

        print(f"\n📈 Overview Stats:")
        print(f"   Total Items: {metrics.overview.get('total_items', 0)}")
        print(f"   Total Words: {metrics.overview.get('total_words', 0)}")
        print(f"   Tasks Extracted: {metrics.overview.get('tasks_extracted', 0)}")
        print(f"   Interactions Logged: {metrics.overview.get('interactions_logged', 0)}")
        print(f"   Files Processed: {metrics.overview.get('files_processed', 0)}")

        print(f"\n📋 Recent Tasks (as Highlights):")
        for i, highlight in enumerate(metrics.insights.recent_highlights[:3], 1):
            print(f"   {i}. {highlight.title}")
            print(f"      {highlight.excerpt[:80]}...")
            print(f"      Source: {highlight.source}")
            print()

        print(f"🏷️  Top Topics (from task tags):")
        for topic, score in metrics.insights.top_topics[:5]:
            print(f"   - {topic}: {score:.1%}")

        print(f"\n💡 Knowledge Gaps:")
        for gap in metrics.insights.knowledge_gaps:
            print(f"   - {gap}")

        print(f"\n📊 Trend Data:")
        print(f"   Labels: {metrics.trends.labels}")
        for dataset in metrics.trends.datasets:
            print(f"   {dataset.label}: {dataset.data}")

        print("\n" + "="*60)
        print("✅ DASHBOARD INTEGRATION TEST PASSED")
        print("="*60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_dashboard())
    sys.exit(0 if success else 1)
