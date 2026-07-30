# Agent Evaluation Results Analysis

**Generated**: 2026-07-25 15:39:26
**Dataset**: 13 queries evaluated
**Scorers**: 4 (Faithfulness, ExpectationsMet, ResponseQuality, criteria)

## Overall Pass Rates

  Faithfulness                     0.0% (0/13) ✗
  ExpectationsMet                  0.0% (0/13) ✗
  ResponseQuality                100.0% (13/13) ✓✓
  criteria                         0.0% (0/13) ✗


**Average Pass Rate**: 25.0%


## Failure Patterns Detected

### 1. Multi-Failure Queries [CRITICAL]

**Description**: Queries failing 3 or more scorers — need comprehensive fixes

**Affected Queries**: 1

- **Query**: "unknown"
  - Failed scorers: Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria


## Recommendations

### 1. Fix multi-failure queries [CRITICAL]

- **Issue**: 1 queries failing multiple scorers
- **Expected Impact**: Critical for baseline quality
- **Effort**: High

### 2. Improve Faithfulness performance [HIGH]

- **Issue**: Only 0.0% pass rate (0/13)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

### 3. Improve ExpectationsMet performance [HIGH]

- **Issue**: Only 0.0% pass rate (0/13)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

### 4. Improve criteria performance [HIGH]

- **Issue**: Only 0.0% pass rate (0/13)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

## Next Steps

1. Address CRITICAL and HIGH priority recommendations first
2. Re-run evaluation after implementing fixes
3. Compare results to measure improvement
4. Consider expanding dataset to cover identified gaps

---

**Report Generated**: 2026-07-25 15:39:26
**Evaluation Framework**: MLflow Agent Evaluation
