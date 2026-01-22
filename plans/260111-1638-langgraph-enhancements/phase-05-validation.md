---
title: "Phase 5: Validation Framework with RAGAS"
status: pending
effort: 1d
---

# Phase 5: Validation Framework with RAGAS

## Context

- [Plan Overview](./plan.md)
- [ADR-001](../docs/adr/001-langgraph-enhancements.md) - success metrics defined
- External Vietnamese test dataset available for benchmarking

## Overview

Implement RAGAS evaluation pipeline to measure quality improvements. Compare baseline vs enhanced system on Vietnamese test data.

## Key Insights

1. **RAGAS metrics**: context_relevancy, answer_relevancy, faithfulness
2. **Vietnamese dataset**: Convert from competition format to RAGAS format
3. **Baseline first**: Run evaluation on current system before enhancements
4. **A/B comparison**: Side-by-side baseline vs enhanced results

## Requirements

### Functional
- Convert Vietnamese test data to RAGAS Dataset format
- Evaluate baseline system (before Phase 1-4)
- Evaluate enhanced system (after Phase 1-4)
- Generate comparison report

### Non-Functional
- Context Relevance: >0.75 (target)
- Answer Relevance: >0.80 (target)
- Faithfulness: >0.85 (target)
- Vietnamese Performance: +15-25% vs baseline

## Architecture

```
Validation Pipeline:

┌─────────────────────────────────┐
│   External Vietnamese Dataset   │
│   (questions + ground truth)    │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│   convert_to_ragas_format()     │
│   - question, answer, contexts  │
│   - ground_truth                │
└───────────────┬─────────────────┘
                ↓
        ┌───────┴───────┐
        ↓               ↓
┌───────────────┐ ┌───────────────┐
│   Baseline    │ │   Enhanced    │
│   System      │ │   System      │
└───────┬───────┘ └───────┬───────┘
        ↓               ↓
┌───────────────┐ ┌───────────────┐
│ RAGAS Eval    │ │ RAGAS Eval    │
│ - context_rel │ │ - context_rel │
│ - answer_rel  │ │ - answer_rel  │
│ - faithful    │ │ - faithful    │
└───────┬───────┘ └───────┬───────┘
        └───────┬─────────┘
                ↓
┌─────────────────────────────────┐
│   Comparison Report (Markdown)  │
│   - Metric improvements         │
│   - Per-query analysis          │
│   - Recommendations             │
└─────────────────────────────────┘
```

## Implementation Steps

### Task 5.1: Create Dataset Converter (0.25d)

**File**: `tests/evaluation/dataset_converter.py`

```python
from typing import List, Dict, Any
from datasets import Dataset
import json

def load_vietnamese_dataset(path: str) -> List[Dict]:
    """Load external Vietnamese test data."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def convert_to_ragas_format(
    raw_data: List[Dict],
    rag_service,
    collection_name: str
) -> Dataset:
    """Convert test data to RAGAS Dataset format.

    Expected raw_data format:
    [
        {
            "question": "Cau hoi ve noi dung",
            "ground_truth": "Cau tra loi dung",
            "context_ids": ["doc1", "doc2"]  # Optional
        }
    ]

    Returns:
        Dataset with columns: question, answer, contexts, ground_truth
    """
    processed = []

    for item in raw_data:
        question = item["question"]
        ground_truth = item["ground_truth"]

        # Generate answer using RAG
        result = await rag_service.query_with_rag(
            query=question,
            collection_name=collection_name,
            language="vi"
        )

        # Extract contexts
        contexts = [src["text"] for src in result.get("sources", [])]

        processed.append({
            "question": question,
            "answer": result["answer"],
            "contexts": contexts,
            "ground_truth": ground_truth
        })

    return Dataset.from_dict({
        "question": [p["question"] for p in processed],
        "answer": [p["answer"] for p in processed],
        "contexts": [p["contexts"] for p in processed],
        "ground_truth": [p["ground_truth"] for p in processed]
    })
```

### Task 5.2: Create Evaluation Pipeline (0.25d)

**File**: `tests/evaluation/ragas_evaluator.py`

```python
from ragas import evaluate
from ragas.metrics import (
    context_relevancy,
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision
)
from datasets import Dataset
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

METRICS = [
    context_relevancy,
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision
]

async def evaluate_rag_system(
    dataset: Dataset,
    llm_model: str = None
) -> Dict[str, float]:
    """Run RAGAS evaluation on dataset.

    Args:
        dataset: RAGAS-format dataset
        llm_model: Model for evaluation (uses default if None)

    Returns:
        Dictionary of metric scores
    """
    try:
        result = evaluate(
            dataset=dataset,
            metrics=METRICS
        )

        scores = {
            "context_relevancy": float(result["context_relevancy"]),
            "answer_relevancy": float(result["answer_relevancy"]),
            "faithfulness": float(result["faithfulness"]),
            "context_recall": float(result["context_recall"]),
            "context_precision": float(result["context_precision"])
        }

        logger.info(f"RAGAS scores: {scores}")
        return scores

    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        raise
```

### Task 5.3: Create Comparison Script (0.25d)

**File**: `tests/evaluation/run_comparison.py`

```python
import asyncio
import json
from datetime import datetime
from pathlib import Path

from tests.evaluation.dataset_converter import (
    load_vietnamese_dataset,
    convert_to_ragas_format
)
from tests.evaluation.ragas_evaluator import evaluate_rag_system

async def run_comparison(
    dataset_path: str,
    baseline_service,
    enhanced_service,
    collection_name: str,
    output_dir: str = "reports"
):
    """Run baseline vs enhanced comparison.

    Args:
        dataset_path: Path to Vietnamese test data
        baseline_service: RAG service without enhancements
        enhanced_service: RAG service with enhancements
        collection_name: Vector DB collection
        output_dir: Directory for report output
    """
    # Load data
    raw_data = load_vietnamese_dataset(dataset_path)
    print(f"Loaded {len(raw_data)} test cases")

    # Evaluate baseline
    print("Evaluating baseline system...")
    baseline_dataset = await convert_to_ragas_format(
        raw_data, baseline_service, collection_name
    )
    baseline_scores = await evaluate_rag_system(baseline_dataset)

    # Evaluate enhanced
    print("Evaluating enhanced system...")
    enhanced_dataset = await convert_to_ragas_format(
        raw_data, enhanced_service, collection_name
    )
    enhanced_scores = await evaluate_rag_system(enhanced_dataset)

    # Generate report
    report = generate_comparison_report(
        baseline_scores,
        enhanced_scores,
        len(raw_data)
    )

    # Save report
    output_path = Path(output_dir) / f"ragas-comparison-{datetime.now().strftime('%Y%m%d-%H%M')}.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(report)
    print(f"Report saved to: {output_path}")

    return baseline_scores, enhanced_scores


def generate_comparison_report(
    baseline: Dict[str, float],
    enhanced: Dict[str, float],
    sample_size: int
) -> str:
    """Generate Markdown comparison report."""

    lines = [
        "# RAGAS Evaluation: Baseline vs Enhanced",
        f"\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Sample Size**: {sample_size} queries",
        f"**Language**: Vietnamese",
        "",
        "## Summary",
        "",
        "| Metric | Baseline | Enhanced | Delta | Target | Status |",
        "|--------|----------|----------|-------|--------|--------|"
    ]

    targets = {
        "context_relevancy": 0.75,
        "answer_relevancy": 0.80,
        "faithfulness": 0.85,
        "context_recall": 0.70,
        "context_precision": 0.70
    }

    for metric in baseline.keys():
        b = baseline[metric]
        e = enhanced[metric]
        delta = e - b
        delta_pct = (delta / b * 100) if b > 0 else 0
        target = targets.get(metric, "N/A")
        status = "PASS" if e >= target else "FAIL"

        lines.append(
            f"| {metric} | {b:.3f} | {e:.3f} | "
            f"{'+' if delta >= 0 else ''}{delta:.3f} ({delta_pct:+.1f}%) | "
            f"{target} | {status} |"
        )

    # Analysis
    lines.extend([
        "",
        "## Analysis",
        "",
        "### Improvements",
        ""
    ])

    improved = [m for m in baseline if enhanced[m] > baseline[m]]
    for m in improved:
        delta_pct = (enhanced[m] - baseline[m]) / baseline[m] * 100
        lines.append(f"- **{m}**: +{delta_pct:.1f}% improvement")

    regressed = [m for m in baseline if enhanced[m] < baseline[m]]
    if regressed:
        lines.extend(["", "### Regressions", ""])
        for m in regressed:
            delta_pct = (enhanced[m] - baseline[m]) / baseline[m] * 100
            lines.append(f"- **{m}**: {delta_pct:.1f}% regression")

    # Recommendations
    lines.extend([
        "",
        "## Recommendations",
        ""
    ])

    if enhanced.get("context_relevancy", 0) < targets["context_relevancy"]:
        lines.append("- [ ] Improve reranking prompts for better context selection")

    if enhanced.get("faithfulness", 0) < targets["faithfulness"]:
        lines.append("- [ ] Add citation verification in generation prompts")

    if all(enhanced[m] >= targets.get(m, 0) for m in enhanced):
        lines.append("- [x] All targets met. Ready for production deployment.")

    return "\n".join(lines)


if __name__ == "__main__":
    # CLI usage
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--collection", default="default")
    args = parser.parse_args()

    # Would need to initialize services here
    asyncio.run(run_comparison(args.dataset, None, None, args.collection))
```

### Task 5.4: Create Evaluation Test (0.25d)

**File**: `tests/evaluation/test_ragas.py`

```python
import pytest
from datasets import Dataset
from tests.evaluation.ragas_evaluator import evaluate_rag_system

class TestRAGASEvaluation:
    @pytest.fixture
    def sample_dataset(self):
        """Create small test dataset."""
        return Dataset.from_dict({
            "question": [
                "Bao cao Q4 noi gi ve doanh thu?",
                "Cong ty co bao nhieu nhan vien?"
            ],
            "answer": [
                "Doanh thu Q4 dat 3.1 trieu USD, tang 24% so voi Q3.",
                "Cong ty hien co 500 nhan vien."
            ],
            "contexts": [
                ["Bao cao Q4 2025: Doanh thu dat 3.1 trieu USD..."],
                ["Tong so nhan vien tinh den 12/2025: 500 nguoi."]
            ],
            "ground_truth": [
                "Doanh thu Q4 la 3.1 trieu USD.",
                "Cong ty co 500 nhan vien."
            ]
        })

    @pytest.mark.slow
    async def test_evaluate_returns_all_metrics(self, sample_dataset):
        """Should return all RAGAS metrics."""
        scores = await evaluate_rag_system(sample_dataset)

        assert "context_relevancy" in scores
        assert "answer_relevancy" in scores
        assert "faithfulness" in scores
        assert 0 <= scores["context_relevancy"] <= 1
        assert 0 <= scores["answer_relevancy"] <= 1

    @pytest.mark.slow
    async def test_high_quality_answers_score_well(self, sample_dataset):
        """High-quality answers should score above thresholds."""
        scores = await evaluate_rag_system(sample_dataset)

        # These should pass for well-crafted test data
        assert scores["faithfulness"] >= 0.7
```

## Success Criteria

- [ ] Dataset converter handles Vietnamese test data
- [ ] RAGAS evaluation runs without errors
- [ ] Comparison report generated in Markdown
- [ ] Baseline scores recorded before enhancements
- [ ] Enhanced scores show improvement:
  - Context Relevance: >0.75
  - Answer Relevance: >0.80
  - Faithfulness: >0.85
- [ ] Vietnamese performance: +15-25% vs baseline

## Report Output Example

```markdown
# RAGAS Evaluation: Baseline vs Enhanced

**Date**: 2026-01-18 14:30
**Sample Size**: 100 queries
**Language**: Vietnamese

## Summary

| Metric | Baseline | Enhanced | Delta | Target | Status |
|--------|----------|----------|-------|--------|--------|
| context_relevancy | 0.650 | 0.780 | +0.130 (+20.0%) | 0.75 | PASS |
| answer_relevancy | 0.700 | 0.820 | +0.120 (+17.1%) | 0.80 | PASS |
| faithfulness | 0.750 | 0.870 | +0.120 (+16.0%) | 0.85 | PASS |

## Analysis

### Improvements
- **context_relevancy**: +20.0% improvement
- **answer_relevancy**: +17.1% improvement
- **faithfulness**: +16.0% improvement

## Recommendations
- [x] All targets met. Ready for production deployment.
```

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| RAGAS API changes | Low | Pin version in requirements |
| Evaluation takes too long | Medium | Use sample subset for CI |
| Vietnamese LLM scoring bias | Medium | Manual spot-check samples |

## Dependencies

```
# Add to requirements-dev.txt
ragas>=0.1.0
datasets>=2.14.0
```
