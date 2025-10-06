# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Always breakdown large task and ask clarifying questions when needed. Think step by step and show reasoning for complex problems, use specific examples. When giving feedback, explain thought process and highlight issues and opportunities

## Project Overview

IntelliRAG is a RAG (Retrieval-Augmented Generation) system integrating Gemini AI with Weaviate vector database.

**Project**: Production-Ready RAG System with MLOps Pipeline  
**Methodology**: Test-Driven Development (TDD) - **STRICTLY ENFORCED**  
**Timeline**: 4-6 weeks  
**Coverage Target**: >80% (CI/CD enforced)  
**Budget**: $300/month (GKE + Local GPU hybrid) 

## 🎯 Core Mission

Build an enterprise RAG system that:
- Processes multi-modal documents (PDF, DOCX, CSV, TXT, images)
- Serves LLM inference via local GPU (RTX 4070Ti) + KServe
- Deploys to GKE with full observability stack
- Maintains production-grade quality standards

---

## 🛠️ Tech Stack & Documentation
- Python 3.11, 3.12
- Package Manager: `uv`

### **Core Framework**
- **FastAPI** (`/tiangolo/fastapi` - Trust: 9.9)
  - Async path operations with `async def`
  - Dependency injection via `Depends()`
  - Background tasks with `BackgroundTasks`
  - Router-level dependencies with `APIRouter`
  
- **Pydantic** (`/pydantic/pydantic` - Trust: 9.6)
  - `BaseModel` for data validation
  - `@field_validator` for custom validation
  - `Field()` for strict mode and constraints
  - Nested model validation

### **Vector & Embeddings**
- **Qdrant Client** (`/qdrant/qdrant-client` - Trust: 9.8)
  - Async operations supported
  - Collection management
  - Vector search with filters
  
- **Sentence Transformers** (`/ukplab/sentence-transformers` - Trust: 7.8)
  - Pre-trained embedding models
  - Batch encoding support
  - `all-MiniLM-L6-v2` (384 dim, recommended)

### **Testing**
- **Pytest** (`/pytest-dev/pytest` - Trust: 9.5)
  - `pytest-asyncio` for async tests
  - `pytest-cov` for coverage
  - `pytest-mock` for mocking
  - Fixtures with `@pytest.fixture`

### **LLM & Processing**
- **Ollama** (Local serving): Qwen2.5-7B + MiniCPM-V
- **httpx**: Async HTTP client for LLM calls
- **Docling**: Document processing, parsing diverse formats (PDF, DOCX, PPTX, XLSX, HTML, WAV, MP3, VTT, images (PNG, TIFF, JPEG, ...))

### **Infrastructure**
- **Kubernetes**: GKE Autopilot
- **Helm**: Deployment charts
- **Terraform**: IaC for GKE
- **Tailscale**: Secure VPN (GKE ↔ Local GPU)
- **Prometheus + Grafana**: Metrics
- **Loki**: Logging
- **Jaeger**: Tracing
- **MLFlow + DVC**: Model/data versioning

---

## 🔴🟢♻️ TDD Workflow (MANDATORY)

### **The Sacred TDD Cycle**

```
RED (Fail) → GREEN (Pass) → REFACTOR (Clean)
     ↓            ↓              ↓
  Write Test   Implement     Improve Code
  & See FAIL   Minimal       Keep Tests
               Solution      Green
```

### **Before ANY Code Implementation**

```bash
# 1. Create test file FIRST
touch tests/unit/test_.py

# 2. Write test that WILL FAIL
vim tests/unit/test_.py

# 3. Run test - MUST see failure
pytest tests/unit/test_.py:::: -v
# Expected: FAILED ❌

# 4. Implement minimal code
vim app/services/.py

# 5. Run test - MUST pass
pytest tests/unit/test_.py:::: -v
# Expected: PASSED ✅

# 6. Refactor 
# Improve code while keeping tests green

# 7. Check coverage
pytest tests/unit/test_.py --cov=app.services. --cov-report=term-missing
# Target: >80%
```

### **Critical TDD Rules**

**ALWAYS:**
- ✅ Write failing test first, DO NOT write implementation code yet.
- ✅ Run test and verify it FAILS
- ✅ Write minimal code to pass. DO NOT modify tests.
- ✅ Improve code quality while keeping all tests pass.
- ✅ Commit only when all tests pass
- ✅ Maintain >80% coverage

**NEVER:**
- ❌ Skip failing tests (`@pytest.mark.skip`)
- ❌ Comment out assertions to pass tests
- ❌ Implement without test
- ❌ Ignore test failures
- ❌ Commit code without tests
- ❌ Commit with failing tests
- ❌ Commit secrets (`.env`, API keys)
- ❌ Ignore coverage drops
- ❌ Add AI attributions in code

---

## 📁 Project Structure

```
rag-system/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── api/
│   │   ├── __init__.py
│   │   ├── upload.py              # POST /upload
│   │   ├── embed.py               # POST /embed
│   │   └── query.py               # POST /query (RAG)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── preprocessing/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseHandler abstract
│   │   │   ├── pdf.py             # PDFHandler
│   │   │   ├── docx.py            # DocxHandler
│   │   │   ├── image.py           # ImageHandler (OCR + Vision)
│   │   │   ├── csv_handler.py     # CSVHandler
│   │   │   └── text.py            # TextHandler
│   │   ├── llm_client.py          # OllamaClient (async)
│   │   ├── embedding.py           # EmbeddingService
│   │   ├── vectordb.py            # QdrantService
│   │   └── rag_pipeline.py        # RAGPipeline
│   └── models/
│       ├── __init__.py
│       └── schemas.py             # Pydantic models
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── unit/
│   │   ├── test_preprocessing_pdf.py
│   │   ├── test_preprocessing_docx.py
│   │   ├── test_preprocessing_image.py
│   │   ├── test_preprocessing_csv.py
│   │   ├── test_preprocessing_text.py
│   │   ├── test_embedding.py
│   │   ├── test_llm_client.py
│   │   ├── test_vectordb.py
│   │   └── test_rag_pipeline.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   └── test_rag_flow.py
│   ├── evaluation/
│   │   └── test_ragas.py          # RAGAS metrics
│   └── fixtures/
│       ├── sample.pdf
│       ├── sample.docx
│       ├── sample.csv
│       ├── sample.txt
│       └── sample.jpg
├── kubernetes/
│   └── (Helm charts, manifests)
├── terraform/
│   └── (GKE infrastructure)
├── docs/
│   └── (Project documentation)
├── .github/
│   └── workflows/
│       └── deploy.yml             # CI/CD pipeline
├── pytest.ini                     # Pytest config
├── requirements.txt
├── requirements-dev.txt
└── CLAUDE.md                      # This file
```

---

## 🔒 CRITICAL CONSTRAINTS

### DO NOT:
- Skip writing tests before implementation
- Modify tests to make implementation pass (except fixing actual test bugs)
- Mock everything (over-mocking makes tests brittle)
- Test implementation details (test behavior, not internals)
- Use production API keys or production databases in tests

### DO:
- Write tests that define expected behavior clearly
- Use fixtures for reusable test data
- Keep tests independent (no test should depend on another)
- Test edge cases and error conditions
- Use meaningful assertion messages
- Run full test suite before committing

---

## Development Rules

### General
- Update existing docs (Markdown files) in `./docs` directory before any code refactoring
- Add new docs (Markdown files) to `./docs` directory after new feature implementation (do not create duplicated docs)
- use `context7` mcp tools for docs of plugins/packages
- use `senera` mcp tools for semantic retrieval and editing capabilities
- whenever you want to see the whole code base, use this command: `repomix` and read the output summary file.

### Code Quality Guidelines
- Don't be too harsh on code linting and formatting
- Prioritize functionality and readability over strict style enforcement
- Use reasonable code quality standards that enhance developer productivity
- Allow for minor style variations when they improve code clarity

### Pre-commit/Push Rules
- Keep commits focused on the actual code changes
- **DO NOT** commit and push any confidential information (such as dotenv files, API keys, database credentials, etc.) to git repository!
- NEVER automatically add AI attribution signatures like:
  "🤖 Generated with [Claude Code]"
  "Co-Authored-By: Claude noreply@anthropic.com"
  Any AI tool attribution or signature
- Create clean, professional commit messages without AI references. Use conventional commit format.