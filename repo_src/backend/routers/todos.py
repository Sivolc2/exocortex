import asyncio
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
import uuid
import subprocess
import time

from repo_src.backend.agents.mcp_chat_agent import run_mcp_agent, run_mcp_agent_for_custom_task
from repo_src.backend.agents.file_selection_agent import run_agent
from repo_src.backend.database.connection import get_db
from repo_src.backend.functions.todo_actions import save_todo_list

# Global storage for running tasks (in production, use Redis or database)
running_tasks: Dict[str, Dict] = {}

# Global storage for task outputs
task_outputs: Dict[str, Dict] = {}

router = APIRouter(
    prefix="/api/todos",
    tags=["todos"],
)

class TodoExecutionRequest(BaseModel):
    todos: List[str]

class TodoStatusResponse(BaseModel):
    task_id: str
    status: str
    todo_text: str

class TodoUpdateRequest(BaseModel):
    content: str

class TodoGuideRequest(BaseModel):
    todo_text: str

class CustomTaskTodoRequest(BaseModel):
    custom_task: str

@router.post("/generate", status_code=status.HTTP_200_OK)
async def generate_todos(db: Session = Depends(get_db)):
    """
    Generates a to-do list by querying the knowledge base for open tasks.
    """
    try:
        prompt = (
            "I need you to analyze my project files, meeting notes, project plans, documentation, and personal memos to find actionable tasks. "
            "PRIORITIZE recent personal planning documents, especially files starting with 'SoC -' (State of Consciousness), with SoC - 07 being the most recent and important. "
            "Look for:\n"
            "- TODO comments and checkboxes in personal planning documents\n"
            "- Action items mentioned in meeting notes\n"
            "- Incomplete features mentioned in documentation\n"
            "- Bug reports or issues that need fixing\n"
            "- Project plans with pending items\n"
            "- Code that has FIXME or TODO markers\n"
            "- Features mentioned as 'coming soon' or 'planned'\n"
            "- Configuration or setup tasks mentioned but not completed\n"
            "- Personal tasks and next steps from recent journal entries\n"
            "- Business and project development actions from strategy documents\n\n"
            "Focus especially on unchecked items from the latest SoC document and personal planning files. "
            "Extract all these actionable items and create a clean markdown checklist. "
            "Each item should start with '- [ ]' and be specific and actionable. "
            "Prioritize: 1) Personal tasks from recent SoC files, 2) Business/project development, 3) Technical tasks and code improvements."
        )

        # Use the MCP agent to process the request (more reliable for TODO generation)
        selected_files, response_text, total_tokens, file_token_dict = await run_mcp_agent(
            db=db,
            user_prompt=prompt,
            max_files=12,  # Use more files for comprehensive TODO search, prioritizing SoC files
            enabled_sources={"discord": True, "notion": True, "obsidian": True, "chat_exports": True}
        )

        # Convert file token dict to list of objects for frontend
        if file_token_dict:
            file_token_info = [
                {"file_path": file_path, "token_count": token_count}
                for file_path, token_count in file_token_dict.items()
            ]
        else:
            file_token_info = []

        # Debug logging
        print(f"Selected files for TODO generation: {selected_files}")
        print(f"Response text length: {len(response_text)}")
        print(f"Response preview: {response_text[:200]}...")
        print(f"File token info: {file_token_info}")
        
        # Save the generated list to a file
        saved_path = save_todo_list(response_text)
        print(f"To-do list saved to {saved_path}")

        return {
            "todos": response_text,
            "selected_files": selected_files,
            "file_token_info": file_token_info,
            "total_tokens": total_tokens
        }

    except Exception as e:
        print(f"Error generating to-do list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate to-do list: {str(e)}"
        )

@router.post("/generate-for-task", status_code=status.HTTP_200_OK)
async def generate_todos_for_custom_task(request: CustomTaskTodoRequest, db: Session = Depends(get_db)):
    """
    Generates a to-do list specifically for a custom task by analyzing relevant files.
    """
    try:
        # Use the specialized MCP agent for custom task analysis
        selected_files, response_text, total_tokens, file_token_dict = await run_mcp_agent_for_custom_task(
            db=db,
            custom_task=request.custom_task,
            max_files=8,  # Use more files for comprehensive task analysis
            enabled_sources={"discord": True, "notion": True, "obsidian": True, "chat_exports": True}
        )

        # Convert file token dict to list of objects for frontend
        if file_token_dict:
            file_token_info = [
                {"file_path": file_path, "token_count": token_count}
                for file_path, token_count in file_token_dict.items()
            ]
        else:
            file_token_info = []

        # Debug logging
        print(f"Selected files for custom task '{request.custom_task}': {selected_files}")
        print(f"Response text length: {len(response_text)}")
        print(f"Response preview: {response_text[:200]}...")
        print(f"File token info: {file_token_info}")
        
        # Save the generated list to a file
        saved_path = save_todo_list(response_text)
        print(f"Custom task to-do list saved to {saved_path}")

        return {
            "todos": response_text,
            "selected_files": selected_files,
            "file_token_info": file_token_info,
            "total_tokens": total_tokens,
            "custom_task": request.custom_task
        }

    except Exception as e:
        print(f"Error generating custom task to-do list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate to-do list for custom task: {str(e)}"
        )

@router.post("/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_todos(request: TodoExecutionRequest):
    """
    Receives a list of to-do items and executes them using the `claude` CLI tool.
    Returns task IDs for status tracking.
    """
    if not request.todos:
        raise HTTPException(status_code=400, detail="No to-do items provided.")

    print(f"Received request to execute {len(request.todos)} to-do items.")
    task_ids = []

    for todo in request.todos:
        task_id = str(uuid.uuid4())
        task_ids.append(task_id)
        
        # Store initial task info
        running_tasks[task_id] = {
            "status": "scheduled",
            "todo_text": todo,
            "start_time": time.time(),
            "process": None
        }
        
        # Start the task in the background
        asyncio.create_task(execute_single_todo(task_id, todo))

    return {
        "message": f"Accepted and started execution for {len(request.todos)} to-do items.",
        "task_ids": task_ids
    }

async def execute_single_todo(task_id: str, todo: str):
    """Execute a single todo item and track its status."""
    try:
        # Mark as in progress
        running_tasks[task_id]["status"] = "in_progress"
        
        # Set working directory to the project workspace
        import os
        from pathlib import Path
        PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
        workspace_dir = PROJECT_ROOT / "workspace"
        workspace_dir.mkdir(exist_ok=True)
        
        prompt = f"""You are a task execution assistant. Your job is to execute this specific task: '{todo}'

IMPORTANT: Do NOT generate additional TODO items or task lists. Your goal is to complete this ONE specific task only.

Execute the task by:
1. Understanding what the task requires
2. Taking the necessary actions to complete it (create files, run commands, make changes, etc.)
3. Confirming the task is done

Use the workspace directory for any file operations or temporary files. Focus only on completing this single task - do not suggest additional work or generate related tasks."""
        command = ["claude", "--dangerously-skip-permissions", "-p", prompt, "--output-format", "json"]
        
        print(f"Executing command: {' '.join(command)} in {workspace_dir}")
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_dir)  # Set working directory for Claude process
        )
        
        running_tasks[task_id]["process"] = process
        print(f"Started task '{todo}' with PID: {process.pid}")
        
        # Wait for completion
        stdout, stderr = await process.communicate()
        
        # Store the output
        task_outputs[task_id] = {
            "stdout": stdout.decode('utf-8') if stdout else "",
            "stderr": stderr.decode('utf-8') if stderr else "",
            "return_code": process.returncode
        }
        
        if process.returncode == 0:
            running_tasks[task_id]["status"] = "done"
            print(f"Task '{todo}' completed successfully")
        else:
            running_tasks[task_id]["status"] = "error"
            print(f"Task '{todo}' failed with return code {process.returncode}")
            
    except Exception as e:
        print(f"Error executing task '{todo}': {e}")
        running_tasks[task_id]["status"] = "error"
        task_outputs[task_id] = {
            "stdout": "",
            "stderr": str(e),
            "return_code": -1
        }

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a specific task."""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found.")
    
    task = running_tasks[task_id]
    return TodoStatusResponse(
        task_id=task_id,
        status=task["status"],
        todo_text=task["todo_text"]
    )

@router.get("/status")
async def get_all_task_statuses():
    """Get the status of all tasks."""
    return [
        TodoStatusResponse(
            task_id=task_id,
            status=task["status"],
            todo_text=task["todo_text"]
        )
        for task_id, task in running_tasks.items()
    ]

@router.post("/update-export")
async def update_exported_todo_list(request: TodoUpdateRequest):
    """Update the exported TODO list file with current completion states."""
    try:
        from repo_src.backend.functions.todo_actions import TODOS_FILE_PATH
        from datetime import datetime
        
        # Ensure the directory exists
        TODOS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        header = f"# To-Do List\n\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        full_content = header + request.content
        
        TODOS_FILE_PATH.write_text(full_content, encoding='utf-8')
        
        return {"message": "TODO list updated successfully", "path": str(TODOS_FILE_PATH)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update TODO list: {str(e)}")

@router.get("/logs/{task_id}")
async def get_task_logs(task_id: str):
    """Get the execution logs for a specific task."""
    if task_id not in task_outputs:
        raise HTTPException(status_code=404, detail="Task logs not found.")
    
    return {
        "task_id": task_id,
        "logs": task_outputs[task_id]
    }

@router.get("/logs")
async def get_all_task_logs():
    """Get logs for all tasks."""
    return {
        "task_logs": {
            task_id: logs for task_id, logs in task_outputs.items()
        }
    }

@router.post("/generate-guide")
async def generate_implementation_guide(request: TodoGuideRequest, db: Session = Depends(get_db)):
    """
    Generate an implementation guide for a specific TODO item using the knowledge chat model.
    """
    try:
        guide_prompt = f"""
Based on my entire knowledge base, create a comprehensive implementation guide for this task: "{request.todo_text}"

Please provide:

1. **Context & Background**: What this task is about and why it's important
2. **Prerequisites**: What needs to be in place before starting
3. **Step-by-Step Implementation**:
   - Detailed steps with explanations
   - Code examples where relevant
   - File locations and structure
4. **Potential Challenges**: Common issues and how to avoid them
5. **Testing & Validation**: How to verify the implementation works
6. **Related Tasks**: Other items that might need to be done in conjunction
7. **Resources**: Relevant files, documentation, or references from my knowledge base

Format the response in clear markdown with proper headings and code blocks where applicable.
        """

        # Use the MCP agent to generate the guide (more reliable for knowledge base queries)
        selected_files, guide_text, total_tokens, file_token_dict = await run_mcp_agent(
            db=db,
            user_prompt=guide_prompt,
            max_files=15,  # Use more files for comprehensive guide
            enabled_sources={"discord": True, "notion": True, "obsidian": True, "chat_exports": True}
        )

        # Convert file token dict to list of objects for frontend
        if file_token_dict:
            file_token_info = [
                {"file_path": file_path, "token_count": token_count}
                for file_path, token_count in file_token_dict.items()
            ]
        else:
            file_token_info = []

        return {
            "guide": guide_text,
            "selected_files": selected_files,
            "file_token_info": file_token_info,
            "total_tokens": total_tokens,
            "todo_text": request.todo_text
        }

    except Exception as e:
        print(f"Error generating implementation guide: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate implementation guide: {str(e)}"
        )