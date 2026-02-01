# Autonomous Review Pod: Audit Report

**Date:** October 26, 2023
**Target:** Feature Branch (Lineage Intelligence) vs Main
**Reviewers:** Senior Software Engineer, Project Manager, Data Architect

---

## 1. Executive Summary

The "Lineage Intelligence" feature introduces significant value by providing natural language explanations and conversational capabilities over the data lineage graph. However, the current implementation suffers from code duplication in LLM interactions, uses fragile in-memory state management that poses a risk for the upcoming server migration, and relies on heuristic SQL matching that may yield inaccurate lineage results.

---

## 2. Perspective: Senior Software Engineer

**Focus:** Implementation details, DRY principles, Error Handling.

### Critique
*   **DRY Violation (Critical):** Both `LineageConversationAgent` and `LineageNarrator` implement near-identical logic for calling the LLM client, handling timeouts, catching errors, and managing fallbacks. This logic should be centralized to ensure consistent behavior and easier maintenance.
*   **Gemini Flash 3 Integration:** The current implementation uses `OllamaClient` with a default `stream=False`. While this works, the default timeout of **15 seconds** (hardcoded in multiple places) is likely too aggressive for a reasoning model like Gemini Flash 3 analyzing complex lineage graphs. This will lead to frequent `asyncio.TimeoutError`s, triggering fallbacks and degrading user experience.
*   **Error Handling:** The error handling is "graceful" in that it prevents crashes, but it swallows exceptions broadly. `LineageNarrator` does a better job of attempting to parse JSON despite noise, but this logic is coupled to the narrator rather than being a shared utility.

### Recommendations
1.  **Extract LLM Logic:** Create a `safe_llm_call` utility in `src/lineage/llm_utils.py` that handles the `asyncio.wait_for`, `try/except` blocks, and fallback mechanisms.
2.  **Configurable Timeouts:** Ensure timeouts are strictly driven by the `ModelRouter` and not hardcoded defaults in the method signatures.

---

## 3. Perspective: Project Manager

**Focus:** User Experience, Deployment, Technical Debt.

### Critique
*   **Technical Debt (High Risk):** The `LineageConversationAgent` uses an in-memory dictionary `_conversation_contexts` to store session history.
    *   **Issue:** When we migrate to the dedicated Mac Mini server (or any production environment), restarting the application service will wipe all active user conversations.
    *   **Inconsistency:** The project already has a `ChatSession` table in `src/database/models.py`, but this new feature ignores it in favor of a volatile in-memory solution.
*   **Feature Creep:** The "Conversation Agent" attempts to be a full chatbot with its own context management. This overlaps significantly with existing chat capabilities. A tighter integration with the existing `ChatSession` would reduce complexity.
*   **UX Fragility:** The "Intent Classification" relies on regex keywords (`QuestionClassifier`). While simple, it is brittle. A user asking "Where does this data originate?" works, but subtle variations might fail or misclassify, leading to frustrating "I don't understand" loops.

---

## 4. Perspective: Data Architect

**Focus:** Data Lineage, State Consistency, Dependencies.

### Critique
*   **Data Integrity:** The `LineageConversationAgent` finds relevant tables using `QueryHistory.generated_sql.ilike(f"%{table}%")`.
    *   **Issue:** This is a "fuzzy" match. Searching for table `user` will incorrectly match `user_sessions`, `payment_user_ref`, etc. This creates "phantom" lineage connections in the conversational context that do not exist in the actual schema.
*   **Architecture & Circular Dependencies:**
    *   **Good:** The `SQLLineageParser` -> `LineageGraph` -> `LineageNarrator` flow is unidirectional and clean.
    *   **Concern:** The `LineageConversationAgent` performs ad-hoc lineage analysis (regex on SQL) that is separate from the robust `SQLLineageParser`. This creates two "sources of truth" for lineage: the rigorous graph parser and the conversational agent's sloppy regex. They will inevitably disagree.

---

## 5. Proposed Fixes (Critical)

We must address the DRY violation and standardized LLM error handling immediately.

### A. New Utility: `src/lineage/llm_utils.py`

Add a `safe_llm_call` function to centralize execution logic.

```python
import asyncio
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

async def safe_llm_call(
    llm_func: Callable,
    fallback_value: str,
    timeout_seconds: float = 15.0,
    error_context: str = "LLM generation",
) -> str:
    """
    Executes an LLM generation call with standardized timeout and error handling.

    Args:
        llm_func: A coroutine function that triggers the LLM generation (e.g. client.generate)
        fallback_value: The string to return if the call fails or times out.
        timeout_seconds: Maximum time to wait for the result.
        error_context: Description of the operation for logging.

    Returns:
        The generated text or the fallback value.
    """
    try:
        response = await asyncio.wait_for(
            llm_func,
            timeout=timeout_seconds
        )
        return response.strip() if response else fallback_value
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ {error_context} timed out after {timeout_seconds}s. Using fallback.")
        return fallback_value
    except Exception as e:
        logger.error(f"❌ {error_context} failed: {e}. Using fallback.")
        return fallback_value
```

### B. Refactor: `src/lineage/lineage_narrator.py`

Refactor `generate_narrative` to use the new utility.

```python
# ... imports ...
from src.lineage.llm_utils import extract_json_object, safe_llm_call

# ... inside LineageNarrator class ...

    async def generate_narrative(
        self,
        lineage_graph: LineageGraph,
        question: Optional[str] = None,
        schema_context: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> LineageNarrative:
        # ... (setup code) ...

        effective_timeout = timeout or self.timeout_seconds

        # ... (model selection code) ...

        # Define the actual call
        generate_task = self.client.generate(
            prompt=prompt,
            temperature=0.2,
            model=model_to_use,
        )

        response_text = await safe_llm_call(
            llm_func=generate_task,
            fallback_value="",  # We handle empty response in parsing logic or pass deterministic summary here
            timeout_seconds=effective_timeout,
            error_context=f"Lineage narrative ({len(lineage_graph.nodes)} nodes)"
        )

        if not response_text:
             return self._fallback_narrative(lineage_graph, deterministic_summary)

        # Parse response
        narrative = self._parse_response(response_text, lineage_graph, deterministic_summary)
        # ...
```

### C. Refactor: `src/lineage/lineage_conversation_agent.py`

Refactor `_call_llm` to use the utility.

```python
# ... imports ...
from src.lineage.llm_utils import safe_llm_call

# ... inside LineageConversationAgent class ...

    async def _call_llm(self, prompt: str, fallback: str) -> str:
        """Call LLM with timeout and fallback using shared utility."""

        generate_task = self.client.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.3,
        )

        return await safe_llm_call(
            llm_func=generate_task,
            fallback_value=fallback,
            timeout_seconds=self.timeout_seconds,
            error_context="Lineage conversation"
        )
```

---

## 6. Future Roadmap (Mac Mini Migration)

1.  **Persist Conversation State:** Replace `_conversation_contexts` (in-memory dict) with the existing `ChatSession` database model. Use `connection_id` and `user_id` to resume sessions across server restarts.
2.  **Unified Lineage Source:** Deprecate the regex-based SQL matching in `LineageConversationAgent`. Instead, pre-process all `QueryHistory` entries using `SQLLineageParser` and store the parsed lineage (JSON) in a new `lineage_metadata` column. The agent should query this structured data.
3.  **Frontend-Backend State Sync:** Ensure the React `LineageChat` component handles connection interruptions gracefully (e.g., implementing a retry mechanism with exponential backoff) since the Mac Mini might be on a residential network or subject to maintenance reboots.
