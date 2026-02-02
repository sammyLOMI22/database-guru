# File Data Source User Guide

This guide covers how to use CSV and Excel files as queryable data sources in Database Guru.

## Overview

Database Guru allows you to upload CSV and Excel files and query them using SQL alongside your traditional database connections. Files are processed using DuckDB's high-performance columnar engine, providing fast query execution without requiring data import into external databases.

## Supported File Types

| Format | Extension | Description |
|--------|-----------|-------------|
| **CSV** | `.csv` | Comma-separated values with auto-detected delimiters |
| **Excel (Modern)** | `.xlsx` | Excel 2007+ format with sheet selection |
| **Excel (Legacy)** | `.xls` | Excel 97-2003 format |

**Limits:**
- Maximum file size: 100 MB
- Maximum rows: Limited by available memory (1GB default)

## Getting Started

### Uploading a File via UI

1. **Open the Upload Modal**
   - Click the **"+ Upload File"** button in the sidebar
   - Or drag-and-drop a file onto the interface

2. **Select Your File**
   - Click to browse or drag-and-drop
   - Supported formats: CSV, XLSX, XLS

3. **Configure Options** (Optional)
   - **Display Name**: Give your file a friendly name (defaults to filename)
   - **Sheet Selection** (Excel only): Choose which sheet to import
   - **Scope**: Session-specific or Global (shared)

4. **Upload and Process**
   - Click **"Upload"** to start processing
   - Schema is automatically inferred
   - View progress indicator

5. **View Results**
   - See the generated DuckDB table name
   - View row count and column types
   - Access schema and data preview

### Uploading via API

```bash
# Upload a CSV file
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@sales_data.csv" \
  -F "name=Sales Data Q4" \
  -F "is_global=false" \
  -F "session_id=your-session-id"

# Upload an Excel file with specific sheet
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@workbook.xlsx" \
  -F "name=Revenue Report" \
  -F "sheet_name=Sheet2"
```

## Schema Preview

After upload, view the inferred schema:

### Schema Tab
- **Column Name**: The detected column name
- **Type**: Inferred data type (INTEGER, DOUBLE, VARCHAR, DATE, etc.)
- **Nullable**: Whether the column allows NULL values
- **Sample Values**: Up to 5 sample values from the data

### Preview Tab
- View the first 20 rows of data (configurable up to 100)
- See actual data values in table format
- Truncation indicator if data exceeds limit

### Type Detection

DuckDB automatically detects these types:

| DuckDB Type | Normalized Type | Example Values |
|-------------|-----------------|----------------|
| `BIGINT`, `INTEGER`, `SMALLINT` | INTEGER | `1`, `42`, `1000` |
| `DOUBLE`, `FLOAT`, `DECIMAL` | DOUBLE | `3.14`, `99.99` |
| `VARCHAR`, `TEXT` | VARCHAR | `"hello"`, `"world"` |
| `BOOLEAN` | BOOLEAN | `true`, `false` |
| `DATE` | DATE | `2024-01-15` |
| `TIMESTAMP` | TIMESTAMP | `2024-01-15 10:30:00` |

## Querying Files

### Finding Your Table Name

Each uploaded file gets a unique DuckDB table name:
- Format: `file_{id}_{sanitized_name}`
- Example: `file_1_sales_data`, `file_3_revenue_2024`

View the table name in:
- Upload success message
- File details panel
- Schema preview

### Natural Language Queries

Ask questions naturally, referencing your file:

```
"Show me total revenue by product from sales_data"
"What are the top 5 customers in the uploaded file?"
"Count records where status is 'active' in my CSV"
```

### Direct SQL Queries

Use the table name directly:

```sql
-- Basic query
SELECT * FROM file_1_sales_data LIMIT 10;

-- Aggregation
SELECT product_id, SUM(revenue) as total
FROM file_1_sales_data
GROUP BY product_id
ORDER BY total DESC;

-- Filtering
SELECT * FROM file_1_sales_data
WHERE sale_date >= '2024-01-01'
AND status = 'completed';
```

### Joining with Database Tables

Combine file data with connected databases:

```sql
-- Join file with database table
SELECT f.product_name, f.revenue, p.category
FROM file_1_sales_data f
JOIN products p ON f.product_id = p.id;
```

## File Scoping

### Session-Scoped Files (Default)
- **Visibility**: Only in current chat session
- **Cleanup**: Deleted when session ends
- **Use Case**: Temporary analysis, ad-hoc queries

### Global Files
- **Visibility**: Available to all sessions
- **Cleanup**: Manual deletion or auto-cleanup after 30 days
- **Use Case**: Reference data, shared datasets

Set scope during upload:
```bash
# Session-scoped (default)
-F "is_global=false"

# Global
-F "is_global=true"
```

## Managing Files

### List Files
```bash
# All files for session
curl "http://localhost:8000/api/files/?session_id=your-session-id"

# Include global files
curl "http://localhost:8000/api/files/?session_id=your-session-id&include_global=true"

# All global files only
curl "http://localhost:8000/api/files/?is_global=true"
```

### Get File Details
```bash
curl http://localhost:8000/api/files/1
```

### Refresh Schema
If your file changes, refresh the schema:
```bash
curl -X POST http://localhost:8000/api/files/1/refresh
```

### Delete File
```bash
curl -X DELETE http://localhost:8000/api/files/1
```

## Excel-Specific Features

### Inspecting Sheets Before Upload

For Excel files with multiple sheets:

```bash
curl -X POST http://localhost:8000/api/files/excel-sheets \
  -F "file=@workbook.xlsx"
```

Response:
```json
{
  "filename": "workbook.xlsx",
  "sheets": ["Sheet1", "Sales Data", "Summary"]
}
```

### Selecting a Sheet

Specify the sheet during upload:
```bash
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@workbook.xlsx" \
  -F "sheet_name=Sales Data"
```

If no sheet is specified, the first sheet is used.

## Best Practices

### File Preparation

1. **Clean Headers**: Use clear, unique column names
2. **Consistent Types**: Keep data types consistent in each column
3. **No Empty Rows**: Remove empty rows at the top
4. **UTF-8 Encoding**: Use UTF-8 for CSV files

### Performance Tips

1. **Filter Early**: Add WHERE clauses to reduce data scanned
2. **Limit Rows**: Use LIMIT for exploratory queries
3. **Index Columns**: For frequently filtered columns, consider database import

### Security Considerations

1. **No Sensitive Data**: Don't upload files with passwords or PII
2. **Session Scope**: Use session-scoped files for temporary data
3. **Auto-Cleanup**: Files are automatically deleted after 30 days (configurable)

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "File too large" | File exceeds 100MB limit. Split or compress |
| "Unsupported format" | Only .csv, .xlsx, .xls are supported |
| "Schema inference failed" | Check file format, ensure valid data |
| "Table not found" | File may have been cleaned up. Re-upload |

### Content Validation Errors

Files are validated for:
- Valid file extension
- Correct magic bytes (file content matches extension)
- Non-empty content
- Reasonable file size

### Memory Issues

If queries fail with memory errors:
1. Reduce query scope with WHERE/LIMIT
2. Query specific columns instead of SELECT *
3. Check `DUCKDB_FILE_MEMORY_LIMIT` setting

## Configuration

### Environment Variables

```bash
# File storage
FILE_UPLOAD_DIR=uploads/          # Where files are stored
FILE_MAX_SIZE_MB=100              # Maximum file size in MB
FILE_ALLOWED_TYPES=.csv,.xlsx,.xls  # Allowed extensions

# Cleanup
FILE_AUTO_CLEANUP_DAYS=30         # Auto-delete after N days
FILE_SESSION_CLEANUP_ON_DELETE=true  # Delete session files on session end

# DuckDB performance
DUCKDB_FILE_MEMORY_LIMIT=1GB      # Max memory for file queries
DUCKDB_FILE_THREADS=4             # Processing threads
```

## API Reference

### Upload File
```
POST /api/files/upload
Content-Type: multipart/form-data

Parameters:
- file (required): The file to upload
- name (optional): Display name
- sheet_name (optional): Excel sheet to import
- session_id (optional): Chat session ID
- is_global (optional): true/false for global scope
```

### List Files
```
GET /api/files/

Query Parameters:
- session_id: Filter by session
- is_global: Filter by global flag
- include_global: Include global files with session files
- status: Filter by processing status
```

### Get File
```
GET /api/files/{file_id}
```

### Get Schema
```
GET /api/files/{file_id}/schema
```

### Get Preview
```
GET /api/files/{file_id}/preview?limit=20
```

### Refresh Schema
```
POST /api/files/{file_id}/refresh
```

### Delete File
```
DELETE /api/files/{file_id}
```

### Get Excel Sheets
```
POST /api/files/excel-sheets
Content-Type: multipart/form-data

Parameters:
- file (required): Excel file to inspect
```

## Related Documentation

- [Multi-Database Guide](MULTI_DATABASE_GUIDE.md) - Using files with multiple databases
- [File Data Source Testing Guide](testing/FILE_DATA_SOURCE_TESTING.md) - Testing the feature
- [DuckDB Quick Start](DUCKDB_QUICKSTART.md) - DuckDB basics
