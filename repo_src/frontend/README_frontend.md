# Frontend Application (Chat Interface)

This directory contains a React + TypeScript frontend application that provides a chat interface for interacting with the backend.

## Features

- Send messages to an LLM assistant.
- The assistant answers questions based on a set of documents loaded on the backend.
- View a history of the conversation.

## Development

### Prerequisites

- Node.js 18+
- pnpm (or npm/yarn)

### Installation

From the project root:

```bash
pnpm install
```

### Running the development server

```bash
pnpm dev:frontend
```

This will start the development server on http://localhost:5173.

## Project Structure

- `src/`: Source code
  - `styles/`: CSS files for styling the application
  - `App.tsx`: Main application component containing all chat logic and UI
  - `main.tsx`: Application entry point
  - `vite-env.d.ts`: TypeScript definitions for Vite environment variables.

## Technologies Used

- React 18
- TypeScript
- Vite (build tool)

## API Integration

The frontend communicates with the backend API at `/api/chat`. The Vite development server is configured via `vite.config.ts` to proxy API requests to the backend server running on port 8000, avoiding CORS issues in development.
