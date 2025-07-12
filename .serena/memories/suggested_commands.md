# ADK Development Commands

## Testing
```bash
# Run unit tests
pytest tests/unittests

# Run specific test file
pytest tests/unittests/test_agents.py

# Run with coverage
pytest tests/unittests --cov=google.adk
```

## Formatting and Linting
```bash
# Auto-format code (run from project root)
./autoformat.sh

# Run pylint
pylint src/google/adk
```

## Development Tools
```bash
# Start development UI
adk web

# Start API server
adk api_server

# Run agent in CLI
adk run <agent_path>

# Evaluate agent
adk eval <agent_path> <eval_set_path>

# Deploy agent
adk deploy <agent_path> --project <gcp_project>
```

## Git Commands
```bash
# Standard git workflow
git status
git add .
git commit -m "message"
git push origin <branch>

# Create PR
git checkout -b feature/branch-name
git push -u origin feature/branch-name
```

## Package Management
```bash
# Install ADK
pip install google-adk

# Install from source
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```