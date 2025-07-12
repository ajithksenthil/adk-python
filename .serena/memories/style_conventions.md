# ADK Code Style and Conventions

## Python Style
- Follows Google Python Style Guide
- **Indentation**: 2 spaces
- **Line Length**: Maximum 80 characters
- **Naming Conventions**:
  - Functions/variables: `snake_case`
  - Classes: `CamelCase`
  - Constants: `UPPERCASE_SNAKE_CASE`
- **Docstrings**: Required for all public modules, functions, classes, and methods

## ADK-Specific Conventions
- **Imports in src/**: Use relative imports (`from ..agents.llm_agent import LlmAgent`)
- **Imports in tests/**: Use absolute imports (`from google.adk.agents.llm_agent import LlmAgent`)
- **Always use**: `from __future__ import annotations` after the license header
- **Import from module directly**, not from `__init__.py`

## File Structure Requirements
- Agent directories must have `__init__.py` with `from . import agent`
- `agent.py` must define `root_agent` variable
- Use autoformat.sh for formatting and import organization

## Comments and Documentation
- Comments should explain WHY, not WHAT
- Well-written code should be self-documenting
- Use complete sentences in comments

## Breaking Changes
- Follow Semantic Versioning 2.0.0
- Public API includes:
  - All public classes/methods in google.adk namespace
  - Built-in tool interfaces
  - Data schemas (sessions, memory, evaluations)
  - CLI commands and arguments
  - Wire format for API server