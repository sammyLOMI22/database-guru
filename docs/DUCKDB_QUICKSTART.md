# DuckDB Quick Start Guide

## 5-Minute Setup

### 1. Install DuckDB Support

The dependencies are already in `requirements.txt`. Just install them:

```bash
source venv/bin/activate
pip install duckdb==1.1.3 duckdb-engine==0.13.2
```

### 2. Create Sample Database

Run the provided script to create a sample DuckDB database:

```bash
python scripts/create_sample_duckdb.py
```

Output:
```
Creating DuckDB database: /Users/sam/database-guru/sample_ecommerce.duckdb
Creating tables...
Inserting sample data...

Database created successfully!

Table summary:
  categories: 4 rows
  products: 20 rows
  customers: 15 rows
  orders: 10 rows
  order_items: 15 rows
  reviews: 10 rows
```

### 3. Start Database Guru

```bash
./start.sh
```

This starts:
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:3000

### 4. Connect to DuckDB

1. Open http://localhost:3000
2. Click **"Connections"** in the sidebar
3. Click **"+ Add Connection"**
4. Select **"DuckDB"**
5. Fill in:
   - **Connection Name**: "Sample E-commerce"
   - **Database File Path**: `/Users/sam/database-guru/sample_ecommerce.duckdb`
6. Click **"Test Connection"** → Should see: ✅ "Successfully connected to DuckDB: v1.1.3"
7. Click **"Save Connection"**
8. Click the connection to activate it

### 5. Start Querying!

Now you can ask questions in natural language:

**Try these queries:**

1. "Show me all products"
2. "What are the top 5 most expensive products?"
3. "Which customers have placed more than 1 order?"
4. "What's the total revenue from all orders?"
5. "Show me products with ratings above 4 stars"
6. "List all orders from customers in California"
7. "What's the average order value?"
8. "Which product category has the most products?"

### 6. Verify It's Working

You should see:
- Generated SQL query
- Query results in a table
- Execution time
- Row count

## Troubleshooting

### Issue: "DuckDB support not installed"

**Fix:**
```bash
source venv/bin/activate
pip install duckdb duckdb-engine
```

### Issue: "Cannot open file"

**Fix:**
- Use the full absolute path to your .duckdb file
- Example: `/Users/sam/database-guru/sample_ecommerce.duckdb`
- Don't use relative paths like `./sample_ecommerce.duckdb`

### Issue: Connection test fails

**Fix:**
1. Verify the file exists: `ls -lh sample_ecommerce.duckdb`
2. Check file permissions: `chmod 644 sample_ecommerce.duckdb`
3. Make sure you're using the full path

## Advanced Usage

### In-Memory Database

For temporary data:
1. Connection Name: "Temp Analysis"
2. Database File Path: `:memory:`

### Query CSV Files

DuckDB can query CSV files directly:

```sql
SELECT * FROM 'data.csv' LIMIT 10;
```

### Query Parquet Files

```sql
SELECT * FROM 'data.parquet' WHERE date > '2024-01-01';
```

### Create Tables from Files

```sql
CREATE TABLE products AS SELECT * FROM 'products.csv';
```

## Example Workflows

### Data Analysis

1. Load CSV into DuckDB
2. Ask natural language questions
3. Export results

### ETL Pipeline

1. Import data from multiple sources
2. Transform with SQL queries
3. Analyze with natural language queries

### Development Testing

1. Use in-memory database
2. Load test data
3. Test queries quickly

## Performance Tips

1. **Create indexes** on frequently queried columns
2. **Use Parquet** instead of CSV for large datasets
3. **Batch operations** are faster than row-by-row
4. DuckDB **automatically optimizes** most queries

## Next Steps

- Read the full documentation: [docs/DUCKDB_SUPPORT.md](docs/DUCKDB_SUPPORT.md)
- Try the test suite: `python tests/test_duckdb_connection.py`
- Explore DuckDB features: https://duckdb.org/docs/

## Summary

✅ **DuckDB is now fully integrated!**

You can:
- Connect to DuckDB databases
- Query using natural language
- View results in the UI
- Leverage DuckDB's fast analytics
- Use all Database Guru features

**Enjoy the power of DuckDB with the simplicity of natural language queries!** 🦆
