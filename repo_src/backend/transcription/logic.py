import os
from pathlib import Path
from datetime import datetime

TRANSCRIPTS_DIR = Path(__file__).parent.parent / "transcripts"

def save_transcript(text: str):
    """
    Saves the transcribed text by appending to a daily file.
    """
    # Ensure the transcripts directory exists
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)

    # Create a filename based on the current date
    today_str = datetime.now().strftime('%Y-%m-%d')
    file_path = TRANSCRIPTS_DIR / f"transcript_{today_str}.md"

    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Append the new transcript with a timestamp and separators
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n\n**Timestamp: {timestamp_str}**\n\n{text}")

    print(f"Transcript appended to {file_path}") 