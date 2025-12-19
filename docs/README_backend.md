# Backend

This is the backend API built with FastAPI, following a functional-core, imperative-shell architecture.

## Features

- **Database**: SQLAlchemy ORM with SQLite for development, easily configurable for PostgreSQL.
- **Item Management**: CRUD operations for items (legacy feature).
- **Chat Interface**: "Chat with your Docs" feature using OpenRouter to answer questions based on local documents.
- **Architecture**: Clear separation between pure functions and side effects.

## Architecture

- **Functions**: Pure functions for business logic (located in `functions/`).
- **Pipelines**: Orchestration of pure functions and side effects (located in `pipelines/`).
- **Adapters**: Wrappers for database CRUD operations, external API calls, and other side effects (located in `adapters/`).
- **`llm_chat/`**: Contains the logic for the "Chat with your Docs" feature, including the OpenRouter API interface.

## Setup

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables by running the setup script from the project root:
```bash
# From project root
pnpm setup-env
```
4. Run the development server:
```bash
uvicorn repo_src.backend.main:app --reload
```

The API will be available at http://localhost:8000

## API Endpoints

- `GET /`: Welcome message
- `GET /api/hello`: Simple connectivity test
- `GET /api/items`: List all items
- `POST /api/items/`: Create a new item
- `DELETE /api/items/{id}`: Delete an item
- `POST /api/chat/`: Chat with your docs (requires OpenRouter API key)

## Chat Feature

The chat feature uses OpenRouter to provide LLM-powered responses based on documents in the `documents/` directory. To use this feature:

1. Get an API key from https://openrouter.ai/keys
2. Add your API key to `repo_src/backend/.env`:
   ```
   OPENROUTER_API_KEY="sk-or-v1-your-actual-key-here"
   ```
3. The system will automatically load all `.md` and `.txt` files from the `documents/` directory as context.

## Testing

Run tests with:
```bash
pytest
```

## Database

The backend uses SQLAlchemy with SQLite for development. The database file is created automatically when you first run the application. 