import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Any, Dict
from sqlalchemy.orm import Session

from repo_src.backend.llm_chat.llm_interface import ask_llm
from repo_src.backend.database.models import IndexEntry

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DOCUMENTS_DIR = PROJECT_ROOT / "repo_src" / "backend" / "data" / "processed" / "current"

def _get_current_datetime() -> str:
    """Get the current date and time formatted for system prompts"""
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

def _estimate_token_count(text: str) -> int:
    """
    Estimates the number of tokens in a text string using a simple heuristic.
    
    This is a rough approximation based on word count and punctuation.
    For more accurate counting, you could use tiktoken or similar libraries.
    
    Args:
        text: The text to estimate tokens for
        
    Returns:
        Estimated number of tokens
    """
    # Split by whitespace to get word count
    words = text.split()
    word_count = len(words)
    
    # Rough approximation: average English word is about 1.3 tokens
    # Add extra for punctuation and special characters
    token_estimate = int(word_count * 1.3)
    
    # Add small buffer for formatting, markdown, etc.
    return int(token_estimate * 1.1)

def _get_project_file_tree(enabled_sources: Optional[dict] = None) -> str:
    """
    Generates a string representation of the documents directory file tree.
    Optionally filters directories by enabled sources.
    """
    lines = []
    
    if not DOCUMENTS_DIR.exists():
        return "No documents directory found."
    
    # If source filtering is enabled, get list of enabled source names
    enabled_source_names = None
    if enabled_sources:
        enabled_source_names = [source for source, enabled in enabled_sources.items() if enabled]
    
    for root, dirs, files in os.walk(DOCUMENTS_DIR):
        # Skip directories that don't match enabled sources
        if enabled_source_names:
            root_basename = os.path.basename(root)
            parent_basename = os.path.basename(os.path.dirname(root))
            
            # Check if this directory or its parent matches any enabled source
            if (root != str(DOCUMENTS_DIR) and 
                root_basename not in enabled_source_names and 
                parent_basename not in enabled_source_names):
                # Also check if root is a subdirectory of any enabled source
                is_subdirectory_of_enabled = False
                for source in enabled_source_names:
                    if f"/{source}/" in root or root.endswith(f"/{source}"):
                        is_subdirectory_of_enabled = True
                        break
                if not is_subdirectory_of_enabled:
                    continue
        
        level = root.replace(str(DOCUMENTS_DIR), '').count(os.sep)
        indent = ' ' * 4 * level
        
        # Prepend a marker for the directory itself if it's not the root
        if root != str(DOCUMENTS_DIR):
            lines.append(f'{indent[:-4]}{os.path.basename(root)}/')

        for f in sorted(files):
            lines.append(f'{indent}{f}')
            
    return "\n".join(lines)

def _get_structured_index_content(db: Session, enabled_sources: Optional[dict] = None) -> str:
    """
    Retrieves structured index content from the database and formats it as a string.
    Filters by enabled sources if provided.
    """
    query = db.query(IndexEntry)
    
    # Filter by enabled sources if provided
    if enabled_sources:
        enabled_source_names = [source for source, enabled in enabled_sources.items() if enabled]
        if enabled_source_names:
            query = query.filter(IndexEntry.source.in_(enabled_source_names))
    
    entries = query.order_by(IndexEntry.file_path).all()
    if not entries:
        return "No entries found in the structured index."
    
    formatted_entries = ["## Structured Index Content ##"]
    for entry in entries:
        formatted_entries.append(f"- FILE: {entry.file_path}")
        if entry.description:
            formatted_entries.append(f"  - DESCRIPTION: {entry.description}")
        if entry.tags:
            formatted_entries.append(f"  - TAGS: {entry.tags}")
        formatted_entries.append(f"  - SOURCE: {entry.source}")
    return "\n".join(formatted_entries)


async def select_relevant_files(user_prompt: str, file_tree: str, db: Session, model: Optional[str], enabled_sources: Optional[dict] = None) -> List[str]:
    """
    Uses an LLM to select relevant files based on the user's prompt and a file tree.
    It also uses a persistent, user-editable structured index from the database for high-level guidance.
    
    Returns:
        A list of file paths relative to the documents directory.
    """
    current_datetime = _get_current_datetime()
    system_message = f"""
Current date and time: {current_datetime}

You are an expert software engineer assistant. Your task is to analyze a user's request and identify the most relevant files from the documents directory to fulfill the request.

You are provided with three pieces of information:
1.  **Structured Index Content**: A manually-curated table of files, their descriptions, and tags. Give this content HIGH PRIORITY. It's the most important guide for you.
2.  **Documents Directory File Tree**: A list of all available files.
3.  **User Request**: The user's question or command.

IMPORTANT: When selecting files, try to sample from different sources/directories when possible to provide diverse perspectives and comprehensive coverage. While some information might be concentrated in one source, aim to include files from various sources unless the query is very specific to a single area.

Based on all three, respond ONLY with a JSON array of file paths. The paths should be relative to the documents directory (e.g., "project_overview.md"). Do not include any other text, explanation, or markdown formatting.

Example response:
["project_overview.md", "tech_stack.md"]
"""
    
    # Get the structured index content from the database (filtered by enabled sources)
    structured_index_content = _get_structured_index_content(db, enabled_sources)
    
    full_prompt = f"{structured_index_content}\n\n## Documents Directory File Tree ##\n{file_tree}\n\n## User Request ##\n{user_prompt}"

    try:
        raw_response = await ask_llm(full_prompt, system_message, model_override=model)
        
        # Clean up response: remove markdown code block fences
        cleaned_response = raw_response.strip().replace('```json', '').replace('```', '').strip()
        
        selected_files = json.loads(cleaned_response)
        if isinstance(selected_files, list):
            # Ensure all paths are valid and exist in the documents directory
            valid_files = [f for f in selected_files if (DOCUMENTS_DIR / f).is_file()]
            return valid_files
        return []
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error decoding file selection response: {e}\nRaw response: {raw_response}")
        # Fallback or error handling can be improved here
        return []
    except Exception as e:
        print(f"An unexpected error occurred during file selection: {e}")
        return []


def _read_files_content(file_paths: List[str]) -> Tuple[str, Dict[str, int]]:
    """
    Reads the content of the given files from the documents directory and concatenates them into a single string.
    
    Returns:
        A tuple containing the concatenated content and a dictionary mapping file paths to their token counts.
    """
    all_content = []
    file_token_counts = {}
    
    for file_path in file_paths:
        try:
            full_path = DOCUMENTS_DIR / file_path
            content = full_path.read_text('utf-8')
            formatted_content = f"--- START OF FILE: {file_path} ---\n{content}\n--- END OF FILE: {file_path} ---\n"
            all_content.append(formatted_content)
            
            # Calculate token count for this individual file
            file_token_counts[file_path] = _estimate_token_count(content)
            
        except FileNotFoundError:
            print(f"Warning: File selected by LLM not found: {file_path}")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
    
    return "\n\n".join(all_content), file_token_counts


async def execute_request_with_context(user_prompt: str, files_content: str, model: Optional[str], **kwargs: Any) -> str:
    """
    Uses an LLM to generate a final response based on the user prompt and the content of selected files.
    """
    current_datetime = _get_current_datetime()
    system_message = f"Current date and time: {current_datetime}\n\nYou are an expert software engineer and senior technical writer. Your task is to fulfill the user's request based on their prompt and the content of relevant documentation files provided below. Provide a comprehensive, clear, and helpful response. Use markdown for formatting where appropriate."
    
    full_prompt = f"## Relevant Documentation File(s) Content ##\n{files_content}\n\n## User Request ##\n{user_prompt}"
    
    final_response = await ask_llm(full_prompt, system_message, model_override=model, **kwargs)
    return final_response


async def run_agent(user_prompt: str, db: Session, selection_model: Optional[str], execution_model: Optional[str], enabled_sources: Optional[dict] = None) -> Tuple[List[str], str, Optional[int], Optional[Dict[str, int]]]:
    """
    Orchestrates the two-step agentic process: file selection and execution.

    Returns:
        A tuple containing the list of selected files, the final response string, estimated total token count, and individual file token counts.
    """
    print("Step 1: Generating documents directory file tree and selecting relevant files...")
    file_tree = _get_project_file_tree(enabled_sources)
    
    selected_files = await select_relevant_files(user_prompt, file_tree, db, model=selection_model, enabled_sources=enabled_sources)
    
    if not selected_files:
        print("No relevant files selected or an error occurred. Proceeding without file context.")
        final_response = await execute_request_with_context(user_prompt, "No files were selected as context.", model=execution_model)
        return [], final_response, None, None

    print(f"Selected files: {selected_files}")

    print("Step 2: Reading file contents and executing final request...")
    files_content, file_token_counts = _read_files_content(selected_files)
    
    if not files_content:
        print("Could not read content from any selected files. Proceeding without file context.")
        final_response = await execute_request_with_context(user_prompt, "The selected files could not be read.", model=execution_model)
        return selected_files, final_response, None, None

    # Calculate total token count for the files content
    total_tokens = sum(file_token_counts.values()) if file_token_counts else None
    print(f"Estimated token count for selected files: {total_tokens:,}")
    
    # Print individual file token counts
    if file_token_counts:
        for file_path, token_count in file_token_counts.items():
            print(f"  {file_path}: {token_count:,} tokens")
    
    final_response = await execute_request_with_context(user_prompt, files_content, model=execution_model)
    
    print("Agent execution complete.")
    return selected_files, final_response, total_tokens, file_token_counts 