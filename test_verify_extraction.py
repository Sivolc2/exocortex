"""Quick script to verify the extraction results"""
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from repo_src.backend.database.connection import SessionLocal
from repo_src.backend.database.models import Task, Interaction, DailyMetric, ProcessingLog

def main():
    db = SessionLocal()

    print("\n" + "="*60)
    print("📊 EXTRACTION VERIFICATION")
    print("="*60 + "\n")

    # Check tasks
    tasks = db.query(Task).all()
    print(f"✅ Total Tasks Extracted: {len(tasks)}\n")

    for i, task in enumerate(tasks, 1):
        status_icon = "☑️" if task.status == "done" else "☐"
        print(f"{i}. {status_icon} {task.raw_text}")
        print(f"   Status: {task.status}")
        if task.context_tags:
            print(f"   Tags: {task.context_tags}")
        if task.due_date:
            print(f"   Due: {task.due_date}")
        print()

    # Check interactions
    interactions = db.query(Interaction).all()
    print(f"\n👥 Total Interactions Extracted: {len(interactions)}\n")

    for i, interaction in enumerate(interactions, 1):
        sentiment_emoji = "😊" if interaction.sentiment_score > 30 else "😐" if interaction.sentiment_score > -30 else "😞"
        print(f"{i}. {sentiment_emoji} {interaction.person_name}")
        print(f"   Sentiment: {interaction.sentiment_score}/100")
        if interaction.summary:
            print(f"   Summary: {interaction.summary}")
        print(f"   Date: {interaction.date}")
        print()

    # Check daily metrics
    metrics = db.query(DailyMetric).all()
    print(f"\n📈 Daily Metrics: {len(metrics)}\n")
    for metric in metrics:
        print(f"Date: {metric.date}")
        print(f"  Mood: {metric.mood_score}/100")
        print(f"  Words Written: {metric.words_written}")
        print()

    # Check processing log
    logs = db.query(ProcessingLog).all()
    print(f"\n📋 Processing Logs: {len(logs)}\n")
    for log in logs:
        status_icon = "✅" if log.processing_status == "success" else "❌"
        print(f"{status_icon} {Path(log.file_path).name}")
        print(f"   Status: {log.processing_status}")
        print(f"   Last Processed: {log.last_processed_at}")
        print()

    print("="*60 + "\n")

    db.close()

if __name__ == "__main__":
    main()
