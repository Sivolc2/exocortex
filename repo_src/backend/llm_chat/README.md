# LLM Chat Logic

This directory contains the core logic for the "Chat with your Docs" feature.

- `llm_interface.py`: Handles all communication with the OpenRouter API. It configures the `OpenAI` client to point to OpenRouter's endpoints.
- `chat_logic.py`: Orchestrates the chat process. It loads documents, constructs the final prompt for the LLM, and calls the `llm_interface`. 