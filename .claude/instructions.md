# RAG System Development Instructions for Claude Code

## Project Context

**Type**: Production RAG system with MLOps pipeline
**Tech Stack**: Python, FastAPI, Ollama, Weaviate, GKE, Helm, Docling, LangChain
**Methodology**: Test-Driven Development (TDD)
**Coverage Test**: >80% (enforced in CI/CD)

## Core Development Rules

### 1. TDD Workflow (MANDATORY)

RED --> GREEN --> REFACTOR

**Every features MUST follow**
1. Write failing test first, DO NOT write implementation code yet.
2. Run test, verify it fails
3. Write minimal code to pass. DO NOT modify tests.
4. Improve code quality while keeping all tests pass.
5. Commit only when all tests pass

### 2. Test-First Commands 

**Before writing ANY implementation:**
```bash
# 1. Create test file
touch tests/unit/test_<feature>.py

# 2. Write test
# (Claude Code writes the test)

# 3. Run test (MUST FAIL)
pytest tests/unit/test_<feature>.py::<TestClass>::<test_method> -v

# 4. Implement feature
# (Claude Code implements)

# 5. Run test (MUST PASS)
pytest tests/unit/test_<feature>.py::<TestClass>::<test_method> -v

# 6. Check coverage
pytest tests/unit/test_<feature>.py --cov=app.<module> --cov-report=term-missing
```

### 3. Prohibited Actions 

**NEVER**:

- Skip failing tests (`@pytest.mark.skip`)
- Comment out assertions to pass tests
- Commit code without tests
- Ignore test failures
- Write implementation before tests
- Commit secrets (`.env`, API keys)
- Add AI attributions in code


