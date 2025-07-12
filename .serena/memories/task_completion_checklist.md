# Task Completion Checklist

When completing a coding task in ADK:

## 1. Code Quality
- [ ] Follow Google Python Style Guide
- [ ] Add proper docstrings to all public methods/classes
- [ ] Use type hints for all function parameters and returns
- [ ] Keep line length under 80 characters
- [ ] Use relative imports in src/, absolute imports in tests/

## 2. Testing
- [ ] Write unit tests for new functionality
- [ ] Ensure all existing tests pass: `pytest tests/unittests`
- [ ] Add integration tests if applicable
- [ ] Consider adding evaluation test cases for agent behavior

## 3. Formatting
- [ ] Run autoformat.sh to fix imports and formatting
- [ ] Run pylint and fix any issues
- [ ] Ensure no trailing whitespace

## 4. Documentation
- [ ] Update docstrings
- [ ] Update README if adding new features
- [ ] Add examples if introducing new patterns

## 5. Before Committing
- [ ] Review all changes
- [ ] Ensure no debug code remains
- [ ] Check that the agent can be loaded: `adk run <agent_path>`
- [ ] Test in development UI: `adk web`

## 6. Commit Message
- [ ] Use descriptive commit messages
- [ ] Reference any related issues
- [ ] Follow conventional commit format if applicable