import os
import glob
from pathlib import Path
from .llm_interface import ask_llm

def load_documents_from_disk() -> str:
    """
    Loads all .md and .txt files from the 'documents' directory
    and concatenates their content into a single string.
    """
    # Get the directory of the current script, then navigate to the 'documents' folder
    script_dir = Path(__file__).parent.parent 
    docs_path = script_dir / "documents"
    
    print(f"Loading documents from: {docs_path.resolve()}")

    document_contents = []
    
    # Find all .md and .txt files in the documents directory
    for extension in ["*.md", "*.txt"]:
        for file_path in docs_path.glob(extension):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    document_contents.append(f"--- START OF {file_path.name} ---\n{file_content}\n--- END OF {file_path.name} ---\n")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")

    if not document_contents:
        print("Warning: No documents found in the 'documents' directory.")
        return "No context documents were found."

    return "\n".join(document_contents)

async def process_chat_request(user_prompt: str) -> str:
    """
    Processes a user's chat request by loading document context,
    constructing a prompt, and querying the LLM.
    """
    documents_context = load_documents_from_disk()

    system_message = "You are a helpful assistant. You answer questions based on the provided context documents. If the answer is not in the documents, say that you cannot find the answer in the provided context."

    # Construct the final prompt for the LLM
    full_prompt = f"Here is the context from my documents:\n\n{documents_context}\n\nBased on this context, please answer the following question:\n\nUser Question: {user_prompt}"

    # Call the LLM with the combined prompt
    llm_response = await ask_llm(full_prompt, system_message=system_message)
    
    return llm_response 