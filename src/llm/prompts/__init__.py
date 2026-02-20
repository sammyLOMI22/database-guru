"""Prompt templates for SQL generation, analysis, and dialect rules.

Re-exports all public symbols for backward compatibility with
``from src.llm.prompts import ...``.
"""

from src.llm.prompts.dialects import DIALECT_RULES, get_dialect_rules
from src.llm.prompts.analysis import (
    NARRATIVE_GENERATION_PROMPT,
    MULTI_DATABASE_NARRATIVE_PROMPT,
    SCHEMA_ANALYSIS_TEMPLATE,
    QUERY_EXPLANATION_TEMPLATE,
    QUERY_OPTIMIZATION_TEMPLATE,
)
from src.llm.prompts.narrative_tiers import (
    get_narrative_prompt,
    NARRATIVE_TOKEN_BUDGETS,
    MAX_SAMPLE_ROWS_BY_TIER,
    MAX_INSIGHTS_BY_TIER,
)
from src.llm.prompts.sql_generation import (
    SYSTEM_PROMPT,
    SQL_GENERATION_TEMPLATE,
    ERROR_CORRECTION_TEMPLATE,
    MULTI_DATABASE_SYSTEM_PROMPT,
    MULTI_DATABASE_QUERY_TEMPLATE,
    INTENT_SQL_REQUIREMENTS,
    FEW_SHOT_EXAMPLES,
    build_intent_instructions,
    build_sql_prompt,
    build_chat_messages,
    build_few_shot_examples,
)

__all__ = [
    "DIALECT_RULES",
    "get_dialect_rules",
    "NARRATIVE_GENERATION_PROMPT",
    "MULTI_DATABASE_NARRATIVE_PROMPT",
    "SCHEMA_ANALYSIS_TEMPLATE",
    "QUERY_EXPLANATION_TEMPLATE",
    "QUERY_OPTIMIZATION_TEMPLATE",
    "SYSTEM_PROMPT",
    "SQL_GENERATION_TEMPLATE",
    "ERROR_CORRECTION_TEMPLATE",
    "MULTI_DATABASE_SYSTEM_PROMPT",
    "MULTI_DATABASE_QUERY_TEMPLATE",
    "INTENT_SQL_REQUIREMENTS",
    "FEW_SHOT_EXAMPLES",
    "build_intent_instructions",
    "build_sql_prompt",
    "build_chat_messages",
    "build_few_shot_examples",
    "get_narrative_prompt",
    "NARRATIVE_TOKEN_BUDGETS",
    "MAX_SAMPLE_ROWS_BY_TIER",
    "MAX_INSIGHTS_BY_TIER",
]
