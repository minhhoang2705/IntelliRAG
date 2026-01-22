---
title: "LangGraph Enhancements: Multi-Language RAG with Agentic Workflows"
description: "Implement template system, two-stage retrieval, ReAct agent, code execution, and validation"
status: pending
priority: P1
effort: 7d
branch: feature/langgraph-enhancements
tags: [langgraph, rag, multilingual, react-agent, templates]
created: 2026-01-11
---

# LangGraph Enhancements Implementation Plan

## Overview

Enhance IntelliRAG query routing with multi-language support, advanced retrieval, and agentic workflows.

**Total Effort**: 7 days (2+1+2+1+1)
**Branch**: `feature/langgraph-enhancements`
**Coverage Target**: >80%

## Phases

| Phase | Description | Effort | Status | File |
|-------|-------------|--------|--------|------|
| 1 | Template System + Language Detection | 2d | complete | [phase-01](./phase-01-template-system.md) |
| 2 | Two-Stage Retrieval (Reranking) | 1d | pending | [phase-02](./phase-02-two-stage-retrieval.md) |
| 3 | LangGraph ReAct Agent (MULTI_HOP) | 2d | pending | [phase-03](./phase-03-react-agent.md) |
| 4 | Code Execution Enhancement | 1d | pending | [phase-04](./phase-04-code-execution.md) |
| 5 | Validation Framework (RAGAS) | 1d | pending | [phase-05](./phase-05-validation.md) |

## Key Design Decisions

1. **FastText** for language detection (120k sentences/s, 176 languages)
2. **LangGraph-exclusive** - no AgentExecutor, build ReAct node in graph.py
3. **Jinja2 SandboxedEnvironment** for template security
4. **RestrictedPython + timeout** for code execution (not raw PythonREPLTool)
5. **Long-form answers** - NOT A/B/C/D format

## Success Criteria

- Context Relevance: >0.75 (RAGAS)
- Answer Relevance: >0.80 (RAGAS)
- P95 Latency: <250ms (simple queries)
- Multi-hop Success: >80%
- Test Coverage: >80%

## References

- [Research: Jinja2/LangChain](./research/researcher-01-jinja2-langchain-report.md)
- [Research: ReAct Agent](./research/researcher-02-react-agent-report.md)
- [Architecture](../docs/architecture/langgraph-enhanced-architecture.md)
- [ADR-001](../docs/adr/001-langgraph-enhancements.md)

## Unresolved Questions

~~1. FastText model path: bundle in container or download on init?~~ → **RESOLVED: Download on init**
~~2. Rerank model: same vLLM endpoint or dedicated smaller model?~~ → **RESOLVED: Dedicated smaller model**

---

## Validation Summary

**Validated**: 2026-01-11
**Questions asked**: 4

### Confirmed Decisions

| Decision | User Choice | Impact |
|----------|-------------|--------|
| FastText deployment | Download on first init | Simpler deployment, ~2s cold start acceptable |
| Rerank model | Dedicated smaller model (e.g., bge-reranker) | Better performance isolation, need to add reranker deployment |
| ReAct pattern | LangGraph-native (build in graph.py) | Confirms planned approach, no AgentExecutor |
| Vietnamese test data | Available | Phase 5 can proceed as planned |

### Action Items

- [ ] **Phase 2 update**: Add bge-reranker deployment to Phase 2 (instead of using vLLM endpoint)
- [ ] Update `phase-02-two-stage-retrieval.md` with dedicated reranker architecture
- [ ] Add KServe InferenceService for bge-reranker to kubernetes manifests

### Recommendation

**Proceed to implementation.** All key decisions validated. One minor plan adjustment needed for Phase 2 (dedicated reranker model).
