# Task Completion Checklist

## When Completing Any Task

### 1. Tests First (TDD)
- [ ] Write failing test BEFORE implementation
- [ ] Run test and verify it FAILS
- [ ] Implement minimal code to pass test
- [ ] Run test and verify it PASSES
- [ ] Refactor while keeping tests green
- [ ] Check coverage is >80%

### 2. Code Quality
- [ ] Add type hints to all functions
- [ ] Add docstrings to classes and public functions
- [ ] Handle edge cases and errors properly
- [ ] Use specific exception types
- [ ] Follow naming conventions

### 3. Testing
```bash
# Run full test suite
pytest

# Check coverage
pytest --cov=app --cov-report=term-missing

# Ensure >80% coverage for modified files
```

### 4. Documentation
- [ ] Update existing docs in ./docs/ if refactoring
- [ ] Add new docs for new features (don't duplicate)
- [ ] Update README if API changes
- [ ] Document environment variables in .env.example

### 5. Pre-Commit
- [ ] Run all tests pass
- [ ] Coverage >80%
- [ ] No hardcoded secrets or credentials
- [ ] No AI attribution comments
- [ ] Clean commit message: `<type>(<scope>): <description>`

### 6. Never Commit
- .env files with real credentials
- API keys or tokens
- Database credentials
- AI signatures/attributions
- Failing tests
- Code with <80% coverage