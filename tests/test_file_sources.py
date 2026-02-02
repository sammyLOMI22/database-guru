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

    # Create an async read function
    content = sample_csv_content
    read_called = [False]

    async def read():
        return content

    async def seek(pos):
        pass

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

        async def read():
            return large_csv_content

        async def seek(pos):
            pass

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

        async def read():
            return b""

        async def seek(pos):
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

        path, hash_, size = await handler.save_file(
            sample_csv_file,
            session_id="test-session-123",
            is_global=False,
        )

        assert path.exists()
        assert path.parent.name == "test-session-123"
        assert hash_ is not None
        assert size > 0

    @pytest.mark.asyncio
    async def test_save_file_deduplication_hash(self, handler, sample_csv_content, temp_upload_dir):
        """Test that same content produces same hash."""
        handler.upload_dir = Path(temp_upload_dir)
        handler._ensure_upload_dir()

        # Create two files with same content
        file1 = MagicMock(spec=UploadFile)
        file1.filename = "file1.csv"

        async def read1():
            return sample_csv_content

        async def seek1(pos):
            pass

        file1.read = read1
        file1.seek = seek1

        file2 = MagicMock(spec=UploadFile)
        file2.filename = "file2.csv"

        async def read2():
            return sample_csv_content

        async def seek2(pos):
            pass

        file2.read = read2
        file2.seek = seek2

        _, hash1, _ = await handler.save_file(file1, None, True)
        _, hash2, _ = await handler.save_file(file2, None, True)

        assert hash1 == hash2
