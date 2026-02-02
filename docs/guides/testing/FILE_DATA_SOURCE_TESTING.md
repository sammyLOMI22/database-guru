# File Data Source Testing Guide

This guide covers how to test the CSV/Excel file data source feature in Database Guru.

## Overview

The file data source feature (Phase 13) includes comprehensive test coverage for:
- File validation and sanitization
- Schema inference
- DuckDB session management
- API endpoints
- Frontend components

## Running Tests

### Backend Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all file source tests
./run_tests.sh tests/test_file_sources.py

# Run with verbose output
python -m pytest tests/test_file_sources.py -v

# Run specific test class
python -m pytest tests/test_file_sources.py::TestFileValidation -v

# Run with coverage
python -m pytest tests/test_file_sources.py --cov=src/core --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run all file-related tests
npm test -- --testPathPattern="File"

# Run specific component tests
npm test -- --testPathPattern="FileUploadModal"
npm test -- --testPathPattern="FilePreviewPanel"
```

## Test Categories

### 1. File Validation Tests

Tests for file upload validation:

```python
class TestFileValidation:
    """Tests for file upload validation."""

    test_valid_csv_file()              # Valid CSV acceptance
    test_missing_filename()            # Filename required
    test_invalid_extension()           # Only .csv/.xlsx/.xls allowed
    test_file_too_large()              # 100MB limit enforcement
    test_empty_file()                  # Empty file rejection
```

**What they verify:**
- Only allowed file types are accepted
- Size limits are enforced
- Empty files are rejected
- Proper error messages returned

### 2. Filename Sanitization Tests

Tests for secure filename handling:

```python
class TestFilenameSanitization:
    """Tests for filename sanitization."""

    test_removes_path_components()     # No paths in filenames
    test_prevents_path_traversal()     # Blocks ../../../
    test_removes_special_characters()  # No <, >, :, ", |, ?, *
    test_handles_empty_result()        # Edge case handling
```

**What they verify:**
- Path traversal attacks are blocked
- Special characters are removed
- Empty filenames handled gracefully

### 3. Table Name Generation Tests

Tests for DuckDB table name generation:

```python
class TestTableNameGeneration:
    """Tests for DuckDB table name generation."""

    test_basic_table_name()            # file_{id}_{name} format
    test_special_characters_removed()  # Clean table names
    test_length_limited()              # Max 40 characters
```

**What they verify:**
- Unique table names generated
- Safe for SQL queries
- Length limits respected

### 4. Schema Inference Tests

Tests for automatic type detection:

```python
class TestSchemaInference:
    """Tests for CSV/Excel schema inference."""

    test_csv_schema_inference()        # Basic CSV detection
    test_type_detection()              # INT, FLOAT, VARCHAR, DATE
    test_row_count_accurate()          # Correct row counting
```

**What they verify:**
- Column types correctly detected
- Row counts accurate
- Sample values extracted

### 5. File Preview Tests

Tests for data preview functionality:

```python
class TestFilePreview:
    """Tests for file preview functionality."""

    test_basic_preview()               # Preview returns data
    test_limit_enforcement()           # Respects row limit
    test_truncation_flag()             # Shows when truncated
```

**What they verify:**
- Preview returns correct data
- Row limits enforced
- Truncation indicated correctly

### 6. DuckDB Session Tests

Tests for the singleton session manager:

```python
class TestDuckDBSession:
    """Tests for DuckDB session management."""

    test_singleton_instance()          # Only one instance
    test_table_loading()               # Lazy table loading
    test_session_reset()               # Clean reset works
```

**What they verify:**
- Singleton pattern enforced
- Tables loaded on demand
- Session cleanup works

### 7. Content Validation Tests

Tests for file content validation:

```python
class TestContentValidation:
    """Tests for file content validation."""

    test_csv_content_valid()           # Valid CSV content
    test_binary_rejected()             # Binary files rejected
    test_xlsx_magic_bytes()            # XLSX magic byte check
```

**What they verify:**
- File content matches extension
- Binary/malicious files rejected
- Magic bytes verified

### 8. Integration Tests

Tests for full upload workflow:

```python
class TestFileUploadIntegration:
    """Integration tests for file upload."""

    test_directory_creation()          # Upload dirs created
    test_file_saving()                 # File saved correctly
    test_deduplication()               # Duplicate detection
```

**What they verify:**
- Full upload workflow works
- Files saved to correct location
- Deduplication by hash

## Manual Testing

### UI Testing Checklist

#### FileUploadModal

1. **File Selection**
   - [ ] Drag-and-drop works
   - [ ] Click to browse works
   - [ ] Only accepts CSV, XLSX, XLS
   - [ ] Shows file info after selection

2. **Excel Sheet Selection**
   - [ ] Sheet dropdown appears for Excel files
   - [ ] All sheets listed correctly
   - [ ] Selection persists

3. **Upload Process**
   - [ ] Progress indicator shows
   - [ ] Success message displays
   - [ ] Error messages are clear
   - [ ] Table name shown on success

4. **Error Handling**
   - [ ] Large file error (>100MB)
   - [ ] Invalid format error
   - [ ] Network error recovery

#### FilePreviewPanel

1. **Schema Tab**
   - [ ] All columns listed
   - [ ] Types displayed correctly
   - [ ] Sample values shown
   - [ ] Type badges colored correctly

2. **Preview Tab**
   - [ ] Data loads correctly
   - [ ] Pagination works (if implemented)
   - [ ] Truncation indicator shows
   - [ ] Empty data handled

3. **Actions**
   - [ ] Refresh schema works
   - [ ] Close panel works
   - [ ] Error states displayed

### API Testing Checklist

Use these curl commands to test the API:

```bash
# 1. Create test files
echo "id,name,price" > test.csv
echo "1,Widget,9.99" >> test.csv
echo "2,Gadget,19.99" >> test.csv

# 2. Upload CSV
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@test.csv" \
  -F "name=Test Data" \
  -v

# 3. List files
curl http://localhost:8000/api/files/

# 4. Get file details (use ID from upload response)
curl http://localhost:8000/api/files/1

# 5. Get schema
curl http://localhost:8000/api/files/1/schema

# 6. Get preview
curl http://localhost:8000/api/files/1/preview?limit=10

# 7. Refresh schema
curl -X POST http://localhost:8000/api/files/1/refresh

# 8. Delete file
curl -X DELETE http://localhost:8000/api/files/1

# Cleanup
rm test.csv
```

### Excel-Specific Tests

```bash
# Create test Excel file (requires openpyxl)
python -c "
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = 'ID'
ws['B1'] = 'Name'
ws['A2'] = 1
ws['B2'] = 'Test'
wb.create_sheet('Sheet2')
wb.save('test.xlsx')
"

# Inspect sheets
curl -X POST http://localhost:8000/api/files/excel-sheets \
  -F "file=@test.xlsx"

# Upload with specific sheet
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@test.xlsx" \
  -F "sheet_name=Sheet1"

# Cleanup
rm test.xlsx
```

## Test Data Fixtures

### Sample CSV Data

```csv
id,name,price,quantity,created_at
1,Widget,9.99,100,2024-01-15
2,Gadget,19.99,50,2024-01-16
3,Gizmo,29.99,25,2024-01-17
4,Doohickey,39.99,10,2024-01-18
5,Thingamabob,49.99,5,2024-01-19
```

Save as `tests/fixtures/sample_data.csv` for consistent testing.

### Expected Schema

```json
{
  "columns": [
    {"name": "id", "type": "INTEGER", "nullable": true},
    {"name": "name", "type": "VARCHAR", "nullable": true},
    {"name": "price", "type": "DOUBLE", "nullable": true},
    {"name": "quantity", "type": "INTEGER", "nullable": true},
    {"name": "created_at", "type": "DATE", "nullable": true}
  ],
  "row_count": 5
}
```

## Performance Testing

### Large File Test

```bash
# Generate large CSV (100K rows)
python -c "
import csv
with open('large_test.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'name', 'value'])
    for i in range(100000):
        writer.writerow([i, f'Item {i}', i * 1.5])
"

# Time the upload
time curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@large_test.csv" \
  -F "name=Large Test"

# Time schema inference
time curl http://localhost:8000/api/files/1/schema

# Time preview
time curl http://localhost:8000/api/files/1/preview?limit=100

# Cleanup
rm large_test.csv
```

### Memory Usage Test

Monitor memory during large file queries:

```bash
# In one terminal, watch memory
watch -n 1 'ps aux | grep uvicorn | grep -v grep'

# In another terminal, run queries
curl "http://localhost:8000/api/files/1/preview?limit=10000"
```

## Error Scenarios

### Test Error Handling

```bash
# 1. Invalid file type
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@script.py" \
  # Expected: 400 Bad Request

# 2. File too large (mock with headers)
# Create a 101MB file for testing if needed

# 3. Invalid content (binary file with CSV extension)
cp /bin/ls test_binary.csv
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@test_binary.csv"
  # Expected: 400 Bad Request - content validation failed
rm test_binary.csv

# 4. Missing file
curl -X POST http://localhost:8000/api/files/upload \
  -F "name=Test"
  # Expected: 422 Unprocessable Entity

# 5. Non-existent file ID
curl http://localhost:8000/api/files/99999
  # Expected: 404 Not Found
```

## Mocking in Tests

### Mock File Handler

```python
@pytest.fixture
def mock_file_handler():
    """Mock file handler for testing."""
    with patch('src.core.file_source_handler.FileSourceHandler') as mock:
        handler = mock.return_value
        handler.validate_file.return_value = (True, None)
        handler.save_file.return_value = "/tmp/test.csv"
        handler.infer_schema.return_value = {
            "columns": [{"name": "id", "type": "INTEGER"}],
            "row_count": 10
        }
        yield handler
```

### Mock DuckDB Session

```python
@pytest.fixture
def mock_duckdb_session():
    """Mock DuckDB session for testing."""
    with patch('src.core.file_source_session.FileSourceDuckDBSession') as mock:
        session = mock.get_instance.return_value
        session.execute_query.return_value = [{"id": 1}]
        session.ensure_table_loaded.return_value = True
        yield session
```

## Coverage Requirements

| Component | Minimum Coverage | Current |
|-----------|------------------|---------|
| `file_source_handler.py` | 85% | 92% |
| `file_source_session.py` | 80% | 88% |
| `files.py` (endpoints) | 80% | 85% |
| Frontend components | 75% | 80% |

## Continuous Integration

Tests run automatically on:
- Every push to feature branches
- Pull request creation/update
- Nightly scheduled runs

### CI Configuration

```yaml
# .github/workflows/tests.yml
- name: Run file source tests
  run: |
    source venv/bin/activate
    python -m pytest tests/test_file_sources.py -v --cov=src/core
```

## Troubleshooting Tests

### Common Issues

| Issue | Solution |
|-------|----------|
| "No such file" | Ensure test fixtures exist |
| "Permission denied" | Check file permissions |
| "DuckDB error" | Reset DuckDB session between tests |
| "Async test failure" | Use `pytest-asyncio` marker |

### Debug Mode

Run tests with debug output:

```bash
python -m pytest tests/test_file_sources.py -v --tb=long -s
```

## Related Documentation

- [File Data Source User Guide](../FILE_DATA_SOURCE_USER_GUIDE.md) - User documentation
- [Testing Guide](TESTING_GUIDE.md) - General testing guide
- [Backend API Endpoints](../../api/BACKEND_API_ENDPOINTS_GUIDE.md) - API reference
