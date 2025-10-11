"""Prompt templates for SQL generation"""

SYSTEM_PROMPT = """You are an expert SQL query generator. Your job is to convert natural language questions into valid SQL queries.

CRITICAL RULES:
1. Generate ONLY the SQL query - no explanations, no markdown, no extra text
2. Use proper SQL syntax for the specified database type
3. Always use parameterized queries when user input is involved
4. Never include DROP, DELETE, TRUNCATE, or other destructive operations unless explicitly requested
5. Use appropriate JOINs, WHERE clauses, and aggregations based on the question
6. Return only SELECT queries unless modification is explicitly requested
7. Use table and column names EXACTLY as provided in the schema - look for "Table:" in the schema
8. Include LIMIT clauses for queries that could return large result sets
9. ALWAYS include the table name in SELECT statements (e.g., SELECT * FROM table_name LIMIT 10)
10. NEVER generate incomplete SQL like "SELECT * LIMIT 10" - always specify FROM table_name
11. Database names (like "ECommerceTestDB") are NOT table names - only use table names from the schema
12. If the user mentions "database" in their question, they likely mean grouping/aggregating data, NOT querying a table called "database"

Output format: Return ONLY the SQL query, nothing else."""


SQL_GENERATION_TEMPLATE = """Given the following database schema:

{schema}

Generate a SQL query to answer this question: {question}

Database type: {database_type}

IMPORTANT:
- Your query MUST include the table name (e.g., SELECT * FROM products LIMIT 10)
- NEVER write incomplete queries like "SELECT * LIMIT 10"
- Use ONLY the table names from the schema above (look for "Table:" in the schema)
- Do NOT use database connection names as table names
- Valid table names are: products, orders, customers, etc. (from schema above)
- INVALID table names: database names like "ECommerceTestDB" are NOT tables

SQL Query:"""


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
) -> str:
    """
    Build a complete prompt for SQL generation

    Args:
        question: Natural language question
        schema: Database schema information
        database_type: Type of database (postgresql, mysql, sqlite, etc.)
        examples: Optional few-shot examples

    Returns:
        Complete prompt string
    """
    prompt = SQL_GENERATION_TEMPLATE.format(
        schema=schema,
        question=question,
        database_type=database_type,
    )

    if examples:
        prompt = f"{examples}\n\n{prompt}"

    return prompt


def build_chat_messages(
    question: str,
    schema: str,
    database_type: str = "postgresql",
    conversation_history: list = None,
) -> list:
    """
    Build chat messages for conversation-based SQL generation

    Args:
        question: Natural language question
        schema: Database schema information
        database_type: Type of database
        conversation_history: Previous conversation messages

    Returns:
        List of message dictionaries
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Add current question
    user_message = build_sql_prompt(question, schema, database_type)
    messages.append({"role": "user", "content": user_message})

    return messages


# Few-shot examples for better SQL generation
FEW_SHOT_EXAMPLES = """
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
"""
