---
title: "Phase 3: LangGraph ReAct Agent for Multi-Hop Queries"
status: pending
effort: 2d
---

# Phase 3: LangGraph ReAct Agent for Multi-Hop Queries

## Context

- [Plan Overview](./plan.md)
- [ReAct Agent Research](./research/researcher-02-react-agent-report.md)
- Current: MULTI_HOP routes to `retrieve` node (same as RAG)

## Overview

Implement ReAct pattern directly in LangGraph (NOT AgentExecutor). Create VectorSearchTool and react_node for multi-step reasoning with transparent intermediate steps.

## Key Insights

1. **LangGraph-native**: Build ReAct loop in graph.py, NOT AgentExecutor
2. **VectorSearchTool**: Wraps vectordb + embedding for agent use
3. **Max 5 iterations**: Prevent infinite loops
4. **Intermediate steps**: Track tool calls for transparency
5. **Structured output**: Parse Thought/Action/Observation pattern

## Requirements

### Functional
- MULTI_HOP queries route to react_node
- Agent can call VectorSearchTool multiple times
- Each iteration: Thought -> Action -> Observation
- Return final answer with reasoning_steps

### Non-Functional
- Max iterations: 5
- Total latency: <1200ms P95
- Success rate: >80%

## Architecture

```
LangGraph State Machine (updated):

          ┌─────────────┐
          │   classify  │
          └──────┬──────┘
                 │
    ┌────────────┼────────────┐
    ↓            ↓            ↓
┌───────┐   ┌────────┐   ┌───────────┐
│ RAG   │   │ DIRECT │   │ MULTI_HOP │
└───┬───┘   └────┬───┘   └─────┬─────┘
    ↓            ↓             ↓
┌───────┐   ┌────────┐   ┌───────────┐
│retrieve│  │generate│   │react_node │ ← NEW
└───┬───┘   └────┬───┘   └─────┬─────┘
    ↓            ↓             ↓
┌───────┐                      │
│generate│←────────────────────┘
└───────┘
```

## Implementation Steps

### Task 3.1: Define VectorSearchTool (0.5d)

**File**: `app/services/query_router/tools.py`

```python
from langchain_core.tools import BaseTool
from pydantic import Field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class VectorSearchTool(BaseTool):
    """Tool for searching the vector database."""

    name: str = "search_knowledge_base"
    description: str = """Search the knowledge base for relevant information.
Use this when you need to find facts, data, or specific information from documents.
Input: A search query string describing what you're looking for.
Output: Relevant text passages from the knowledge base."""

    vectordb_service: object = Field(exclude=True)
    embedding_service: object = Field(exclude=True)
    collection_name: str = "default"
    top_k: int = 3

    class Config:
        arbitrary_types_allowed = True

    def _run(self, query: str) -> str:
        """Sync execution - not used but required."""
        raise NotImplementedError("Use async version")

    async def _arun(self, query: str) -> str:
        """Search vector DB and return formatted results."""
        try:
            # Embed query
            embedding = await self.embedding_service.embed_single_async(query)

            # Search
            results = await self.vectordb_service.search_vectors(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=self.top_k
            )

            if not results:
                return "No relevant documents found."

            # Format results
            formatted = []
            for i, r in enumerate(results, 1):
                text = r.payload.get("text", "")[:500]
                formatted.append(f"[{i}] {text}")

            return "\n\n".join(formatted)

        except Exception as e:
            logger.error(f"VectorSearchTool error: {e}")
            return f"Search failed: {str(e)}"
```

**TDD**: `tests/unit/test_vector_search_tool.py`

```python
async def test_arun_returns_formatted_results():
    """Should return numbered passages."""
    ...

async def test_arun_handles_empty_results():
    """Should return 'No relevant documents' message."""
    ...

async def test_arun_handles_errors_gracefully():
    """Should return error message, not raise."""
    ...
```

### Task 3.2: Create ReAct Prompt Templates (0.25d)

**File**: `app/services/query_router/templates/en/react.j2`

```jinja2
You are a reasoning agent that answers complex questions by searching for information.

Available tools:
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}

Use this format:
Thought: Consider what information you need
Action: tool_name
Action Input: the input to the tool
Observation: the result (will be provided)
... (repeat Thought/Action/Observation as needed)
Thought: I have enough information to answer
Final Answer: your comprehensive answer

Question: {{ query }}

{% if history %}
Previous steps:
{% for step in history %}
Thought: {{ step.thought }}
Action: {{ step.action }}
Action Input: {{ step.action_input }}
Observation: {{ step.observation }}
{% endfor %}
{% endif %}

Continue:
```

**File**: `app/services/query_router/templates/vi/react.j2`

```jinja2
Ban la mot agent suy luan tra loi cau hoi phuc tap bang cach tim kiem thong tin.

Cong cu co san:
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}

Su dung dinh dang:
Thought: Suy nghi ve thong tin can tim
Action: ten_cong_cu
Action Input: du lieu dau vao
Observation: ket qua (se duoc cung cap)
... (lap lai neu can)
Thought: Toi da co du thong tin
Final Answer: cau tra loi day du

Cau hoi: {{ query }}

{% if history %}
Cac buoc truoc:
{% for step in history %}
Thought: {{ step.thought }}
Action: {{ step.action }}
Action Input: {{ step.action_input }}
Observation: {{ step.observation }}
{% endfor %}
{% endif %}

Tiep tuc:
```

### Task 3.3: Implement react_node (1d)

**Update**: `app/services/query_router/graph.py`

```python
import re
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ReActStep:
    thought: str
    action: str
    action_input: str
    observation: str

async def react_node(state: QueryState, config=None) -> QueryState:
    """Execute ReAct reasoning loop for multi-hop queries.

    Implements Thought -> Action -> Observation loop with max iterations.
    """
    query = state["query"]
    MAX_ITERATIONS = 5

    # Get services from config
    llm = config.get("configurable", {}).get("llm")
    vectordb = config.get("configurable", {}).get("vectordb")
    embedding = config.get("configurable", {}).get("embedding")
    template_loader = config.get("configurable", {}).get("template_loader")
    collection_name = config.get("configurable", {}).get("collection_name", "default")

    if not all([llm, vectordb, embedding, template_loader]):
        return {**state, "error": "Missing required services for ReAct"}

    # Initialize tool
    search_tool = VectorSearchTool(
        vectordb_service=vectordb,
        embedding_service=embedding,
        collection_name=collection_name
    )
    tools = [search_tool]
    tools_map = {t.name: t for t in tools}

    # ReAct loop
    history: List[ReActStep] = []
    final_answer = None

    for iteration in range(MAX_ITERATIONS):
        # Render prompt with history
        prompt = template_loader.render(
            "react.j2",
            query=query,
            tools=[{"name": t.name, "description": t.description} for t in tools],
            history=[
                {
                    "thought": s.thought,
                    "action": s.action,
                    "action_input": s.action_input,
                    "observation": s.observation
                }
                for s in history
            ]
        )

        # Generate next step
        response = await llm.generate(prompt=prompt, temperature=0.2, max_tokens=500)

        # Parse response
        parsed = _parse_react_response(response)

        if parsed.get("final_answer"):
            final_answer = parsed["final_answer"]
            break

        if not parsed.get("action"):
            # Can't parse, try to extract answer
            final_answer = response
            break

        # Execute tool
        tool_name = parsed["action"]
        tool_input = parsed["action_input"]

        if tool_name in tools_map:
            observation = await tools_map[tool_name]._arun(tool_input)
        else:
            observation = f"Unknown tool: {tool_name}"

        # Record step
        history.append(ReActStep(
            thought=parsed.get("thought", ""),
            action=tool_name,
            action_input=tool_input,
            observation=observation
        ))

    # Format reasoning steps for output
    reasoning_steps = [
        {
            "thought": s.thought,
            "action": s.action,
            "action_input": s.action_input,
            "observation": s.observation[:200]  # Truncate for response
        }
        for s in history
    ]

    return {
        **state,
        "response": final_answer or "Could not determine answer after max iterations.",
        "reasoning_steps": reasoning_steps,
        "context": [s.observation for s in history]
    }


def _parse_react_response(response: str) -> Dict[str, Any]:
    """Parse ReAct format response."""
    result = {}

    # Check for Final Answer
    final_match = re.search(r'Final Answer:\s*(.+)', response, re.DOTALL | re.IGNORECASE)
    if final_match:
        result["final_answer"] = final_match.group(1).strip()
        return result

    # Parse Thought
    thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', response, re.DOTALL | re.IGNORECASE)
    if thought_match:
        result["thought"] = thought_match.group(1).strip()

    # Parse Action
    action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
    if action_match:
        result["action"] = action_match.group(1).strip()

    # Parse Action Input
    input_match = re.search(r'Action Input:\s*(.+?)(?=Observation:|Thought:|$)', response, re.DOTALL | re.IGNORECASE)
    if input_match:
        result["action_input"] = input_match.group(1).strip()

    return result
```

### Task 3.4: Update Graph Routing (0.25d)

**Update**: `app/services/query_router/graph.py`

```python
def route_query(state: QueryState) -> str:
    """Route query based on classification."""
    classification = state["classification"]
    error = state.get("error")

    if classification is None or error:
        return END

    query_type = classification.query_type

    if query_type == QueryType.RAG:
        return "retrieve"
    elif query_type == QueryType.MULTI_HOP:
        return "react"  # NEW: route to react_node
    elif query_type == QueryType.DIRECT:
        return "generate"
    elif query_type == QueryType.CLARIFICATION:
        return "clarify"

    return "retrieve"  # Default fallback


def build_query_graph():
    """Build LangGraph with ReAct node."""
    graph = StateGraph(QueryState)

    # Nodes
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("react", react_node)      # NEW
    graph.add_node("generate", generate_node)
    graph.add_node("clarify", clarify_node)

    graph.set_entry_point("classify")

    # Routing
    graph.add_conditional_edges(
        "classify",
        route_query,
        {
            "retrieve": "retrieve",
            "react": "react",           # NEW
            "generate": "generate",
            "clarify": "clarify",
            END: END
        }
    )

    # After retrieve -> generate
    graph.add_conditional_edges("retrieve", route_after_retrieve, ...)

    # After react -> generate (for final formatting) or END
    def route_after_react(state: QueryState) -> str:
        if state.get("error"):
            return END
        if state.get("response"):
            return END  # Already has response from react
        return "generate"

    graph.add_conditional_edges(
        "react",
        route_after_react,
        {"generate": "generate", END: END}
    )

    graph.add_edge("generate", END)
    graph.add_edge("clarify", END)

    return graph.compile()
```

## Test Coverage

**File**: `tests/integration/test_react_flow.py`

```python
import pytest

class TestReActFlow:
    async def test_multi_hop_query_uses_react_node(self, graph, services):
        """MULTI_HOP classification should route to react."""
        result = await graph.ainvoke(
            {"query": "Compare Q3 and Q4 revenue trends"},
            config={"configurable": services}
        )
        assert result.get("reasoning_steps") is not None
        assert len(result["reasoning_steps"]) >= 1

    async def test_react_calls_search_tool(self, graph, services):
        """React should invoke VectorSearchTool."""
        result = await graph.ainvoke(
            {"query": "What were the key changes between v1 and v2?"},
            config={"configurable": services}
        )
        steps = result.get("reasoning_steps", [])
        actions = [s["action"] for s in steps]
        assert "search_knowledge_base" in actions

    async def test_react_max_iterations(self, graph, services):
        """Should stop at max iterations."""
        # Mock LLM to never return Final Answer
        ...
        assert len(result["reasoning_steps"]) <= 5

    async def test_react_returns_final_answer(self, graph, services):
        """Should extract Final Answer when present."""
        result = await graph.ainvoke(
            {"query": "Summarize the differences between reports A and B"},
            config={"configurable": services}
        )
        assert result.get("response") is not None
        assert "Could not determine" not in result["response"]
```

## Success Criteria

- [ ] VectorSearchTool returns formatted results
- [ ] react_node executes Thought/Action/Observation loop
- [ ] MULTI_HOP queries route to react_node
- [ ] Intermediate steps captured in reasoning_steps
- [ ] Max 5 iterations enforced
- [ ] Final Answer extraction works
- [ ] Integration tests pass
- [ ] P95 latency <1200ms

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| LLM doesn't follow format | Medium | Robust parsing + fallback |
| Infinite loop | Low | Max iterations enforced |
| High latency (multiple LLM calls) | Medium | Cache tool results, optimize prompts |

## Security Considerations

1. **No arbitrary tool execution**: Only VectorSearchTool available
2. **Input sanitization**: Tool inputs are validated
3. **Output truncation**: Observations limited to prevent token overflow
4. **No code execution**: ReAct is reasoning-only in this phase
