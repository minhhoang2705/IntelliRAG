# LangChain ReAct Agent Implementation Research

**Date**: 2026-01-11 | **Status**: Complete | **Coverage**: LangChain 0.2+

---

## Executive Summary

LangChain's `create_react_agent()` provides a lightweight ReAct agent factory for reasoning-then-acting workflows. However, production systems (including IntelliRAG) should prioritize **LangGraph** for stateful management, human-in-the-loop control, and advanced debugging. ReAct remains useful for simpler agent patterns.

---

## 1. create_react_agent() API

### Overview
Implements the ReAct paper pattern (Synergizing Reasoning and Acting in Language Models). Creates a prompt-based agent without explicit state management.

### Signature (LangChain 0.2+)
```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import BaseTool

agent = create_react_agent(
    llm=model,              # Must support structured output
    tools=[tool1, tool2],   # List[BaseTool]
    prompt=custom_prompt    # Optional: PromptTemplate
)
executor = AgentExecutor(agent=agent, tools=tools, max_iterations=15)
result = executor.invoke({"input": "User query"})
```

### Key Parameters
- **llm**: Must support JSON/tool-calling (vLLM OpenAI-compatible required)
- **tools**: BaseTool instances with clear docstrings
- **prompt**: ReAct-formatted PromptTemplate (auto-generated if omitted)

### Best Practices (2025)
1. **Explicit Model Configuration**: Set temperature, max_tokens, timeouts
2. **Tool Descriptions**: Clear, concise docstrings for LLM understanding
3. **Type Hints**: Enable schema generation for tool inputs
4. **Cost Budgeting**: Set max_tokens aggressively after testing
5. **Force JSON Mode**: Reduce token overhead by ~23%

---

## 2. AgentExecutor Configuration

### Critical Parameters

| Parameter | Default | Purpose | Recommendation |
|-----------|---------|---------|-----------------|
| `max_iterations` | 15 | Max reasoning steps | Set based on task complexity; 10-25 typical |
| `handle_parsing_errors` | False | Error recovery strategy | Use `True` + custom string for production |
| `verbose` | False | Debug output | Enable in dev, disable in production |
| `return_intermediate_steps` | False | Track reasoning chain | Enable for transparency/observability |

### handle_parsing_errors Strategies
```python
# Strategy 1: Raise error (default)
executor = AgentExecutor(handle_parsing_errors=False)

# Strategy 2: Send error back to LLM
executor = AgentExecutor(handle_parsing_errors=True)

# Strategy 3: Custom error message
executor = AgentExecutor(
    handle_parsing_errors="Check output conforms to Action/Action Input syntax"
)

# Strategy 4: Callable handler
def error_handler(exc: Exception) -> str:
    return f"Parse error: {str(exc)}. Try again."

executor = AgentExecutor(handle_parsing_errors=error_handler)
```

### max_iterations Safety
- **Default (15)**: Prevents infinite loops, adequate for most workflows
- **Rule**: `max_iterations >= (expected_tools_calls + 2)`
- **Monitoring**: Log iteration counts to detect inefficient reasoning patterns

---

## 3. Custom Tool Creation

### Pattern 1: @tool Decorator (Simplest)
```python
from langchain_core.tools import tool

@tool
def calculate_sum(a: int, b: int) -> int:
    """Add two numbers and return result."""
    return a + b

# Auto-generates schema, handles conversion
```

### Pattern 2: BaseTool Subclass (Advanced)
```python
from langchain_core.tools import BaseTool
from typing import Optional

class CustomSearchTool(BaseTool):
    name: str = "search"
    description: str = "Search knowledge base"

    def _run(self, query: str) -> str:
        # Synchronous execution
        return search_kb(query)

    async def _arun(self, query: str) -> str:
        # Async execution for better throughput
        return await async_search_kb(query)
```

### Tool Best Practices
1. **Strict Input Validation**: Parse/validate before execution
2. **Clear Docstrings**: Tool description critical for LLM decision-making
3. **Type Hints**: Required for schema generation (`int`, `str`, `List[str]`)
4. **Error Handling**: Never let tool errors crash executor
5. **Async Support**: Implement `_arun()` for non-blocking operations
6. **Result Formatting**: Return strings/JSON, not raw objects

---

## 4. PythonREPLTool Safe Execution

### Overview
PythonREPLTool executes arbitrary Python code. High security risk.

### Safe Configuration
```python
from langchain_experimental.tools import PythonREPLTool

# ⚠️ NOT recommended for untrusted input
tool = PythonREPLTool()

# ✅ Better: Sandbox with RestrictedPython
from restricted_python import compile_restricted

code = "result = 2 + 2"
compiled = compile_restricted(code, '<string>', 'exec')
# Only allows safe operations
```

### Security Constraints (Must Implement)
- **No file system access** (disable `open()`, `os.system()`)
- **No network calls** (block `requests`, `urllib`)
- **No module imports** (restrict `__import__`)
- **Timeout** (set execution timeout to 5-10s)
- **Input validation** (audit LLM-generated code before execution)

### IntelliRAG Recommendation
**Avoid PythonREPLTool** in production. Use structured tools instead (search, compute, retrieval). If code execution needed, implement in isolated container with strict allowlist.

---

## 5. Extracting intermediate_steps for Transparency

### Enable Collection
```python
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    return_intermediate_steps=True,
    max_iterations=15
)

result = executor.invoke({"input": "query"})
# result.get("intermediate_steps") == [
#     (AgentAction(tool, tool_input), tool_output),
#     ...
# ]
```

### Transparency Pattern
```python
def format_reasoning_chain(result: Dict) -> str:
    """Format agent reasoning for user visibility"""
    chain = []
    for action, observation in result.get("intermediate_steps", []):
        chain.append(f"Thought: {action.log}")
        chain.append(f"Action: {action.tool} → {action.tool_input}")
        chain.append(f"Result: {observation}")
    return "\n".join(chain)
```

### Observability Integration
- **Jaeger/Tracing**: Log each tool invocation as separate span
- **Prometheus**: Track tool call counts, latencies per tool
- **Structured Logs**: Include intermediate_steps in JSON logs for analysis

---

## Production Readiness Assessment

| Factor | Status | Recommendation |
|--------|--------|-----------------|
| **ReAct for IntelliRAG** | ⚠️ Limited Use | Use LangGraph instead (already implemented in query routing) |
| **Tool Creation** | ✅ Ready | @tool decorator for simple RAG tools; BaseTool for complex logic |
| **Error Handling** | ✅ Ready | Set `handle_parsing_errors=True` + custom message |
| **Transparency** | ✅ Ready | Enable `return_intermediate_steps` + structured logging |
| **Security** | ⚠️ Caution | Avoid PythonREPLTool; use structured tools only |

---

## Implementation Roadmap for IntelliRAG

1. **Audit Existing Query Router**: Verify LangGraph implementation (already done per codebase)
2. **Tool Standardization**: Refactor all RAG tools to BaseTool pattern if needed
3. **Error Recovery**: Update AgentExecutor configs with safe `handle_parsing_errors`
4. **Tracing Integration**: Log `intermediate_steps` to Jaeger/Prometheus
5. **Documentation**: Add tool creation guide to developer docs

---

## Sources

- [LangChain create_react_agent Documentation](https://python.langchain.com/api_reference/langchain/agents/langchain.agents.react.agent.create_react_agent.html)
- [LangGraph ReAct Agent from Scratch](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/)
- [AgentExecutor API Reference](https://python.langchain.com/api_reference/langchain/agents/langchain.agents.agent.AgentExecutor.html)
- [Handle Parsing Errors Guide](https://python.langchain.com/v0.1/docs/modules/agents/how_to/handle_parsing_errors/)
- [BaseTool Documentation](https://python.langchain.com/api_reference/core/tools/langchain_core.tools.base.BaseTool.html)
- [PythonREPLTool API](https://api.python.langchain.com/en/latest/tools/langchain_experimental.tools.python.tool.PythonREPLTool.html)
- [LangChain Tools Guide (Pinecone)](https://www.pinecone.io/learn/series/langchain/langchain-tools/)

---

## Unresolved Questions

1. Should IntelliRAG adopt ReAct or continue LangGraph-exclusive approach? (Recommend: LangGraph-exclusive based on current architecture)
2. Do existing RAG tools need refactoring to full BaseTool pattern or are @tool decorators sufficient?
3. Should PythonREPLTool be explicitly blocked in production environment config?
