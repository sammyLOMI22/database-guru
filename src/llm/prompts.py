"""Prompt templates for SQL generation"""

SYSTEM_PROMPT = """You are an expert SQL query generator. Your job is to convert natural language questions into valid SQL queries.

CRITICAL RULES - SCHEMA FIRST:
1. ONLY use table and column names that exist in the provided schema - NEVER invent or assume table names
2. The schema provided is the ONLY source of truth for table/column names
3. If the query CANNOT be answered with the available schema (e.g., asking about customers but no customers table exists), respond with:
   CANNOT_ANSWER: [brief explanation of what's missing]
4. Look for "Table:" in the schema to identify valid table names

CHAIN OF THOUGHT (for complex queries):
When answering queries that involve JOINs or multiple tables:
5. First identify ALL tables needed for the query (both for data AND for filtering)
6. Check if tables are DIRECTLY related (share a foreign key) - if NOT, find the bridge table
7. Use the COMMON JOIN PATHS section in the schema - it shows how to connect tables
8. NEVER invent join columns - only use columns that exist in the schema
9. Consider what columns to SELECT
10. Apply WHERE conditions - make sure you JOIN to the table that has the filter column!
11. Add GROUP BY for aggregations
12. Apply ORDER BY and LIMIT as needed

CRITICAL FOR MULTI-TABLE QUERIES:
- If you need to filter by a column (e.g., state, status), you MUST JOIN to the table that has it
- Look at Foreign Keys section to see how tables connect
- If there's no direct FK between two tables, use a bridge table (e.g., order_items connects orders to products)
- If using table aliases, you MUST define them: FROM customers c JOIN orders o (not just using c, o without definition)
- Either use full table names (customers.id) OR define aliases (FROM customers c ... WHERE c.id)

JOIN REASONING (for complex queries involving 2+ tables):
Before writing the SQL, mentally plan the join path:
1. Identify the SOURCE table (where the data comes from)
2. Identify the TARGET table (where the filter/grouping applies)
3. Find the PATH: Are they directly connected via FK? If not, what bridge table(s) connect them?
4. Verify each JOIN condition uses matching column types (e.g., id = id, not id = name)
5. ALWAYS qualify columns with table names when multiple tables are involved to avoid ambiguity
   - GOOD: SELECT customers.name, orders.total FROM customers JOIN orders
   - BAD: SELECT name, total FROM customers JOIN orders (ambiguous if both have 'name')

ADDITIONAL RULES:
11. Generate ONLY the SQL query - no explanations, no markdown, no extra text
12. Use proper SQL syntax for the specified database type
13. Never include DROP, DELETE, TRUNCATE, or other destructive operations unless explicitly requested
14. Use appropriate JOINs, WHERE clauses, and aggregations based on the question
15. Return only SELECT queries unless modification is explicitly requested
16. Include LIMIT clauses for queries that could return large result sets
17. ALWAYS include the table name in SELECT statements (e.g., SELECT * FROM table_name LIMIT 10)
18. Database names (like "ECommerceTestDB") are NOT table names

LOCATION HANDLING - DYNAMIC (adapt to actual schema):
- Look for [LOCATION:us_state] hint in schema - these columns use 2-letter codes (CA, NY, TX)
- Look for [LOCATION:city] or similar hints - these use full names
- When query mentions a location (state, city, country), find the table with that location column in the schema
- If the location column is in a different table than your target data, use JOIN paths from the Foreign Keys section
- NEVER assume location is in a specific table - CHECK THE SCHEMA for which table has [LOCATION] columns

DYNAMIC JOIN PATH DISCOVERY:
1. Identify which table has the column you need to filter on (check schema for [LOCATION] or column names)
2. Find the join path using Foreign Keys section - follow the FK relationships
3. Use the EXACT column names shown in the schema (id vs customer_id, etc.)

CRITICAL SQL SYNTAX RULES:
- Column references are: table_name.column_name (e.g., orders.customer_id)
- NEVER use nested dots like: table.other_table.column - this is INVALID SQL!
- When joining tables, use the EXACT column names from the schema Foreign Keys section
- Different databases may have different column names (id vs customer_id) - USE WHAT'S IN THE SCHEMA

Output format: Return ONLY the SQL query, OR "CANNOT_ANSWER: reason" if impossible."""


SQL_GENERATION_TEMPLATE = """Given the following database schema:

{schema}

Generate a SQL query to answer this question: {question}

Database type: {database_type}
Row limit: {row_limit}

CRITICAL - READ THE SCHEMA ABOVE CAREFULLY:
- Use ONLY the table names listed in the schema above (look for "Table:" entries)
- NEVER assume table names exist - only use what's in the schema
- If the question asks about data that doesn't exist in this schema (e.g., "customers" when there's no customers table, or "state/location" when no such column exists), respond with: CANNOT_ANSWER: [what data is missing]
- For location/state queries, use 2-letter codes (CA, TX, NY) if a state column exists
- Include LIMIT {row_limit} in your query (unless doing aggregations like COUNT/SUM/AVG)

{dialect_rules}

SQL Query (or CANNOT_ANSWER if impossible):"""


# Dialect-specific SQL rules (addresses PR review: dialect specificity)
DIALECT_RULES = {
    "sqlite": """SQLITE-SPECIFIC RULES:
- Use strftime() for date formatting: strftime('%Y-%m-%d', date_column)
- Use date('now') for current date, datetime('now') for current timestamp
- Use || for string concatenation (NOT CONCAT)
- Use LIKE for case-insensitive matching (SQLite LIKE is case-insensitive for ASCII)
- Use IFNULL() instead of COALESCE() for simple null handling
- Boolean values are 0 and 1, not TRUE/FALSE
- Use substr() instead of SUBSTRING()""",

    "postgresql": """POSTGRESQL-SPECIFIC RULES:
- Use ILIKE for case-insensitive matching (NOT LIKE)
- Use NOW() or CURRENT_TIMESTAMP for current time
- Use DATE_TRUNC() for date truncation: DATE_TRUNC('month', date_column)
- Use to_char() for date formatting
- Use :: for type casting: column::text, column::integer
- Use COALESCE() for null handling
- Boolean values are TRUE/FALSE
- Use LIMIT with OFFSET for pagination""",

    "mysql": """MYSQL-SPECIFIC RULES:
- Use DATE_FORMAT() for date formatting: DATE_FORMAT(date_column, '%Y-%m-%d')
- Use NOW() for current timestamp, CURDATE() for current date
- Use CONCAT() for string concatenation
- Use IFNULL() or COALESCE() for null handling
- Use LOWER(column) = LOWER('value') for case-insensitive matching
- Use backticks for identifier quoting: `table_name`
- Use LIMIT with OFFSET for pagination""",

    "duckdb": """DUCKDB-SPECIFIC RULES:
- Similar to PostgreSQL syntax
- Use strftime() for date formatting
- Use CURRENT_DATE, CURRENT_TIMESTAMP for current time
- Use || for string concatenation
- Use ILIKE for case-insensitive matching
- Supports list and struct types natively
- Use TRY_CAST() for safe type casting""",
}


def get_dialect_rules(database_type: str) -> str:
    """Get dialect-specific rules for a database type."""
    return DIALECT_RULES.get(database_type.lower(), "")


# ============================================================================
# INTENT-DRIVEN PROMPTING (Phase 1 - SQL Quality Enhancement)
# ============================================================================
# Intent-specific SQL requirements that MUST be followed based on query type.
# This prevents common errors like missing GROUP BY for aggregations,
# missing JOINs for relationship queries, etc.

INTENT_SQL_REQUIREMENTS = {
    "lookup": """QUERY TYPE: SIMPLE LOOKUP
Your SQL should:
- Use a simple SELECT statement
- Include appropriate columns (not just SELECT *)
- Add LIMIT clause for large tables
- No aggregation or GROUP BY needed""",

    "aggregation": """QUERY TYPE: AGGREGATION (COUNT/SUM/AVG/etc.)
CRITICAL REQUIREMENTS:
- You MUST include an aggregation function: COUNT(), SUM(), AVG(), MIN(), MAX()
- If selecting non-aggregated columns, you MUST include GROUP BY for those columns
- Do NOT include LIMIT when returning aggregated results (one row per group)
- Common patterns:
  * COUNT(*) for totals
  * COUNT(DISTINCT column) for unique counts
  * SUM(column), AVG(column) for numeric analysis
  * GROUP BY for per-category/per-group breakdowns""",

    "comparison": """QUERY TYPE: COMPARISON/FILTERING
Your SQL should:
- Include appropriate WHERE clause with comparison operators
- Use proper data types in comparisons (strings in quotes, numbers without)
- Consider NULL handling (IS NULL, IS NOT NULL, COALESCE)
- For range queries, use BETWEEN or >= AND <=
- For pattern matching, use LIKE or ILIKE""",

    "relationship": """QUERY TYPE: RELATIONSHIP (Multiple Tables)
CRITICAL REQUIREMENTS:
- You MUST use JOIN to connect related tables
- Check the Foreign Keys section in the schema for exact join columns
- Use appropriate JOIN type:
  * INNER JOIN for matching records in both tables
  * LEFT JOIN when the right table may not have matches
- ALWAYS qualify column names with table names to avoid ambiguity
- If two tables aren't directly related, look for a bridge table""",

    "temporal": """QUERY TYPE: TEMPORAL (Date/Time Filtering)
Your SQL should:
- Use date functions appropriate for the database type
- For "last N days": date_column >= CURRENT_DATE - INTERVAL 'N days'
- For "this month/year": Extract and compare month/year
- Consider timezone implications if applicable
- Sort by date if showing recent records (ORDER BY date_column DESC)""",

    "ranking": """QUERY TYPE: RANKING (Top N / Bottom N)
Your SQL should:
- Include ORDER BY clause with the ranking criteria
- Use LIMIT N for top/bottom N results
- For aggregated rankings, combine with GROUP BY and aggregation functions
- Consider ties: multiple records with same value
- Pattern: SELECT ... ORDER BY column DESC/ASC LIMIT N""",
}


def build_intent_instructions(
    intent_result: "QueryIntentResult" = None,
    include_entities: bool = True
) -> str:
    """Build intent-specific instructions to guide SQL generation.

    This is the core of Phase 1 - Intent-Driven Prompting. By telling the LLM
    exactly what type of query is needed and what SQL constructs are required,
    we dramatically improve first-attempt accuracy for complex queries.

    Args:
        intent_result: The classified query intent from QueryIntentClassifier
        include_entities: Whether to include extracted entities information

    Returns:
        Formatted string with intent-specific instructions to add to the prompt
    """
    if not intent_result:
        return ""

    sections = []

    # 1. Intent type requirements
    intent_key = intent_result.intent.value
    if intent_key in INTENT_SQL_REQUIREMENTS:
        sections.append(INTENT_SQL_REQUIREMENTS[intent_key])

    # 2. Required tables (if identified)
    if intent_result.required_tables:
        tables_list = ", ".join(sorted(intent_result.required_tables))
        sections.append(f"""TABLES YOU SHOULD USE:
The query involves these tables: {tables_list}
- Verify these tables exist in the schema above
- If using multiple tables, check Foreign Keys for how they connect""")

    # 3. Required aggregations
    if intent_result.aggregations:
        agg_list = ", ".join(intent_result.aggregations)
        sections.append(f"""AGGREGATIONS REQUIRED:
You MUST include these functions: {agg_list}
- Remember to add GROUP BY for any non-aggregated columns in SELECT""")

    # 4. Filter conditions extracted
    if intent_result.filters:
        filter_info = []
        for f in intent_result.filters:
            op = f.get("operator", "=")
            val = f.get("value", "?")
            filter_info.append(f"  - {op} {val}")
        if filter_info:
            sections.append(f"""FILTER CONDITIONS DETECTED:
Apply these filters in your WHERE clause:
{chr(10).join(filter_info)}""")

    # 5. Entity mentions (optional - helps with debugging)
    if include_entities and intent_result.extracted_entities:
        # Group by type
        tables = [e for e in intent_result.extracted_entities if e.entity_type == "table" and e.mapped_to_schema]
        columns = [e for e in intent_result.extracted_entities if e.entity_type == "column" and e.mapped_to_schema]
        locations = [e for e in intent_result.extracted_entities if e.entity_type == "location"]

        entity_notes = []
        if tables:
            entity_notes.append(f"Tables mentioned: {', '.join(e.schema_match for e in tables)}")
        if columns:
            entity_notes.append(f"Columns mentioned: {', '.join(e.schema_match for e in columns)}")
        if locations:
            loc_info = [f"{e.original_text}→{e.normalized_value}" for e in locations if e.normalized_value]
            if loc_info:
                entity_notes.append(f"Locations: {', '.join(loc_info)}")

        if entity_notes:
            sections.append(f"""ENTITIES IDENTIFIED IN QUESTION:
{chr(10).join('- ' + note for note in entity_notes)}""")

    if not sections:
        return ""

    # Wrap in clear delimiters
    return f"""
═══════════════════════════════════════════════════════════════
QUERY INTENT ANALYSIS (Confidence: {intent_result.confidence:.0%})
═══════════════════════════════════════════════════════════════

{chr(10).join(sections)}

═══════════════════════════════════════════════════════════════
"""


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


ERROR_CORRECTION_TEMPLATE = """This SQL query resulted in an error. Fix it:

Query:
{sql}

Error:
{error}

Schema:
{schema}

Database type: {database_type}

Provide the corrected SQL query ONLY, no explanation."""


MULTI_DATABASE_SYSTEM_PROMPT = """You are an expert SQL query generator with access to MULTIPLE databases. Your job is to convert natural language questions into valid SQL queries that may span multiple databases.

CRITICAL RULES:
1. You have access to multiple databases - analyze which database(s) contain the data needed
2. If the question requires data from multiple databases, generate separate queries for each
3. Prefix each query with the database name in this format:
   DATABASE: database_name
   SELECT ... FROM table_name ...;

4. Generate ONLY valid SQL queries - no explanations in the query section
5. Use proper SQL syntax for each database's type
6. Never include DROP, DELETE, TRUNCATE unless explicitly requested
7. Use table and column names EXACTLY as provided in the schema
8. Include LIMIT clauses for queries that could return large result sets
9. If comparing data across databases, generate separate queries and note that results need to be combined
10. ALWAYS include the table name in SELECT statements (e.g., SELECT * FROM products LIMIT 10)
11. NEVER generate incomplete SQL like "SELECT * LIMIT 10" - always specify FROM table_name

Output format:
DATABASE: database_name_1
SELECT * FROM table_name LIMIT 10;

DATABASE: database_name_2
SELECT * FROM table_name LIMIT 10;

If only one database is needed, output:
DATABASE: database_name
SELECT * FROM table_name LIMIT 10;"""


MULTI_DATABASE_QUERY_TEMPLATE = """You have access to the following databases:

{schema}

User question: {question}

Instructions:
1. Identify which database(s) contain the relevant data for this question
2. Generate appropriate SQL query/queries for the identified database(s)
3. If the question requires comparing or combining data from multiple databases, generate separate queries for each database
4. Always prefix each query with "DATABASE: <database_name>"
5. CRITICAL: Every SELECT statement MUST include FROM table_name (e.g., SELECT * FROM products LIMIT 10)
6. NEVER write incomplete queries like "SELECT * LIMIT 10"

Generate the SQL query/queries:"""


def build_sql_prompt(
    question: str,
    schema: str,
    database_type: str = "postgresql",
    examples: str = "",
    row_limit: int = 100,
) -> str:
    """
    Build a complete prompt for SQL generation

    Args:
        question: Natural language question
        schema: Database schema information
        database_type: Type of database (postgresql, mysql, sqlite, etc.)
        examples: Optional few-shot examples
        row_limit: Maximum rows to return (default: 100)

    Returns:
        Complete prompt string
    """
    # Get dialect-specific rules (addresses PR review: dialect specificity)
    dialect_rules = get_dialect_rules(database_type)

    prompt = SQL_GENERATION_TEMPLATE.format(
        schema=schema,
        question=question,
        database_type=database_type,
        row_limit=row_limit,
        dialect_rules=dialect_rules,
    )

    if examples:
        prompt = f"{examples}\n\n{prompt}"

    return prompt


def build_chat_messages(
    question: str,
    schema: str,
    database_type: str = "postgresql",
    conversation_history: list = None,
    row_limit: int = 100,
    examples: str = "",
    intent_result: "QueryIntentResult" = None,
) -> list:
    """
    Build chat messages for conversation-based SQL generation

    Args:
        question: Natural language question
        schema: Database schema information
        database_type: Type of database
        conversation_history: Previous conversation messages
        row_limit: Maximum rows to return (default: 100)
        examples: Optional few-shot examples to include
        intent_result: Optional classified query intent for intent-driven prompting

    Returns:
        List of message dictionaries
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Build intent instructions if available (Phase 1 - Intent-Driven Prompting)
    intent_instructions = ""
    if intent_result:
        intent_instructions = build_intent_instructions(intent_result)

    # Add current question with row limit, examples, and intent instructions
    user_message = build_sql_prompt(
        question, schema, database_type, examples=examples, row_limit=row_limit
    )

    # Prepend intent instructions to the user message if available
    if intent_instructions:
        user_message = f"{intent_instructions}\n{user_message}"

    messages.append({"role": "user", "content": user_message})

    return messages


# Few-shot examples for better SQL generation
FEW_SHOT_EXAMPLES = """
IMPORTANT: These examples show SQL PATTERNS only. The table names (users, products, orders, customers)
are examples - you MUST replace them with ACTUAL table names from the provided schema.

Example 1:
Question: Show me all users who signed up last week
SQL: SELECT * FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' LIMIT 100

Example 2:
Question: List all products
SQL: SELECT * FROM products LIMIT 10

Example 3:
Question: What are the top 10 products by revenue?
SQL: SELECT p.name, SUM(oi.quantity * oi.price) as total_revenue
FROM products p
JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.name
ORDER BY total_revenue DESC
LIMIT 10

Example 4:
Question: How many active customers do we have?
SQL: SELECT COUNT(DISTINCT id) FROM customers WHERE status = 'active'

Example 5:
Question: Show all orders
SQL: SELECT * FROM orders LIMIT 10

Example 6:
Question: Group orders by status
SQL: SELECT status, COUNT(*) as count FROM orders GROUP BY status

Example 7:
Question: Show products grouped by category
SQL: SELECT category, COUNT(*) as product_count FROM products GROUP BY category

Example 8 (Location filtering - DYNAMIC based on schema):
Question: Show me records from California
SQL: SELECT * FROM [table_with_state_column] WHERE [state_column] = 'CA' LIMIT 100
Note: Find the table with [LOCATION:us_state] hint in schema. Use 2-letter codes for US states.

Example 9 (Multi-table JOIN with location filter - DYNAMIC):
Question: What items are associated with a specific location?
Pattern:
1. Find which table has the location column (look for [LOCATION] hint in schema)
2. Find the JOIN path from your target table to the location table using Foreign Keys
3. Build JOINs following the FK relationships with EXACT column names from schema
SQL Pattern:
SELECT DISTINCT target.*
FROM target_table target
JOIN bridge_table bridge ON target.[pk] = bridge.[fk_to_target]
JOIN ... (follow FK chain to location table)
WHERE location_table.[location_column] = 'VALUE'
Note: Column names vary by database (id vs customer_id, etc.) - USE EXACT NAMES FROM SCHEMA!

Example 10 (JOIN pattern - use actual table names from schema):
Question: Show products with their categories
SQL: SELECT p.name, c.name as category_name
FROM products p
JOIN categories c ON p.category_id = c.id
LIMIT 100

Example 11 (Aggregation with GROUP BY):
Question: Get order totals by product
SQL: SELECT p.name, SUM(oi.quantity * oi.price) as total_sales
FROM products p
JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.name
ORDER BY total_sales DESC LIMIT 10

Example 12 (Simple filter - use columns that exist in schema):
Question: Find products in a specific category
SQL: SELECT * FROM products WHERE category_id = (SELECT id FROM categories WHERE name LIKE '%search_term%') LIMIT 100
"""


def build_few_shot_examples(
    schema_dict: dict = None,
    intent=None,
    row_limit: int = 10,
    use_enhanced: bool = True
) -> str:
    """Build few-shot examples - dynamic if schema provided, else static.

    When a schema dictionary is provided, generates examples using the ACTUAL
    table and column names from that schema. This prevents the LLM from copying
    example table names (like "users", "products") that may not exist.

    Args:
        schema_dict: Parsed schema dictionary from SchemaInspector
        intent: Optional QueryIntent to prioritize relevant examples
        row_limit: Default LIMIT clause value for examples
        use_enhanced: If True, use Phase 4 enhanced examples with bridge tables

    Returns:
        Formatted string of examples for inclusion in prompt
    """
    if schema_dict:
        try:
            from src.llm.dynamic_example_generator import DynamicExampleGenerator
            generator = DynamicExampleGenerator(schema_dict)

            if intent:
                # Intent-specific examples
                return generator.get_intent_specific_examples(intent, row_limit)
            elif use_enhanced:
                # Phase 4: Use enhanced examples with bridge tables and multi-table aggregations
                return generator.generate_enhanced_examples(intent=intent, row_limit=row_limit)
            else:
                # General examples
                return generator.generate_examples(row_limit=row_limit)
        except Exception as e:
            # Fallback to static examples on error
            import logging
            logging.getLogger(__name__).warning(
                f"Dynamic example generation failed, using static: {e}"
            )

    # Fallback: use static examples with disclaimer
    return FEW_SHOT_EXAMPLES


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
