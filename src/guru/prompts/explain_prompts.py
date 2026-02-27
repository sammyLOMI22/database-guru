"""Tiered EXPLAIN analysis prompts for different model sizes (Phase 22).

Provides compact, standard, and enhanced prompt templates selected
based on the model size to optimize token usage and quality.
"""

from src.llm.prompt_optimizer import ModelSize


# ============================================================================
# Token budgets per tier
# ============================================================================

EXPLAIN_TOKEN_BUDGETS = {
    ModelSize.SMALL: 600,
    ModelSize.MEDIUM: 1200,
    ModelSize.LARGE: 2000,
}


# ============================================================================
# COMPACT — Small models (top-3 bottlenecks, 1 index suggestion)
# ============================================================================

EXPLAIN_PROMPT_COMPACT = """SQL performance analyst. Database: {database_type}

Query:
{sql}

EXPLAIN plan:
{explain_plan}

Warnings:
{warnings}

{schema_context}
Return JSON ONLY:
{{"summary": "1 sentence on worst bottleneck", "overall_severity": "good|warning|critical", "bottlenecks": [{{"node_type": "str", "table_or_index": "str", "severity": "low|medium|high|critical", "description": "str", "impact_estimate": "str"}}], "index_suggestions": [{{"table": "str", "columns": ["col"], "reason": "str", "create_sql": "CREATE INDEX ...", "estimated_speedup": "str"}}], "query_rewrites": [], "general_recommendations": ["str"], "confidence": 0.0-1.0}}"""


# ============================================================================
# STANDARD — Medium models (full bottlenecks, index suggestions, rewrites)
# ============================================================================

EXPLAIN_PROMPT_STANDARD = """You are a database performance analyst. Analyze this execution plan and provide actionable optimization advice.

DATABASE TYPE: {database_type}

SQL QUERY:
{sql}

EXECUTION PLAN:
{explain_plan}

DETERMINISTIC WARNINGS:
{warnings}

{schema_context}

INSTRUCTIONS:
1. Identify ALL performance bottlenecks (sequential scans, disk spills, expensive joins)
2. Suggest specific indexes with CREATE INDEX SQL statements
3. If the query can be rewritten for better performance, provide the rewritten SQL
4. Estimate the impact of each suggestion

Return JSON ONLY with this structure:
{{
  "summary": "2-3 sentence overview of query performance and main issues",
  "overall_severity": "good|warning|critical",
  "bottlenecks": [
    {{
      "node_type": "operation type (e.g. Seq Scan, Hash Join)",
      "table_or_index": "affected table or index name",
      "severity": "low|medium|high|critical",
      "description": "what the bottleneck is and why it matters",
      "impact_estimate": "estimated performance impact"
    }}
  ],
  "index_suggestions": [
    {{
      "table": "table name",
      "columns": ["column1", "column2"],
      "reason": "why this index helps",
      "create_sql": "CREATE INDEX idx_name ON table(col1, col2)",
      "estimated_speedup": "e.g. 10-50x for filtered queries"
    }}
  ],
  "query_rewrites": [
    {{
      "original_pattern": "what in the original query is suboptimal",
      "rewritten_sql": "improved SQL",
      "reason": "why this is better",
      "expected_improvement": "estimated improvement"
    }}
  ],
  "general_recommendations": ["actionable recommendation"],
  "confidence": 0.0-1.0
}}"""


# ============================================================================
# ENHANCED — Large models (all above + before/after estimates, memory tuning)
# ============================================================================

EXPLAIN_PROMPT_ENHANCED = """You are an expert database performance analyst with deep knowledge of {database_type} internals.

Analyze this execution plan and provide comprehensive, actionable optimization advice.

DATABASE TYPE: {database_type}

SQL QUERY:
{sql}

EXECUTION PLAN:
{explain_plan}

DETERMINISTIC WARNINGS:
{warnings}

{schema_context}

ANALYSIS REQUIREMENTS:
1. Identify ALL performance bottlenecks:
   - Sequential/full table scans on large tables
   - Disk spills (sort or hash operations exceeding memory)
   - Inefficient join strategies (nested loops where hash/merge would be better)
   - High row estimates that get filtered down
   - Missing or unused indexes

2. Provide specific index suggestions:
   - Include the full CREATE INDEX statement
   - Consider composite indexes for multi-column filters
   - For PostgreSQL, suggest CONCURRENTLY when appropriate
   - Consider partial indexes for filtered queries

3. Suggest query rewrites if applicable:
   - Provide the complete rewritten SQL
   - Explain why the rewrite is more efficient
   - Consider CTEs, subquery optimization, EXISTS vs IN, etc.

4. Estimate before/after performance impact:
   - Current estimated cost or actual time
   - Expected cost/time after applying suggestions
   - Explain the reasoning

5. Server-level recommendations if relevant:
   - work_mem adjustments for disk spills
   - effective_cache_size considerations
   - Other relevant configuration parameters

Return JSON ONLY with this structure:
{{
  "summary": "3-4 sentence comprehensive overview of query performance",
  "overall_severity": "good|warning|critical",
  "bottlenecks": [
    {{
      "node_type": "operation type",
      "table_or_index": "affected table or index",
      "severity": "low|medium|high|critical",
      "description": "detailed explanation of the bottleneck",
      "impact_estimate": "quantified impact (e.g. '85% of total query cost')"
    }}
  ],
  "index_suggestions": [
    {{
      "table": "table name",
      "columns": ["column1", "column2"],
      "reason": "detailed explanation of why this index helps",
      "create_sql": "CREATE INDEX CONCURRENTLY idx_name ON table(col1, col2)",
      "estimated_speedup": "e.g. Seq Scan (cost=1823) -> Index Scan (cost=8)"
    }}
  ],
  "query_rewrites": [
    {{
      "original_pattern": "suboptimal pattern in the original query",
      "rewritten_sql": "complete improved SQL query",
      "reason": "detailed explanation of the improvement",
      "expected_improvement": "quantified improvement estimate"
    }}
  ],
  "before_after_estimate": "Current: ~500ms, After suggestions: ~12ms (index eliminates Seq Scan)",
  "general_recommendations": ["detailed, actionable recommendation"],
  "confidence": 0.0-1.0
}}"""


# ============================================================================
# Prompt selector
# ============================================================================

_PROMPT_MAP = {
    ModelSize.SMALL: EXPLAIN_PROMPT_COMPACT,
    ModelSize.MEDIUM: EXPLAIN_PROMPT_STANDARD,
    ModelSize.LARGE: EXPLAIN_PROMPT_ENHANCED,
}


def get_explain_prompt(model_size: ModelSize) -> str:
    """Get the appropriate EXPLAIN prompt template for the given model size."""
    return _PROMPT_MAP.get(model_size, EXPLAIN_PROMPT_STANDARD)
