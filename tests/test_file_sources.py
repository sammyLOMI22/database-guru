"""Tests for file source functionality

Phase 13: CSV & Excel File Support

Tests for file upload, validation, schema inference, and API endpoints.
"""
import io
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.file_source_handler import FileSourceHandler, get_file_source_by_id, list_file_sources
from src.core.file_source_session import FileSourceDuckDBSession
from src.core.file_utils import validate_file_path, sanitize_sheet_name
from src.database.models import FileSource


@pytest.fixture
def settings():
    """Create test settings."""
    from src.config.settings import Settings
    settings = Settings()
    settings.FILE_UPLOAD_DIR = tempfile.mkdtemp()
    settings.FILE_MAX_SIZE_MB = 10
    settings.FILE_ALLOWED_TYPES = ".csv,.xlsx,.xls"
    settings.FILE_AUTO_CLEANUP_DAYS = 30
    return settings


@pytest.fixture
def handler(settings):
    """Create FileSourceHandler instance."""
    return FileSourceHandler(settings)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return b"id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n"


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Create a mock UploadFile for CSV."""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_data.csv"
    file.content_type = "text/csv"

    # Create an async read function that supports optional size parameter
    content = sample_csv_content
    pos = [0]

    async def read(size=-1):
        if size == -1:
            chunk = content[pos[0]:]
            pos[0] = len(content)
            return chunk
        chunk = content[pos[0]:pos[0] + size]
        pos[0] += len(chunk)
        return chunk

    async def seek(p):
        pos[0] = p

    file.read = read
    file.seek = seek

    return file


@pytest.fixture
def large_csv_content():
    """Generate CSV content that exceeds size limit."""
    # Generate 11MB of data
    rows = ["id,name,data"]
    for i in range(100000):
        rows.append(f"{i},name_{i},{'x' * 100}")
    return "\n".join(rows).encode()


class TestFileValidation:
    """Tests for file validation."""

    @pytest.mark.asyncio
    async def test_validate_csv_file_success(self, handler, sample_csv_file):
        """Test successful CSV file validation."""
        is_valid, error = await handler.validate_file(sample_csv_file)
        assert is_valid is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_validate_file_no_filename(self, handler):
        """Test validation fails for missing filename."""
        file = MagicMock(spec=UploadFile)
        file.filename = None

        is_valid, error = await handler.validate_file(file)
        assert is_valid is False
        assert "Filename is required" in error

    @pytest.mark.asyncio
    async def test_validate_file_invalid_extension(self, handler):
        """Test validation fails for invalid file extension."""
        file = MagicMock(spec=UploadFile)
        file.filename = "test.pdf"

        async def read():
            return b"some content"

        async def seek(pos):
            pass

        file.read = read
        file.seek = seek

        is_valid, error = await handler.validate_file(file)
        assert is_valid is False
        assert "not allowed" in error

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, handler, large_csv_content):
        """Test validation fails for oversized files."""
        file = MagicMock(spec=UploadFile)
        file.filename = "large.csv"
        pos = [0]

        async def read(size=-1):
            if size == -1:
                chunk = large_csv_content[pos[0]:]
                pos[0] = len(large_csv_content)
                return chunk
            chunk = large_csv_content[pos[0]:pos[0] + size]
            pos[0] += len(chunk)
            return chunk

        async def seek(p):
            pos[0] = p

        file.read = read
        file.seek = seek

        is_valid, error = await handler.validate_file(file)
        assert is_valid is False
        assert "exceeds limit" in error

    @pytest.mark.asyncio
    async def test_validate_file_empty(self, handler):
        """Test validation fails for empty files."""
        file = MagicMock(spec=UploadFile)
        file.filename = "empty.csv"

        async def read(size=-1):
            return b""

        async def seek(p):
            pass

        file.read = read
        file.seek = seek

        is_valid, error = await handler.validate_file(file)
        assert is_valid is False
        assert "empty" in error.lower()


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_sanitize_removes_path_components(self, handler):
        """Test that path components are removed."""
        result = handler._sanitize_filename("/etc/passwd")
        assert "/" not in result
        assert "passwd" in result

    def test_sanitize_removes_traversal(self, handler):
        """Test that path traversal is blocked."""
        result = handler._sanitize_filename("../../../etc/passwd")
        assert ".." not in result

    def test_sanitize_removes_special_chars(self, handler):
        """Test that special characters are removed."""
        result = handler._sanitize_filename("file<>:\"|?*.csv")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert result.endswith(".csv")

    def test_sanitize_handles_empty(self, handler):
        """Test that empty filenames get default name."""
        result = handler._sanitize_filename("")
        assert result == "unnamed_file"

    def test_sanitize_handles_dot_files(self, handler):
        """Test that dot files get renamed."""
        result = handler._sanitize_filename(".hidden")
        assert not result.startswith(".")


class TestTableNameGeneration:
    """Tests for DuckDB table name generation."""

    def test_generate_table_name_basic(self, handler):
        """Test basic table name generation."""
        result = handler._generate_table_name("sales_data.csv", 42)
        assert result.startswith("file_42_")
        assert "sales_data" in result

    def test_generate_table_name_special_chars(self, handler):
        """Test table name with special characters."""
        result = handler._generate_table_name("my data (2024).csv", 1)
        assert result.startswith("file_1_")
        assert "(" not in result
        assert ")" not in result
        assert " " not in result

    def test_generate_table_name_long_filename(self, handler):
        """Test table name length is limited."""
        long_name = "a" * 100 + ".csv"
        result = handler._generate_table_name(long_name, 1)
        # Should be file_1_ + max 30 chars
        assert len(result) <= 40


class TestSchemaInference:
    """Tests for schema inference using DuckDB."""

    @pytest.fixture
    def temp_csv_file(self, settings, sample_csv_content):
        """Create a temporary CSV file."""
        path = Path(settings.FILE_UPLOAD_DIR) / "test.csv"
        path.write_bytes(sample_csv_content)
        yield path
        if path.exists():
            path.unlink()

    @pytest.mark.asyncio
    async def test_infer_schema_csv(self, handler, temp_csv_file):
        """Test schema inference from CSV file."""
        schema = await handler.infer_schema(temp_csv_file, "csv")

        assert "columns" in schema
        assert "row_count" in schema
        assert "sample_values" in schema

        assert len(schema["columns"]) == 3  # id, name, value
        assert schema["row_count"] == 3

        # Check column types
        col_names = [c["name"] for c in schema["columns"]]
        assert "id" in col_names
        assert "name" in col_names
        assert "value" in col_names

    @pytest.mark.asyncio
    async def test_infer_schema_type_detection(self, handler, settings):
        """Test that DuckDB correctly infers types."""
        csv_content = b"int_col,float_col,str_col,date_col\n1,1.5,hello,2024-01-15\n2,2.5,world,2024-01-16\n"
        path = Path(settings.FILE_UPLOAD_DIR) / "typed.csv"
        path.write_bytes(csv_content)

        try:
            schema = await handler.infer_schema(path, "csv")
            columns = {c["name"]: c["type"] for c in schema["columns"]}

            # DuckDB should infer appropriate types (may vary by DuckDB version)
            assert any(t in columns["int_col"] for t in ["INTEGER", "BIGINT", "NUMBER"])
            assert any(t in columns["float_col"] for t in ["DOUBLE", "FLOAT", "NUMBER"])
            assert "VARCHAR" in columns["str_col"]
        finally:
            path.unlink()


class TestFilePreview:
    """Tests for file preview functionality."""

    @pytest.fixture
    def file_source_mock(self, settings, sample_csv_content):
        """Create a mock FileSource with temp file."""
        path = Path(settings.FILE_UPLOAD_DIR) / "preview_test.csv"
        path.write_bytes(sample_csv_content)

        fs = MagicMock(spec=FileSource)
        fs.id = 1
        fs.name = "Test File"
        fs.file_path = str(path)
        fs.file_type = "csv"
        fs.sheet_name = None

        yield fs

        if path.exists():
            path.unlink()

    @pytest.mark.asyncio
    async def test_get_preview_basic(self, handler, file_source_mock):
        """Test basic preview functionality."""
        preview = await handler.get_preview(file_source_mock, limit=10)

        assert "columns" in preview
        assert "data" in preview
        assert "row_count" in preview
        assert "total_rows" in preview
        assert "truncated" in preview

        assert preview["columns"] == ["id", "name", "value"]
        assert len(preview["data"]) == 3
        assert preview["total_rows"] == 3
        assert preview["truncated"] is False

    @pytest.mark.asyncio
    async def test_get_preview_limit(self, handler, settings):
        """Test preview respects limit."""
        # Create file with more rows
        rows = ["id,name"] + [f"{i},name_{i}" for i in range(100)]
        csv_content = "\n".join(rows).encode()
        path = Path(settings.FILE_UPLOAD_DIR) / "many_rows.csv"
        path.write_bytes(csv_content)

        fs = MagicMock(spec=FileSource)
        fs.file_path = str(path)
        fs.file_type = "csv"
        fs.sheet_name = None

        try:
            preview = await handler.get_preview(fs, limit=5)
            assert len(preview["data"]) == 5
            assert preview["total_rows"] == 100
            assert preview["truncated"] is True
        finally:
            path.unlink()


class TestDuckDBSession:
    """Tests for FileSourceDuckDBSession."""

    @pytest.fixture(autouse=True)
    async def reset_session(self):
        """Reset DuckDB session before each test."""
        await FileSourceDuckDBSession.reset_session()
        yield
        await FileSourceDuckDBSession.reset_session()

    def test_get_session_creates_singleton(self):
        """Test that get_session returns a singleton."""
        session1 = FileSourceDuckDBSession.get_session()
        session2 = FileSourceDuckDBSession.get_session()
        assert session1 is session2

    @pytest.mark.asyncio
    async def test_is_table_loaded_initially_false(self):
        """Test that tables are not loaded initially."""
        result = await FileSourceDuckDBSession.is_table_loaded("test_table")
        assert result is False

    def test_get_loaded_tables_empty(self):
        """Test loaded tables list is initially empty."""
        tables = FileSourceDuckDBSession.get_loaded_tables()
        assert tables == []

    @pytest.mark.asyncio
    async def test_reset_session_clears_state(self):
        """Test that reset clears all state."""
        # Add some state
        FileSourceDuckDBSession._loaded_tables.add("test_table")
        FileSourceDuckDBSession._table_metadata["test_table"] = {"row_count": 100}

        await FileSourceDuckDBSession.reset_session()

        assert len(FileSourceDuckDBSession._loaded_tables) == 0
        assert len(FileSourceDuckDBSession._table_metadata) == 0
        assert FileSourceDuckDBSession._instance is None


class TestContentValidation:
    """Tests for file content validation."""

    @pytest.mark.asyncio
    async def test_validate_csv_content(self, handler):
        """Test CSV content validation."""
        valid_csv = b"col1,col2\nval1,val2\n"
        result = await handler._validate_content(valid_csv, ".csv")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_csv_binary_content(self, handler):
        """Test that binary content fails CSV validation."""
        binary_content = b"\x00\x01\x02\x03\x04"
        result = await handler._validate_content(binary_content, ".csv")
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_xlsx_magic_bytes(self, handler):
        """Test XLSX magic bytes validation."""
        valid_xlsx = b"PK\x03\x04" + b"\x00" * 100
        result = await handler._validate_content(valid_xlsx, ".xlsx")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_xlsx_invalid_magic(self, handler):
        """Test invalid XLSX magic bytes."""
        invalid_content = b"NOT_A_ZIP_FILE"
        result = await handler._validate_content(invalid_content, ".xlsx")
        assert result is False


class TestCleanupSoftDelete:
    """Tests for soft-delete behavior in cleanup_file and cleanup_expired_files."""

    @pytest.mark.asyncio
    async def test_cleanup_file_soft_deletes(self, handler, settings, sample_csv_content):
        """Test that cleanup_file sets is_active=False and processing_status='deleted'."""
        # Create a temp file on disk
        path = Path(settings.FILE_UPLOAD_DIR) / "to_delete.csv"
        path.write_bytes(sample_csv_content)

        # Create a mock FileSource
        fs = MagicMock(spec=FileSource)
        fs.id = 42
        fs.name = "To Delete"
        fs.file_path = str(path)
        fs.is_active = True
        fs.processing_status = 'ready'
        fs.processing_error = None

        db = AsyncMock(spec=AsyncSession)

        await handler.cleanup_file(fs, db)

        # Should soft-delete, NOT call db.delete()
        db.delete.assert_not_called()
        db.commit.assert_called_once()

        # Should mark as inactive/deleted
        assert fs.is_active is False
        assert fs.processing_status == 'deleted'
        assert fs.processing_error == 'File has been removed'

        # Physical file should be deleted
        assert not path.exists()

    @pytest.mark.asyncio
    async def test_cleanup_file_physical_file_deleted(self, handler, settings, sample_csv_content):
        """Test that the physical file is still removed from disk."""
        path = Path(settings.FILE_UPLOAD_DIR) / "physical_delete.csv"
        path.write_bytes(sample_csv_content)
        assert path.exists()

        fs = MagicMock(spec=FileSource)
        fs.id = 43
        fs.name = "Physical Delete"
        fs.file_path = str(path)
        fs.is_active = True
        fs.processing_status = 'ready'
        fs.processing_error = None

        db = AsyncMock(spec=AsyncSession)

        await handler.cleanup_file(fs, db)

        assert not path.exists()

    @pytest.mark.asyncio
    async def test_cleanup_expired_files_calls_unload_table(self, settings, sample_csv_content):
        """Test that cleanup_expired_files calls unload_table for each expired file."""
        from datetime import timedelta
        from src.core.file_source_handler import cleanup_expired_files

        # Mock the database session
        db = AsyncMock(spec=AsyncSession)

        # Create mock expired file sources
        fs1 = MagicMock(spec=FileSource)
        fs1.id = 1
        fs1.name = "Expired 1"
        fs1.file_path = "/nonexistent/file1.csv"
        fs1.duckdb_table_name = "file_1_expired1"
        fs1.is_active = True
        fs1.processing_status = 'ready'
        fs1.processing_error = None

        fs2 = MagicMock(spec=FileSource)
        fs2.id = 2
        fs2.name = "Expired 2"
        fs2.file_path = "/nonexistent/file2.csv"
        fs2.duckdb_table_name = "file_2_expired2"
        fs2.is_active = True
        fs2.processing_status = 'ready'
        fs2.processing_error = None

        # Mock the query result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [fs1, fs2]
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        with patch('src.core.file_source_session.FileSourceDuckDBSession') as mock_session_cls:
            mock_session_cls.unload_table = AsyncMock()

            count = await cleanup_expired_files(db)

            # Should have called unload_table for each file
            assert mock_session_cls.unload_table.call_count == 2
            mock_session_cls.unload_table.assert_any_call("file_1_expired1")
            mock_session_cls.unload_table.assert_any_call("file_2_expired2")


# Integration tests would go here, using actual database and file system
class TestFileSourceIntegration:
    """Integration tests for file source functionality."""

    @pytest.fixture
    def temp_upload_dir(self):
        """Create temporary upload directory."""
        import tempfile
        import shutil
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path)

    @pytest.mark.asyncio
    async def test_save_file_creates_directories(self, handler, sample_csv_file, temp_upload_dir):
        """Test that save_file creates necessary directories."""
        handler.upload_dir = Path(temp_upload_dir)
        handler._ensure_upload_dir()

        test_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        path, hash_, size = await handler.save_file(
            sample_csv_file,
            session_id=test_uuid,
            is_global=False,
        )

        assert path.exists()
        assert path.parent.name == test_uuid
        assert hash_ is not None
        assert size > 0

    @pytest.mark.asyncio
    async def test_save_file_deduplication_hash(self, handler, sample_csv_content, temp_upload_dir):
        """Test that same content produces same hash."""
        handler.upload_dir = Path(temp_upload_dir)
        handler._ensure_upload_dir()

        # Create two files with same content (mock chunked reads)
        def make_mock_file(filename, content):
            f = MagicMock(spec=UploadFile)
            f.filename = filename
            pos = [0]

            async def read(size=-1):
                if size == -1:
                    chunk = content[pos[0]:]
                    pos[0] = len(content)
                    return chunk
                chunk = content[pos[0]:pos[0] + size]
                pos[0] += len(chunk)
                return chunk

            async def seek(p):
                pos[0] = p

            f.read = read
            f.seek = seek
            return f

        file1 = make_mock_file("file1.csv", sample_csv_content)
        file2 = make_mock_file("file2.csv", sample_csv_content)

        _, hash1, _ = await handler.save_file(file1, None, True)
        _, hash2, _ = await handler.save_file(file2, None, True)

        assert hash1 == hash2


class TestPathValidation:
    """Tests for file path validation security."""

    def test_validate_file_path_valid(self, handler, settings, sample_csv_content):
        """Test that valid paths within upload dir are accepted."""
        path = Path(settings.FILE_UPLOAD_DIR) / "test.csv"
        path.write_bytes(sample_csv_content)

        try:
            result = validate_file_path(str(path), handler.upload_dir)
            assert result == str(path.resolve())
        finally:
            path.unlink()

    def test_validate_file_path_traversal_blocked(self, handler):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(ValueError, match="outside the allowed upload directory"):
            validate_file_path("/etc/passwd", handler.upload_dir)

    def test_validate_file_path_relative_traversal_blocked(self, handler, settings):
        """Test that relative path traversal is blocked."""
        traversal_path = str(Path(settings.FILE_UPLOAD_DIR) / ".." / ".." / "etc" / "passwd")
        with pytest.raises(ValueError, match="outside the allowed upload directory"):
            validate_file_path(traversal_path, handler.upload_dir)

    def test_validate_file_path_empty(self, handler):
        """Test that empty paths are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_file_path("", handler.upload_dir)

    def test_validate_file_path_nonexistent(self, handler, settings):
        """Test that nonexistent files are rejected."""
        nonexistent = str(Path(settings.FILE_UPLOAD_DIR) / "nonexistent.csv")
        with pytest.raises(ValueError, match="does not exist"):
            validate_file_path(nonexistent, handler.upload_dir)


class TestSheetNameSanitization:
    """Tests for Excel sheet name sanitization."""

    def test_sanitize_sheet_name_valid(self):
        """Test that valid sheet names pass through."""
        assert sanitize_sheet_name("Sheet1") == "Sheet1"
        assert sanitize_sheet_name("Sales Data") == "Sales Data"
        assert sanitize_sheet_name("Q4-2024") == "Q4-2024"
        assert sanitize_sheet_name("data_backup") == "data_backup"

    def test_sanitize_sheet_name_removes_sql_injection(self):
        """Test that SQL injection attempts are sanitized."""
        # Single quotes removed
        assert "'" not in sanitize_sheet_name("Sheet'; DROP TABLE--")
        # Semicolons removed
        assert ";" not in sanitize_sheet_name("Sheet1; DELETE FROM")
        # Comments removed
        assert "--" not in sanitize_sheet_name("Sheet1--")

    def test_sanitize_sheet_name_empty_returns_default(self):
        """Test that empty sheet names return default."""
        assert sanitize_sheet_name("") == "Sheet1"
        assert sanitize_sheet_name(None) == "Sheet1"
        assert sanitize_sheet_name("   ") == "Sheet1"

    def test_sanitize_sheet_name_length_limit(self):
        """Test that long sheet names are truncated."""
        long_name = "A" * 200
        result = sanitize_sheet_name(long_name)
        assert len(result) <= 100
