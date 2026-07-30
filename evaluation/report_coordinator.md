# Agent Evaluation Results Analysis

**Generated**: 2026-07-25 15:39:26
**Dataset**: 17 queries evaluated
**Scorers**: 5 (ExpectationsMet, Faithfulness, ResponseQuality, criteria, expected_route)

## Overall Pass Rates

  ExpectationsMet                 23.5% (4/17) ✗
  Faithfulness                    29.4% (5/17) ✗
  ResponseQuality                 76.5% (13/17) ⚠
  criteria                         0.0% (0/17) ✗
  expected_route                   0.0% (0/17) ✗


**Average Pass Rate**: 25.9%


## Failure Patterns Detected

### 1. Multi-Failure Queries [CRITICAL]

**Description**: Queries failing 3 or more scorers — need comprehensive fixes

**Affected Queries**: 1

- **Query**: "unknown"
  - Failed scorers: ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, ExpectationsMet, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, Faithfulness, ResponseQuality, ResponseQuality, ResponseQuality, ResponseQuality, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, criteria, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route, expected_route


## Recommendations

### 1. Fix multi-failure queries [CRITICAL]

- **Issue**: 1 queries failing multiple scorers
- **Expected Impact**: Critical for baseline quality
- **Effort**: High

### 2. Improve ExpectationsMet performance [HIGH]

- **Issue**: Only 23.5% pass rate (4/17)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

### 3. Improve Faithfulness performance [HIGH]

- **Issue**: Only 29.4% pass rate (5/17)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

### 4. Improve criteria performance [HIGH]

- **Issue**: Only 0.0% pass rate (0/17)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

### 5. Improve expected_route performance [HIGH]

- **Issue**: Only 0.0% pass rate (0/17)
- **Expected Impact**: Will improve overall evaluation quality
- **Effort**: Medium

### 6. Improve ResponseQuality performance [MEDIUM]

- **Issue**: Only 76.5% pass rate (13/17)
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
