---
title: "Phase 4: Code Execution Enhancement"
status: pending
effort: 1d
---

# Phase 4: Code Execution Enhancement

## Context

- [Plan Overview](./plan.md)
- [ReAct Research](./research/researcher-02-react-agent-report.md) - recommends RestrictedPython
- Current: No CODE_EXECUTION query type

## Overview

Add CODE_EXECUTION query type for mathematical/computational queries. Use RestrictedPython with timeout guards instead of raw PythonREPLTool.

## Key Insights

1. **RestrictedPython**: Safer than PythonREPLTool (no file I/O, no network)
2. **Timeout**: 5-second limit per execution
3. **Self-correction**: Up to 5 retries with error feedback
4. **Whitelist globals**: Only math, statistics, decimal modules
5. **AST validation**: Check for placeholders before execution

## Requirements

### Functional
- Classify computational queries as CODE_EXECUTION
- Generate Python code via LLM
- Validate syntax and check for placeholders
- Execute in restricted sandbox with timeout
- Retry on error with feedback to LLM

### Non-Functional
- Execution timeout: 5 seconds
- Max retries: 5
- Success rate: >85%

## Architecture

```
CODE_EXECUTION Flow:

Query: "Calculate 15% of 2,450"
        ↓
┌───────────────────────┐
│ classify → CODE_EXEC  │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│   code_execute_node   │
├───────────────────────┤
│ 1. Generate code (LLM)│
│ 2. Validate (AST)     │
│ 3. Check placeholders │
│ 4. Execute (sandbox)  │
│ 5. Retry if error     │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│   generate (answer)   │
└───────────────────────┘
```

## Implementation Steps

### Task 4.1: Add CODE_EXECUTION to QueryType (0.1d)

**Update**: `app/services/query_router/classifier.py`

```python
class QueryType(Enum):
    RAG = "rag"
    DIRECT = "direct"
    CLARIFICATION = "clarification"
    MULTI_HOP = "multi_hop"
    CODE_EXECUTION = "code_execution"  # NEW
```

**Update**: `app/services/query_router/prompts.py` (few-shot examples)

Add example:
```python
{
    "query": "Calculate compound interest on $10,000 at 5% for 3 years",
    "response": '{"query_type": "code_execution", "confidence": 0.95, "reasoning": "Mathematical calculation requiring computation"}'
}
```

### Task 4.2: Create CodeExecutor Service (0.5d)

**File**: `app/services/query_router/code_executor.py`

```python
import ast
import logging
import math
import statistics
from decimal import Decimal
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from RestrictedPython import compile_restricted, safe_builtins

logger = logging.getLogger(__name__)

# Allowed globals for safe execution
SAFE_GLOBALS = {
    "__builtins__": safe_builtins,
    "math": math,
    "statistics": statistics,
    "Decimal": Decimal,
    "abs": abs,
    "round": round,
    "sum": sum,
    "min": min,
    "max": max,
    "len": len,
    "range": range,
    "list": list,
    "dict": dict,
    "float": float,
    "int": int,
    "str": str,
    "print": lambda *args: None,  # Capture print output
}

PLACEHOLDER_PATTERNS = ["TODO", "...", "pass", "FIXME", "NotImplemented"]


class CodeExecutor:
    """Safe Python code execution with RestrictedPython."""

    def __init__(self, timeout: int = 5, max_retries: int = 5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.executor = ThreadPoolExecutor(max_workers=1)

    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate code syntax and check for placeholders.

        Returns:
            (is_valid, error_message)
        """
        # Check for placeholders
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in code:
                return False, f"Code contains placeholder: {pattern}"

        # Validate syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        return True, None

    def _execute_restricted(self, code: str) -> Dict[str, Any]:
        """Execute code in restricted environment."""
        # Compile with RestrictedPython
        try:
            byte_code = compile_restricted(
                code,
                '<inline>',
                'exec'
            )
        except SyntaxError as e:
            return {"success": False, "error": f"Compile error: {e}"}

        # Execute with safe globals
        local_vars = {}
        try:
            exec(byte_code, SAFE_GLOBALS.copy(), local_vars)

            # Look for 'result' variable
            if 'result' in local_vars:
                return {"success": True, "result": local_vars['result']}

            # Return all non-builtin variables
            output = {k: v for k, v in local_vars.items()
                      if not k.startswith('_')}
            return {"success": True, "result": output or "Executed successfully"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, code: str) -> Dict[str, Any]:
        """Execute code with timeout.

        Returns:
            {"success": bool, "result": Any, "error": Optional[str]}
        """
        # Validate first
        is_valid, error = self.validate_code(code)
        if not is_valid:
            return {"success": False, "error": error}

        # Execute with timeout
        try:
            future = self.executor.submit(self._execute_restricted, code)
            return future.result(timeout=self.timeout)
        except TimeoutError:
            return {"success": False, "error": f"Execution timed out after {self.timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_with_retry(
        self,
        query: str,
        llm_client,
        template_loader,
        language: str = None
    ) -> Dict[str, Any]:
        """Generate and execute code with self-correction loop.

        Args:
            query: User query describing computation
            llm_client: LLM service for code generation
            template_loader: For rendering prompts
            language: Language for prompts

        Returns:
            {"success": bool, "result": Any, "code": str, "attempts": int}
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            # Generate code
            prompt = template_loader.render(
                "code_gen.j2",
                language=language,
                query=query,
                previous_error=last_error
            )

            code = await llm_client.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=200
            )

            # Extract code from response (handle markdown blocks)
            code = self._extract_code(code)

            logger.info(f"Attempt {attempt}: Generated code:\n{code}")

            # Execute
            result = self.execute(code)

            if result["success"]:
                return {
                    "success": True,
                    "result": result["result"],
                    "code": code,
                    "attempts": attempt
                }

            last_error = result["error"]
            logger.warning(f"Attempt {attempt} failed: {last_error}")

        return {
            "success": False,
            "error": last_error,
            "attempts": self.max_retries
        }

    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response."""
        import re

        # Try to extract from markdown code block
        match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try generic code block
        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Return as-is (might be raw code)
        return response.strip()
```

### Task 4.3: Create Code Generation Template (0.1d)

**File**: `app/services/query_router/templates/en/code_gen.j2`

```jinja2
Generate Python code to solve this problem.

RULES:
- Store final answer in variable named 'result'
- Use only: math, statistics, Decimal, basic Python
- NO file operations, NO network calls, NO imports
- NO placeholders (TODO, ..., pass)
- Return complete, executable code

{% if previous_error %}
Previous attempt failed with: {{ previous_error }}
Fix the error and try again.
{% endif %}

Problem: {{ query }}

Python code (no markdown, just code):
```

**File**: `app/services/query_router/templates/vi/code_gen.j2`

```jinja2
Tao ma Python de giai quyet van de nay.

QUY TAC:
- Luu ket qua vao bien 'result'
- Chi dung: math, statistics, Decimal, Python co ban
- KHONG doc/ghi file, KHONG goi mang, KHONG import
- KHONG dung placeholder (TODO, ..., pass)
- Tra ve code hoan chinh, chay duoc

{% if previous_error %}
Lan truoc loi: {{ previous_error }}
Sua loi va thu lai.
{% endif %}

Bai toan: {{ query }}

Ma Python (khong markdown, chi code):
```

### Task 4.4: Implement code_execute_node (0.2d)

**Update**: `app/services/query_router/graph.py`

```python
from app.services.query_router.code_executor import CodeExecutor

async def code_execute_node(state: QueryState, config=None) -> QueryState:
    """Execute code for computational queries."""
    query = state["query"]

    llm = config.get("configurable", {}).get("llm")
    template_loader = config.get("configurable", {}).get("template_loader")

    if not llm or not template_loader:
        return {**state, "error": "Missing services for code execution"}

    executor = CodeExecutor(timeout=5, max_retries=5)

    result = await executor.execute_with_retry(
        query=query,
        llm_client=llm,
        template_loader=template_loader
    )

    if result["success"]:
        return {
            **state,
            "context": [{
                "type": "computation",
                "result": str(result["result"]),
                "code": result["code"],
                "attempts": result["attempts"]
            }]
        }
    else:
        # Fallback: let generate node handle without computation
        logger.warning(f"Code execution failed: {result['error']}")
        return {
            **state,
            "context": [{
                "type": "computation_failed",
                "error": result["error"]
            }]
        }
```

### Task 4.5: Update Graph Routing (0.1d)

**Update**: `app/services/query_router/graph.py`

```python
def route_query(state: QueryState) -> str:
    classification = state["classification"]
    if classification is None or state.get("error"):
        return END

    query_type = classification.query_type

    routing = {
        QueryType.RAG: "retrieve",
        QueryType.MULTI_HOP: "react",
        QueryType.CODE_EXECUTION: "code_execute",  # NEW
        QueryType.DIRECT: "generate",
        QueryType.CLARIFICATION: "clarify"
    }
    return routing.get(query_type, "retrieve")


def build_query_graph():
    graph = StateGraph(QueryState)

    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("react", react_node)
    graph.add_node("code_execute", code_execute_node)  # NEW
    graph.add_node("generate", generate_node)
    graph.add_node("clarify", clarify_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        route_query,
        {
            "retrieve": "retrieve",
            "react": "react",
            "code_execute": "code_execute",  # NEW
            "generate": "generate",
            "clarify": "clarify",
            END: END
        }
    )

    # code_execute -> generate
    graph.add_edge("code_execute", "generate")
    # ... rest unchanged
```

## Test Coverage

**File**: `tests/unit/test_code_executor.py`

```python
import pytest
from app.services.query_router.code_executor import CodeExecutor

class TestCodeExecutor:
    @pytest.fixture
    def executor(self):
        return CodeExecutor(timeout=2, max_retries=3)

    def test_validate_rejects_placeholders(self, executor):
        is_valid, error = executor.validate_code("result = TODO")
        assert not is_valid
        assert "placeholder" in error.lower()

    def test_validate_rejects_syntax_errors(self, executor):
        is_valid, error = executor.validate_code("result = ")
        assert not is_valid
        assert "syntax" in error.lower()

    def test_execute_simple_math(self, executor):
        result = executor.execute("result = 2450 * 0.15")
        assert result["success"]
        assert result["result"] == 367.5

    def test_execute_timeout(self, executor):
        result = executor.execute("while True: pass")
        assert not result["success"]
        assert "timeout" in result["error"].lower()

    def test_execute_blocks_file_access(self, executor):
        result = executor.execute("result = open('/etc/passwd').read()")
        assert not result["success"]

    def test_execute_blocks_imports(self, executor):
        result = executor.execute("import os; result = os.listdir('/')")
        assert not result["success"]

    def test_extract_code_from_markdown(self, executor):
        response = "```python\nresult = 42\n```"
        code = executor._extract_code(response)
        assert code == "result = 42"
```

## Success Criteria

- [ ] CODE_EXECUTION added to QueryType
- [ ] CodeExecutor validates and executes safely
- [ ] Timeout enforced at 5 seconds
- [ ] RestrictedPython blocks dangerous operations
- [ ] Self-correction retry loop works
- [ ] code_execute_node integrated in graph
- [ ] Tests pass with >80% coverage
- [ ] Success rate >85% on computational queries

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| RestrictedPython bypass | Very Low | Limited globals, no imports |
| Timeout not enforced | Low | ThreadPoolExecutor with strict timeout |
| LLM generates unsafe code | Medium | Validation layer before execution |

## Security Considerations

1. **RestrictedPython**: No arbitrary Python execution
2. **Whitelist globals**: Only math/statistics modules
3. **No imports**: compile_restricted blocks import statements
4. **Timeout**: Prevents infinite loops
5. **AST validation**: Catches syntax issues before execution
6. **Placeholder check**: Prevents incomplete code execution
