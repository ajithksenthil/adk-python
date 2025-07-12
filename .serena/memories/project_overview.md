# ADK Python Project Overview

## Purpose
The Agent Development Kit (ADK) is an open-source, code-first Python toolkit for building, evaluating, and deploying sophisticated AI agents with flexibility and control. While optimized for Gemini and the Google ecosystem, ADK is model-agnostic and deployment-agnostic.

## Tech Stack
- **Language**: Python 3.8+
- **Core Framework**: Pydantic for data validation
- **API Layer**: FastAPI for exposing agents as APIs
- **Frontend**: Angular (for development UI)
- **LLM Support**: Gemini, Anthropic, LiteLLM
- **Deployment**: Google Vertex AI, Cloud Run, GKE
- **Testing**: pytest

## Key Components
- **Agents**: Base classes (BaseAgent, LlmAgent) for agent blueprints
- **Tools**: Capabilities that agents can use (search, APIs, etc.)
- **Runners**: Orchestrate the "Reason-Act" loop
- **Sessions**: Manage conversation state
- **Memory**: Long-term recall across sessions
- **Artifacts**: Handle non-textual data
- **Evaluation**: Framework for testing agent quality

## Architecture Patterns
- Code-first approach (everything defined in Python)
- Modular composition of agents
- Deployment-agnostic design
- Clear separation between agent logic and deployment

## Project Structure
```
adk-python/
├── src/google/adk/
│   ├── agents/        # Agent implementations
│   ├── tools/         # Tool implementations
│   ├── models/        # LLM connections
│   ├── sessions/      # Session management
│   ├── memory/        # Memory services
│   ├── evaluation/    # Evaluation framework
│   └── cli/           # CLI tools
└── tests/             # Test suite
```