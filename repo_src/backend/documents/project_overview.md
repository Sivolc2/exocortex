# Project Overview

This project is a sophisticated monorepo template designed for building full-stack applications with a focus on human-AI collaboration. It features a "functional-core, imperative-shell" architecture.

## Key Components

- **Backend**: A Python-based API built with FastAPI. It handles business logic, database interactions, and communication with external services like LLMs.
- **Frontend**: A modern web application built with React, TypeScript, and Vite. It provides the user interface.
- **Monorepo Tooling**: The project uses `pnpm` workspaces and `turbo` for efficient script running and dependency management across the frontend and backend.
- **AI Integration**: The architecture is designed to be "AI-friendly," with clear separation of concerns, auto-generating documentation, and context-aware scripts. A core feature is the chat interface that uses OpenRouter to answer questions based on the documents in this very folder. 