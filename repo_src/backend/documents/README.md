# Document Store

This directory contains the text and markdown files that the chat interface uses as its knowledge base.

The `chat_logic.py` in the backend will load all `.md` and `.txt` files from this directory into memory to provide context to the LLM for answering user questions. 