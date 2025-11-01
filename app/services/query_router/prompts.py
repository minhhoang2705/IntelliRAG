"""Classification prompts for query routing.
"""

CLASSIFICATION_SYSTEM_PROMPT = """You are a query classifier for a RAG (Retrieval-Augmented Generation) system.

Your task is to classify user queries into one of these categories:

1. **RAG** - Query requires retrieving information from specific documents
   - Examples: "What does the Q4 report say?", "Summarize the contract terms"

2. **DIRECT** - Query can be answered directly without document retrieval
   - Examples: "What is Python?", "How do I reverse a list?", "Hello, how are you?"

3. **CLARIFICATION** - Query is ambiguous or needs more information
   - Examples: "Tell me about it", "What do you think?", "Can you help?"

4. **MULTI_HOP** - Query requires multiple reasoning steps across documents
   - Examples: "Compare revenue trends in Q3 and Q4", "How do these three contracts differ?"

Respond ONLY with valid JSON in this exact format:
{"query_type": "rag|direct|clarification|multi_hop", "confidence": 0.0-1.0, "reasoning": "brief explanation"}"""


FEW_SHOT_EXAMPLES = [
    {
        "query": "What is the capital of France?",
        "response": '{"query_type": "direct", "confidence": 0.98, "reasoning": "General knowledge question, no documents needed"}'
    },
    {
        "query": "What does our privacy policy say about data retention?",
        "response": '{"query_type": "rag", "confidence": 0.95, "reasoning": "Asks about specific document content (privacy policy)"}'
    },
    {
        "query": "Tell me more",
        "response": '{"query_type": "clarification", "confidence": 0.92, "reasoning": "Vague reference without context, needs clarification"}'
    },
    {
        "query": "Compare the pricing models in contract A vs contract B",
        "response": '{"query_type": "multi_hop", "confidence": 0.90, "reasoning": "Requires retrieving and comparing multiple documents"}'
    }
]


def build_classification_prompt(query: str) -> str:
    """Build the full classification prompt with few-shot examples.

    Args:
        query: User query to classify

    Returns:
        Formatted prompt string
    """
    examples_text = "\n\n".join([
        f"Query: {ex['query']}\nResponse: {ex['response']}"
        for ex in FEW_SHOT_EXAMPLES
    ])

    prompt = f"""{CLASSIFICATION_SYSTEM_PROMPT}

Here are some examples:

{examples_text}

Now classify this query:
Query: {query}
Response:"""

    return prompt
