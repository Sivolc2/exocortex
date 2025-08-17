import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
TODOS_FILE_PATH = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed" / "current" / "obsidian" / "GENERATED_TODOS.md"

def save_todo_list(content: str) -> str:
    """
    Saves the generated to-do list to a specific file.

    Args:
        content: The markdown content of the to-do list.

    Returns:
        The path to the saved file as a string.
    """
    try:
        # Ensure the directory exists
        TODOS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        header = f"# To-Do List\n\n*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        full_content = header + content

        TODOS_FILE_PATH.write_text(full_content, encoding='utf-8')
        return str(TODOS_FILE_PATH)
    except Exception as e:
        print(f"Error saving to-do list: {e}")
        raise