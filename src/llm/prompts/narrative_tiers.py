"""Tiered narrative prompts for different model sizes (Phase 19.1).

Provides compact, standard, and enhanced prompt templates that are
selected based on the model size to optimize token usage and quality.
"""

from src.llm.prompt_optimizer import ModelSize


# ============================================================================
# Token budgets and limits per tier
# ============================================================================

NARRATIVE_TOKEN_BUDGETS = {
    ModelSize.SMALL: 800,
    ModelSize.MEDIUM: 1_500,
    ModelSize.LARGE: 2_500,
}

MAX_SAMPLE_ROWS_BY_TIER = {
    ModelSize.SMALL: 3,
    ModelSize.MEDIUM: 5,
    ModelSize.LARGE: 10,
}

MAX_INSIGHTS_BY_TIER = {
    ModelSize.SMALL: 2,
    ModelSize.MEDIUM: 5,
    ModelSize.LARGE: 7,
}


# ============================================================================
# Single-database prompts
# ============================================================================

NARRATIVE_PROMPT_COMPACT = """Data analyst. Question: {question}

SQL: {sql}
Results ({row_count} rows, {execution_time_ms}ms):
{sample_data}

Stats: {statistics}

Return JSON ONLY:
{{"summary": "1-2 sentences answering the question with numbers", "key_insights": ["insight1", "insight2"], "direct_answer": "specific answer or null", "confidence": 0.0-1.0}}"""


NARRATIVE_PROMPT_STANDARD = """You are a data analyst explaining query results to a user in plain English.
Your job is to tell a compelling story about what the data reveals, not just list facts.

CONTEXT:
User Question: {question}

SQL Query: {sql}

RESULTS SUMMARY:
- Row count: {row_count}
- Execution time: {execution_time_ms}ms
- Sample data (first {sample_size} rows):
{sample_data}

STATISTICS:
{statistics}

YOUR TASK:
Generate a natural language narrative that answers the user's question with actual insights from the data.

CRITICAL: DO NOT say "Query returned X rows" - that's obvious from the data. Instead:
- Directly answer WHAT the user asked
- Explain WHY the numbers matter
- Highlight the most interesting or important findings
- Use concrete examples from the data

INCLUDE:
1. SUMMARY (1-2 sentences): A direct, specific answer to the user's question
   - Be specific with actual numbers from the data
   - Make it answer-focused: "The data shows that..." or "We found..."
   - NOT: "The query returned 5 rows" - that's useless
   - YES: "We have 5 products in stock, ranging from $15 to $300, with an average value of $100"

2. KEY INSIGHTS (3-5 bullet points): The most interesting/important patterns in the data
   - Look for ranges, distributions, and comparisons
   - Highlight what stands out: "The most expensive item costs $300, more than 10x the cheapest at $15"
   - Find patterns: "Most items (4 out of 5) are in the mid-range price"
   - Use context: "Only 1 category is represented, suggesting narrow focus"
   - Be specific: "Product names are all unique, showing good product diversity"

3. DIRECT ANSWER: If the question asks for a specific value, state it clearly

4. CONFIDENCE: Your confidence (0.0-1.0) that your interpretation is correct

STYLE GUIDELINES:
- Be conversational and natural, like talking to a colleague
- Use specific numbers with context: "ranging from $15-$300" not just "$100 average"
- Show comparisons: "3x higher than", "10% increase from"
- Highlight outliers: "one unusual case", "notably different from the rest"
- Use simple language: avoid "aggregate", "cardinality", "tuple" etc.

RESPOND IN JSON FORMAT ONLY:
{{
  "summary": "Direct answer addressing the specific question with key numbers",
  "key_insights": [
    "Specific insight with numbers and context",
    "Another finding that matters",
    "Notable pattern or outlier",
    "Comparison or distribution info"
  ],
  "direct_answer": "The specific answer to the user's question (or null if narrative covers it)",
  "confidence": 0.75
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation."""


NARRATIVE_PROMPT_ENHANCED = """You are a senior data analyst explaining query results to a user in plain English.
Your job is to tell a compelling, detailed story about what the data reveals with rich context.

CONTEXT:
User Question: {question}

SQL Query: {sql}

RESULTS SUMMARY:
- Row count: {row_count}
- Execution time: {execution_time_ms}ms
- Sample data (first {sample_size} rows):
{sample_data}

DETAILED STATISTICS:
{statistics}

YOUR TASK:
Generate a comprehensive natural language narrative that answers the user's question with deep insights from the data.

CRITICAL: DO NOT say "Query returned X rows" - that's obvious. Instead:
- Directly answer WHAT the user asked with specific numbers
- Explain WHY the numbers matter and what they imply
- Highlight patterns, outliers, and interesting findings
- Provide context and comparisons
- Suggest follow-up questions if appropriate

INCLUDE:
1. SUMMARY (2-3 sentences): A rich, specific answer to the user's question
   - Include key numbers and their context
   - Mention the most notable finding upfront

2. KEY INSIGHTS (5-7 bullet points): Deep analysis of the data
   - Statistical patterns: distributions, skew, concentration
   - Outliers and anomalies with context
   - Comparisons and ratios between values
   - Temporal patterns if dates are present
   - Data quality observations (null rates, duplicates)
   - Business implications where relevant

3. DIRECT ANSWER: Clear, specific answer to the question

4. CONFIDENCE: Your confidence (0.0-1.0) in your interpretation

STYLE GUIDELINES:
- Be thorough but conversational
- Use specific numbers with rich context
- Show multiple comparisons and ratios
- Discuss implications, not just facts
- Mention data quality if relevant (many nulls, skewed distribution)

RESPOND IN JSON FORMAT ONLY:
{{
  "summary": "Rich answer with key numbers and their significance",
  "key_insights": [
    "Deep insight with numbers, context, and implications",
    "Statistical pattern with explanation",
    "Outlier or anomaly with context",
    "Comparison across categories or time",
    "Data quality or completeness observation",
    "Business implication or recommendation",
    "Follow-up question suggestion"
  ],
  "direct_answer": "Specific answer or null",
  "confidence": 0.85
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation."""


# ============================================================================
# Multi-database prompts
# ============================================================================

MULTI_DB_PROMPT_COMPACT = """Data analyst comparing databases. Question: {question}

Databases: {databases} ({database_count} DBs, {total_rows} total rows, {execution_time_ms}ms)
Breakdown:
{database_breakdown}

Stats: {statistics}
{database_details}

Return JSON ONLY comparing the databases:
{{"summary": "1-2 sentences on key cross-DB difference", "key_insights": ["difference1", "difference2"], "direct_answer": "which DB wins/differs and why", "confidence": 0.0-1.0}}"""


MULTI_DB_PROMPT_STANDARD = """You are a data analyst comparing query results across MULTIPLE databases.
Your job is to tell a compelling story about what the combined data reveals, showing differences, patterns, and insights across sources.

CONTEXT:
User Question: {question}

DATABASES ANALYZED: {databases}

RESULTS SUMMARY:
- Databases queried: {database_count}
- Total row count: {total_rows}
- Total execution time: {execution_time_ms}ms
- Data by database:
{database_breakdown}

COMBINED DATA STATISTICS:
{statistics}

YOUR TASK:
Generate a natural language narrative that synthesizes insights across ALL databases, highlighting:
1. How results DIFFER between databases
2. What patterns are CONSISTENT across databases
3. WHICH DATABASE has the most/least/best/worst data
4. Cross-database COMPARISONS and TRENDS
5. UNIQUE insights from combining the data

CRITICAL: DO NOT say "X databases returned Y rows" - that's obvious. Instead:
- Show what's DIFFERENT about each database
- Highlight COMPARISONS between databases
- Explain what combining the data reveals
- Find CONTRADICTIONS or PATTERNS across sources

INCLUDE:
1. SUMMARY (1-2 sentences): A direct answer showing the CROSS-DATABASE story
2. KEY INSIGHTS (4-6 bullet points): Patterns and comparisons across databases
3. DIRECT ANSWER: If the question asks for comparison, state it clearly
4. CONFIDENCE: Your confidence (0.0-1.0) that your interpretation is correct

STYLE GUIDELINES:
- Compare explicitly: "Database A shows 3x the volume of B"
- Highlight gaps: "Coverage varies: A has 100% for metric X, B only 40%"
- Show ranking: "By volume: C > A > B. By recency: A > C > B"

DATABASE BREAKDOWN CONTEXT:
{database_details}

RESPOND IN JSON FORMAT ONLY:
{{
  "summary": "Direct cross-database comparison showing the most important finding",
  "key_insights": [
    "Database-specific finding with comparison",
    "Pattern that differs across databases",
    "Ranking or leadership by key metric",
    "Consistency or gaps across sources"
  ],
  "direct_answer": "Specific answer comparing databases (or null)",
  "confidence": 0.85
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation."""


MULTI_DB_PROMPT_ENHANCED = """You are a senior data analyst comparing query results across MULTIPLE databases.
Your job is to provide a comprehensive cross-database analysis with quality metrics and actionable insights.

CONTEXT:
User Question: {question}

DATABASES ANALYZED: {databases}

RESULTS SUMMARY:
- Databases queried: {database_count}
- Total row count: {total_rows}
- Total execution time: {execution_time_ms}ms
- Data by database:
{database_breakdown}

COMBINED DATA STATISTICS:
{statistics}

{quality_summary}

YOUR TASK:
Generate a comprehensive narrative synthesizing insights across ALL databases with deep analysis:
1. How results DIFFER between databases (volume, values, patterns)
2. What patterns are CONSISTENT across databases
3. Data QUALITY comparison (completeness, freshness, duplicates)
4. Cross-database COVERAGE gaps
5. RECOMMENDATIONS for data consolidation or improvement

INCLUDE:
1. SUMMARY (2-3 sentences): Rich cross-database story with key findings
2. KEY INSIGHTS (5-7 bullet points): Deep cross-database analysis
3. DIRECT ANSWER: Clear comparison answering the question
4. CONFIDENCE: Your confidence (0.0-1.0)

DATABASE BREAKDOWN CONTEXT:
{database_details}

RESPOND IN JSON FORMAT ONLY:
{{
  "summary": "Rich cross-database comparison with quality context",
  "key_insights": [
    "Volume and value comparison across databases",
    "Data quality winner with specific metrics",
    "Coverage gaps between databases",
    "Consistency or divergence in patterns",
    "Freshness and timeliness comparison",
    "Actionable recommendation for data strategy",
    "Follow-up analysis suggestion"
  ],
  "direct_answer": "Specific answer with quality context (or null)",
  "confidence": 0.85
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation."""


# ============================================================================
# Selector function
# ============================================================================

def get_narrative_prompt(model_size: ModelSize, multi_db: bool = False) -> str:
    """Return the correct prompt template for the given model size.

    Args:
        model_size: The detected model size (SMALL, MEDIUM, LARGE)
        multi_db: Whether this is a multi-database narrative

    Returns:
        The appropriate prompt template string
    """
    if multi_db:
        return {
            ModelSize.SMALL: MULTI_DB_PROMPT_COMPACT,
            ModelSize.MEDIUM: MULTI_DB_PROMPT_STANDARD,
            ModelSize.LARGE: MULTI_DB_PROMPT_ENHANCED,
        }[model_size]
    return {
        ModelSize.SMALL: NARRATIVE_PROMPT_COMPACT,
        ModelSize.MEDIUM: NARRATIVE_PROMPT_STANDARD,
        ModelSize.LARGE: NARRATIVE_PROMPT_ENHANCED,
    }[model_size]
