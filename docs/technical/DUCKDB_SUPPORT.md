# DuckDB Support in Database Guru

## Overview

Database Guru now supports DuckDB, an in-process SQL OLAP database management system. DuckDB is designed for analytical query workloads and provides excellent performance for data analysis tasks.

## Features

- Full DuckDB integration with Database Guru
- Support for file-based and in-memory databases
- Schema introspection
- Natural language to SQL query generation
- Query execution with results visualization

## Getting Started

### 1. Install Dependencies

The required dependencies are already included in `requirements.txt`:

```bash
pip install duckdb==1.1.3 duckdb-engine==0.13.2
```

### 2. Create a DuckDB Database

You can create a sample DuckDB database using the provided script:

```bash
python scripts/create_sample_duckdb.py
```

This creates a `sample_ecommerce.duckdb` file with:
- 6 tables (categories, products, customers, orders, order_items, reviews)
- Sample e-commerce data for testing

### 3. Connect to DuckDB in Database Guru

1. Start Database Guru
2. Go to the **Connections** tab
3. Click **+ Add Connection**
4. Select **DuckDB** as the database type
5. Enter connection details:
   - **Connection Name**: Give it a meaningful name (e.g., "My DuckDB")
   - **Database File Path**: Full path to your .duckdb file
     - Example: `/Users/sam/database-guru/sample_ecommerce.duckdb`
     - Or use `:memory:` for an in-memory database
6. Click **Test Connection** to verify
7. Click **Save Connection**
8. Activate the connection
9. Start querying!

## Example Queries

Once connected, you can ask questions like:

- "Show me all products with price greater than $50"
- "What are the top 5 customers by total order value?"
- "List all orders placed in the last month"
- "Which products have the highest average rating?"
- "Show me total revenue by product category"

## Technical Details

### Connection URL Format

DuckDB connections use the following URL format:

```
duckdb:///path/to/database.duckdb
```

For in-memory databases:

```
duckdb:///:memory:
```

### Synchronous Operations

Unlike PostgreSQL and MySQL, DuckDB doesn't have an async driver. Database Guru handles this automatically by:

1. Using synchronous SQLAlchemy sessions for DuckDB
2. Executing queries in a thread pool to avoid blocking the async event loop
3. Providing the same API as other databases

This means you get the same experience regardless of the database type!

### Schema Introspection

DuckDB's `information_schema` is fully supported for schema introspection. Database Guru can automatically:

- Discover all tables
- List columns with data types
- Identify primary keys
- Detect foreign key relationships
- Show indexes

## Use Cases

DuckDB is particularly well-suited for:

1. **Data Analysis**: Fast analytical queries on large datasets
2. **ETL Pipelines**: Transform and analyze data before loading to production
3. **Development/Testing**: Lightweight alternative to full database servers
4. **Data Science**: Analyze CSV, Parquet, and other file formats
5. **Embedded Analytics**: In-process database for applications

## Limitations

- **No Server**: DuckDB is an embedded database (no client-server architecture)
- **No Authentication**: File-based security only
- **Single Writer**: Only one process can write at a time
- **Sync Operations**: Uses synchronous SQLAlchemy (but Database Guru handles this transparently)

## Performance Tips

1. **Use Parquet**: DuckDB excels at reading Parquet files
2. **Create Indexes**: Add indexes on frequently queried columns
3. **Batch Operations**: DuckDB is optimized for bulk operations
4. **Memory Settings**: DuckDB automatically manages memory efficiently

## File Formats

DuckDB can directly query various file formats:

```sql
-- Query CSV files
SELECT * FROM 'data.csv';

-- Query Parquet files
SELECT * FROM 'data.parquet';

-- Query JSON files
SELECT * FROM 'data.json';
```

You can ask Database Guru to generate queries that work with these formats!

## Migration from SQLite

If you're currently using SQLite, DuckDB offers:

- Much faster analytical queries
- Better support for complex aggregations
- Built-in support for window functions
- Native Parquet support
- Better handling of large datasets

To migrate:

1. Export SQLite data to CSV or Parquet
2. Create a DuckDB database
3. Import data using DuckDB's fast bulk loading
4. Update connection in Database Guru

## Troubleshooting

### Connection Issues

**Error**: "DuckDB support not installed"

**Solution**:
```bash
source venv/bin/activate
pip install duckdb duckdb-engine
```

### File Path Issues

**Error**: "IO Error: Cannot open file"

**Solution**:
- Use absolute paths, not relative paths
- Ensure the file exists
- Check file permissions
- On Windows, use forward slashes: `C:/path/to/database.duckdb`

### Query Performance

If queries are slow:

1. Check if indexes exist on filtered columns
2. Consider using DuckDB's query profiling: `EXPLAIN ANALYZE`
3. Ensure your hardware has sufficient RAM
4. Break complex queries into smaller steps

## Resources

- [DuckDB Official Documentation](https://duckdb.org/docs/)
- [DuckDB Python API](https://duckdb.org/docs/api/python/overview)
- [SQLAlchemy DuckDB Engine](https://github.com/Mause/duckdb_engine)

## Testing

Run the DuckDB connection test:

```bash
python tests/test_duckdb_connection.py
```

This verifies:
- Connection establishment
- URL building
- Query execution
- Schema discovery

## Support

If you encounter issues with DuckDB support:

1. Check that dependencies are installed
2. Verify the database file path is correct
3. Review the logs in `backend.log`
4. Run the test script to isolate the issue
5. Report issues on GitHub with error details

---

**Happy querying with DuckDB!** 🦆
