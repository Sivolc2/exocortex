"""
Entity extraction functions for converting markdown documents into structured data.
These are pure functions that take text and return structured entities (Tasks, People, etc.)
"""

import json
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

from repo_src.backend.llm_chat.llm_interface import ask_llm
from repo_src.backend.data.schemas import TaskCreate, InteractionCreate, ExtractedEntities


def generate_content_hash(content: str) -> str:
    """Generate a SHA256 hash of the content for change detection."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_entity_id(prefix: str, source_path: str, text: str) -> str:
    """Generate a unique ID for an entity based on its content and source."""
    unique_string = f"{source_path}:{text}"
    hash_suffix = hashlib.md5(unique_string.encode('utf-8')).hexdigest()[:8]
    return f"{prefix}_{hash_suffix}"


async def extract_tasks(content: str, source_file_path: str) -> List[TaskCreate]:
    """
    Pure function: Extracts actionable tasks from markdown content using LLM.

    Args:
        content: The markdown text to analyze
        source_file_path: Path to the source file (for tracking)

    Returns:
        List of TaskCreate objects representing extracted tasks
    """
    system_message = """You are a task extraction assistant. Your job is to identify actionable tasks from text.
Extract tasks that are:
- Explicit TODO items (like "- [ ] Buy milk")
- Implicit action items (like "Need to fix the bug" or "Should call John")
- Commitments made in conversations (like "I'll send the email" or "Bob will review the code")

For each task, determine:
- raw_text: The task description
- status: "open" for uncompleted tasks, "done" for completed tasks (checked boxes), "waiting" for tasks waiting on others
- due_date: If a specific date is mentioned (format: YYYY-MM-DD), otherwise null
- context_tags: Relevant tags or categories (comma-separated, e.g., "work,email" or "home,shopping")

Return ONLY a JSON array of tasks. Example:
[
  {
    "raw_text": "Buy milk",
    "status": "open",
    "due_date": null,
    "context_tags": "home,shopping"
  },
  {
    "raw_text": "Send project update to team",
    "status": "open",
    "due_date": "2024-01-15",
    "context_tags": "work,email"
  }
]

If no tasks are found, return an empty array: []
"""

    prompt = f"""Analyze this document and extract all actionable tasks:

--- DOCUMENT START ---
{content}
--- DOCUMENT END ---

Return the tasks as a JSON array as specified."""

    try:
        response = await ask_llm(prompt, system_message, model_override="anthropic/claude-3.5-haiku")

        # Try to parse the JSON response
        # The LLM might wrap it in markdown code blocks
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()

        tasks_data = json.loads(response_clean)

        # Convert to TaskCreate objects
        tasks = []
        for task_dict in tasks_data:
            # Generate a unique ID for this task
            task_id = generate_entity_id("task", source_file_path, task_dict["raw_text"])

            # Parse due_date if present
            due_date = None
            if task_dict.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(task_dict["due_date"])
                except:
                    pass

            task = TaskCreate(
                source_file_path=source_file_path,
                raw_text=task_dict["raw_text"],
                status=task_dict.get("status", "open"),
                due_date=due_date,
                context_tags=task_dict.get("context_tags")
            )
            tasks.append(task)

        return tasks

    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        print(f"Response was: {response}")
        return []
    except Exception as e:
        print(f"Error extracting tasks: {e}")
        return []


async def extract_interactions(content: str, source_file_path: str, source_date: Optional[datetime] = None) -> List[InteractionCreate]:
    """
    Pure function: Extracts social interactions and people mentions from content.

    Args:
        content: The markdown text to analyze
        source_file_path: Path to the source file
        source_date: Date of the interaction (falls back to file metadata or current date)

    Returns:
        List of InteractionCreate objects
    """
    system_message = """You are a social interaction analyzer. Extract information about interactions with people.

Look for:
- Names of people mentioned or conversed with
- The nature of the interaction (meeting, email, chat, call)
- Sentiment of the interaction (-100 to 100, where -100 is very negative, 0 is neutral, 100 is very positive)
- A brief summary of the interaction

Return ONLY a JSON array of interactions. Example:
[
  {
    "person_name": "John Smith",
    "sentiment_score": 75,
    "summary": "Had a productive meeting about the Q1 roadmap. John is excited about the new features."
  },
  {
    "person_name": "Sarah Chen",
    "sentiment_score": -20,
    "summary": "Discussed the bug in production. Sarah is frustrated with the delays."
  }
]

If no interactions are found, return: []
"""

    prompt = f"""Analyze this document and extract social interactions:

--- DOCUMENT START ---
{content}
--- DOCUMENT END ---

Return the interactions as a JSON array."""

    try:
        response = await ask_llm(prompt, system_message, model_override="anthropic/claude-3.5-haiku")

        # Clean and parse response
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()

        interactions_data = json.loads(response_clean)

        # Use source_date if provided, otherwise use current time
        interaction_date = source_date or datetime.now()

        # Convert to InteractionCreate objects
        interactions = []
        for interaction_dict in interactions_data:
            interaction_id = generate_entity_id(
                "interaction",
                source_file_path,
                f"{interaction_dict['person_name']}:{interaction_dict.get('summary', '')}"
            )

            interaction = InteractionCreate(
                person_name=interaction_dict["person_name"],
                date=interaction_date,
                sentiment_score=interaction_dict.get("sentiment_score", 0),
                summary=interaction_dict.get("summary"),
                source_file_path=source_file_path
            )
            interactions.append(interaction)

        return interactions

    except json.JSONDecodeError as e:
        print(f"Error parsing interactions JSON: {e}")
        print(f"Response was: {response}")
        return []
    except Exception as e:
        print(f"Error extracting interactions: {e}")
        return []


async def extract_sentiment(content: str) -> int:
    """
    Pure function: Extracts overall sentiment/mood from content.

    Args:
        content: The markdown text to analyze

    Returns:
        Sentiment score from -100 (very negative) to 100 (very positive)
    """
    system_message = """You are a sentiment analyzer. Analyze the overall emotional tone and mood of the text.

Return ONLY a single integer between -100 and 100:
- -100 to -50: Very negative (anger, sadness, frustration, despair)
- -50 to -1: Somewhat negative (disappointment, worry, stress)
- 0: Neutral (factual, balanced, no strong emotion)
- 1 to 50: Somewhat positive (satisfied, hopeful, content)
- 50 to 100: Very positive (joy, excitement, enthusiasm, gratitude)

Return ONLY the number, nothing else. Example responses: 75, -30, 0"""

    prompt = f"""Analyze the sentiment of this text:

--- TEXT START ---
{content}
--- TEXT END ---

Return only the sentiment score as a number."""

    try:
        response = await ask_llm(prompt, system_message, model_override="anthropic/claude-3.5-haiku")
        score = int(response.strip())
        # Clamp to valid range
        return max(-100, min(100, score))
    except Exception as e:
        print(f"Error extracting sentiment: {e}")
        return 0  # Default to neutral


async def extract_people_mentions(content: str) -> List[str]:
    """
    Pure function: Extracts names of people mentioned in the content.

    Args:
        content: The markdown text to analyze

    Returns:
        List of person names
    """
    system_message = """You are a named entity extractor. Extract all person names mentioned in the text.

Return ONLY a JSON array of person names. Example:
["John Smith", "Sarah Chen", "Dr. Maria Rodriguez"]

If no people are mentioned, return: []"""

    prompt = f"""Extract all person names from this text:

--- TEXT START ---
{content}
--- TEXT END ---

Return only the JSON array of names."""

    try:
        response = await ask_llm(prompt, system_message, model_override="anthropic/claude-3.5-haiku")

        # Clean response
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()

        people = json.loads(response_clean)
        return people if isinstance(people, list) else []

    except Exception as e:
        print(f"Error extracting people: {e}")
        return []


async def extract_all_entities(content: str, source_file_path: str, source_date: Optional[datetime] = None) -> ExtractedEntities:
    """
    High-level function: Extracts all entities from a document in a single pass.

    Args:
        content: The markdown text to analyze
        source_file_path: Path to the source file
        source_date: Date associated with the content

    Returns:
        ExtractedEntities object containing all extracted data
    """
    # Extract all entities concurrently would be ideal, but for now we'll do sequentially
    tasks = await extract_tasks(content, source_file_path)
    interactions = await extract_interactions(content, source_file_path, source_date)
    sentiment = await extract_sentiment(content)
    people = await extract_people_mentions(content)

    return ExtractedEntities(
        tasks=tasks,
        interactions=interactions,
        sentiment_score=sentiment,
        people_mentioned=people
    )
