"""
Reflector Pipeline - ETL for extracting structured entities from markdown files.

This pipeline implements the "Silver Layer" transformation:
- Bronze Layer: Raw markdown files (immutable)
- Silver Layer: Structured entities (tasks, interactions, metrics) in SQLite
- Gold Layer: Aggregated insights and dashboards (computed from Silver)

Usage:
    python -m repo_src.backend.pipelines.reflect --path /path/to/markdown/dir
"""

import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from repo_src.backend.database.connection import SessionLocal, engine
from repo_src.backend.database.models import Task, Interaction, DailyMetric, ProcessingLog
from repo_src.backend.functions.extractors import (
    extract_all_entities,
    generate_content_hash,
    generate_entity_id
)


def get_markdown_files(base_path: Path, pattern: str = "**/*.md") -> List[Path]:
    """
    Find all markdown files in the given directory.

    Args:
        base_path: Root directory to search
        pattern: Glob pattern for matching files

    Returns:
        List of Path objects for markdown files
    """
    if not base_path.exists():
        print(f"Warning: Path does not exist: {base_path}")
        return []

    return list(base_path.glob(pattern))


def get_files_to_process(db: Session, markdown_files: List[Path]) -> List[Path]:
    """
    Determine which files need processing based on content hash changes.

    Args:
        db: Database session
        markdown_files: List of markdown file paths

    Returns:
        List of files that are new or have changed since last processing
    """
    files_to_process = []

    for file_path in markdown_files:
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            current_hash = generate_content_hash(content)

            # Check if file was processed before
            log_entry = db.query(ProcessingLog).filter(
                ProcessingLog.file_path == str(file_path)
            ).first()

            if not log_entry or log_entry.content_hash != current_hash:
                files_to_process.append(file_path)
                print(f"✓ Will process: {file_path.name} (new or changed)")
            else:
                print(f"⊘ Skipping: {file_path.name} (already processed)")

        except Exception as e:
            print(f"Error checking file {file_path}: {e}")
            continue

    return files_to_process


async def process_file(db: Session, file_path: Path) -> bool:
    """
    Process a single markdown file: extract entities and store in database.

    Args:
        db: Database session
        file_path: Path to markdown file

    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        print(f"\n📄 Processing: {file_path.name}")

        # Read file content
        content = file_path.read_text(encoding='utf-8')
        content_hash = generate_content_hash(content)

        # Try to extract date from filename or use file modification time
        source_date = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Extract all entities using LLM
        print(f"   Extracting entities...")
        entities = await extract_all_entities(
            content=content,
            source_file_path=str(file_path),
            source_date=source_date
        )

        # Store tasks
        print(f"   Found {len(entities.tasks)} tasks")
        for task_data in entities.tasks:
            task_id = generate_entity_id("task", str(file_path), task_data.raw_text)

            # Check if task already exists
            existing_task = db.query(Task).filter(Task.id == task_id).first()

            if existing_task:
                # Update existing task
                existing_task.status = task_data.status
                existing_task.due_date = task_data.due_date
                existing_task.context_tags = task_data.context_tags
                existing_task.updated_at = datetime.now()
            else:
                # Create new task
                task = Task(
                    id=task_id,
                    source_file_path=task_data.source_file_path,
                    raw_text=task_data.raw_text,
                    status=task_data.status,
                    due_date=task_data.due_date,
                    context_tags=task_data.context_tags,
                    extracted_at=datetime.now()
                )
                db.add(task)

        # Store interactions
        print(f"   Found {len(entities.interactions)} interactions")
        for interaction_data in entities.interactions:
            interaction_id = generate_entity_id(
                "interaction",
                str(file_path),
                f"{interaction_data.person_name}:{interaction_data.summary or ''}"
            )

            # Check if interaction already exists
            existing_interaction = db.query(Interaction).filter(
                Interaction.id == interaction_id
            ).first()

            if not existing_interaction:
                interaction = Interaction(
                    id=interaction_id,
                    person_name=interaction_data.person_name,
                    date=interaction_data.date,
                    sentiment_score=interaction_data.sentiment_score,
                    summary=interaction_data.summary,
                    source_file_path=interaction_data.source_file_path
                )
                db.add(interaction)

        # Update daily metrics if sentiment was extracted
        if entities.sentiment_score is not None:
            date_str = source_date.strftime("%Y-%m-%d")
            daily_metric = db.query(DailyMetric).filter(
                DailyMetric.date == date_str
            ).first()

            if daily_metric:
                # Update existing metric (average sentiment)
                daily_metric.mood_score = entities.sentiment_score
                daily_metric.updated_at = datetime.now()
            else:
                # Create new daily metric
                daily_metric = DailyMetric(
                    date=date_str,
                    mood_score=entities.sentiment_score,
                    tasks_completed=0,
                    words_written=len(content.split()),
                    meetings_recorded=0
                )
                db.add(daily_metric)

        # Update processing log
        log_entry = db.query(ProcessingLog).filter(
            ProcessingLog.file_path == str(file_path)
        ).first()

        if log_entry:
            log_entry.content_hash = content_hash
            log_entry.last_processed_at = datetime.now()
            log_entry.processing_status = "success"
            log_entry.error_message = None
        else:
            log_entry = ProcessingLog(
                file_path=str(file_path),
                content_hash=content_hash,
                processing_status="success"
            )
            db.add(log_entry)

        # Commit all changes
        db.commit()
        print(f"   ✅ Successfully processed {file_path.name}")
        return True

    except Exception as e:
        print(f"   ❌ Error processing {file_path.name}: {e}")
        db.rollback()

        # Log the error
        log_entry = db.query(ProcessingLog).filter(
            ProcessingLog.file_path == str(file_path)
        ).first()

        if log_entry:
            log_entry.processing_status = "failed"
            log_entry.error_message = str(e)
        else:
            log_entry = ProcessingLog(
                file_path=str(file_path),
                content_hash="",
                processing_status="failed",
                error_message=str(e)
            )
            db.add(log_entry)

        db.commit()
        return False


async def run_reflector_pipeline(
    base_path: Optional[Path] = None,
    max_files: Optional[int] = None,
    force: bool = False
) -> dict:
    """
    Main entry point for the reflector pipeline.

    Args:
        base_path: Directory containing markdown files (default: processed/current/)
        max_files: Maximum number of files to process (for testing)
        force: If True, reprocess all files regardless of hash

    Returns:
        Dictionary with processing statistics
    """
    # Default to processed/current directory
    if base_path is None:
        project_root = Path(__file__).parent.parent.parent.parent
        base_path = project_root / "processed" / "current"

    print(f"\n{'='*60}")
    print(f"🔮 REFLECTOR PIPELINE - ETL for Exocortex")
    print(f"{'='*60}")
    print(f"Source: {base_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Get database session
    db = SessionLocal()

    try:
        # Find all markdown files
        print("🔍 Scanning for markdown files...")
        markdown_files = get_markdown_files(base_path)
        print(f"   Found {len(markdown_files)} markdown files\n")

        if not markdown_files:
            print("No markdown files found. Exiting.")
            return {
                "total_files": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 0
            }

        # Determine which files need processing
        if force:
            files_to_process = markdown_files
            print("⚠️  Force mode: processing all files\n")
        else:
            print("📊 Checking which files need processing...")
            files_to_process = get_files_to_process(db, markdown_files)
            print(f"\n   {len(files_to_process)} files need processing")
            print(f"   {len(markdown_files) - len(files_to_process)} files up to date\n")

        # Limit files if requested
        if max_files and len(files_to_process) > max_files:
            print(f"⚠️  Limiting to {max_files} files (testing mode)\n")
            files_to_process = files_to_process[:max_files]

        # Process each file
        success_count = 0
        error_count = 0

        for file_path in files_to_process:
            success = await process_file(db, file_path)
            if success:
                success_count += 1
            else:
                error_count += 1

        # Print summary
        print(f"\n{'='*60}")
        print(f"✨ PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total files scanned: {len(markdown_files)}")
        print(f"Files processed: {success_count}")
        print(f"Files skipped: {len(markdown_files) - len(files_to_process)}")
        print(f"Errors: {error_count}")
        print(f"{'='*60}\n")

        return {
            "total_files": len(markdown_files),
            "processed": success_count,
            "skipped": len(markdown_files) - len(files_to_process),
            "errors": error_count
        }

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Reflector ETL pipeline")
    parser.add_argument(
        "--path",
        type=str,
        help="Path to markdown directory (default: processed/current/)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum number of files to process (for testing)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing of all files"
    )

    args = parser.parse_args()

    base_path = Path(args.path) if args.path else None

    # Run the pipeline
    result = asyncio.run(run_reflector_pipeline(
        base_path=base_path,
        max_files=args.max_files,
        force=args.force
    ))
