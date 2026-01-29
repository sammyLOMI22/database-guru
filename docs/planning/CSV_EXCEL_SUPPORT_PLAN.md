# CSV & Excel File Support Plan

**Created**: January 28, 2026
**Status**: PLANNING
**Priority**: HIGH
**Estimated Effort**: 3-4 weeks

---

## Executive Summary

Enable users to upload CSV and Excel files as data sources alongside traditional database connections. Users can combine multiple spreadsheets with existing database connections and ask natural language questions across all data sources.

---

## User Stories

### Primary Use Cases

1. **Single File Query**: "Upload sales.csv and show me total revenue by region"
2. **Multi-File Analysis**: "Compare data from customers.xlsx and orders.csv - which customers haven't ordered in 6 months?"
3. **File + Database Join**: "Join my uploaded prospects.csv with the existing customers database to find prospects not yet in our CRM"
4. **Cross-Source Aggregation**: "Combine revenue from all sources (PostgreSQL production DB + uploaded quarterly_reports.xlsx) and show YoY growth"

### User Flow

```
User clicks "Add Data Source" → Chooses "Upload File" → Selects CSV/Excel
    ↓
System validates file, extracts schema, creates virtual table
    ↓
File appears in Connections Panel alongside database connections
    ↓
User can select multiple sources (files + databases) for a chat session
    ↓
User asks natural language questions → LLM generates SQL across all sources
```

---

## Technical Architecture

### Overview

```
                              ┌─────────────────────────────────────────┐
                              │            FRONTEND                      │
                              │  ┌─────────────────────────────────────┐│
                              │  │   FileUploadModal.tsx               ││
                              │  │   • Drag & drop upload              ││
                              │  │   • File type validation            ││
                              │  │   • Upload progress                 ││
                              │  └─────────────────────────────────────┘│
                              │  ┌─────────────────────────────────────┐│
                              │  │   DataSourcesPanel.tsx (enhanced)   ││
                              │  │   • Database connections            ││
                              │  │   • Uploaded files                  ││
                              │  │   • Unified data source list        ││
                              │  └─────────────────────────────────────┘│
                              └────────────────────┬────────────────────┘
                                                   │ REST API
                              ┌────────────────────▼────────────────────┐
                              │            BACKEND                       │
                              │  ┌─────────────────────────────────────┐│
                              │  │   /api/files/ endpoints             ││
                              │  │   • POST /upload                    ││
                              │  │   • GET /                           ││
                              │  │   • DELETE /{id}                    ││
                              │  │   • GET /{id}/schema                ││
                              │  │   • GET /{id}/preview               ││
                              │  └─────────────────────────────────────┘│
                              │  ┌─────────────────────────────────────┐│
                              │  │   FileSourceHandler                 ││
                              │  │   • CSV/Excel parsing               ││
                              │  │   • Schema inference                ││
                              │  │   • DuckDB virtual table creation   ││
                              │  └─────────────────────────────────────┘│
                              │  ┌─────────────────────────────────────┐│
                              │  │   MultiDatabaseHandler (enhanced)   ││
                              │  │   • Database connections            ││
                              │  │   • File-based data sources         ││
                              │  │   • Cross-source query execution    ││
                              │  └─────────────────────────────────────┘│
                              └────────────────────┬────────────────────┘
                                                   │
                              ┌────────────────────▼────────────────────┐
                              │            STORAGE                       │
                              │  ┌───────────┐  ┌───────────────────────┐│
                              │  │ uploads/  │  │ DuckDB (in-memory or  ││
                              │  │ directory │  │ persistent per-file)  ││
                              │  └───────────┘  └───────────────────────┘│
                              └─────────────────────────────────────────┘
```

### Why DuckDB for File Queries?

DuckDB is already integrated into Database Guru and provides:
- **Native CSV/Parquet support** via `read_csv_auto()` and `read_parquet()`
- **Excel support** via DuckDB's `excel` extension
- **In-memory performance** for fast queries on uploaded files
- **SQL compatibility** with existing LLM-generated queries
- **JOIN capability** across DuckDB tables (representing files)

### Data Flow for File Queries

```
1. FILE UPLOAD
   User uploads sales.csv
       ↓
   Backend saves to uploads/{session_id}/sales.csv
       ↓
   FileSourceHandler creates DuckDB virtual table:
       CREATE TABLE sales AS SELECT * FROM read_csv_auto('uploads/.../sales.csv')
       ↓
   Schema extracted and stored in FileSource model
       ↓
   File appears as data source in UI

2. QUERY EXECUTION
   User asks: "Show top 10 sales from my uploaded file and production DB"
       ↓
   MultiDatabaseHandler builds combined schema:
       - Database: production (PostgreSQL)
       - File: sales.csv (DuckDB virtual table)
       ↓
   LLM generates SQL with source prefixes:
       -- For PostgreSQL
       DATABASE: production
       SELECT customer_id, amount FROM orders WHERE amount > 1000;

       -- For uploaded file
       DATABASE: sales_csv
       SELECT customer, total FROM sales WHERE total > 1000;
       ↓
   Results merged and returned to user
```

---

## Database Models

### New: FileSource Model

```python
# src/database/models.py

class FileSource(Base):
    """Store uploaded file data sources"""
    __tablename__ = "file_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Display name (e.g., "Q4 Sales Report")

    # File metadata
    original_filename = Column(String(255), nullable=False)  # Original upload name
    file_type = Column(String(20), nullable=False)  # 'csv', 'xlsx', 'xls'
    file_size_bytes = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)  # Path in uploads directory
    file_hash = Column(String(64), nullable=True)  # SHA-256 for deduplication

    # For Excel files with multiple sheets
    sheet_name = Column(String(255), nullable=True)  # Sheet name if Excel

    # Schema information (extracted from file)
    schema_cache = Column(JSON, nullable=True)  # {columns: [{name, type, nullable}], row_count, sample_values}
    schema_updated_at = Column(DateTime, nullable=True)

    # DuckDB integration
    duckdb_table_name = Column(String(255), nullable=False)  # Virtual table name in DuckDB

    # Ownership and access
    user_id = Column(String(255), index=True, nullable=True)  # File owner
    chat_session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=True)  # Scoped to session
    is_global = Column(Boolean, default=False)  # If true, available across all sessions

    # Status
    is_active = Column(Boolean, default=True)
    processing_status = Column(String(20), default='pending')  # pending, processing, ready, error
    processing_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Auto-cleanup for temporary files

    # Indexes
    __table_args__ = (
        Index('idx_file_user_session', 'user_id', 'chat_session_id'),
        Index('idx_file_hash', 'file_hash'),
    )
```

### Enhanced: ChatSession Model

```python
# Add to ChatSession model

class ChatSession(Base):
    # ... existing fields ...

    # Enhanced to support both database connections and file sources
    active_connection_ids = Column(JSON, nullable=False, default=list)  # [1, 2, 3]
    active_file_source_ids = Column(JSON, nullable=False, default=list)  # [1, 2]  # NEW
```

---

## API Endpoints

### File Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/` | GET | List all file sources for user/session |
| `/api/files/upload` | POST | Upload CSV/Excel file (multipart/form-data) |
| `/api/files/{id}` | GET | Get file source details |
| `/api/files/{id}` | DELETE | Delete file source and cleanup |
| `/api/files/{id}/schema` | GET | Get extracted schema |
| `/api/files/{id}/preview` | GET | Get first N rows as preview |
| `/api/files/{id}/refresh` | POST | Re-parse file and update schema |

### Upload Endpoint Details

```python
# src/api/endpoints/files.py

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),  # Display name (defaults to filename)
    sheet_name: Optional[str] = Form(None),  # For Excel files
    chat_session_id: Optional[str] = Form(None),  # Scope to session
    is_global: bool = Form(False),  # Make available globally
    db: AsyncSession = Depends(get_db),
):
    """
    Upload CSV or Excel file as a data source.

    Supported formats:
    - CSV (.csv)
    - Excel (.xlsx, .xls)

    File size limit: 100MB (configurable)
    """
    # Validate file type
    # Save to uploads directory
    # Parse and extract schema
    # Create DuckDB virtual table
    # Return FileSource object
```

### Response Schema

```python
# src/models/schemas.py

class FileSourceResponse(BaseModel):
    id: int
    name: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    processing_status: str
    schema: Optional[FileSchema]
    row_count: Optional[int]
    created_at: datetime

class FileSchema(BaseModel):
    columns: List[ColumnInfo]
    row_count: int
    sample_values: Dict[str, List[Any]]  # Column name -> sample values

class ColumnInfo(BaseModel):
    name: str
    type: str  # inferred SQL type
    nullable: bool
    sample_values: List[Any]
```

---

## Core Components

### 1. FileSourceHandler

```python
# src/core/file_source_handler.py

class FileSourceHandler:
    """Handle file uploads and convert to queryable data sources"""

    SUPPORTED_TYPES = {'.csv', '.xlsx', '.xls'}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    async def process_upload(
        self,
        file: UploadFile,
        name: str,
        session_id: Optional[str] = None,
    ) -> FileSource:
        """
        Process uploaded file:
        1. Validate file type and size
        2. Save to uploads directory
        3. Parse file and infer schema
        4. Create DuckDB virtual table
        5. Return FileSource record
        """

    async def infer_schema(self, file_path: str, file_type: str) -> FileSchema:
        """
        Infer column types from file content.
        Uses DuckDB's type inference for accuracy.
        """

    async def create_virtual_table(
        self,
        file_source: FileSource,
        duckdb_session: Any,
    ) -> str:
        """
        Create DuckDB virtual table for file.
        Returns table name.
        """
        if file_source.file_type == 'csv':
            return f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT * FROM read_csv_auto('{file_path}', header=true)
            """
        elif file_source.file_type in ('xlsx', 'xls'):
            return f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT * FROM read_excel('{file_path}', sheet='{sheet_name}')
            """

    async def get_preview(
        self,
        file_source: FileSource,
        limit: int = 20
    ) -> List[Dict]:
        """Get first N rows for preview"""

    async def cleanup_file(self, file_source: FileSource) -> None:
        """Delete file and DuckDB table"""
```

### 2. Enhanced MultiDatabaseHandler

```python
# src/core/multi_db_handler.py (enhanced)

class MultiDatabaseHandler:
    """Handle queries across databases AND file sources"""

    async def build_combined_schema(
        self,
        connections: List[DatabaseConnection],
        file_sources: List[FileSource],  # NEW
    ) -> Dict[str, Any]:
        """
        Build combined schema from both databases and file sources.
        """
        combined_schema = {
            "databases": [],      # Existing database connections
            "file_sources": [],   # NEW: File-based sources
            "total_tables": 0,
            "total_columns": 0,
        }

        # Add database schemas (existing logic)
        for conn in connections:
            # ... existing introspection ...

        # Add file source schemas (NEW)
        for file_source in file_sources:
            file_schema = {
                "source_id": file_source.id,
                "name": file_source.name,
                "source_type": "file",
                "file_type": file_source.file_type,
                "tables": [{
                    "name": file_source.duckdb_table_name,
                    "columns": file_source.schema_cache.get("columns", []),
                    "row_count": file_source.schema_cache.get("row_count", 0),
                }],
            }
            combined_schema["file_sources"].append(file_schema)
            combined_schema["total_tables"] += 1

        return combined_schema

    def format_schema_for_llm(self, combined_schema: Dict[str, Any]) -> str:
        """
        Format combined schema for LLM consumption.
        Includes both databases and file sources with clear labels.
        """
        lines = []

        # Database sources
        lines.append("## DATABASE SOURCES")
        for db in combined_schema["databases"]:
            # ... existing formatting ...

        # File sources (NEW)
        lines.append("\n## FILE SOURCES (CSV/Excel uploads)")
        for file_source in combined_schema["file_sources"]:
            lines.append(f"\n--- File: {file_source['name']} ({file_source['file_type'].upper()}) ---")
            lines.append(f"Query as: {file_source['tables'][0]['name']}")
            for table in file_source["tables"]:
                for col in table.get("columns", []):
                    lines.append(f"  - {col['name']} ({col['type']})")

        return "\n".join(lines)
```

### 3. FileSourceDuckDBSession

```python
# src/core/file_source_session.py

class FileSourceDuckDBSession:
    """
    Manages DuckDB sessions for file-based queries.
    Uses shared in-memory database for performance.
    """

    _instance: Optional[duckdb.DuckDBPyConnection] = None
    _loaded_tables: Set[str] = set()

    @classmethod
    def get_session(cls) -> duckdb.DuckDBPyConnection:
        """Get or create shared DuckDB session"""
        if cls._instance is None:
            cls._instance = duckdb.connect(':memory:')
            # Load Excel extension
            cls._instance.execute("INSTALL excel; LOAD excel;")
        return cls._instance

    @classmethod
    async def ensure_table_loaded(
        cls,
        file_source: FileSource
    ) -> str:
        """Ensure file is loaded as DuckDB table, return table name"""
        table_name = file_source.duckdb_table_name

        if table_name not in cls._loaded_tables:
            session = cls.get_session()
            if file_source.file_type == 'csv':
                session.execute(f"""
                    CREATE OR REPLACE TABLE {table_name} AS
                    SELECT * FROM read_csv_auto('{file_source.file_path}')
                """)
            else:
                session.execute(f"""
                    CREATE OR REPLACE TABLE {table_name} AS
                    SELECT * FROM read_excel('{file_source.file_path}')
                """)
            cls._loaded_tables.add(table_name)

        return table_name
```

---

## Frontend Components

### 1. FileUploadModal.tsx

```tsx
// frontend/src/components/FileUploadModal.tsx

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: (fileSource: FileSource) => void;
  chatSessionId?: string;
}

export default function FileUploadModal({
  isOpen,
  onClose,
  onUploadComplete,
  chatSessionId
}: FileUploadModalProps) {
  // Features:
  // - Drag & drop zone
  // - File type validation (CSV, XLSX, XLS)
  // - File size validation (100MB max)
  // - Upload progress bar
  // - Sheet selector for Excel files
  // - Preview of first 5 rows after upload
  // - Custom display name input
}
```

### 2. DataSourcesPanel.tsx (Enhanced)

```tsx
// frontend/src/components/DataSourcesPanel.tsx
// Replaces/enhances ConnectionsPanel.tsx

interface DataSource {
  id: number;
  name: string;
  type: 'database' | 'file';
  subtype: string;  // 'postgresql', 'csv', 'xlsx', etc.
  isActive: boolean;
  metadata: {
    // For databases
    host?: string;
    database_name?: string;
    // For files
    original_filename?: string;
    row_count?: number;
    file_size?: number;
  };
}

export default function DataSourcesPanel({
  onSourceSelect,
  selectedSourceIds
}: Props) {
  // Features:
  // - Unified list of databases and files
  // - Visual distinction between source types (icons)
  // - Multi-select for cross-source queries
  // - "Add Database" and "Upload File" buttons
  // - File preview on hover
  // - Delete confirmation for files
}
```

### 3. FilePreviewPanel.tsx

```tsx
// frontend/src/components/FilePreviewPanel.tsx

interface FilePreviewPanelProps {
  fileSource: FileSource;
  onClose: () => void;
}

export default function FilePreviewPanel({ fileSource, onClose }: Props) {
  // Features:
  // - Schema display (columns, types)
  // - First 20 rows preview
  // - Row count and file size
  // - Refresh schema button
  // - Delete file button
}
```

---

## Implementation Phases

### Phase 1: Core Backend (Week 1)
**Goal**: File upload, storage, and schema extraction

| Task | Effort | Files |
|------|--------|-------|
| Create FileSource model and migration | 0.5d | `src/database/models.py` |
| Create uploads directory structure | 0.25d | `src/config/settings.py` |
| Implement FileSourceHandler | 1.5d | `src/core/file_source_handler.py` |
| Add file upload endpoint | 0.5d | `src/api/endpoints/files.py` |
| Add file CRUD endpoints | 0.5d | `src/api/endpoints/files.py` |
| Schema inference for CSV | 0.5d | `src/core/file_source_handler.py` |
| Schema inference for Excel | 0.5d | `src/core/file_source_handler.py` |
| Unit tests for file handling | 1d | `tests/test_file_sources.py` |

**Deliverables**:
- Files can be uploaded and stored
- Schema is automatically extracted
- Files listed via API

### Phase 2: DuckDB Integration (Week 2)
**Goal**: Query files as SQL tables

| Task | Effort | Files |
|------|--------|-------|
| FileSourceDuckDBSession manager | 1d | `src/core/file_source_session.py` |
| Virtual table creation for CSV | 0.5d | `src/core/file_source_handler.py` |
| Virtual table creation for Excel | 0.5d | `src/core/file_source_handler.py` |
| Enhance MultiDatabaseHandler for files | 1d | `src/core/multi_db_handler.py` |
| Update schema formatter for LLM | 0.5d | `src/core/multi_db_handler.py` |
| File query execution | 1d | `src/core/file_source_session.py` |
| Integration tests | 1d | `tests/test_file_query_integration.py` |

**Deliverables**:
- Files queryable via SQL
- Combined schema includes file sources
- LLM can generate SQL for files

### Phase 3: Cross-Source Queries (Week 3)
**Goal**: Query across databases and files

| Task | Effort | Files |
|------|--------|-------|
| Update ChatSession for file sources | 0.5d | `src/database/models.py` |
| Enhance query endpoint for mixed sources | 1d | `src/api/endpoints/query.py` |
| Cross-source result merging | 1d | `src/core/multi_db_handler.py` |
| Update chat endpoints | 0.5d | `src/api/endpoints/chat.py` |
| Handle file + database JOINs | 1d | `src/core/file_source_handler.py` |
| E2E tests for cross-source queries | 1d | `tests/test_cross_source_queries.py` |

**Deliverables**:
- Users can select files + databases together
- Queries work across mixed sources
- Results properly merged

### Phase 4: Frontend (Week 4)
**Goal**: Full UI for file management

| Task | Effort | Files |
|------|--------|-------|
| FileUploadModal component | 1d | `frontend/src/components/FileUploadModal.tsx` |
| DataSourcesPanel (enhanced) | 1d | `frontend/src/components/DataSourcesPanel.tsx` |
| FilePreviewPanel component | 0.5d | `frontend/src/components/FilePreviewPanel.tsx` |
| File API service | 0.5d | `frontend/src/services/fileApi.ts` |
| Update App.tsx for file sources | 0.5d | `frontend/src/App.tsx` |
| Frontend tests | 1d | `frontend/tests/` |
| Polish and UX improvements | 0.5d | Various |

**Deliverables**:
- Complete file upload UI
- File management in sidebar
- Preview functionality
- Seamless integration with existing UI

---

## Configuration

### New Settings

```python
# src/config/settings.py

class Settings(BaseSettings):
    # ... existing settings ...

    # File Upload Settings
    FILE_UPLOAD_DIR: str = "uploads"
    FILE_MAX_SIZE_MB: int = 100
    FILE_ALLOWED_TYPES: List[str] = [".csv", ".xlsx", ".xls"]
    FILE_AUTO_CLEANUP_DAYS: int = 30  # Auto-delete after N days

    # DuckDB Settings for Files
    DUCKDB_FILE_SESSION_MEMORY_LIMIT: str = "1GB"
    DUCKDB_FILE_THREADS: int = 4
```

---

## Security Considerations

### File Validation

1. **Type Validation**: Only allow CSV, XLSX, XLS
2. **Size Limits**: 100MB max (configurable)
3. **Content Scanning**: Validate file is actually CSV/Excel (not renamed malware)
4. **Path Traversal**: Sanitize filenames to prevent path traversal attacks
5. **Filename Sanitization**: Remove special characters, limit length

### Query Security

1. **SQL Injection**: Use parameterized queries when possible
2. **File Path Exposure**: Never expose absolute file paths in API responses
3. **Resource Limits**: Limit DuckDB memory/CPU usage per query

### Access Control

1. **File Ownership**: Files scoped to user/session
2. **Session Isolation**: Files in one session not visible to others
3. **Cleanup**: Auto-delete expired files

---

## Testing Strategy

### Unit Tests

```python
# tests/test_file_sources.py

class TestFileSourceHandler:
    async def test_upload_csv_file(self):
        """Test CSV file upload and schema extraction"""

    async def test_upload_excel_file(self):
        """Test Excel file upload with sheet selection"""

    async def test_infer_schema_types(self):
        """Test correct type inference for various data"""

    async def test_file_size_limit(self):
        """Test rejection of oversized files"""

    async def test_invalid_file_type(self):
        """Test rejection of unsupported file types"""
```

### Integration Tests

```python
# tests/test_file_query_integration.py

class TestFileQueries:
    async def test_query_csv_file(self):
        """Test querying uploaded CSV as SQL table"""

    async def test_query_excel_file(self):
        """Test querying uploaded Excel as SQL table"""

    async def test_cross_source_query(self):
        """Test query spanning database and file source"""

    async def test_llm_generates_file_sql(self):
        """Test LLM correctly generates SQL for file sources"""
```

### Frontend Tests

```typescript
// frontend/tests/FileUploadModal.test.tsx

describe('FileUploadModal', () => {
  it('accepts valid CSV files');
  it('rejects invalid file types');
  it('shows upload progress');
  it('displays schema after upload');
  it('handles upload errors gracefully');
});
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| File upload success rate | > 99% |
| Schema inference accuracy | > 95% |
| Cross-source query success rate | > 90% |
| Average file processing time | < 5s for 10MB file |
| User adoption | 50% of users try file upload in first month |

---

## Future Enhancements (Post-MVP)

1. **Parquet Support**: Add support for .parquet files
2. **Google Sheets Integration**: Connect to Google Sheets as data source
3. **Auto-Refresh**: Periodically re-import from URLs
4. **Data Transforms**: Allow users to transform/clean data before querying
5. **Large File Support**: Streaming upload for files > 100MB
6. **Version History**: Track multiple versions of uploaded files
7. **Scheduled Cleanup**: Background job to delete old/expired files

---

## Dependencies

### Python Packages

```txt
# requirements.txt additions
openpyxl>=3.1.0        # Excel file reading
xlrd>=2.0.0            # Legacy .xls support
python-magic>=0.4.27   # File type detection
aiofiles>=23.0.0       # Async file operations
```

### Frontend Packages

```json
// package.json additions
{
  "dependencies": {
    "react-dropzone": "^14.2.0",
    "@tanstack/react-table": "^8.10.0"  // If not already present
  }
}
```

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Large files cause OOM | High | Medium | DuckDB memory limits, file size caps |
| Malicious file uploads | High | Low | File type validation, content scanning |
| Schema inference errors | Medium | Medium | Allow manual type overrides |
| DuckDB session conflicts | Medium | Low | Session isolation, connection pooling |
| File storage costs | Low | High | Auto-cleanup, storage limits per user |

---

## Open Questions

1. **File Persistence**: Should files persist across sessions or be session-scoped?
   - **Recommendation**: Default to session-scoped, with option to make "global"

2. **Excel Multi-Sheet**: How to handle Excel files with multiple sheets?
   - **Recommendation**: Let user select sheet during upload, or create separate source per sheet

3. **Data Updates**: How to handle users updating a file?
   - **Recommendation**: Re-upload creates new version, old version retained for N days

4. **JOIN Syntax**: How should LLM reference files in cross-source JOINs?
   - **Recommendation**: Use DuckDB's ATTACH or explicit source prefixes

---

## References

- [DuckDB CSV Import](https://duckdb.org/docs/data/csv/overview.html)
- [DuckDB Excel Extension](https://duckdb.org/docs/extensions/excel.html)
- [Existing Multi-DB Implementation](../technical/FEATURES_MULTI_DB.md)
- [FastAPI File Uploads](https://fastapi.tiangolo.com/tutorial/request-files/)

---

**Document Version**: 1.0
**Author**: Claude Code
**Last Updated**: January 28, 2026
