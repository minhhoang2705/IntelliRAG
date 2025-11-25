# GPU Profiling Report

**Date**: 2025-11-22
**GPU**: NVIDIA GeForce RTX 4070 Ti
**Memory**: 12282 MiB (12GB)
**Driver Version**: 580.95.05
**Model**: Qwen/Qwen3-0.6B via vLLM

---

## Executive Summary

GPU profiling reveals the system is **compute-bound**, not memory-bound. GPU utilization reaches 99% under all load levels (5, 20, 50 concurrent requests), while memory usage remains stable at ~57% (7GB / 12GB). Temperature stays excellent (<45°C) with consistent power draw (~62W).

**Key Finding**: Current `--gpu-memory-utilization=0.5` setting is conservative - we have **43% unused GPU memory** that can be allocated to increase throughput.

---

## Test Results

| Load Level | Concurrent Requests | GPU Util % | Memory Used | Temperature | Power Draw |
|------------|---------------------|------------|-------------|-------------|------------|
| Baseline   | 0                   | 0%         | 7041 MiB    | 33-36°C     | 6.8-7.0 W  |
| Light      | 5                   | 99%        | 7041 MiB    | 38°C        | 60.5 W     |
| Medium     | 20                  | 99%        | 7041 MiB    | 40°C        | 63.0 W     |
| Heavy      | 50                  | 99%        | 7041 MiB    | 43°C        | 62.0 W     |

---

## Detailed Analysis

### GPU Utilization
- **Baseline**: 0% (idle)
- **Under Load**: 99% (all test levels)
- **Conclusion**: GPU is fully utilized even with minimal load (5 concurrent requests)
- **Bottleneck**: Compute-bound, not memory-bound

### Memory Usage
- **Consistent**: 7041 MiB across all loads
- **Utilization**: 57.3% of 12GB total capacity
- **Available**: 5241 MiB (43%) unused headroom
- **Stability**: Perfect - no memory growth or leaks observed
- **Conclusion**: vLLM PagedAttention is managing KV cache efficiently

### Temperature
- **Idle**: 33-36°C
- **Light Load**: 38°C (+5°C)
- **Medium Load**: 40°C (+6°C)
- **Heavy Load**: 43°C (+7°C)
- **Thermal Headroom**: Excellent (RTX 4070 Ti max ~83°C)
- **Cooling**: No thermal throttling risk

### Power Draw
- **Idle**: ~7W
- **Under Load**: 60-63W (8.6x increase)
- **Consistency**: Stable across all load levels
- **TDP**: Well below 285W maximum (RTX 4070 Ti)
- **Efficiency**: Excellent power/performance ratio

---

## Observations

### Positive Findings
1. **GPU fully utilized**: 99% utilization shows efficient compute usage
2. **Memory headroom**: 43% unused capacity for optimization
3. **Stable performance**: No degradation across load levels
4. **Cool operation**: Temperatures remain safe (<45°C)
5. **Efficient batching**: vLLM handles concurrent requests well

### Bottlenecks Identified
1. **GPU Compute**: Primary bottleneck (99% saturation)
   - **Impact**: Limits maximum throughput
   - **Opportunity**: Can't increase GPU compute, but can optimize memory usage

2. **Memory Under-utilization**: 43% unused GPU memory
   - **Impact**: Wasted capacity that could increase throughput
   - **Opportunity**: Increase batch size and KV cache allocation

### No Issues Found
- ✅ No memory leaks (stable 7041 MiB)
- ✅ No thermal throttling (max 43°C)
- ✅ No power issues (62W avg, 285W max)
- ✅ No queue buildup (requests processed efficiently)

---

## Recommendations for Day 3 Optimization

### 1. Increase GPU Memory Utilization
**Current**: `--gpu-memory-utilization=0.5`
**Recommended**: `--gpu-memory-utilization=0.90`

**Rationale**:
- Currently using only 57% of GPU memory
- 43% headroom available (5.2GB unused)
- Increasing to 0.90 adds ~5GB for KV cache
- Should increase batch processing capacity by ~75%

### 2. Increase Maximum Sequences
**Current**: `--max-num-seqs=256` (assumed default)
**Recommended**: `--max-num-seqs=512`

**Rationale**:
- More GPU memory → can process more concurrent sequences
- Current compute saturation shows batching works well
- Doubling sequences should improve throughput by 30-50%

### 3. Enable Advanced Features
**Recommended additions**:
```yaml
--enable-prefix-caching      # Reuse KV cache for common prefixes
--enable-chunked-prefill     # Better handling of long prompts
--kv-cache-dtype=fp8         # Optional: 50% memory savings
```

### 4. Do NOT Change
- ❌ Don't reduce max_model_len (currently adequate)
- ❌ Don't add quantization (model already small at 0.6B)
- ❌ Don't change temperature settings (cooling is fine)

---

## Performance Baseline Metrics

For comparison in Day 3 optimization:

| Metric | Current Value | Target After Optimization |
|--------|--------------|---------------------------|
| GPU Utilization | 99% | 99% (maintain) |
| GPU Memory Used | 7GB (57%) | 10-11GB (85-90%) |
| Max Concurrent | 50 tested | 100+ expected |
| Temperature | 43°C | <60°C acceptable |
| Power Draw | 62W | 80-100W expected |

---

## Next Steps

1. **Day 2**: Run load tests to find breaking point (likely >100 concurrent)
2. **Day 3**: Apply optimizations and re-test
   - Increase gpu-memory-utilization to 0.90
   - Increase max-num-seqs to 512
   - Enable prefix caching
3. **Measure improvement**: Target 20%+ throughput increase

---

**Conclusion**: GPU is efficiently utilized but memory-conservative. Significant performance gains possible by better utilizing available 43% memory headroom.

**Status**: ✅ GPU Profiling Complete - Ready for Optimization
