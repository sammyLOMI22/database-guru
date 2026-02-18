# Action Plan: Phase 19 Refinements

Based on the technical audit, here are the recommended refinements to ensure the iteration is production-ready.

## 1. Critical Refactors (Senior Engineer)

### Move Inline Imports to Module Level
Move imports like `re`, `copy`, and `collections.Counter` to the top of `src/llm/result_narrator.py`.

```python
# Move these to the top of the file
import re
import copy
from collections import Counter
```

### Optimize Statistical Guardrails
Ensure outlier detection and trends have sufficient data before attempting analysis.

```python
# src/llm/result_narrator.py

def _detect_anomalies(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Increase threshold for meaningful anomalies
    if not results or len(results) < 5:
        return {"anomalies_found": False, "anomaly_count": 0}
    # ... rest of the logic
```

## 2. Token Budget Enforcement (Project Manager)

### Use Token Budgets for Statistics Truncation
Currently, `NARRATIVE_TOKEN_BUDGETS` is defined but not enforced. Use it to limit the size of the `statistics` string sent to the LLM.

```python
# src/llm/result_narrator.py

def _compress_statistics(self, statistics: Dict[str, Any], tier: ModelSize) -> str:
    budget = NARRATIVE_TOKEN_BUDGETS.get(tier, 1500)
    stats_str = json.dumps(statistics, indent=2, default=str)

    if len(stats_str) > budget:
        # Fallback to a more compact version if over budget
        return self._format_essential_stats(statistics)
    return stats_str
```

## 3. Data Integrity & Accuracy (Data Analyst)

### Improved Hash Fingerprint
To reduce collision risk in the `AnalyticsCache`, include a few middle rows in the hash.

```python
# src/services/analytics_cache.py

@staticmethod
def compute_result_hash(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "empty"

    # Add a middle row to the fingerprint to reduce collision risk
    mid_idx = len(results) // 2
    fingerprint = {
        "columns": sorted(results[0].keys()),
        "count": len(results),
        "first": {k: str(v) for k, v in list(results[0].items())[:5]},
        "mid": {k: str(v) for k, v in list(results[mid_idx].items())[:5]} if len(results) > 2 else {},
        "last": {k: str(v) for k, v in list(results[-1].items())[:5]},
    }
    # ... rest of hash logic
```

## 4. Feature Cohesion (Product)

### Frontend: Adaptive Scoring Notification
Let users know when a specific scoring preset (Business/Scientific) is being used for chart recommendations.

```typescript
// frontend/src/components/insights/ChartInsights.tsx

// Suggestion: Add a small badge or tooltip if preset !== 'default'
{preset !== 'default' && (
  <Badge variant="outline" title={`Using ${preset} scoring rules`}>
    Adaptive: {preset}
  </Badge>
)}
```
