# Exocortex: AI-Powered Knowledge Aggregation & Management System

A comprehensive framework for aggregating, indexing, and querying knowledge from multiple data sources (Obsidian, Notion, Discord) with AI-driven insights and collaborative content creation capabilities.

## 🧠 Overview

**Exocortex** is an intelligent knowledge management system that combines:
- **Multi-source data aggregation** from Obsidian vaults, Notion databases, and Discord servers
- **AI-powered indexing and search** with semantic understanding
- **Real-time audio transcription and recording** for meetings and conversations
- **Interactive web interface** for exploring and querying your knowledge base
- **Modular, extensible architecture** designed for AI-assisted development

Perfect for researchers, teams, content creators, and anyone who wants to build a comprehensive external brain from their scattered digital knowledge.

## 🚀 Key Features

### 📊 **Multi-Source Data Integration**
- **Obsidian Vault Sync**: Automatically syncs with your local Obsidian markdown files
- **Notion Integration**: Comprehensive traversal of Notion pages with recursive subpage fetching (40+ pages from complex hierarchies)
- **Discord Chat Archives**: Fetches and formats Discord conversations with rich metadata
- **Unified Data Format**: All sources normalized into consistent markdown-based documents

### 🔍 **Intelligent Knowledge Management**
- **Semantic Search & Indexing**: AI-powered document similarity and retrieval
- **Interactive Query Interface**: Web-based exploration of your knowledge graph
- **CSV Import/Export**: Manage document indexes and metadata
- **Physical Index Support**: Bridge digital and analog note-taking systems

### 🎙️ **Audio & Recording Features**
- **Real-time Audio Transcription**: Live speech-to-text with high accuracy
- **Meeting Recording**: Capture and transcribe conversations automatically
- **Audio Context Tool**: Enhance AI conversations with audio input

### 🤖 **AI-First Architecture**
- **Functional-core design** with pure functions and side-effect isolation
- **AI-friendly documentation** with auto-generated context files
- **Registry system** for AI model context and metadata
- **Comprehensive testing harness** supporting frontend, backend, and E2E testing

## 🏗️ Project Structure

```
.
├── repo_src
│   ├── backend            # Python backend with functional core
│   │   ├── adapters/      # DB / HTTP side-effect wrappers
│   │   ├── data/          # immutable schemas/constants
│   │   ├── functions/     # pure functions
│   │   ├── pipelines/     # orchestration layers
│   │   ├── tests/         # unit and integration tests
│   │   ├── utils/         # generic helpers
│   │   ├── main.py        # entrypoint
│   │   └── README_backend.md
│   ├── frontend           # React/TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/  # reusable UI components
│   │   │   ├── hooks/       # custom React hooks
│   │   │   ├── pages/       # route-level components
│   │   │   ├── services/    # API clients and services
│   │   │   ├── types/       # TypeScript type definitions
│   │   │   └── utils/       # utility functions
│   │   └── README_frontend.md
│   ├── scripts            # developer tooling and utilities
│   └── shared             # shared types and utilities
│       └── README_shared.md
├── docs
│   ├── adr/             # architecture decision records
│   ├── diagrams/        # system and component diagrams
│   ├── pipelines/       # auto-generated pipeline documentation
│   ├── prd/             # product requirements documents
│   └── README_*.md      # documentation guides
├── registry/            # auto-generated documentation and indexes
└── .github/workflows    # CI/CD configuration
```

## 🚀 Quick Start

### Initial Setup
```bash
# One-command project setup
pnpm setup-project       # Install dependencies, create venv, install Python packages, and set up env files

# Or manual step-by-step setup:
pnpm install              # Frontend dependencies
python -m venv .venv      # Create Python virtual environment
source .venv/bin/activate # Activate Python virtual environment
pip install -r repo_src/backend/requirements.txt
pnpm setup-env            # Set up environment variables
```

### Data Source Configuration

Configure your data sources in `config.yaml`:

```yaml
data_sources:
  obsidian:
    enabled: true
    vault_path: "repo_src/backend/documents" # Your Obsidian vault path
  
  notion:
    enabled: true
    database_id: "your_notion_page_or_database_id"
    
  discord:
    enabled: true
    server_id: "your_discord_server_id"
    channel_ids:
      - "channel_id_1"
      - "channel_id_2"
    message_limit: 1000
```

Set up your API keys in `repo_src/backend/.env`:
```bash
# Required for Notion integration
NOTION_API_KEY="secret_..."

# Required for Discord integration  
DISCORD_BOT_TOKEN="your_discord_bot_token"

# Required for AI features
OPENROUTER_API_KEY="sk-or-v1-..."
```

### Running the System

```bash
# Start development servers
pnpm dev                  # Start both frontend and backend servers
pnpm dev:clean            # Reset ports and start dev servers
pnpm dev:frontend         # Run only frontend (localhost:5173)
pnpm dev:backend          # Run only backend (localhost:8000)

# Data aggregation
pnpm data:combine         # Fetch and combine data from all configured sources

# Obsidian sync utilities
pnpm obsidian:sync        # One-time sync of Obsidian vault
pnpm obsidian:watch       # Watch for changes and sync continuously
```

### Development Workflow

```bash
# Code quality
pnpm lint                # Run linters
pnpm typecheck           # Run type checking
pnpm test                # Run tests for both frontend and backend
pnpm e2e                 # Run end-to-end tests with Playwright
pnpm ci                  # Run full CI pipeline (lint, typecheck, tests)

# Documentation and registry
pnpm ctx:sync            # Update AI context registry
pnpm refresh-docs        # Update documentation and diagrams
```

## 🧪 Testing

This project uses a comprehensive testing harness that allows running all tests with a single command while keeping each language's tooling isolated:

- **Frontend**: Vitest + React Testing Library
- **Backend**: pytest + hypothesis
- **E2E**: Playwright

See [README.testing.md](README.testing.md) for detailed information about the testing setup.

## 📊 Data Sources & Integration

### Obsidian Integration
- **Automatic Sync**: Connects to your local Obsidian vault (markdown files)
- **Real-time Watching**: Monitor and sync vault changes automatically
- **Full-text Indexing**: All markdown content searchable and indexed
- **Metadata Extraction**: File modification times, links, and structure preserved

### Notion Integration  
- **Comprehensive Page Fetching**: Retrieves 40+ pages from complex hierarchical structures
- **Recursive Traversal**: Automatically discovers and fetches all subpages and nested content
- **Block-level Processing**: Converts Notion blocks to markdown with proper formatting
- **Rich Metadata**: Preserves page properties, creation dates, and URLs

### Discord Integration
- **Multi-channel Support**: Fetch from multiple Discord channels simultaneously  
- **Rich Message Formatting**: Preserves usernames, timestamps, reactions, and attachments
- **Configurable Limits**: Control message count and date ranges
- **Conversation Context**: Maintains thread structure and reply relationships

## 📝 Development & AI Integration

### AI-First Architecture
This repository is designed for effective human-AI collaboration:

1. **AI-Friendly Documentation**: Auto-generated context files in `registry/`
2. **Functional Core Design**: Pure functions separated from side effects
3. **Comprehensive Testing**: Frontend, backend, and E2E test coverage
4. **Modular Components**: Easy to extend and modify with AI assistance

### Key Documentation
- **[Data Infrastructure Guide](docs/guides/06_data_infra.md)**: Comprehensive data source setup
- **[Audio Recording Guide](docs/guides/05_recording.md)**: Audio transcription features  
- **[Feature Development Flow](docs/feature_flow.md)**: Step-by-step contribution process
- **[Discord Setup Guide](DISCORD_SETUP.md)**: Complete Discord bot configuration

### Registry System
The [registry](registry/) directory provides AI-friendly context:
- **backend_context.md**: Index of backend functionality
- **frontend_context.md**: Frontend components and functions
- **pipeline_context.md**: Application pipeline summaries
- **context.json**: Machine-readable metadata for AI tools

## 🔧 Advanced Usage

### Data Pipeline
```bash
# Full data refresh from all sources
pnpm data:combine

# Monitor specific sources
pnpm obsidian:watch-smart    # Intelligent Obsidian sync
```

### Development Tools
```bash
# Update AI context registry
pnpm ctx:sync

# Generate documentation diagrams  
pnpm diagrams:generate

# Full documentation refresh
pnpm refresh-docs
```

### Testing & Quality
```bash
# Comprehensive testing
pnpm ci                     # Full CI pipeline
pnpm test                   # All unit tests
pnpm e2e                    # End-to-end tests
pnpm coverage               # Test coverage reports
```

## 🏛️ Architecture

Built on a **functional-core architecture** that separates:
- **Pure Functions**: Business logic without side effects (`functions/`)
- **Adapters**: Database and API integrations (`adapters/`)
- **Pipelines**: Orchestration layers (`pipelines/`)
- **Data Sources**: Modular fetchers for external systems (`data_sources/`)

This design enables:
- **AI-assisted development** with clear separation of concerns
- **Easy testing** with isolated, pure functions
- **Extensible architecture** for adding new data sources
- **Reliable operations** with predictable, side-effect-free core logic

## 📄 License

ISC
