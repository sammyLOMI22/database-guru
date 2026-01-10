# 🚀 Option 2: Enhanced Observability + User Feedback Integration
## Complete Implementation Plan

> **Timeline**: 2 weeks (52-72 hours)
> **Goal**: Transparent AI system that learns from users and continuously improves
> **Status**: 📋 Ready to implement

---

## 📊 Executive Summary

This plan implements two critical features that complement your existing intelligent agents:

### Week 1: Enhanced Observability (22-30 hours)
Make the AI transparent - users see every decision the agent makes, understand query plans, and track correction attempts.

### Week 2: User Feedback Integration (30-42 hours)
Enable continuous learning - users correct queries, system learns patterns, and automatically applies knowledge to future queries.

### Why This Order?
1. **Users need visibility before they can provide good feedback**
2. **Observability is a quick win** (3-4 days) with immediate UX impact
3. **Feedback builds on observability** - users understand context when correcting
4. **Completes Phase 0** of your roadmap (6/6 features!)

---

## 🎯 Success Criteria

### Week 1 Deliverables
- [ ] Agent execution trace displayed in UI (timeline view)
- [ ] Query plan visualization with complexity, tables, joins
- [ ] Correction attempts history with error details
- [ ] Verification warnings prominently displayed
- [ ] All data returned in API response (backward compatible)

### Week 2 Deliverables
- [ ] User feedback submission (SQL corrections, issue reports)
- [ ] Feedback testing & learning integration
- [ ] SQL editor component for corrections
- [ ] Feedback stats dashboard
- [ ] E2E: Submit feedback → Learn → Auto-apply to future queries

---

# 📅 Week 1: Enhanced Observability

## Day 1: Backend - Agent Trace System (6-8 hours)

### Overview
Capture and expose the agent's decision-making process at each step.

### Task 1.1: Create AgentTrace Class

**File**: `src/llm/self_correcting_agent.py`

**Add after imports:**

```python
from typing import List, Dict, Any
from datetime import datetime

class AgentTrace:
    """
    Captures agent execution trace for transparency

    This class records each significant decision point during query processing,
    allowing users to understand what the agent did and why.
    """

    def __init__(self):
        self.steps: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()

    def add_step(
        self,
        step_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        icon: Optional[str] = None
    ):
        """
        Add a step to the execution trace

        Args:
            step_type: Type of step (analysis, planning, attempt_start, success, etc.)
            message: Human-readable message describing what happened
            metadata: Additional structured data about this step
            icon: Optional emoji icon for UI display
        """
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        self.steps.append({
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_ms": round(elapsed, 2),
            "type": step_type,
            "message": message,
            "metadata": metadata or {},
            "icon": icon or self._default_icon(step_type)
        })

        logger.debug(f"[Trace] {message} (+{elapsed:.0f}ms)")

    def _default_icon(self, step_type: str) -> str:
        """Get default emoji icon for step type"""
        icons = {
            "analysis": "🔍",
            "planning": "🧠",
            "planning_complete": "📋",
            "attempt_start": "🔧",
            "quick_fix": "⚡",
            "learned_correction": "🎓",
            "llm_correction": "🤖",
            "execution": "▶️",
            "success": "✅",
            "failure": "❌",
            "verification": "🔍",
            "warning": "⚠️"
        }
        return icons.get(step_type, "•")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        total_time = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        return {
            "total_steps": len(self.steps),
            "total_time_ms": round(total_time, 2),
            "steps": self.steps
        }

    def get_summary(self) -> str:
        """Get human-readable summary of trace"""
        total_time = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return f"Completed {len(self.steps)} steps in {total_time:.0f}ms"
```

### Task 1.2: Integrate Trace into SelfCorrectingSQLAgent

**File**: `src/llm/self_correcting_agent.py`

**Update `generate_and_execute_with_retry` method:**

```python
async def generate_and_execute_with_retry(
    self,
    question: str,
    schema: str,
    session,
    database_type: str = "postgresql",
    allow_write: bool = False,
    model: Optional[str] = None,
    schema_dict: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Generate SQL with automatic error correction and retry

    Now includes full execution trace for transparency.
    """
    # NEW: Initialize trace
    trace = AgentTrace()
    trace.add_step(
        "analysis",
        f"Analyzing query: {question[:100]}...",
        metadata={"question_length": len(question)}
    )

    attempts: List[CorrectionAttempt] = []
    last_error = None
    sql = None

    # Initialize schema-aware fixer if enabled
    if self.enable_schema_fixes:
        try:
            from src.llm.schema_aware_fixer import SchemaAwareFixer
            import json
            schema_dict = json.loads(schema) if isinstance(schema, str) else schema
            self.schema_fixer = SchemaAwareFixer(schema_dict)
            trace.add_step("setup", "Schema-aware fixer initialized", metadata={
                "num_tables": len(schema_dict.get("tables", {}))
            })
        except Exception as e:
            logger.warning(f"Failed to initialize schema-aware fixer: {e}")
            self.schema_fixer = None

    executor = SQLExecutor(
        max_rows=1000,
        timeout_seconds=30,
        allow_write=allow_write
    )

    # Try query planning first for complex queries
    query_plan = None
    if self.enable_query_planning and self.planning_agent:
        try:
            trace.add_step("planning", "🧠 Checking if query planning should be used...")

            planning_result = await self.planning_agent.plan_and_generate_sql(
                question=question,
                schema=schema,
                database_type=database_type,
                sql_generator=self.generator,
                model=model,
                schema_dict=schema_dict
            )

            if planning_result.get("used_planning"):
                query_plan = planning_result["plan"]
                trace.add_step(
                    "planning_complete",
                    f"📋 Query plan created: complexity={query_plan.complexity.value}, confidence={query_plan.confidence:.2f}",
                    metadata={
                        "complexity": query_plan.complexity.value,
                        "confidence": query_plan.confidence,
                        "num_tables": len(query_plan.tables),
                        "num_joins": len(query_plan.joins)
                    }
                )
                if planning_result.get("sql"):
                    sql = planning_result["sql"]
        except Exception as e:
            trace.add_step("warning", f"⚠️ Query planning failed, falling back to direct generation: {e}")
            logger.warning(f"Query planning failed, falling back to direct generation: {e}")

    # Main retry loop
    for attempt_num in range(1, self.max_retries + 1):
        try:
            trace.add_step(
                "attempt_start",
                f"🔧 Attempt {attempt_num}/{self.max_retries}",
                metadata={"attempt": attempt_num, "max_retries": self.max_retries}
            )

            # Generate or fix SQL
            if attempt_num == 1:
                # First attempt: generate from scratch (or use plan-based SQL)
                if sql is None:
                    trace.add_step("generation", f"Generating SQL for: {question[:50]}...")
                    gen_result = await self.generator.generate_sql(
                        question=question,
                        schema=schema,
                        database_type=database_type,
                        allow_write=allow_write,
                        model=model
                    )
                    sql = gen_result["sql"]
                else:
                    trace.add_step("generation", "Using SQL from query plan")
                    gen_result = {"sql": sql, "is_valid": True}
            else:
                # Retry: fix the error
                trace.add_step("correction", f"Attempting to fix SQL error (attempt {attempt_num})")

                # Categorize error
                error_type = self.diagnostics.categorize_error(last_error)
                error_context = self.diagnostics.extract_error_context(last_error, error_type)
                hints = self.diagnostics.generate_fix_hints(error_type, error_context)

                # Try schema-aware quick fix FIRST (fastest, no LLM call)
                quick_fix_used = False
                if self.enable_schema_fixes and self.schema_fixer:
                    from src.llm.schema_aware_fixer import QuickFix
                    quick_fix = self.schema_fixer.quick_fix(
                        sql=sql,
                        error_type=error_type,
                        error_message=last_error,
                        context=error_context
                    )

                    if quick_fix.success and quick_fix.confidence >= 0.7:
                        sql = quick_fix.fixed_sql
                        quick_fix_used = True
                        trace.add_step(
                            "quick_fix",
                            f"⚡ Quick fix applied: {quick_fix.explanation} (confidence: {quick_fix.confidence:.2f})",
                            metadata={
                                "fix_method": "schema_aware",
                                "confidence": quick_fix.confidence,
                                "explanation": quick_fix.explanation
                            }
                        )
                        # Continue to execution without LLM call

                if not quick_fix_used:
                    # Quick fix didn't work, use learned corrections or LLM
                    # Check for learned corrections
                    learned_correction = None
                    if self.learner:
                        learned_corrections = await self.learner.find_applicable_corrections(
                            error_type=error_type,
                            error_message=last_error,
                            database_type=database_type,
                            sql=sql,
                            limit=1
                        )
                        if learned_corrections:
                            learned_correction = learned_corrections[0]
                            trace.add_step(
                                "learned_correction",
                                f"🎓 Found learned correction (confidence: {learned_correction['confidence_score']:.2f})",
                                metadata={
                                    "correction_id": learned_correction['id'],
                                    "confidence": learned_correction['confidence_score']
                                }
                            )
                            hints += f"\n\nLearned correction available: {learned_correction['correction_description']}"

                    # Add hints to error message for better correction
                    enhanced_error = f"{last_error}\n\nHints:\n{hints}"

                    # Generate corrected SQL using LLM
                    trace.add_step("llm_correction", "🤖 Generating correction with LLM...")
                    fix_result = await self.generator.fix_sql_error(
                        sql=sql,
                        error=enhanced_error,
                        schema=schema,
                        database_type=database_type
                    )
                    sql = fix_result["sql"]

            # Execute SQL
            trace.add_step("execution", f"▶️ Executing SQL...")
            exec_result = await executor.execute_query(
                session=session,
                sql=sql
            )

            # Record attempt
            attempt = CorrectionAttempt(
                attempt_number=attempt_num,
                sql=sql,
                error=None if exec_result["success"] else exec_result["error"],
                error_type=ErrorType.UNKNOWN if exec_result["success"] else self.diagnostics.categorize_error(exec_result["error"]),
                success=exec_result["success"],
                execution_time_ms=exec_result.get("execution_time_ms"),
                row_count=exec_result.get("row_count")
            )
            attempts.append(attempt)

            if exec_result["success"]:
                # Success! But verify results make sense
                trace.add_step(
                    "success",
                    f"✅ Query succeeded on attempt {attempt_num}/{self.max_retries}",
                    metadata={
                        "row_count": exec_result.get("row_count"),
                        "execution_time_ms": exec_result.get("execution_time_ms")
                    }
                )

                # Verify results if enabled
                verification_result = None
                verification_warnings = []
                if self.enable_result_verification and self.verification_agent:
                    try:
                        trace.add_step("verification", "🔍 Verifying query results...")
                        verification_result = await self.verification_agent.verify_results(
                            question=question,
                            sql=sql,
                            result=exec_result,
                            schema=schema,
                            database_type=database_type
                        )

                        if verification_result.is_suspicious:
                            trace.add_step(
                                "warning",
                                f"⚠️ Suspicious results detected: {verification_result.description}",
                                metadata={
                                    "confidence": verification_result.confidence,
                                    "issue_type": verification_result.issue_type.value if verification_result.issue_type else None
                                }
                            )

                            # Run diagnostics if needed
                            diagnostics = None
                            if verification_result.diagnostic_queries:
                                trace.add_step("diagnostics", "📊 Running diagnostics...")
                                diagnostics = await self.verification_agent.run_diagnostics(
                                    sql=sql,
                                    verification=verification_result,
                                    session=session,
                                    database_type=database_type
                                )

                            # Generate improvement hints
                            hints = self.verification_agent.generate_improvement_hints(
                                question=question,
                                sql=sql,
                                verification=verification_result,
                                diagnostics=diagnostics
                            )

                            # If high confidence issue and auto-fix enabled, try to regenerate
                            if (verification_result.confidence >= 0.7 and
                                attempt_num < self.max_retries and
                                self.verification_agent.enable_auto_fix):

                                trace.add_step("regeneration", "🔧 High confidence issue detected, attempting to regenerate query...")

                                # Add verification feedback to the next attempt
                                last_error = f"Query succeeded but returned suspicious results:\n{hints}"

                                # Mark this attempt as failed verification
                                attempt.success = False
                                attempt.error = verification_result.description

                                # Continue to next attempt
                                continue
                            else:
                                # Low confidence or last attempt - return with warning
                                verification_warnings.append(
                                    f"⚠️ Result verification: {verification_result.description}"
                                )
                    except Exception as e:
                        trace.add_step("error", f"Error during result verification: {e}")
                        logger.error(f"Error during result verification: {e}")
                        verification_warnings.append(f"Result verification failed: {str(e)}")

                # Learn from this correction if it was a retry
                if attempt_num > 1 and self.learner and len(attempts) > 0:
                    # Get the original error from the first failed attempt
                    first_attempt = attempts[0]
                    if not first_attempt.success and first_attempt.error:
                        trace.add_step("learning", "✨ Learning from successful correction...")
                        await self.learner.learn_from_correction(
                            error_type=first_attempt.error_type,
                            original_sql=first_attempt.sql,
                            original_error=first_attempt.error,
                            corrected_sql=sql,
                            database_type=database_type,
                            was_successful=True
                        )

                trace.add_step("complete", f"✅ Process complete: {trace.get_summary()}")

                return {
                    "success": True,
                    "sql": sql,
                    "result": exec_result,
                    "attempts": attempts,
                    "self_corrected": attempt_num > 1,
                    "total_attempts": attempt_num,
                    "question": question,
                    "model_used": model or self.generator.settings.OLLAMA_MODEL,
                    "verification": verification_result,
                    "verification_warnings": verification_warnings,
                    "query_plan": query_plan.to_dict() if query_plan else None,
                    "used_planning": query_plan is not None,
                    "trace": trace.to_dict()  # NEW: Include trace in response
                }

            # Failed - save error for next retry
            last_error = exec_result["error"]
            trace.add_step(
                "failure",
                f"❌ Attempt {attempt_num} failed: {last_error[:100]}...",
                metadata={"error": last_error[:200]}
            )

            # If this is the last attempt, don't retry
            if attempt_num >= self.max_retries:
                break

        except Exception as e:
            logger.error(f"Exception during attempt {attempt_num}: {e}")
            trace.add_step("error", f"💥 Exception: {str(e)}")
            last_error = str(e)

            # Record failed attempt
            attempt = CorrectionAttempt(
                attempt_number=attempt_num,
                sql=sql or "",
                error=str(e),
                error_type=ErrorType.UNKNOWN,
                success=False,
                execution_time_ms=None,
                row_count=None
            )
            attempts.append(attempt)

            if attempt_num >= self.max_retries:
                break

    # All retries exhausted
    trace.add_step("complete", f"❌ Query failed after {self.max_retries} attempts")

    return {
        "success": False,
        "sql": sql or "",
        "error": last_error,
        "attempts": attempts,
        "self_corrected": len(attempts) > 1,
        "total_attempts": len(attempts),
        "question": question,
        "model_used": model or self.generator.settings.OLLAMA_MODEL,
        "message": f"Failed after {self.max_retries} attempts",
        "trace": trace.to_dict()  # NEW: Include trace even for failures
    }
```

### Task 1.3: Update Response Schemas

**File**: `src/models/schemas.py`

**Add new models:**

```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TraceStep(BaseModel):
    """A single step in agent execution trace"""
    timestamp: str
    elapsed_ms: float
    type: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    icon: Optional[str] = None

class AgentTraceResponse(BaseModel):
    """Complete agent execution trace"""
    total_steps: int
    total_time_ms: float
    steps: List[TraceStep]

class AttemptDetail(BaseModel):
    """Details of a single correction attempt"""
    attempt_number: int
    sql: str
    success: bool
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: Optional[float] = None
    row_count: Optional[int] = None

class QueryPlanSummary(BaseModel):
    """Summary of query plan for UI display"""
    complexity: str
    intent: str
    confidence: float
    reasoning: str
    tables: List[Dict[str, Any]]
    joins: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    aggregations: List[Dict[str, Any]]
    grouping: Optional[Dict[str, Any]] = None
    ordering: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    joins_count: int
    filters_count: int
    aggregations_count: int
```

**Update QueryResponse:**

```python
class QueryResponse(BaseModel):
    """Enhanced query response with full observability"""
    query_id: int
    question: str
    sql: str
    is_valid: bool
    is_read_only: bool
    warnings: List[str] = Field(default_factory=list)
    results: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    cached: bool = False
    timestamp: str

    # NEW: Enhanced observability fields
    trace: Optional[AgentTraceResponse] = None
    query_plan: Optional[QueryPlanSummary] = None
    attempts: Optional[List[AttemptDetail]] = None
    self_corrected: bool = False
    total_attempts: int = 1
    verification_warnings: List[str] = Field(default_factory=list)
    used_planning: bool = False

    class Config:
        from_attributes = True
```

### Deliverable Checklist
- [ ] AgentTrace class created with step tracking
- [ ] Integrated into generate_and_execute_with_retry
- [ ] Response schemas updated
- [ ] Trace included in API response
- [ ] Backward compatible (all new fields optional)

---

## Day 2: Backend - Format Query Plan & Attempts (4-6 hours)

### Task 2.1: Add Plan Formatter to QueryPlanningAgent

**File**: `src/llm/query_planning_agent.py`

**Add method to QueryPlanningAgent class:**

```python
def format_plan_for_ui(self, plan: QueryPlan) -> Dict[str, Any]:
    """
    Format query plan for frontend display

    Converts QueryPlan object to a UI-friendly structure with all
    necessary information for visualization.

    Args:
        plan: QueryPlan object to format

    Returns:
        Dictionary with UI-friendly plan structure
    """
    return {
        "complexity": plan.complexity.value,
        "intent": plan.intent,
        "confidence": plan.confidence,
        "reasoning": plan.reasoning,

        "tables": [
            {
                "name": t.name,
                "alias": t.alias,
                "purpose": t.purpose
            } for t in plan.tables
        ],

        "joins": [
            {
                "from": j.from_table,
                "to": j.to_table,
                "type": j.join_type,
                "on": j.on_condition,
                "purpose": j.purpose
            } for j in plan.joins
        ],

        "filters": [
            {
                "column": f.column,
                "operator": f.operator,
                "value": f.value,
                "purpose": f.purpose
            } for f in plan.filters
        ],

        "aggregations": [
            {
                "function": a.function,
                "column": a.column,
                "alias": a.alias,
                "purpose": a.purpose
            } for a in plan.aggregations
        ],

        "grouping": {
            "columns": plan.grouping.columns,
            "purpose": plan.grouping.purpose
        } if plan.grouping else None,

        "ordering": {
            "column": plan.ordering.column,
            "direction": plan.ordering.direction,
            "purpose": plan.ordering.purpose
        } if plan.ordering else None,

        "limit": plan.limit,

        # Summary counts for UI badges
        "joins_count": len(plan.joins),
        "filters_count": len(plan.filters),
        "aggregations_count": len(plan.aggregations)
    }
```

### Task 2.2: Add Attempts Formatter to SelfCorrectingSQLAgent

**File**: `src/llm/self_correcting_agent.py`

**Add method to track fix methods (add instance variable in __init__):**

```python
def __init__(self, ...):
    # ... existing code ...
    self.fix_methods: Dict[int, str] = {}  # Track which fix method was used per attempt
```

**Add formatter method:**

```python
def format_attempts_for_ui(
    self,
    attempts: List[CorrectionAttempt]
) -> List[Dict[str, Any]]:
    """
    Format correction attempts for frontend display

    Args:
        attempts: List of CorrectionAttempt objects

    Returns:
        List of UI-friendly attempt dictionaries
    """
    return [
        {
            "attempt_number": a.attempt_number,
            "sql": a.sql,
            "success": a.success,
            "error": a.error,
            "error_type": a.error_type.value if a.error_type else None,
            "execution_time_ms": a.execution_time_ms,
            "row_count": a.row_count,
            "fix_method": self.fix_methods.get(a.attempt_number)
        } for a in attempts
    ]
```

**Update retry loop to track fix methods:**

```python
# In generate_and_execute_with_retry, after quick fix:
if quick_fix_used:
    self.fix_methods[attempt_num] = "quick_fix"
    # ... rest of quick fix code ...

# After learned correction:
if learned_correction:
    self.fix_methods[attempt_num] = "learned"
    # ... rest of learned correction code ...

# After LLM correction:
if not quick_fix_used:
    self.fix_methods[attempt_num] = "llm"
    # ... rest of LLM correction code ...
```

### Task 2.3: Update Query Endpoint to Use Formatters

**File**: `src/api/endpoints/query.py`

**Update process_query function:**

```python
# After agent_result is obtained, before building response_data
# Format query plan if present
formatted_plan = None
if agent_result.get("query_plan"):
    from src.llm.query_planning_agent import QueryPlanningAgent
    # The plan is already a dict, just ensure it has the right structure
    formatted_plan = agent_result["query_plan"]

# Format attempts if present
formatted_attempts = None
if agent_result.get("attempts"):
    formatted_attempts = self_correcting_agent.format_attempts_for_ui(
        agent_result["attempts"]
    )

# Build response
response_data = {
    "query_id": query_record.id,
    "question": request.question,
    "sql": sql,
    "is_valid": is_valid,
    "is_read_only": is_read_only,
    "warnings": warnings,
    "results": execution_result.get("data") if execution_result and execution_result.get("success") else None,
    "row_count": execution_result.get("row_count") if execution_result else None,
    "execution_time_ms": execution_result.get("execution_time_ms") if execution_result else None,
    "cached": False,
    "timestamp": datetime.utcnow().isoformat(),

    # NEW: Observability fields
    "trace": agent_result.get("trace"),
    "query_plan": formatted_plan,
    "attempts": formatted_attempts,
    "self_corrected": agent_result.get("self_corrected", False),
    "total_attempts": agent_result.get("total_attempts", 1),
    "verification_warnings": agent_result.get("verification_warnings", []),
    "used_planning": agent_result.get("used_planning", False)
}
```

### Deliverable Checklist
- [ ] Plan formatter method created
- [ ] Attempts formatter method created
- [ ] Fix method tracking implemented
- [ ] Query endpoint updated to use formatters
- [ ] Test API response includes all new fields

---

## Day 3: Frontend - Timeline Components (6-8 hours)

### Task 3.1: Create Agent Trace Component

**File**: `frontend/src/components/AgentTrace.tsx` (NEW)

```typescript
import React, { useState } from 'react';

interface TraceStep {
  timestamp: string;
  elapsed_ms: number;
  type: string;
  message: string;
  metadata: Record<string, any>;
  icon?: string;
}

interface AgentTraceProps {
  trace: {
    total_steps: number;
    total_time_ms: number;
    steps: TraceStep[];
  };
}

export const AgentTrace: React.FC<AgentTraceProps> = ({ trace }) => {
  const [expanded, setExpanded] = useState(false);

  const getStepColor = (type: string): string => {
    if (type.includes('success')) return 'text-green-600 bg-green-50';
    if (type.includes('failure') || type.includes('error')) return 'text-red-600 bg-red-50';
    if (type.includes('warning')) return 'text-yellow-600 bg-yellow-50';
    if (type.includes('verification')) return 'text-blue-600 bg-blue-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getStepBorderColor = (type: string): string => {
    if (type.includes('success')) return 'border-green-200';
    if (type.includes('failure') || type.includes('error')) return 'border-red-200';
    if (type.includes('warning')) return 'border-yellow-200';
    if (type.includes('verification')) return 'border-blue-200';
    return 'border-gray-200';
  };

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">📊</span>
          <div>
            <h3 className="font-semibold text-gray-900">
              Agent Execution Trace
            </h3>
            <p className="text-sm text-gray-500">
              {trace.total_steps} steps • {trace.total_time_ms.toFixed(0)}ms
            </p>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${
            expanded ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 p-4">
          <div className="space-y-3">
            {trace.steps.map((step, idx) => (
              <div
                key={idx}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getStepColor(step.type)} ${getStepBorderColor(step.type)}`}
              >
                {/* Icon */}
                <span className="text-2xl flex-shrink-0">
                  {step.icon || '•'}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-sm flex-1">
                      {step.message}
                    </p>
                    <span className="text-xs text-gray-500 flex-shrink-0">
                      +{step.elapsed_ms.toFixed(0)}ms
                    </span>
                  </div>

                  {/* Step Type Badge */}
                  <div className="mt-1">
                    <span className="inline-block text-xs px-2 py-0.5 rounded bg-white bg-opacity-50">
                      {step.type}
                    </span>
                  </div>

                  {/* Metadata (expandable) */}
                  {Object.keys(step.metadata).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                        Show details
                      </summary>
                      <pre className="text-xs bg-white p-2 rounded mt-1 overflow-x-auto border">
                        {JSON.stringify(step.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              <strong>Total execution time:</strong> {trace.total_time_ms.toFixed(2)}ms
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
```

### Task 3.2: Create Correction History Component

**File**: `frontend/src/components/CorrectionHistory.tsx` (NEW)

```typescript
import React, { useState } from 'react';

interface Attempt {
  attempt_number: number;
  sql: string;
  success: boolean;
  error?: string;
  error_type?: string;
  execution_time_ms?: number;
  row_count?: number;
  fix_method?: string;
}

interface CorrectionHistoryProps {
  attempts: Attempt[];
  selfCorrected: boolean;
}

export const CorrectionHistory: React.FC<CorrectionHistoryProps> = ({
  attempts,
  selfCorrected
}) => {
  const [expanded, setExpanded] = useState(false);

  // Don't show if no corrections were made
  if (!selfCorrected || attempts.length <= 1) {
    return null;
  }

  const getFixMethodBadge = (method?: string) => {
    const badges = {
      'quick_fix': { label: 'Quick Fix', color: 'bg-purple-100 text-purple-800' },
      'learned': { label: 'Learned', color: 'bg-blue-100 text-blue-800' },
      'llm': { label: 'LLM', color: 'bg-orange-100 text-orange-800' }
    };

    if (!method || !badges[method]) {
      return null;
    }

    const badge = badges[method];
    return (
      <span className={`text-xs px-2 py-1 rounded ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg overflow-hidden mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-blue-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">✨</span>
          <div>
            <h3 className="font-semibold text-blue-900">
              Auto-Corrected Query
            </h3>
            <p className="text-sm text-blue-700">
              {attempts.length} attempt{attempts.length !== 1 ? 's' : ''} •
              {' '}Success on attempt {attempts.findIndex(a => a.success) + 1}
            </p>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-blue-700 transition-transform ${
            expanded ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-blue-200 p-4">
          <div className="space-y-4">
            {attempts.map((attempt, idx) => (
              <div
                key={idx}
                className={`rounded-lg border-2 overflow-hidden ${
                  attempt.success
                    ? 'border-green-300 bg-green-50'
                    : 'border-red-300 bg-red-50'
                }`}
              >
                {/* Header */}
                <div className={`px-4 py-2 flex items-center justify-between ${
                  attempt.success ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">
                      {attempt.success ? '✅' : '❌'}
                    </span>
                    <span className="font-semibold">
                      Attempt {attempt.attempt_number}
                    </span>
                    {attempt.error_type && (
                      <span className="text-xs px-2 py-0.5 rounded bg-white bg-opacity-50">
                        {attempt.error_type}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {attempt.fix_method && getFixMethodBadge(attempt.fix_method)}
                    {attempt.execution_time_ms && (
                      <span className="text-xs text-gray-600">
                        {attempt.execution_time_ms.toFixed(0)}ms
                      </span>
                    )}
                  </div>
                </div>

                {/* SQL */}
                <div className="p-4">
                  <pre className="text-xs bg-white p-3 rounded border overflow-x-auto font-mono">
                    {attempt.sql}
                  </pre>

                  {/* Error */}
                  {attempt.error && (
                    <div className="mt-3 p-3 bg-red-100 border border-red-200 rounded">
                      <p className="text-xs font-semibold text-red-900 mb-1">
                        Error:
                      </p>
                      <p className="text-xs text-red-800">
                        {attempt.error}
                      </p>
                    </div>
                  )}

                  {/* Success Info */}
                  {attempt.success && attempt.row_count !== undefined && (
                    <div className="mt-3 p-3 bg-green-100 border border-green-200 rounded">
                      <p className="text-xs text-green-800">
                        ✅ Returned {attempt.row_count} row{attempt.row_count !== 1 ? 's' : ''}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

### Deliverable Checklist
- [ ] AgentTrace component created and styled
- [ ] CorrectionHistory component created and styled
- [ ] Components handle edge cases (no data, errors)
- [ ] Responsive design works on mobile
- [ ] Accessible (keyboard navigation, screen readers)

---

## Day 4: Frontend - Query Plan Visualization (6-8 hours)

### Task 4.1: Create Query Plan Component

**File**: `frontend/src/components/QueryPlan.tsx` (NEW)

```typescript
import React, { useState } from 'react';

interface Table {
  name: string;
  alias?: string;
  purpose?: string;
}

interface Join {
  from: string;
  to: string;
  type: string;
  on: string;
  purpose?: string;
}

interface Filter {
  column: string;
  operator: string;
  value: string;
  purpose?: string;
}

interface Aggregation {
  function: string;
  column?: string;
  alias?: string;
  purpose?: string;
}

interface Grouping {
  columns: string[];
  purpose?: string;
}

interface Ordering {
  column: string;
  direction: string;
  purpose?: string;
}

interface QueryPlanProps {
  plan: {
    complexity: string;
    intent: string;
    confidence: number;
    reasoning: string;
    tables: Table[];
    joins: Join[];
    filters: Filter[];
    aggregations: Aggregation[];
    grouping?: Grouping;
    ordering?: Ordering;
    limit?: number;
    joins_count: number;
    filters_count: number;
    aggregations_count: number;
  };
}

export const QueryPlan: React.FC<QueryPlanProps> = ({ plan }) => {
  const [expanded, setExpanded] = useState(true);

  const getComplexityConfig = (complexity: string) => {
    const configs = {
      'simple': {
        color: 'bg-green-100 text-green-800 border-green-300',
        icon: '🟢',
        label: 'Simple'
      },
      'moderate': {
        color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
        icon: '🟡',
        label: 'Moderate'
      },
      'complex': {
        color: 'bg-orange-100 text-orange-800 border-orange-300',
        icon: '🟠',
        label: 'Complex'
      },
      'very_complex': {
        color: 'bg-red-100 text-red-800 border-red-300',
        icon: '🔴',
        label: 'Very Complex'
      }
    };
    return configs[complexity] || configs.simple;
  };

  const complexityConfig = getComplexityConfig(plan.complexity);

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg overflow-hidden mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-purple-100 transition-colors"
      >
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xl">📋</span>
          <div>
            <h3 className="font-semibold text-purple-900">Query Plan</h3>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className={`text-xs px-2 py-1 rounded border ${complexityConfig.color}`}>
                {complexityConfig.icon} {complexityConfig.label}
              </span>
              <span className="text-xs px-2 py-1 rounded bg-white border border-purple-200">
                Confidence: {(plan.confidence * 100).toFixed(0)}%
              </span>
              {plan.tables.length > 0 && (
                <span className="text-xs text-purple-700">
                  {plan.tables.length} table{plan.tables.length !== 1 ? 's' : ''}
                </span>
              )}
              {plan.joins_count > 0 && (
                <span className="text-xs text-purple-700">
                  {plan.joins_count} join{plan.joins_count !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-purple-700 transition-transform ${
            expanded ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-purple-200 p-4 space-y-4">
          {/* Intent */}
          <div className="bg-white rounded-lg p-3 border border-purple-100">
            <h4 className="font-semibold text-purple-900 text-sm mb-1">
              Intent
            </h4>
            <p className="text-sm text-gray-700">{plan.intent}</p>
          </div>

          {/* Tables */}
          {plan.tables.length > 0 && (
            <div>
              <h4 className="font-semibold text-purple-900 text-sm mb-2">
                Tables ({plan.tables.length})
              </h4>
              <div className="space-y-2">
                {plan.tables.map((table, idx) => (
                  <div
                    key={idx}
                    className="bg-white p-3 rounded-lg border border-purple-100"
                  >
                    <div className="flex items-center gap-2">
                      <code className="text-sm font-mono font-semibold text-purple-900">
                        {table.name}
                      </code>
                      {table.alias && (
                        <span className="text-xs text-gray-500">
                          as <code className="font-mono">{table.alias}</code>
                        </span>
                      )}
                    </div>
                    {table.purpose && (
                      <p className="text-xs text-gray-600 mt-1">
                        {table.purpose}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Joins */}
          {plan.joins.length > 0 && (
            <div>
              <h4 className="font-semibold text-purple-900 text-sm mb-2">
                Joins ({plan.joins.length})
              </h4>
              <div className="space-y-2">
                {plan.joins.map((join, idx) => (
                  <div
                    key={idx}
                    className="bg-white p-3 rounded-lg border border-purple-100"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <code className="text-sm font-mono text-purple-900">
                        {join.from}
                      </code>
                      <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                        {join.type}
                      </span>
                      <span className="text-gray-400">→</span>
                      <code className="text-sm font-mono text-purple-900">
                        {join.to}
                      </code>
                    </div>
                    <code className="text-xs text-gray-600 block mt-1">
                      ON {join.on}
                    </code>
                    {join.purpose && (
                      <p className="text-xs text-blue-600 mt-1">
                        💡 {join.purpose}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filters */}
          {plan.filters.length > 0 && (
            <div>
              <h4 className="font-semibold text-purple-900 text-sm mb-2">
                Filters ({plan.filters.length})
              </h4>
              <div className="space-y-2">
                {plan.filters.map((filter, idx) => (
                  <div
                    key={idx}
                    className="bg-white p-3 rounded-lg border border-purple-100"
                  >
                    <code className="text-sm font-mono text-purple-900">
                      {filter.column} {filter.operator} {filter.value}
                    </code>
                    {filter.purpose && (
                      <p className="text-xs text-gray-600 mt-1">
                        {filter.purpose}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Aggregations */}
          {plan.aggregations.length > 0 && (
            <div>
              <h4 className="font-semibold text-purple-900 text-sm mb-2">
                Aggregations ({plan.aggregations.length})
              </h4>
              <div className="space-y-2">
                {plan.aggregations.map((agg, idx) => (
                  <div
                    key={idx}
                    className="bg-white p-3 rounded-lg border border-purple-100"
                  >
                    <code className="text-sm font-mono text-purple-900">
                      {agg.function}({agg.column || '*'})
                      {agg.alias && ` AS ${agg.alias}`}
                    </code>
                    {agg.purpose && (
                      <p className="text-xs text-gray-600 mt-1">
                        {agg.purpose}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Grouping */}
          {plan.grouping && (
            <div className="bg-white p-3 rounded-lg border border-purple-100">
              <h4 className="font-semibold text-purple-900 text-sm mb-1">
                Grouping
              </h4>
              <code className="text-sm font-mono text-gray-700">
                GROUP BY {plan.grouping.columns.join(', ')}
              </code>
              {plan.grouping.purpose && (
                <p className="text-xs text-gray-600 mt-1">
                  {plan.grouping.purpose}
                </p>
              )}
            </div>
          )}

          {/* Ordering */}
          {plan.ordering && (
            <div className="bg-white p-3 rounded-lg border border-purple-100">
              <h4 className="font-semibold text-purple-900 text-sm mb-1">
                Ordering
              </h4>
              <code className="text-sm font-mono text-gray-700">
                ORDER BY {plan.ordering.column} {plan.ordering.direction}
              </code>
              {plan.ordering.purpose && (
                <p className="text-xs text-gray-600 mt-1">
                  {plan.ordering.purpose}
                </p>
              )}
            </div>
          )}

          {/* Limit */}
          {plan.limit && (
            <div className="bg-white p-3 rounded-lg border border-purple-100">
              <h4 className="font-semibold text-purple-900 text-sm mb-1">
                Limit
              </h4>
              <code className="text-sm font-mono text-gray-700">
                LIMIT {plan.limit}
              </code>
            </div>
          )}

          {/* Reasoning */}
          <div className="bg-white rounded-lg p-3 border border-purple-100">
            <h4 className="font-semibold text-purple-900 text-sm mb-2">
              Reasoning
            </h4>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">
              {plan.reasoning}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
```

### Task 4.2: Create Verification Warnings Component

**File**: `frontend/src/components/VerificationWarnings.tsx` (NEW)

```typescript
import React from 'react';

interface VerificationWarningsProps {
  warnings: string[];
}

export const VerificationWarnings: React.FC<VerificationWarningsProps> = ({
  warnings
}) => {
  if (!warnings || warnings.length === 0) {
    return null;
  }

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mt-4">
      <div className="flex">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-yellow-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-yellow-800">
            Result Verification Warning{warnings.length > 1 ? 's' : ''}
          </h3>
          <div className="mt-2 text-sm text-yellow-700">
            <ul className="list-disc space-y-1 pl-5">
              {warnings.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
```

### Task 4.3: Integrate All Components into QueryResults

**File**: `frontend/src/components/QueryResults.tsx` (UPDATE)

```typescript
import React from 'react';
import { AgentTrace } from './AgentTrace';
import { CorrectionHistory } from './CorrectionHistory';
import { QueryPlan } from './QueryPlan';
import { VerificationWarnings } from './VerificationWarnings';
import { SQLDisplay } from './SQLDisplay'; // Assume this exists
import { ResultsTable } from './ResultsTable'; // Assume this exists

interface QueryResultsProps {
  result: {
    query_id: number;
    question: string;
    sql: string;
    is_valid: boolean;
    warnings: string[];
    results?: any[];
    row_count?: number;
    execution_time_ms?: number;

    // Observability fields
    trace?: any;
    query_plan?: any;
    attempts?: any[];
    self_corrected: boolean;
    total_attempts: number;
    verification_warnings?: string[];
    used_planning: boolean;
  };
}

export const QueryResults: React.FC<QueryResultsProps> = ({ result }) => {
  return (
    <div className="space-y-4">
      {/* Header with stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-semibold text-gray-900">
            Query Results
          </h2>

          <div className="flex items-center gap-2 flex-wrap">
            {result.used_planning && (
              <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-800">
                🧠 Planned
              </span>
            )}
            {result.self_corrected && (
              <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                ✨ Auto-corrected
              </span>
            )}
            {result.execution_time_ms && (
              <span className="text-xs text-gray-500">
                {result.execution_time_ms.toFixed(0)}ms
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Verification Warnings (if any) */}
      {result.verification_warnings && result.verification_warnings.length > 0 && (
        <VerificationWarnings warnings={result.verification_warnings} />
      )}

      {/* General Warnings (if any) */}
      {result.warnings && result.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-semibold text-yellow-900 mb-2">Warnings</h4>
          <ul className="list-disc list-inside text-sm text-yellow-800">
            {result.warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Query Plan (if available) */}
      {result.query_plan && (
        <QueryPlan plan={result.query_plan} />
      )}

      {/* Correction History (if auto-corrected) */}
      {result.self_corrected && result.attempts && (
        <CorrectionHistory
          attempts={result.attempts}
          selfCorrected={result.self_corrected}
        />
      )}

      {/* SQL Display */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
          <h3 className="font-semibold text-gray-700">Generated SQL</h3>
        </div>
        <SQLDisplay sql={result.sql} />
      </div>

      {/* Results Table */}
      {result.results && result.results.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
            <h3 className="font-semibold text-gray-700">
              Results ({result.row_count} row{result.row_count !== 1 ? 's' : ''})
            </h3>
          </div>
          <ResultsTable data={result.results} />
        </div>
      )}

      {/* Agent Trace (if available) */}
      {result.trace && (
        <AgentTrace trace={result.trace} />
      )}
    </div>
  );
};
```

### Deliverable Checklist
- [ ] QueryPlan component created with full visualization
- [ ] VerificationWarnings component created
- [ ] All components integrated into QueryResults
- [ ] Responsive layout works on all screen sizes
- [ ] Components handle missing/optional data gracefully

---

## Week 1 Testing & Validation

### Testing Checklist

**Backend:**
- [ ] AgentTrace captures all key decision points
- [ ] Trace is included in API response
- [ ] Query plan formatting works correctly
- [ ] Attempts formatting includes fix methods
- [ ] All new fields are optional (backward compatible)

**Frontend:**
- [ ] AgentTrace renders correctly with all step types
- [ ] CorrectionHistory shows when self_corrected=true
- [ ] QueryPlan displays all plan components
- [ ] Verification warnings display prominently
- [ ] Components are responsive on mobile

**Integration:**
- [ ] End-to-end: Submit query → See full trace in UI
- [ ] Complex query → See query plan
- [ ] Auto-corrected query → See correction history
- [ ] Verification warning → See warning banner

---

# 📅 Week 2: User Feedback Integration

## Day 5-6: Backend - Feedback API & Database (8-12 hours)

### Task 5.1: Create UserFeedback Database Model

**File**: `src/database/models.py`

**Add new model:**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

class UserFeedback(Base):
    """
    User corrections and feedback on queries

    Stores user-provided corrections to enable continuous learning.
    Feedback can be SQL corrections, column/table name fixes, or result issues.
    """
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # Link to original query
    query_id = Column(Integer, ForeignKey("query_history.id"), nullable=False, index=True)
    query = relationship("QueryHistory", back_populates="feedbacks")

    # Feedback type
    feedback_type = Column(String(50), nullable=False, index=True)
    # Types: "sql_correction", "column_name", "table_name", "result_issue"

    # Original and corrected content
    original_sql = Column(Text, nullable=False)
    corrected_sql = Column(Text, nullable=True)
    correction_description = Column(Text, nullable=True)

    # Specific corrections (structured data)
    # Example: {"from": "category", "to": "category_name", "table": "products"}
    correction_details = Column(JSON, nullable=True)

    # Quality indicators
    user_confidence = Column(Float, default=1.0)  # 0.0 to 1.0
    applied_successfully = Column(Boolean, default=False, index=True)

    # Learning integration
    learned_correction_id = Column(
        Integer,
        ForeignKey("learned_corrections.id"),
        nullable=True
    )
    learned_correction = relationship("LearnedCorrection")

    # Metadata
    user_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    applied_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<UserFeedback(id={self.id}, type={self.feedback_type}, query_id={self.query_id})>"


# Update QueryHistory to have feedback relationship
# Add this to the QueryHistory class:
class QueryHistory(Base):
    # ... existing fields ...

    # Add relationship
    feedbacks = relationship("UserFeedback", back_populates="query", cascade="all, delete-orphan")
```

### Task 5.2: Create Feedback Schemas

**File**: `src/models/schemas.py`

**Add feedback schemas:**

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime

class FeedbackCreate(BaseModel):
    """Create user feedback on a query"""
    query_id: int = Field(..., description="ID of the query being corrected")
    feedback_type: str = Field(
        ...,
        description="Type of feedback: sql_correction, column_name, table_name, result_issue"
    )
    corrected_sql: Optional[str] = Field(None, description="Corrected SQL query")
    correction_description: Optional[str] = Field(
        None,
        description="Description of what was wrong and how it was fixed"
    )
    correction_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured correction data (e.g., {'from': 'category', 'to': 'category_name'})"
    )
    user_notes: Optional[str] = Field(None, description="Additional user notes")
    user_confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="User's confidence in the correction (0.0 to 1.0)"
    )

    @field_validator('feedback_type')
    @classmethod
    def validate_feedback_type(cls, v):
        valid_types = ['sql_correction', 'column_name', 'table_name', 'result_issue']
        if v not in valid_types:
            raise ValueError(f'feedback_type must be one of {valid_types}')
        return v


class FeedbackResponse(BaseModel):
    """User feedback response"""
    id: int
    query_id: int
    feedback_type: str
    original_sql: str
    corrected_sql: Optional[str]
    correction_description: Optional[str]
    correction_details: Optional[Dict[str, Any]]
    user_confidence: float
    applied_successfully: bool
    learned_correction_id: Optional[int]
    user_notes: Optional[str]
    created_at: datetime
    applied_at: Optional[datetime]

    class Config:
        from_attributes = True


class FeedbackApplyRequest(BaseModel):
    """Apply user feedback to learning system"""
    feedback_id: int = Field(..., description="ID of the feedback to apply")
    test_before_learning: bool = Field(
        True,
        description="Test the correction before adding to learning system"
    )


class FeedbackStatsResponse(BaseModel):
    """Feedback statistics"""
    total_feedback: int
    applied_to_learning: int
    pending: int
    by_type: Dict[str, int]
```

### Task 5.3: Create Feedback API Endpoints

**File**: `src/api/endpoints/feedback.py` (NEW)

```python
"""User feedback endpoints for continuous learning"""
import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackApplyRequest,
    FeedbackStatsResponse
)
from src.api.dependencies.common import get_db
from src.database.models import UserFeedback, QueryHistory, DatabaseConnection
from src.llm.correction_learner import CorrectionLearner
from src.llm.self_correcting_agent import ErrorType, ErrorDiagnostics
from src.core.executor import SQLExecutor
from src.core.user_db_connector import UserDatabaseConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit user feedback on a query

    Users can:
    - Correct SQL queries
    - Report column/table name issues
    - Flag result problems
    - Provide domain knowledge

    The feedback is stored and can later be applied to the learning system.
    """
    try:
        # Verify query exists
        stmt = select(QueryHistory).where(QueryHistory.id == feedback.query_id)
        result = await db.execute(stmt)
        query = result.scalar_one_or_none()

        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query {feedback.query_id} not found"
            )

        # Create feedback record
        feedback_record = UserFeedback(
            query_id=feedback.query_id,
            feedback_type=feedback.feedback_type,
            original_sql=query.generated_sql,
            corrected_sql=feedback.corrected_sql,
            correction_description=feedback.correction_description,
            correction_details=feedback.correction_details,
            user_confidence=feedback.user_confidence,
            user_notes=feedback.user_notes
        )

        db.add(feedback_record)
        await db.commit()
        await db.refresh(feedback_record)

        logger.info(
            f"User feedback submitted: id={feedback_record.id}, "
            f"type={feedback.feedback_type}, query_id={feedback.query_id}"
        )

        return FeedbackResponse.model_validate(feedback_record)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.post("/apply", response_model=FeedbackResponse)
async def apply_feedback_to_learning(
    request: FeedbackApplyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply user feedback to the learning system

    This:
    1. Optionally tests the corrected SQL to ensure it works
    2. Adds the correction to the learned_corrections table
    3. Makes the correction available for automatic application in future queries

    The system will now automatically apply this correction when similar errors occur.
    """
    try:
        # Get feedback
        stmt = select(UserFeedback).where(UserFeedback.id == request.feedback_id)
        result = await db.execute(stmt)
        feedback = result.scalar_one_or_none()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {request.feedback_id} not found"
            )

        if feedback.applied_successfully:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback already applied to learning system"
            )

        # Get original query for context
        query = await db.get(QueryHistory, feedback.query_id)

        # Test correction if requested
        tested_successfully = False
        if request.test_before_learning and feedback.corrected_sql:
            logger.info(f"Testing user correction before learning (feedback_id={feedback.id})...")

            # Get active connection
            stmt = select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            result = await db.execute(stmt)
            active_conn = result.scalar_one_or_none()

            if active_conn:
                async with UserDatabaseConnector.get_user_db_session(active_conn) as user_db:
                    executor = SQLExecutor(max_rows=10, timeout_seconds=30)
                    test_result = await executor.execute_query(
                        session=user_db,
                        sql=feedback.corrected_sql
                    )
                    tested_successfully = test_result["success"]

                    if not tested_successfully:
                        error_msg = test_result.get('error', 'Unknown error')
                        logger.warning(
                            f"User correction failed testing: {error_msg} "
                            f"(feedback_id={feedback.id})"
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Corrected SQL failed to execute: {error_msg}"
                        )
            else:
                logger.warning("No active connection for testing correction")

        # Learn from feedback
        learner = CorrectionLearner(db_session=db, enable_learning=True)

        # Determine error type from original query
        error_type = ErrorType.UNKNOWN
        if query.error_message:
            error_type = ErrorDiagnostics.categorize_error(query.error_message)

        # Create learned correction
        learned_id = await learner.learn_from_correction(
            error_type=error_type,
            original_sql=feedback.original_sql,
            original_error=query.error_message or "User-reported issue",
            corrected_sql=feedback.corrected_sql or feedback.original_sql,
            database_type=query.database_type,
            was_successful=True,
            correction_description=feedback.correction_description or "User correction",
            source="user_feedback",
            confidence_override=feedback.user_confidence
        )

        # Update feedback record
        feedback.applied_successfully = True
        feedback.applied_at = datetime.utcnow()
        feedback.learned_correction_id = learned_id

        await db.commit()
        await db.refresh(feedback)

        logger.info(
            f"✨ Learned from user feedback: feedback_id={feedback.id}, "
            f"learned_correction_id={learned_id}"
        )

        return FeedbackResponse.model_validate(feedback)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to apply feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply feedback: {str(e)}"
        )


@router.get("/query/{query_id}", response_model=List[FeedbackResponse])
async def get_query_feedback(
    query_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all feedback for a specific query"""
    try:
        stmt = (
            select(UserFeedback)
            .where(UserFeedback.query_id == query_id)
            .order_by(desc(UserFeedback.created_at))
        )
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()

        return [FeedbackResponse.model_validate(f) for f in feedbacks]

    except Exception as e:
        logger.error(f"Failed to get feedback for query {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback: {str(e)}"
        )


@router.get("/recent", response_model=List[FeedbackResponse])
async def get_recent_feedback(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get recent feedback submissions"""
    try:
        stmt = (
            select(UserFeedback)
            .order_by(desc(UserFeedback.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()

        return [FeedbackResponse.model_validate(f) for f in feedbacks]

    except Exception as e:
        logger.error(f"Failed to get recent feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent feedback: {str(e)}"
        )


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    """Get feedback statistics"""
    try:
        # Total feedback count
        total_result = await db.execute(select(func.count(UserFeedback.id)))
        total = total_result.scalar() or 0

        # Applied count
        applied_result = await db.execute(
            select(func.count(UserFeedback.id))
            .where(UserFeedback.applied_successfully == True)
        )
        applied = applied_result.scalar() or 0

        # By type
        type_result = await db.execute(
            select(UserFeedback.feedback_type, func.count(UserFeedback.id))
            .group_by(UserFeedback.feedback_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        return FeedbackStatsResponse(
            total_feedback=total,
            applied_to_learning=applied,
            pending=total - applied,
            by_type=by_type
        )

    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a feedback entry"""
    try:
        stmt = select(UserFeedback).where(UserFeedback.id == feedback_id)
        result = await db.execute(stmt)
        feedback = result.scalar_one_or_none()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {feedback_id} not found"
            )

        await db.delete(feedback)
        await db.commit()

        logger.info(f"Feedback deleted: id={feedback_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete feedback: {str(e)}"
        )
```

### Task 5.4: Create Database Migration

**Create migration file:**

```bash
# Activate virtual environment
source venv/bin/activate

# Create migration
alembic revision --autogenerate -m "Add user_feedback table"

# Review the generated migration file, then apply
alembic upgrade head
```

**Manual SQL (if not using Alembic):**

```sql
-- Create user_feedback table
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL REFERENCES query_history(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL,
    original_sql TEXT NOT NULL,
    corrected_sql TEXT,
    correction_description TEXT,
    correction_details JSONB,
    user_confidence REAL DEFAULT 1.0,
    applied_successfully BOOLEAN DEFAULT FALSE,
    learned_correction_id INTEGER REFERENCES learned_corrections(id) ON DELETE SET NULL,
    user_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_user_feedback_query_id ON user_feedback(query_id);
CREATE INDEX idx_user_feedback_type ON user_feedback(feedback_type);
CREATE INDEX idx_user_feedback_applied ON user_feedback(applied_successfully);
CREATE INDEX idx_user_feedback_created_at ON user_feedback(created_at);
```

### Task 5.5: Register Feedback Router

**File**: `src/main.py`

```python
from src.api.endpoints import feedback

# Add with other routers
app.include_router(feedback.router, prefix="/api")
```

### Deliverable Checklist
- [ ] UserFeedback model created
- [ ] Feedback schemas created with validation
- [ ] All feedback endpoints implemented
- [ ] Database migration created and applied
- [ ] Router registered in main app
- [ ] Test endpoints with Swagger UI

---

## Day 7-8: Frontend - Feedback UI (10-12 hours)

### Task 7.1: Create SQL Editor Component

**File**: `frontend/src/components/SQLEditor.tsx` (NEW)

```typescript
import React, { useState } from 'react';

interface SQLEditorProps {
  initialSQL: string;
  readOnly?: boolean;
  onChange?: (sql: string) => void;
}

export const SQLEditor: React.FC<SQLEditorProps> = ({
  initialSQL,
  readOnly = false,
  onChange
}) => {
  const [sql, setSQL] = useState(initialSQL);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newSQL = e.target.value;
    setSQL(newSQL);
    onChange?.(newSQL);
  };

  return (
    <textarea
      value={sql}
      onChange={handleChange}
      readOnly={readOnly}
      className={`
        w-full p-4 font-mono text-sm
        border rounded-lg
        min-h-[200px]
        focus:outline-none focus:ring-2 focus:ring-blue-500
        ${readOnly ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}
      `}
      spellCheck={false}
      placeholder="Enter SQL query..."
    />
  );
};
```

### Task 7.2: Create Feedback Modal Component

**File**: `frontend/src/components/FeedbackModal.tsx` (NEW)

```typescript
import React, { useState } from 'react';
import { SQLEditor } from './SQLEditor';

interface FeedbackModalProps {
  queryId: number;
  originalSQL: string;
  onSubmit: (feedback: FeedbackData) => Promise<void>;
  onClose: () => void;
}

interface FeedbackData {
  query_id: number;
  feedback_type: string;
  corrected_sql?: string;
  correction_description?: string;
  correction_details?: any;
  user_notes?: string;
  user_confidence: number;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  queryId,
  originalSQL,
  onSubmit,
  onClose
}) => {
  const [feedbackType, setFeedbackType] = useState('sql_correction');
  const [correctedSQL, setCorrectedSQL] = useState(originalSQL);
  const [description, setDescription] = useState('');
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState(1.0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    // Validation
    if (!description.trim()) {
      setError('Please provide a description of what needs to be corrected');
      return;
    }

    if (feedbackType === 'sql_correction' && correctedSQL === originalSQL) {
      setError('Corrected SQL is the same as original SQL');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await onSubmit({
        query_id: queryId,
        feedback_type: feedbackType,
        corrected_sql: feedbackType === 'sql_correction' ? correctedSQL : undefined,
        correction_description: description,
        user_notes: notes || undefined,
        user_confidence: confidence
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Provide Feedback
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Feedback Type */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              What type of feedback are you providing?
            </label>
            <select
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="sql_correction">SQL Correction</option>
              <option value="column_name">Column Name Issue</option>
              <option value="table_name">Table Name Issue</option>
              <option value="result_issue">Result Issue</option>
            </select>
            <p className="text-sm text-gray-500 mt-1">
              {feedbackType === 'sql_correction' && 'Provide a corrected version of the SQL query'}
              {feedbackType === 'column_name' && 'Report an incorrect column name'}
              {feedbackType === 'table_name' && 'Report an incorrect table name'}
              {feedbackType === 'result_issue' && 'Report an issue with the query results'}
            </p>
          </div>

          {/* Original SQL (read-only) */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              Original SQL
            </label>
            <SQLEditor
              initialSQL={originalSQL}
              readOnly={true}
            />
          </div>

          {/* Corrected SQL (if correction type) */}
          {feedbackType === 'sql_correction' && (
            <div className="mb-6">
              <label className="block font-semibold text-gray-900 mb-2">
                Corrected SQL *
              </label>
              <SQLEditor
                initialSQL={correctedSQL}
                onChange={setCorrectedSQL}
              />
            </div>
          )}

          {/* Description */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              What's wrong? / What should change? *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="E.g., Should use 'category_name' instead of 'category' in the WHERE clause"
            />
          </div>

          {/* Additional Notes */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              Additional Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 min-h-[80px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Any additional context or information..."
            />
          </div>

          {/* Confidence Slider */}
          <div className="mb-6">
            <label className="block font-semibold text-gray-900 mb-2">
              How confident are you in this correction?
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={confidence}
                onChange={(e) => setConfidence(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-lg font-semibold text-gray-900 w-16 text-right">
                {Math.round(confidence * 100)}%
              </span>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Not sure</span>
              <span>Very confident</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              disabled={submitting || !description.trim()}
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Submitting...
                </span>
              ) : (
                'Submit Feedback'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
```

### Task 7.3: Create API Service Functions

**File**: `frontend/src/services/api.ts` (UPDATE or CREATE)

```typescript
const API_BASE = '/api';

export interface FeedbackData {
  query_id: number;
  feedback_type: string;
  corrected_sql?: string;
  correction_description?: string;
  correction_details?: any;
  user_notes?: string;
  user_confidence: number;
}

export interface FeedbackResponse {
  id: number;
  query_id: number;
  feedback_type: string;
  original_sql: string;
  corrected_sql?: string;
  correction_description?: string;
  applied_successfully: boolean;
  learned_correction_id?: number;
  created_at: string;
}

export const submitFeedback = async (feedbackData: FeedbackData): Promise<FeedbackResponse> => {
  const response = await fetch(`${API_BASE}/feedback/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(feedbackData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to submit feedback');
  }

  return response.json();
};

export const applyFeedback = async (
  feedbackId: number,
  testFirst: boolean = true
): Promise<FeedbackResponse> => {
  const response = await fetch(`${API_BASE}/feedback/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      feedback_id: feedbackId,
      test_before_learning: testFirst
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to apply feedback');
  }

  return response.json();
};

export const getFeedbackStats = async () => {
  const response = await fetch(`${API_BASE}/feedback/stats`);

  if (!response.ok) {
    throw new Error('Failed to get feedback stats');
  }

  return response.json();
};
```

### Task 7.4: Integrate Feedback into QueryResults

**File**: `frontend/src/components/QueryResults.tsx` (UPDATE)

```typescript
import { useState } from 'react';
import { FeedbackModal } from './FeedbackModal';
import { submitFeedback, applyFeedback } from '../services/api';

export const QueryResults: React.FC<QueryResultsProps> = ({ result }) => {
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState<{
    submitted: boolean;
    applied: boolean;
    learnedId?: number;
  } | null>(null);

  const handleFeedbackSubmit = async (feedbackData: any) => {
    // Submit feedback
    const response = await submitFeedback(feedbackData);

    // Ask if user wants to apply to learning system
    const shouldApply = window.confirm(
      'Feedback submitted! Would you like to apply this correction to the learning system?\n\n' +
      'This will:\n' +
      '• Test the correction to ensure it works\n' +
      '• Add it to the system\'s knowledge base\n' +
      '• Automatically apply it to similar future queries'
    );

    if (shouldApply) {
      try {
        const applyResponse = await applyFeedback(response.id, true);
        setFeedbackStatus({
          submitted: true,
          applied: true,
          learnedId: applyResponse.learned_correction_id
        });
      } catch (error: any) {
        alert(`Failed to apply to learning: ${error.message}`);
        setFeedbackStatus({
          submitted: true,
          applied: false
        });
      }
    } else {
      setFeedbackStatus({
        submitted: true,
        applied: false
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Feedback Success Banner */}
      {feedbackStatus?.submitted && (
        <div className={`rounded-lg p-4 ${
          feedbackStatus.applied
            ? 'bg-green-50 border border-green-200'
            : 'bg-blue-50 border border-blue-200'
        }`}>
          <div className="flex items-start gap-3">
            <span className="text-2xl">
              {feedbackStatus.applied ? '✨' : '💬'}
            </span>
            <div className="flex-1">
              <h4 className={`font-semibold ${
                feedbackStatus.applied ? 'text-green-900' : 'text-blue-900'
              }`}>
                {feedbackStatus.applied
                  ? 'Thank you! The system has learned from your feedback'
                  : 'Thank you for your feedback!'
                }
              </h4>
              <p className={`text-sm mt-1 ${
                feedbackStatus.applied ? 'text-green-700' : 'text-blue-700'
              }`}>
                {feedbackStatus.applied
                  ? `Your correction has been added to the learning system and will be automatically applied to similar queries in the future.${feedbackStatus.learnedId ? ` (Learned correction #${feedbackStatus.learnedId})` : ''}`
                  : 'Your feedback has been recorded. You can apply it to the learning system later from the feedback dashboard.'
                }
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header with Feedback Button */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">SQL Query</h3>
        <button
          onClick={() => setShowFeedbackModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          <span>💬</span>
          <span>Provide Feedback</span>
        </button>
      </div>

      {/* Rest of existing components... */}
      {/* ... Verification Warnings, Query Plan, Correction History, etc. ... */}

      {/* Feedback Modal */}
      {showFeedbackModal && (
        <FeedbackModal
          queryId={result.query_id}
          originalSQL={result.sql}
          onSubmit={handleFeedbackSubmit}
          onClose={() => setShowFeedbackModal(false)}
        />
      )}
    </div>
  );
};
```

### Deliverable Checklist
- [ ] SQLEditor component created
- [ ] FeedbackModal component created
- [ ] API service functions implemented
- [ ] Integrated into QueryResults
- [ ] Success/error handling
- [ ] User confirmation for learning

---

## Day 9-10: Integration & E2E Testing (8-12 hours)

### Task 9.1: End-to-End Testing Scenarios

**Test Scenario 1: Submit SQL Correction**
```
1. Run a query that returns incorrect results
2. Click "Provide Feedback"
3. Select "SQL Correction"
4. Edit the SQL to fix the issue
5. Add description
6. Submit
7. Confirm application to learning
8. Verify feedback appears in database
9. Verify learned_correction created
```

**Test Scenario 2: Verify Learning Applied**
```
1. Submit feedback for common error (e.g., wrong column name)
2. Apply to learning system
3. Run a NEW query with the same error
4. Verify system auto-applies learned correction
5. Check trace shows "learned_correction" step
```

**Test Scenario 3: Observability Full Flow**
```
1. Run complex query
2. Verify query plan displayed
3. Trigger auto-correction (use wrong table name)
4. Verify correction history shows
5. Verify agent trace shows all steps
6. Submit feedback on corrected query
7. Verify feedback integrated with observability data
```

### Task 9.2: Create Test Documentation

**File**: `../technical/OBSERVABILITY_TESTING.md`

```markdown
# Observability & Feedback Testing Guide

## Testing Observability Features

### Agent Trace
1. Submit any query
2. Expand "Agent Execution Trace"
3. Verify all steps shown with icons and timing
4. Check metadata expandable for each step

### Query Plan
1. Submit complex query (e.g., "Compare revenue between categories")
2. Verify "Query Plan" section appears
3. Check complexity badge, confidence score
4. Verify tables, joins, filters displayed correctly

### Correction History
1. Submit query with typo (e.g., "prodcts" instead of "products")
2. Verify "Auto-Corrected Query" section appears
3. Expand to see all attempts
4. Check fix method badges (Quick Fix, Learned, LLM)

## Testing Feedback Features

### Submit Feedback
1. Click "Provide Feedback" on any query result
2. Fill out form
3. Submit
4. Verify success message

### Apply to Learning
1. After submitting feedback, confirm application
2. Wait for testing to complete
3. Verify success message with learned correction ID
4. Check database: learned_corrections table

### Verify Learning Works
1. Run query that triggers learned correction
2. Check agent trace for "learned_correction" step
3. Verify query succeeds without LLM call

## Database Verification

```sql
-- Check feedback submitted
SELECT * FROM user_feedback ORDER BY created_at DESC LIMIT 5;

-- Check learned corrections from feedback
SELECT lc.*
FROM learned_corrections lc
JOIN user_feedback uf ON uf.learned_correction_id = lc.id
ORDER BY lc.created_at DESC;

-- Check stats
SELECT
  feedback_type,
  COUNT(*) as count,
  SUM(CASE WHEN applied_successfully THEN 1 ELSE 0 END) as applied
FROM user_feedback
GROUP BY feedback_type;
```
```

### Task 9.3: Performance Testing

**Test API response times:**
```bash
# Test trace overhead
time curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all products", "database_type": "sqlite"}'

# Should be < 2s for simple queries
# Trace adds ~10-50ms overhead
```

**Test feedback submission:**
```bash
time curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 1,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM products WHERE category_name = '\''electronics'\''",
    "correction_description": "Use category_name instead of category",
    "user_confidence": 1.0
  }'

# Should be < 500ms
```

### Deliverable Checklist
- [ ] All test scenarios pass
- [ ] Database queries return expected data
- [ ] Performance within acceptable limits
- [ ] No errors in browser console
- [ ] No errors in server logs

---

## Day 11: Documentation & Polish (4-6 hours)

### Task 11.1: Create User Guide

**File**: `../guides/USER_FEEDBACK_GUIDE.md`

```markdown
# User Feedback Integration Guide

## Overview
Database Guru learns from your corrections! When you provide feedback on queries, the system remembers and automatically applies your knowledge to future queries.

## How to Provide Feedback

### 1. Submit Feedback on Any Query

After running a query, click the **"Provide Feedback"** button to:
- Correct SQL errors
- Report column/table name issues
- Flag result problems
- Share domain knowledge

### 2. Choose Feedback Type

**SQL Correction**
- Provide a corrected version of the SQL
- The system will learn the correction pattern
- Example: Changing `category` to `category_name`

**Column Name Issue**
- Report when the wrong column was used
- Help the system learn your schema conventions

**Table Name Issue**
- Report when the wrong table was referenced
- Teach the system your database structure

**Result Issue**
- Flag when results don't make sense
- Help improve result verification

### 3. Describe the Issue

Provide a clear description of:
- What was wrong
- What should have been used instead
- Why this is the correct approach

**Good example:**
> "The query used 'category' but our database uses 'category_name' for product categorization. 'category' is an old deprecated column."

### 4. Set Confidence Level

Use the slider to indicate how confident you are:
- **100%**: Absolutely certain this is correct
- **50-80%**: Pretty sure, but not 100%
- **< 50%**: This might work, but I'm unsure

The system uses confidence scores to prioritize corrections.

### 5. Apply to Learning System

After submitting feedback, you'll be asked if you want to apply it to the learning system:

**What happens when you apply:**
1. **Testing**: The system tests your correction to ensure it works
2. **Learning**: If successful, adds it to the knowledge base
3. **Auto-application**: Future similar queries automatically use this correction

**Benefits:**
- ✅ Faster query generation (no LLM retry needed)
- ✅ Consistent results across similar queries
- ✅ System gets smarter over time

## Viewing Learning Impact

### Feedback Stats
Access `/api/feedback/stats` to see:
- Total feedback submitted
- How many applied to learning
- Breakdown by type

### Learned Corrections
Check `/api/learned-corrections/` to see:
- All corrections the system has learned
- Success rates
- Confidence scores

## Privacy & Safety

### Testing Before Learning
When you apply feedback, the system:
1. Tests the corrected SQL on your database
2. Only learns if the test succeeds
3. Never applies untested corrections

### User Control
- You control what gets learned
- You can delete feedback at any time
- Learned corrections can be reviewed and removed

### Transparency
- All learned corrections are visible
- You can see when/how they were learned
- Agent trace shows when learned corrections are applied

## Best Practices

### DO ✅
- Provide specific, detailed descriptions
- Test your corrections before submitting
- Use high confidence for well-tested fixes
- Include business context in notes

### DON'T ❌
- Submit untested corrections
- Use 100% confidence if unsure
- Provide vague descriptions
- Submit duplicate feedback

## Examples

### Example 1: Column Name Correction
**Original SQL:**
```sql
SELECT * FROM products WHERE category = 'electronics'
```

**Corrected SQL:**
```sql
SELECT * FROM products WHERE category_name = 'electronics'
```

**Description:**
> "Our database uses 'category_name' not 'category'. The 'category' column was deprecated in 2023."

**Confidence:** 100%

**Result:** System learns to use `category_name` instead of `category` for the products table.

### Example 2: Table Name Correction
**Original SQL:**
```sql
SELECT * FROM user WHERE id = 1
```

**Corrected SQL:**
```sql
SELECT * FROM users WHERE id = 1
```

**Description:**
> "Table is named 'users' (plural), not 'user'"

**Confidence:** 100%

**Result:** System learns the correct table name.

## Continuous Improvement

The more feedback you provide:
- The smarter the system becomes
- The fewer errors it makes
- The faster it generates queries
- The better it understands your domain

**Your expertise makes the system better for everyone!** 🎓
```

### Task 11.2: Update README.md

**File**: `README.md` (UPDATE)

Add to features section:

```markdown
## 🎯 Features

- ✅ **Enhanced Observability** - See every decision the AI makes (NEW!)
  - Agent execution trace with timing
  - Query plan visualization
  - Correction attempt history
  - Result verification warnings
- ✅ **User Feedback Integration** - Teach the AI your domain knowledge (NEW!)
  - Submit SQL corrections
  - System learns from feedback
  - Auto-applies learned patterns
  - Continuous improvement
- ✅ Natural language to SQL conversion
- ✅ **Query Planning Agent** - 4x better accuracy on complex queries
...
```

Add new section:

```markdown
## 🎓 Teaching the System

Database Guru learns from your feedback! When you correct a query, the system remembers and applies your knowledge to future queries.

### How It Works
1. **Provide Feedback** - Correct SQL, report issues, share domain knowledge
2. **System Tests** - Validates your correction automatically
3. **Learning** - Adds to knowledge base if successful
4. **Auto-Apply** - Future similar queries use learned patterns

### Benefits
- 📈 System gets smarter over time
- ⚡ Faster query generation
- 🎯 Domain-specific accuracy
- 💡 Fewer repeated errors

See [User Feedback Guide](../guides/USER_FEEDBACK_GUIDE.md) for details.
```

### Task 11.3: Update NEXT_FEATURES_ROADMAP.md

**File**: `NEXT_FEATURES_ROADMAP.md` (UPDATE)

Mark as complete:

```markdown
## 📍 Current Status (Updated: 2025-10-18)

### ✅ **PHASE 0 COMPLETE! 🎉🎉🎉**
- ✅ **Self-Correcting SQL Agent**
- ✅ **Learning from Corrections**
- ✅ **Schema-Aware Fixes**
- ✅ **Result Verification Agent**
- ✅ **Query Planning Agent**
- ✅ **Enhanced Observability** ⬅️ **NEW!** (Week 1)
  - Agent execution trace
  - Query plan visualization
  - Correction history display
  - Verification warnings UI
- ✅ **User Feedback Integration** ⬅️ **NEW!** (Week 2)
  - Feedback submission
  - Learning system integration
  - Auto-application of learned patterns
  - Continuous improvement

### 🎯 **PHASE 1: Next Steps**
With Phase 0 complete, here are the best options for Phase 1:

1. **Confidence Scoring** (3-4 days) - Predict success probability
2. **Parallel Correction Attempts** (4-5 days) - 2-3x faster error recovery
3. **LangGraph Multi-Agent System** (1-2 weeks) - Full agentic architecture
4. **Conversational Memory** (2-3 days) - Context across queries
```

### Task 11.4: Create Implementation Summary

**File**: `../reports/OBSERVABILITY_FEEDBACK_IMPLEMENTATION_SUMMARY.md`

```markdown
# Enhanced Observability + User Feedback Implementation Summary

**Completed**: 2025-10-18
**Duration**: 2 weeks
**Status**: ✅ Production Ready

## What Was Built

### Week 1: Enhanced Observability
Made the AI transparent - users can now see every decision the agent makes.

#### Backend Changes
- **AgentTrace class** - Captures execution steps with timing and metadata
- **Enhanced response schemas** - Added trace, query_plan, attempts fields
- **Format helpers** - UI-friendly formatting for plans and attempts

#### Frontend Changes
- **AgentTrace component** - Timeline view of agent decisions
- **QueryPlan component** - Visual query plan with complexity badges
- **CorrectionHistory component** - Shows auto-correction attempts
- **VerificationWarnings component** - Prominent warning display

### Week 2: User Feedback Integration
Enabled continuous learning from user corrections.

#### Backend Changes
- **UserFeedback model** - Database table for feedback storage
- **Feedback API** - 6 endpoints for submission, application, stats
- **Learning integration** - Connects feedback to CorrectionLearner
- **Safety testing** - Tests corrections before learning

#### Frontend Changes
- **SQLEditor component** - In-browser SQL editing
- **FeedbackModal component** - Full feedback submission UI
- **API integration** - Service functions for feedback operations
- **Success flows** - Confirmation and learning application

## Key Features

### Observability
✅ **Agent Trace** - See every step with timing
✅ **Query Plans** - Understand reasoning
✅ **Correction History** - Track auto-fixes
✅ **Verification Warnings** - Catch issues early

### User Feedback
✅ **Submit Corrections** - SQL, column names, table names
✅ **Test Before Learning** - Automatic validation
✅ **Apply to Learning** - Add to knowledge base
✅ **Auto-Application** - Use in future queries

## Performance Impact

### Observability
- **Trace overhead**: ~10-50ms (0.5-2% of query time)
- **Memory**: ~5KB per query for trace data
- **Network**: ~2-3KB additional response size

### Feedback
- **Submission**: < 500ms
- **Testing**: < 2s (includes query execution)
- **Learning**: < 100ms (database write)

## Database Changes

### New Table: user_feedback
```sql
- id (primary key)
- query_id (foreign key to query_history)
- feedback_type (sql_correction, column_name, etc.)
- original_sql, corrected_sql
- correction_description, correction_details
- user_confidence (0.0 to 1.0)
- applied_successfully, learned_correction_id
- created_at, applied_at
```

### Indexes Added
- query_id, feedback_type, applied_successfully, created_at

## API Changes

### New Response Fields (Backward Compatible)
```typescript
{
  // Existing fields...

  // NEW:
  "trace": {...},              // Agent execution trace
  "query_plan": {...},         // Query plan details
  "attempts": [...],           // Correction attempts
  "self_corrected": true,      // Whether auto-corrected
  "total_attempts": 2,         // Number of attempts
  "verification_warnings": [], // Result warnings
  "used_planning": true        // Whether planning was used
}
```

### New Endpoints
- `POST /api/feedback/` - Submit feedback
- `POST /api/feedback/apply` - Apply to learning
- `GET /api/feedback/query/{query_id}` - Get query feedback
- `GET /api/feedback/recent` - Recent feedback
- `GET /api/feedback/stats` - Feedback statistics
- `DELETE /api/feedback/{feedback_id}` - Delete feedback

## Files Changed/Created

### Backend (15 files)
- `src/llm/self_correcting_agent.py` - Added AgentTrace
- `src/models/schemas.py` - Added feedback schemas
- `src/database/models.py` - Added UserFeedback model
- `src/api/endpoints/feedback.py` - **NEW** - 300+ lines
- Migration file for user_feedback table

### Frontend (8 files)
- `frontend/src/components/AgentTrace.tsx` - **NEW**
- `frontend/src/components/QueryPlan.tsx` - **NEW**
- `frontend/src/components/CorrectionHistory.tsx` - **NEW**
- `frontend/src/components/VerificationWarnings.tsx` - **NEW**
- `frontend/src/components/SQLEditor.tsx` - **NEW**
- `frontend/src/components/FeedbackModal.tsx` - **NEW**
- `frontend/src/components/QueryResults.tsx` - Updated
- `frontend/src/services/api.ts` - Added feedback functions

### Documentation (5 files)
- `../guides/USER_FEEDBACK_GUIDE.md` - **NEW**
- `../technical/OBSERVABILITY_TESTING.md` - **NEW**
- `OPTION_2_IMPLEMENTATION_PLAN.md` - **NEW**
- `../reports/OBSERVABILITY_FEEDBACK_IMPLEMENTATION_SUMMARY.md` - **NEW**
- `README.md` - Updated
- `NEXT_FEATURES_ROADMAP.md` - Updated

## Success Metrics

### Adoption
- [ ] % of users viewing agent traces
- [ ] % of users expanding query plans
- [ ] Feedback submissions per week
- [ ] Feedback applied to learning

### Impact
- [ ] Accuracy improvement from feedback
- [ ] Reduction in repeated errors
- [ ] User satisfaction increase
- [ ] Query generation speed improvement

## Testing Completed

✅ Unit tests for AgentTrace
✅ Integration tests for feedback API
✅ E2E test: Submit → Learn → Auto-apply
✅ Performance tests (trace overhead)
✅ UI/UX testing on desktop and mobile

## Known Limitations

1. **Trace storage** - Not persisted to database (only in response)
2. **Feedback dashboard** - No dedicated UI page yet
3. **Bulk operations** - Can't apply multiple feedbacks at once
4. **Analytics** - No detailed metrics dashboard yet

## Future Enhancements

### Short Term (1-2 weeks)
- Persist traces to database for history
- Add feedback dashboard page
- Bulk feedback operations
- Export feedback as CSV

### Medium Term (1 month)
- Analytics dashboard for learning impact
- Feedback voting/ranking system
- Conflict resolution for contradictory feedback
- Feedback categories and tagging

### Long Term (2+ months)
- A/B testing for learned corrections
- Feedback quality scoring
- Automatic feedback detection (flag suspicious results)
- Collaborative filtering for corrections

## Deployment Notes

### Prerequisites
- PostgreSQL 12+ or SQLite 3.35+
- Python 3.11+
- Node.js 18+

### Deployment Steps
1. Pull latest code
2. Run database migration: `alembic upgrade head`
3. Restart backend: `systemctl restart database-guru-backend`
4. Build frontend: `cd frontend && npm run build`
5. Deploy frontend build to web server

### Rollback Plan
If issues occur:
1. Revert database migration: `alembic downgrade -1`
2. Deploy previous code version
3. Restart services

## Conclusion

✅ **Phase 0 Complete!** (6/6 features done)
✅ **Observability Delivered** - Full transparency into AI decisions
✅ **Feedback System Live** - Continuous learning enabled
✅ **Production Ready** - Tested and documented

**Next recommended step:** Confidence Scoring (3-4 days) to optimize resource usage and predict success probability.

---

**Implementation Team:** Claude Code
**Documentation:** Complete
**Status:** ✅ Ready for Production
```

### Deliverable Checklist
- [ ] User guide created
- [ ] README updated
- [ ] Roadmap updated
- [ ] Implementation summary created
- [ ] All docs reviewed and polished

---

## Final Validation Checklist

### Week 1: Observability
- [ ] Agent trace displays in UI for all queries
- [ ] Query plan visualization works correctly
- [ ] Correction history shows for auto-corrected queries
- [ ] Verification warnings display prominently
- [ ] All components responsive on mobile
- [ ] Performance acceptable (< 50ms trace overhead)

### Week 2: Feedback
- [ ] Feedback submission works
- [ ] SQL editor functional
- [ ] Feedback testing validates corrections
- [ ] Learning integration creates learned_corrections
- [ ] Learned corrections auto-apply to future queries
- [ ] Stats endpoint returns correct data

### Integration
- [ ] E2E: Query → Trace → Feedback → Learn → Auto-apply
- [ ] Database migrations applied successfully
- [ ] No errors in browser console
- [ ] No errors in server logs
- [ ] API documentation updated (Swagger)

### Documentation
- [ ] User guide complete and clear
- [ ] Implementation summary accurate
- [ ] README reflects new features
- [ ] Roadmap updated with completion
- [ ] Testing guide usable by others

---

## Success Criteria

This implementation is successful if:

1. ✅ Users can see what the AI is doing (observability)
2. ✅ Users can correct queries (feedback)
3. ✅ System learns from corrections (auto-apply)
4. ✅ Performance impact is minimal (< 5%)
5. ✅ Documentation is clear and complete
6. ✅ All tests pass
7. ✅ Phase 0 roadmap is complete (6/6 features)

---

## Timeline Summary

| Week | Phase | Hours | Deliverables |
|------|-------|-------|--------------|
| 1 | Observability | 22-30h | Trace, Plan, History, Warnings |
| 2 | Feedback | 30-42h | Submit, Test, Learn, Auto-apply |
| **Total** | **Both** | **52-72h** | **Full transparency + learning** |

---

**Ready to implement?** Start with Week 1, Day 1: Backend - Agent Trace System! 🚀
