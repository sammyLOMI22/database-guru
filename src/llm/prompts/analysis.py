"""Prompts for result narration and schema analysis."""

SCHEMA_ANALYSIS_TEMPLATE = """Analyze this database schema and provide a structured summary:

{schema}

Provide:
1. List of all tables
2. Primary relationships between tables
3. Common query patterns possible with this schema

Format as JSON."""


QUERY_EXPLANATION_TEMPLATE = """Explain this SQL query in simple terms:

SQL: {sql}

Schema context:
{schema}

Provide a clear, non-technical explanation of what this query does and what results it returns."""


QUERY_OPTIMIZATION_TEMPLATE = """Optimize this SQL query for better performance:

Original query:
{sql}

Schema:
{schema}

Database type: {database_type}

Provide:
1. Optimized SQL query
2. Brief explanation of optimizations made

Format as JSON with keys: "optimized_sql", "improvements" """


NARRATIVE_GENERATION_PROMPT = """You are a data analyst explaining query results to a user in plain English.
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
   - For "How many..." → "There are X [things]"
   - For "What is..." → "The answer is [specific value]"
   - For "Show me..." → "The data shows [specific findings]"

4. CONFIDENCE: Your confidence (0.0-1.0) that your interpretation is correct
   - 0.9-1.0: Clear, unambiguous results with sufficient sample size
   - 0.7-0.9: Good confidence, reasonable patterns visible
   - 0.5-0.7: Moderate confidence, limited data or unclear patterns
   - <0.5: Low confidence, very small dataset or unclear patterns

STYLE GUIDELINES:
- Be conversational and natural, like talking to a colleague
- Use specific numbers with context: "ranging from $15-$300" not just "$100 average"
- Show comparisons: "3x higher than", "10% increase from"
- Highlight outliers: "one unusual case", "notably different from the rest"
- Use simple language: avoid "aggregate", "cardinality", "tuple" etc.
- GOOD: "We found 5 products, with stock ranging from 15 to 300 units"
- BAD: "The cardinality of products is 5 with numeric aggregate statistics showing min=15, max=300"

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


MULTI_DATABASE_NARRATIVE_PROMPT = """You are a data analyst comparing query results across MULTIPLE databases.
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
   - NOT: "Queried 2 databases, found X and Y rows"
   - YES: "Database A shows 45% higher values than Database B, with DB B having more consistent patterns"
   - Highlight the MOST INTERESTING finding that spans databases

2. KEY INSIGHTS (4-6 bullet points): Patterns and comparisons across databases
   - Compare databases: "Database A leads with X feature, but Database B has better Y coverage"
   - Show differences: "Results vary by 30-50% between databases, suggesting different data collection methods"
   - Identify leaders: "Database C has the highest volume (5000+ rows), Database A has the most recent data"
   - Find patterns: "All databases show X trend, but magnitude differs 3x between sources"
   - Highlight gaps: "Database B is missing data for category Z, only found in A and C"
   - Show completeness: "Complete coverage across all databases for metric X, but sparse for Y"

3. DIRECT ANSWER: If the question asks for comparison, state it clearly
   - For "Compare..." → "Database A has [metric] while Database B has [metric], meaning..."
   - For "Which..." → "Database A [wins/leads/shows most] for [reason]"
   - For "Show me..." → "The data shows X across databases, with these differences..."

4. CONFIDENCE: Your confidence (0.0-1.0) that your interpretation is correct
   - 0.9-1.0: Clear patterns visible across all databases with large sample sizes
   - 0.7-0.9: Good confidence, strong patterns visible despite some variation
   - 0.5-0.7: Moderate confidence, patterns exist but databases are inconsistent
   - <0.5: Low confidence, very different data or small samples across databases

STYLE GUIDELINES:
- Compare explicitly: "Database A shows 3x the volume of B"
- Highlight gaps: "Coverage varies: A has 100% for metric X, B only 40%"
- Show ranking: "By volume: C > A > B. By recency: A > C > B"
- Use percentages for comparisons: "Database B is 25% higher than average"
- Note consistency: "All databases agree on X, but diverge significantly on Y"
- GOOD: "DB A dominates with 60% of total records and most recent data, while DB B shows deeper historical patterns"
- BAD: "Queried 2 databases and found 100 and 80 rows respectively"

DATABASE BREAKDOWN CONTEXT:
{database_details}

RESPOND IN JSON FORMAT ONLY:
{{
  "summary": "Direct cross-database comparison showing the most important finding that spans sources",
  "key_insights": [
    "Database-specific finding with comparison to others",
    "Pattern that differs across databases with magnitude",
    "Ranking or leadership by key metric",
    "Consistency or gaps across sources",
    "Unexpected finding from combining the data",
    "Actionable difference between databases"
  ],
  "direct_answer": "Specific answer to the question comparing databases (or null if narrative covers it)",
  "confidence": 0.85
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting or explanation."""
