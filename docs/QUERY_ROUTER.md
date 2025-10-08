# QUERY_ROUTER.md

This file provides guidance to Claude Code (claude.ai/code) when implementing input query routing this repository.

## 🧠 LangGraph Query Router

### **Purpose**
The LangGraph agent analyzes incoming queries to determine the optimal response strategy:
- **Direct Answer**: Simple factual questions, greetings, math problems
- **RAG Retrieval**: Domain-specific queries requiring document context

### **Benefits**
- **Reduced Latency**: Skip vector DB lookup for simple queries
- **Cost Optimization**: Minimize unnecessary embeddings and searches
- **Better UX**: Faster responses for straightforward questions
- **Resource Efficiency**: Lower load on Qdrant and embedding service

### **Classification Criteria**

```python
# Examples requiring RAG
- "What are the technical specifications in document XYZ?"
- "Summarize the Q4 financial report"
- "Find all mentions of project deadlines"
- "Compare policies between department A and B"

# Examples NOT requiring RAG (Direct answer)
- "What is 2 + 2?"
- "Hello, how are you?"
- "What is the capital of France?"
- "Explain what a RAG system is"
```

### **LangGraph State Graph**

```
START
  ↓
[Classify Query]
  ↓
  ├─> is_rag_needed = True  → [Retrieve Context] → [Generate with Context]
  └─> is_rag_needed = False → [Generate Direct]
                                        ↓
                                    [Return]
                                        ↓
                                      END
```

### **Implementation Components**

1. **Query Classifier** (`langgraph_agent.py`)
   - Uses LLM to classify query intent
   - Returns boolean: `requires_retrieval`
   - Includes confidence score

2. **State Graph** (`graph.py`)
   - Defines routing logic
   - Manages conversation state
   - Handles multi-turn interactions

3. **Prompts** (`prompts.py`)
   - Classification system prompts
   - Few-shot examples
   - Chain-of-thought reasoning

### **Metrics to Track**
- **Classification accuracy**: % correct routing decisions
- **Latency savings**: Direct vs RAG response times
- **RAG precision**: % of RAG queries that needed retrieval
- **User satisfaction**: Feedback on response quality
