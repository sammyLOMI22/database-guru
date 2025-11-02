# Conversational Memory User Guide

**For Database Guru Users**
**Version**: 1.0
**Last Updated**: November 1, 2025

## What is Conversational Memory?

Conversational Memory allows you to have natural, multi-turn conversations with Database Guru. Instead of repeating context in every question, you can ask follow-ups like "filter that" or "sort by price" and the system remembers what you're talking about.

### Before Conversational Memory

```
You: "Show me all products"
AI: Here are all products (100 rows)

You: "Filter products by electronics category"
AI: Here are electronics products (25 rows)

You: "Sort those products by price"
AI: ❌ What products? Please provide more context.
```

### With Conversational Memory

```
You: "Show me all products"
AI: Here are all products (100 rows)

You: "Filter by electronics"
AI: ✅ Here are electronics products (25 rows)

You: "Sort by price"
AI: ✅ Here are electronics products sorted by price
```

---

## Getting Started

### 1. Create a Chat Session

A chat session is a conversation space where your queries are remembered.

**In the UI:**
1. Click "New Session" in the left sidebar
2. Give it a name (e.g., "Product Analysis")
3. Select one or more database connections
4. Click "Create"

**Via API:**
```bash
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Analysis",
    "connection_ids": [1]
  }'
```

### 2. Ask Your First Question

Start with a complete, standalone question:

**Good first questions:**
- "Show me all products"
- "Get customers from California"
- "List orders from last month"

**What happens:**
- Query is processed normally
- Result is saved to conversation history
- Context panel shows your first query

### 3. Ask Follow-Up Questions

Now you can refine your query naturally:

**Follow-up examples:**
- "Filter by electronics"
- "Sort by price"
- "Add where clause"
- "Limit to 10 results"
- "Also show the description"

**What happens:**
- System retrieves conversation context
- Enhances your question with previous queries
- Generates context-aware SQL
- Returns refined results

---

## How to Use Conversational Memory Effectively

### Natural Language Patterns

#### Filters and Refinements

```
Query 1: "Show me all customers"
Query 2: "Filter by California"       ← Adds WHERE clause
Query 3: "Also from New York"         ← Adds OR condition
Query 4: "Who ordered this year"      ← Adds date filter
```

#### Sorting and Ordering

```
Query 1: "Show me all products"
Query 2: "Sort by price"              ← Adds ORDER BY
Query 3: "Show highest first"         ← Changes to DESC
```

#### Aggregation and Grouping

```
Query 1: "Show me all orders"
Query 2: "Group by customer"          ← Adds GROUP BY
Query 3: "Count them"                 ← Adds COUNT(*)
Query 4: "Only show more than 5"      ← Adds HAVING clause
```

#### Combining Tables

```
Query 1: "Show me all products"
Query 2: "Include category names"     ← Adds JOIN
Query 3: "Filter by Electronics"      ← Adds WHERE on joined table
```

---

## Understanding Context

### What Gets Remembered?

For each query in your conversation, the system remembers:

- ✅ The question you asked
- ✅ The SQL that was generated
- ✅ Whether it succeeded or failed
- ✅ How many rows were returned
- ✅ When you asked it

### Context Window

**Default**: Last 3 queries

Why? Most conversations naturally build on the last few exchanges. Remembering too much can confuse the AI.

**What this means:**
- Query 1-3: All remembered
- Query 4: Query 1 is forgotten, Query 2-4 remembered
- Query 5: Query 2 is forgotten, Query 3-5 remembered

### Viewing Your Context

**In the UI:**
- Look for the "💬 Conversation Context" panel
- Shows your recent queries
- Each with SQL, status, and timestamp
- Expand/collapse to save space

**Via API:**
```bash
GET /api/chat/sessions/{session_id}/context
```

---

## When to Start Fresh

### Clear Context

Sometimes you want to start a new topic without the old context interfering.

**When to clear:**
- Switching from products to customers
- Starting a completely different analysis
- Context is confusing the AI
- You want a clean slate

**How to clear:**

**In the UI:**
- Click the trash icon in the Context Panel
- Confirm the dialog
- Context is cleared, next query starts fresh

**Via API:**
```bash
DELETE /api/chat/sessions/{session_id}/context
```

### Create New Session

For major topic changes, create a whole new session:

**When to create new session:**
- Different database
- Different project/analysis
- Want to keep both conversations separate
- Organizing work by topic

---

## Examples by Use Case

### Use Case 1: Product Catalog Analysis

```
Session: "Product Catalog Review"

Query 1: "Show me all products"
→ SQL: SELECT * FROM products
→ Result: 500 products

Query 2: "Filter by electronics"
→ SQL: SELECT * FROM products WHERE category = 'electronics'
→ Result: 120 products

Query 3: "Under $100"
→ SQL: SELECT * FROM products WHERE category = 'electronics' AND price < 100
→ Result: 45 products

Query 4: "Sort by rating descending"
→ SQL: SELECT * FROM products WHERE category = 'electronics' AND price < 100 ORDER BY rating DESC
→ Result: 45 products (sorted)

Query 5: "Top 10 only"
→ SQL: SELECT * FROM products WHERE category = 'electronics' AND price < 100 ORDER BY rating DESC LIMIT 10
→ Result: 10 products
```

### Use Case 2: Customer Segmentation

```
Session: "Customer Analysis Q4 2025"

Query 1: "Show me all customers who ordered this year"
→ SQL: SELECT DISTINCT c.* FROM customers c JOIN orders o ON c.id = o.customer_id WHERE YEAR(o.order_date) = 2025

Query 2: "Group by state"
→ SQL: SELECT c.state, COUNT(*) as customer_count FROM customers c JOIN orders o ON c.id = o.customer_id WHERE YEAR(o.order_date) = 2025 GROUP BY c.state

Query 3: "Show states with more than 50 customers"
→ SQL: SELECT c.state, COUNT(*) as customer_count FROM customers c JOIN orders o ON c.id = o.customer_id WHERE YEAR(o.order_date) = 2025 GROUP BY c.state HAVING COUNT(*) > 50

Query 4: "Sort by count descending"
→ SQL: SELECT c.state, COUNT(*) as customer_count FROM customers c JOIN orders o ON c.id = o.customer_id WHERE YEAR(o.order_date) = 2025 GROUP BY c.state HAVING COUNT(*) > 50 ORDER BY customer_count DESC
```

### Use Case 3: Order Trend Analysis

```
Session: "Order Trends"

Query 1: "Show me orders from last month"
→ SQL: SELECT * FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)

Query 2: "Total revenue"
→ SQL: SELECT SUM(total_amount) as total_revenue FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)

Query 3: "Break down by day"
→ SQL: SELECT DATE(order_date) as order_day, SUM(total_amount) as daily_revenue FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH) GROUP BY DATE(order_date)

Query 4: "Show as chart data"
→ System formats results for visualization
```

---

## Visual Indicators

### Context Panel

**Location**: Below the session selector (collapsible)

**What you see:**
```
💬 Conversation Context (3)
  [Expand/Collapse arrow]  [Refresh] [Clear]

  1. Show me all products
     SELECT * FROM products
     ✓ Success

  2. Filter by electronics
     SELECT * FROM products WHERE category = 'electronics'
     ✓ Success

  3. Sort by price
     SELECT * FROM products WHERE category = 'electronics' ORDER BY price
     ✓ Success

  💡 I'll use this context when you ask follow-up questions
```

### Context Active Badge

When conversational memory is active:

```
💡 Conversational memory active - I'll remember your queries!
```

This blue badge appears at the top of the chat when you have an active session with context.

---

## Tips and Best Practices

### 1. Start with Complete Questions

Always begin with a standalone, complete question:

**Good:**
- ✅ "Show me all products from the electronics category"
- ✅ "Get customers who ordered in 2025"

**Bad:**
- ❌ "Filter by electronics" (first query - no context!)
- ❌ "Sort it" (first query - sort what?)

### 2. Use Natural Language

Speak naturally - the system understands conversational phrases:

**Natural:**
- "Also show the category"
- "Filter that by price under 100"
- "Sort them by date"

**Overly formal:**
- "Apply additional filter on price column"
- "Execute ORDER BY on date field"

### 3. Reference Previous Queries Clearly

Use pronouns and clear references:

**Clear:**
- "Filter those products"
- "Sort by price"
- "Add where clause"

**Unclear:**
- "Do that thing" (what thing?)
- "Apply it" (apply what?)

### 4. Monitor the Context Panel

Keep an eye on what the AI remembers:

- Check the SQL it generated
- Verify success/error status
- Ensure the right queries are in context

### 5. Clear Context When Switching Topics

Don't let old context confuse new queries:

```
Topic 1: Product analysis
  - Query 1-5 about products

[Clear context] ← Important!

Topic 2: Customer analysis
  - Query 6-10 about customers (fresh start)
```

### 6. Use Separate Sessions for Different Projects

Organize your work:

```
Session: "Q4 Sales Analysis"
  - All sales-related queries

Session: "Inventory Review"
  - All inventory queries

Session: "Customer Segmentation"
  - All customer queries
```

---

## Troubleshooting

### Problem: AI doesn't understand my follow-up

**Symptoms:**
- Follow-up query generates wrong SQL
- AI asks for more context
- Results don't match expectation

**Solutions:**
1. Check Context Panel - is the right query in context?
2. Try being more specific: "Filter by electronics category"
3. If stuck, ask a complete standalone question
4. Clear context and start fresh

### Problem: Context panel shows "No conversation history"

**Symptoms:**
- Panel says no history but you asked questions
- Follow-ups don't work

**Solutions:**
1. Verify you selected a chat session (not "Default Mode")
2. Check session_id is being sent (check browser console)
3. Refresh the context panel (click refresh icon)
4. Create a new session if current one is broken

### Problem: Wrong previous queries in context

**Symptoms:**
- Context shows queries from different topic
- Old queries interfering with new ones

**Solutions:**
1. Click the trash icon to clear context
2. Create a new session for the new topic
3. Check you're in the right session

### Problem: System is slow with context

**Symptoms:**
- Queries take longer than expected
- Noticeable lag when asking follow-ups

**Solutions:**
1. Reduce context window size (advanced settings)
2. Clear context regularly
3. Use caching for repeated queries
4. Check database performance

---

## Advanced Features

### Configuring Context Window

**Default**: 3 queries

**To change** (requires backend access):

```python
from src.llm.conversational_memory_agent import get_memory_agent

# Larger window (more context)
agent = get_memory_agent(context_window=5)

# Smaller window (less context, faster)
agent = get_memory_agent(context_window=2)
```

### Error Recovery

The system remembers failed queries too:

```
Query 1: "Show me products"
→ ✓ Success

Query 2: "Filter by invalid_column"
→ ✗ Error: column not found

Query 3: "Filter by category instead"
→ ✓ Success (knows to filter Query 1 results)
```

Failed queries help the AI understand what doesn't work.

### Multi-Database Context

When querying multiple databases in a session:

```
Session: "Production vs Backup Comparison"
Databases: [production, backup]

Query 1: "Show customer counts from both"
→ Queries both databases

Query 2: "Filter by active customers"
→ Filters both database results
```

Context works across multiple databases in the same session!

---

## Keyboard Shortcuts

(If implemented in UI)

- `Ctrl/Cmd + K` - Clear context
- `Ctrl/Cmd + R` - Refresh context
- `Ctrl/Cmd + N` - New session
- `Ctrl/Cmd + Enter` - Submit query

---

## FAQ

### Q: How many queries does it remember?

**A**: Default is 3 queries. This is optimal for most conversations. You can configure this in settings.

### Q: Can I see all my past queries, not just the last 3?

**A**: Yes! Click "History" in the sidebar to see your complete query history for the session.

### Q: Does context work across sessions?

**A**: No. Each session maintains independent context. This keeps conversations organized.

### Q: What happens if I close the browser?

**A**: Your session and context are saved in the database. When you return, select the same session and your context will be there.

### Q: Can I turn off conversational memory?

**A**: Yes. Don't provide a `session_id` in your queries, or use "Default Mode" in the UI. Queries will be processed without context.

### Q: Does this work with all database types?

**A**: Yes! Conversational memory works with PostgreSQL, MySQL, SQLite, MongoDB, and DuckDB.

### Q: Is my conversation data private?

**A**: Yes. All context is stored in your local database. No external services are used.

---

## What's Next?

Now that you understand Conversational Memory:

1. **Try it out** - Create a session and have a multi-turn conversation
2. **Experiment** - See how natural you can make your follow-ups
3. **Organize** - Create sessions for different projects
4. **Share feedback** - Let us know how it works for you!

---

## Related Resources

- [API Documentation](CONVERSATIONAL_MEMORY_API.md) - Technical API reference
- [Implementation Guide](../CONVERSATIONAL_MEMORY_IMPLEMENTATION.md) - How it works under the hood
- [Testing Guide](../TEST_CONVERSATIONAL_MEMORY.md) - Test scenarios and validation

---

**Happy querying!** 🎉

*Database Guru Team*
*November 1, 2025*
