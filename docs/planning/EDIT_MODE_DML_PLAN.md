# Edit Mode & DML Operations Plan

## Overview

This document outlines the plan for adding Edit Mode to Database Guru, enabling users to add, edit, and delete data directly through the UI, with automatic DML script generation and execution.

**Status**: Planning
**Priority**: MEDIUM
**Estimated Effort**: ~4,000 lines of code
**Est. Duration**: 4-5 weeks

---

## Goals

1. **Inline Data Editing** - Edit cell values directly in result tables
2. **Row Operations** - Add new rows, delete existing rows
3. **DML Script Generation** - Generate INSERT, UPDATE, DELETE statements
4. **Safe Execution** - Preview changes, transaction support, rollback capability
5. **Natural Language DML** - Ask AI to generate DML from plain English
6. **Audit Trail** - Track all data modifications

---

## Feature Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EDIT MODE ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              User Actions
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│  Inline Edit  │        │  Add New Row  │        │  Delete Row   │
│  (click cell) │        │  (+ button)   │        │  (trash icon) │
└───────┬───────┘        └───────┬───────┘        └───────┬───────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Change Tracker       │
                    │                         │
                    │  • Pending changes list │
                    │  • Original values      │
                    │  • Modified values      │
                    │  • Change type (I/U/D)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    DML Generator        │
                    │                         │
                    │  • INSERT statements    │
                    │  • UPDATE statements    │
                    │  • DELETE statements    │
                    │  • Dialect-aware        │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       ┌────────────┐    ┌────────────┐    ┌────────────┐
       │  Preview   │    │  Execute   │    │  Export    │
       │  Changes   │    │  with Tx   │    │  Script    │
       └────────────┘    └────────────┘    └────────────┘
```

---

## User Interface Design

### 1. Edit Mode Toggle

Add an "Edit Mode" toggle to the query results area:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Query Results                                    [Edit Mode: OFF 🔒]       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ id  │ name        │ email              │ status   │ created_at      │   │
│  │─────┼─────────────┼────────────────────┼──────────┼─────────────────│   │
│  │ 1   │ John Doe    │ john@example.com   │ active   │ 2024-01-15      │   │
│  │ 2   │ Jane Smith  │ jane@example.com   │ active   │ 2024-02-20      │   │
│  │ 3   │ Bob Wilson  │ bob@example.com    │ inactive │ 2024-03-10      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Edit Mode Enabled

When Edit Mode is ON, the UI transforms:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Query Results                                    [Edit Mode: ON ✏️]        │
│                                                   [+ Add Row] [Save 3]      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ │ id  │ name        │ email              │ status   │ created_at │ 🗑 │
│  │───┼─────┼─────────────┼────────────────────┼──────────┼────────────┼───│
│  │ ☐ │ 1   │ John Doe    │ john@example.com   │ active   │ 2024-01-15 │ 🗑 │
│  │ ☑ │ 2   │ Jane Smith  │ jane@acme.com  *   │ active   │ 2024-02-20 │ 🗑 │  ← Modified
│  │ ☐ │ 3   │ Bob Wilson  │ bob@example.com    │ inactive │ 2024-03-10 │ 🗑 │
│  │ + │ NEW │ Sam Brown   │ sam@example.com    │ pending  │            │ 🗑 │  ← New row
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Pending Changes (3):                                                       │
│  • UPDATE users SET email = 'jane@acme.com' WHERE id = 2                   │
│  • INSERT INTO users (name, email, status) VALUES ('Sam Brown', ...)       │
│                                                                             │
│  [Preview SQL]  [Discard Changes]  [Save Changes]                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Inline Cell Editing

Click a cell to edit:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  │ 2   │ Jane Smith  │ ┌──────────────────┐ │ active   │ 2024-02-20 │ 🗑 │  │
│  │     │             │ │ jane@acme.com    │ │          │            │   │  │
│  │     │             │ │ ──────────────── │ │          │            │   │  │
│  │     │             │ │ Original: jane@  │ │          │            │   │  │
│  │     │             │ │ example.com      │ │          │            │   │  │
│  │     │             │ └──────────────────┘ │          │            │   │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Add New Row Form

Modal or inline form for adding rows:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Add New Row to `users`                                               [X]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  id (auto)        [  Generated  ]  (Primary Key - Auto Increment)          │
│                                                                             │
│  name *           [                              ]                          │
│                                                                             │
│  email *          [                              ]                          │
│                                                                             │
│  status           [ active           ▼]  (Enum: active, inactive, pending) │
│                                                                             │
│  created_at       [ 2026-02-01       ]  (Default: CURRENT_TIMESTAMP)       │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Generated SQL:                                                             │
│  INSERT INTO users (name, email, status, created_at)                       │
│  VALUES ('...', '...', 'active', '2026-02-01');                            │
│                                                                             │
│                                        [Cancel]  [Add Row]  [Add & Another] │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. Delete Confirmation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Confirm Delete                                                       [X]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ⚠️  You are about to delete 2 row(s) from `users`:                        │
│                                                                             │
│  • id: 5 - John Temporary                                                  │
│  • id: 8 - Test User                                                       │
│                                                                             │
│  Generated SQL:                                                             │
│  DELETE FROM users WHERE id IN (5, 8);                                     │
│                                                                             │
│  ⚠️  This action cannot be undone without a backup.                        │
│                                                                             │
│                                        [Cancel]  [Delete 2 Rows]           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6. Preview & Execute Panel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Review Changes                                                       [X]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Summary: 1 INSERT, 2 UPDATE, 1 DELETE                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ -- Generated DML Script                                             │   │
│  │ -- Database: sales_db (PostgreSQL)                                  │   │
│  │ -- Generated: 2026-02-01 14:32:00                                   │   │
│  │                                                                     │   │
│  │ BEGIN;                                                              │   │
│  │                                                                     │   │
│  │ -- Update email for user id=2                                       │   │
│  │ UPDATE users SET email = 'jane@acme.com'                            │   │
│  │ WHERE id = 2;                                                       │   │
│  │                                                                     │   │
│  │ -- Update status for user id=3                                      │   │
│  │ UPDATE users SET status = 'active'                                  │   │
│  │ WHERE id = 3;                                                       │   │
│  │                                                                     │   │
│  │ -- Insert new user                                                  │   │
│  │ INSERT INTO users (name, email, status)                             │   │
│  │ VALUES ('Sam Brown', 'sam@example.com', 'pending');                 │   │
│  │                                                                     │   │
│  │ -- Delete test user                                                 │   │
│  │ DELETE FROM users WHERE id = 99;                                    │   │
│  │                                                                     │   │
│  │ COMMIT;                                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ☑ Wrap in transaction (recommended)                                       │
│  ☐ Execute immediately without review                                      │
│                                                                             │
│  [Copy SQL]  [Download .sql]  [Cancel]  [Execute Changes]                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Natural Language DML

Allow users to describe changes in plain English:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  💬 Describe your data change:                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Set all users with status 'pending' to 'active' if they were        │   │
│  │ created more than 7 days ago                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                       [Generate DML]        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Generated SQL:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ UPDATE users                                                        │   │
│  │ SET status = 'active'                                               │   │
│  │ WHERE status = 'pending'                                            │   │
│  │   AND created_at < NOW() - INTERVAL '7 days';                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ⚠️  This will affect approximately 23 rows.                               │
│                                                                             │
│  [Edit SQL]  [Preview Affected Rows]  [Execute]                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Directory Structure

```
src/
├── dml/
│   ├── __init__.py
│   ├── change_tracker.py      # Track pending changes
│   ├── dml_generator.py       # Generate INSERT/UPDATE/DELETE
│   ├── dml_validator.py       # Validate changes before execution
│   ├── dml_executor.py        # Execute with transaction support
│   ├── nl_dml_agent.py        # Natural language to DML
│   └── audit_logger.py        # Log all DML operations
│
├── api/endpoints/
│   └── dml.py                 # DML API endpoints
│
├── database/
│   └── models.py              # DMLAuditLog model

frontend/src/
├── components/
│   ├── edit/
│   │   ├── EditModeToggle.tsx
│   │   ├── EditableCell.tsx
│   │   ├── EditableRow.tsx
│   │   ├── AddRowForm.tsx
│   │   ├── DeleteConfirmation.tsx
│   │   ├── ChangePreview.tsx
│   │   ├── DMLPreviewPanel.tsx
│   │   └── NaturalLanguageDML.tsx
│   │
│   └── results/
│       └── EditableQueryResults.tsx
│
├── hooks/
│   ├── useChangeTracker.ts
│   ├── useEditMode.ts
│   └── useDMLExecution.ts
│
└── services/
    └── dmlApi.ts
```

### Backend Components

#### 1. Change Tracker

```python
# src/dml/change_tracker.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class ChangeType(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class CellChange:
    """Represents a single cell value change."""
    column: str
    old_value: Any
    new_value: Any


@dataclass
class RowChange:
    """Represents changes to a single row."""
    change_type: ChangeType
    table_name: str
    primary_key: Dict[str, Any]  # {column: value} for composite keys
    changes: List[CellChange] = field(default_factory=list)
    new_row_data: Optional[Dict[str, Any]] = None  # For INSERT


class ChangeTracker:
    """
    Tracks pending changes to data.

    Frontend sends changes here, and this class:
    - Validates changes don't conflict
    - Merges multiple edits to same row
    - Generates DML in correct order
    """

    def __init__(self, table_name: str, primary_key_columns: List[str]):
        self.table_name = table_name
        self.primary_key_columns = primary_key_columns
        self._changes: Dict[str, RowChange] = {}  # keyed by PK hash

    def track_update(
        self,
        primary_key: Dict[str, Any],
        column: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Track a cell update."""
        pk_hash = self._hash_pk(primary_key)

        if pk_hash not in self._changes:
            self._changes[pk_hash] = RowChange(
                change_type=ChangeType.UPDATE,
                table_name=self.table_name,
                primary_key=primary_key,
            )

        # Find existing change to this column or add new
        change = self._changes[pk_hash]
        for cell_change in change.changes:
            if cell_change.column == column:
                cell_change.new_value = new_value
                return

        change.changes.append(CellChange(
            column=column,
            old_value=old_value,
            new_value=new_value,
        ))

    def track_insert(self, row_data: Dict[str, Any]) -> str:
        """Track a new row insertion. Returns temporary ID."""
        temp_id = f"new_{len(self._changes)}"

        self._changes[temp_id] = RowChange(
            change_type=ChangeType.INSERT,
            table_name=self.table_name,
            primary_key={},
            new_row_data=row_data,
        )

        return temp_id

    def track_delete(self, primary_key: Dict[str, Any]) -> None:
        """Track a row deletion."""
        pk_hash = self._hash_pk(primary_key)

        # If this was a pending insert, just remove it
        if pk_hash.startswith("new_"):
            if pk_hash in self._changes:
                del self._changes[pk_hash]
            return

        self._changes[pk_hash] = RowChange(
            change_type=ChangeType.DELETE,
            table_name=self.table_name,
            primary_key=primary_key,
        )

    def discard_change(self, primary_key: Dict[str, Any]) -> None:
        """Discard pending changes for a row."""
        pk_hash = self._hash_pk(primary_key)
        if pk_hash in self._changes:
            del self._changes[pk_hash]

    def discard_all(self) -> None:
        """Discard all pending changes."""
        self._changes.clear()

    def get_changes(self) -> List[RowChange]:
        """Get all pending changes in execution order."""
        # Order: DELETE first, then UPDATE, then INSERT
        changes = list(self._changes.values())
        return sorted(changes, key=lambda c: (
            0 if c.change_type == ChangeType.DELETE else
            1 if c.change_type == ChangeType.UPDATE else 2
        ))

    def get_change_summary(self) -> Dict[str, int]:
        """Get count of changes by type."""
        summary = {"INSERT": 0, "UPDATE": 0, "DELETE": 0}
        for change in self._changes.values():
            summary[change.change_type.value] += 1
        return summary

    def _hash_pk(self, primary_key: Dict[str, Any]) -> str:
        """Create hash key for primary key values."""
        if not primary_key:
            return f"new_{id(primary_key)}"
        return "_".join(str(primary_key.get(col, "")) for col in self.primary_key_columns)
```

#### 2. DML Generator

```python
# src/dml/dml_generator.py

from typing import List, Optional
from src.dml.change_tracker import RowChange, ChangeType
from src.core.dialect_registry import DialectRegistry


class DMLGenerator:
    """
    Generates dialect-aware DML statements.

    Supports: PostgreSQL, MySQL, SQLite, SQL Server
    """

    def __init__(self, dialect: str = "postgresql"):
        self.dialect = dialect
        self.dialect_registry = DialectRegistry()

    def generate_script(
        self,
        changes: List[RowChange],
        wrap_in_transaction: bool = True,
        include_comments: bool = True,
    ) -> str:
        """Generate complete DML script from changes."""
        lines = []

        if include_comments:
            lines.append(f"-- Generated DML Script")
            lines.append(f"-- Dialect: {self.dialect}")
            lines.append(f"-- Changes: {len(changes)}")
            lines.append("")

        if wrap_in_transaction:
            lines.append(self._begin_transaction())
            lines.append("")

        for change in changes:
            if include_comments:
                lines.append(f"-- {change.change_type.value} on {change.table_name}")

            if change.change_type == ChangeType.INSERT:
                lines.append(self._generate_insert(change))
            elif change.change_type == ChangeType.UPDATE:
                lines.append(self._generate_update(change))
            elif change.change_type == ChangeType.DELETE:
                lines.append(self._generate_delete(change))

            lines.append("")

        if wrap_in_transaction:
            lines.append(self._commit_transaction())

        return "\n".join(lines)

    def _generate_insert(self, change: RowChange) -> str:
        """Generate INSERT statement."""
        if not change.new_row_data:
            return ""

        columns = list(change.new_row_data.keys())
        values = [self._format_value(change.new_row_data[col]) for col in columns]

        return (
            f"INSERT INTO {self._quote_identifier(change.table_name)} "
            f"({', '.join(self._quote_identifier(c) for c in columns)})\n"
            f"VALUES ({', '.join(values)});"
        )

    def _generate_update(self, change: RowChange) -> str:
        """Generate UPDATE statement."""
        if not change.changes:
            return ""

        set_clauses = [
            f"{self._quote_identifier(c.column)} = {self._format_value(c.new_value)}"
            for c in change.changes
        ]

        where_clauses = [
            f"{self._quote_identifier(col)} = {self._format_value(val)}"
            for col, val in change.primary_key.items()
        ]

        return (
            f"UPDATE {self._quote_identifier(change.table_name)}\n"
            f"SET {', '.join(set_clauses)}\n"
            f"WHERE {' AND '.join(where_clauses)};"
        )

    def _generate_delete(self, change: RowChange) -> str:
        """Generate DELETE statement."""
        where_clauses = [
            f"{self._quote_identifier(col)} = {self._format_value(val)}"
            for col, val in change.primary_key.items()
        ]

        return (
            f"DELETE FROM {self._quote_identifier(change.table_name)}\n"
            f"WHERE {' AND '.join(where_clauses)};"
        )

    def _format_value(self, value) -> str:
        """Format value for SQL based on type."""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        else:
            return f"'{str(value)}'"

    def _quote_identifier(self, identifier: str) -> str:
        """Quote identifier based on dialect."""
        if self.dialect in ("postgresql", "sqlite"):
            return f'"{identifier}"'
        elif self.dialect == "mysql":
            return f"`{identifier}`"
        elif self.dialect == "sqlserver":
            return f"[{identifier}]"
        return identifier

    def _begin_transaction(self) -> str:
        """Get BEGIN TRANSACTION statement for dialect."""
        if self.dialect == "sqlserver":
            return "BEGIN TRANSACTION;"
        return "BEGIN;"

    def _commit_transaction(self) -> str:
        """Get COMMIT statement for dialect."""
        return "COMMIT;"
```

#### 3. DML Executor

```python
# src/dml/dml_executor.py

from typing import List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.dml.change_tracker import RowChange
from src.dml.dml_generator import DMLGenerator
from src.dml.audit_logger import DMLAuditLogger


@dataclass
class ExecutionResult:
    """Result of DML execution."""
    success: bool
    rows_affected: int
    error_message: Optional[str] = None
    executed_sql: Optional[str] = None


class DMLExecutor:
    """
    Executes DML with transaction support and audit logging.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        dialect: str,
        connection_id: int,
        user_id: Optional[str] = None,
    ):
        self.db = db_session
        self.dialect = dialect
        self.connection_id = connection_id
        self.user_id = user_id
        self.generator = DMLGenerator(dialect)
        self.audit_logger = DMLAuditLogger(db_session)

    async def execute_changes(
        self,
        changes: List[RowChange],
        dry_run: bool = False,
    ) -> ExecutionResult:
        """
        Execute DML changes with transaction support.

        If dry_run=True, generates SQL but doesn't execute.
        """
        if not changes:
            return ExecutionResult(success=True, rows_affected=0)

        # Generate SQL
        sql_script = self.generator.generate_script(
            changes,
            wrap_in_transaction=True,
            include_comments=True,
        )

        if dry_run:
            return ExecutionResult(
                success=True,
                rows_affected=0,
                executed_sql=sql_script,
            )

        # Execute with transaction
        try:
            total_affected = 0

            for change in changes:
                if change.change_type.value == "INSERT":
                    sql = self.generator._generate_insert(change)
                elif change.change_type.value == "UPDATE":
                    sql = self.generator._generate_update(change)
                else:
                    sql = self.generator._generate_delete(change)

                result = await self.db.execute(text(sql.rstrip(";")))
                total_affected += result.rowcount

                # Log to audit trail
                await self.audit_logger.log_change(
                    connection_id=self.connection_id,
                    user_id=self.user_id,
                    change_type=change.change_type.value,
                    table_name=change.table_name,
                    sql_executed=sql,
                    rows_affected=result.rowcount,
                    primary_key=change.primary_key,
                )

            await self.db.commit()

            return ExecutionResult(
                success=True,
                rows_affected=total_affected,
                executed_sql=sql_script,
            )

        except Exception as e:
            await self.db.rollback()

            # Log failed attempt
            await self.audit_logger.log_failure(
                connection_id=self.connection_id,
                user_id=self.user_id,
                sql_attempted=sql_script,
                error_message=str(e),
            )

            return ExecutionResult(
                success=False,
                rows_affected=0,
                error_message=str(e),
                executed_sql=sql_script,
            )

    async def preview_affected_rows(
        self,
        changes: List[RowChange],
    ) -> List[dict]:
        """
        Preview which rows will be affected by UPDATE/DELETE.

        Returns list of current row data for rows that will change.
        """
        affected = []

        for change in changes:
            if change.change_type.value == "INSERT":
                continue

            where_clauses = [
                f"{col} = {self.generator._format_value(val)}"
                for col, val in change.primary_key.items()
            ]

            sql = f"SELECT * FROM {change.table_name} WHERE {' AND '.join(where_clauses)}"
            result = await self.db.execute(text(sql))
            rows = result.mappings().all()
            affected.extend([dict(r) for r in rows])

        return affected
```

#### 4. Natural Language DML Agent

```python
# src/dml/nl_dml_agent.py

from typing import Optional, Dict, Any
from src.llm.ollama_client import OllamaClient
from src.database.schema_manager import SchemaManager


class NaturalLanguageDMLAgent:
    """
    Converts natural language descriptions to DML statements.

    Example: "Delete all users who haven't logged in for 90 days"
    -> DELETE FROM users WHERE last_login < NOW() - INTERVAL '90 days';
    """

    SYSTEM_PROMPT = """You are a SQL DML generator. Convert natural language descriptions
into safe, efficient DML statements (INSERT, UPDATE, DELETE).

Rules:
1. Always use explicit WHERE clauses for UPDATE and DELETE
2. Never generate DROP, TRUNCATE, or DDL statements
3. Use parameterized-style placeholders when values are ambiguous
4. Include comments explaining what the statement does
5. For bulk operations, suggest a SELECT first to preview affected rows

Schema context will be provided. Generate SQL for the specified dialect."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        schema_manager: SchemaManager,
        dialect: str = "postgresql",
    ):
        self.ollama = ollama_client
        self.schema_manager = schema_manager
        self.dialect = dialect

    async def generate_dml(
        self,
        description: str,
        table_name: Optional[str] = None,
        connection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate DML from natural language description.

        Returns:
            {
                "sql": "UPDATE users SET...",
                "operation": "UPDATE",
                "table": "users",
                "estimated_rows": 23,
                "preview_sql": "SELECT * FROM users WHERE...",
                "warnings": ["This will affect 23 rows"]
            }
        """
        # Get schema context
        schema_context = ""
        if connection_id:
            schema = await self.schema_manager.get_schema(connection_id)
            schema_context = self._format_schema(schema, table_name)

        prompt = f"""
{self.SYSTEM_PROMPT}

Dialect: {self.dialect}

Schema:
{schema_context}

User request: {description}

Generate the DML statement. Also provide:
1. A SELECT query to preview affected rows (for UPDATE/DELETE)
2. Estimated row count if possible
3. Any warnings about the operation

Return as JSON:
{{
    "sql": "...",
    "operation": "INSERT|UPDATE|DELETE",
    "table": "table_name",
    "preview_sql": "SELECT...",
    "warnings": ["warning1", "warning2"]
}}
"""

        response = await self.ollama.generate(prompt, temperature=0.1)

        # Parse JSON response
        import json
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Extract JSON from response if wrapped in text
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = {"sql": response, "operation": "UNKNOWN", "warnings": ["Could not parse response"]}

        return result

    def _format_schema(self, schema: dict, table_name: Optional[str] = None) -> str:
        """Format schema for prompt context."""
        lines = []

        tables = schema.get("tables", [])
        if table_name:
            tables = [t for t in tables if t.get("name") == table_name]

        for table in tables[:5]:  # Limit to 5 tables
            lines.append(f"Table: {table['name']}")
            for col in table.get("columns", []):
                pk = " (PK)" if col.get("primary_key") else ""
                nullable = " NULL" if col.get("nullable") else " NOT NULL"
                lines.append(f"  - {col['name']}: {col['type']}{pk}{nullable}")
            lines.append("")

        return "\n".join(lines)
```

#### 5. Audit Logger

```python
# src/dml/audit_logger.py

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DMLAuditLog


class DMLAuditLogger:
    """
    Logs all DML operations for audit trail.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def log_change(
        self,
        connection_id: int,
        user_id: Optional[str],
        change_type: str,
        table_name: str,
        sql_executed: str,
        rows_affected: int,
        primary_key: Optional[Dict[str, Any]] = None,
    ) -> DMLAuditLog:
        """Log a successful DML operation."""
        log_entry = DMLAuditLog(
            connection_id=connection_id,
            user_id=user_id,
            change_type=change_type,
            table_name=table_name,
            sql_executed=sql_executed,
            rows_affected=rows_affected,
            primary_key_values=primary_key,
            executed_at=datetime.utcnow(),
            success=True,
        )

        self.db.add(log_entry)
        await self.db.flush()

        return log_entry

    async def log_failure(
        self,
        connection_id: int,
        user_id: Optional[str],
        sql_attempted: str,
        error_message: str,
    ) -> DMLAuditLog:
        """Log a failed DML operation."""
        log_entry = DMLAuditLog(
            connection_id=connection_id,
            user_id=user_id,
            sql_executed=sql_attempted,
            executed_at=datetime.utcnow(),
            success=False,
            error_message=error_message,
        )

        self.db.add(log_entry)
        await self.db.flush()

        return log_entry
```

### Database Models

```python
# src/database/models.py additions

class DMLAuditLog(Base):
    """Audit trail for all DML operations."""
    __tablename__ = "dml_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Context
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    user_id = Column(String(100), index=True)
    chat_session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=True)

    # Operation details
    change_type = Column(String(20))  # INSERT, UPDATE, DELETE
    table_name = Column(String(255))
    sql_executed = Column(Text, nullable=False)
    rows_affected = Column(Integer, default=0)
    primary_key_values = Column(JSON)  # For tracking specific rows

    # Status
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text)

    # Timing
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    connection = relationship("DatabaseConnection", backref="dml_audit_logs")


class ConnectionWritePermission(Base):
    """Track which connections allow write operations."""
    __tablename__ = "connection_write_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), unique=True, nullable=False)

    # Permissions
    allow_insert = Column(Boolean, default=False)
    allow_update = Column(Boolean, default=False)
    allow_delete = Column(Boolean, default=False)

    # Safety settings
    require_where_clause = Column(Boolean, default=True)  # Prevent UPDATE/DELETE without WHERE
    max_rows_per_operation = Column(Integer, default=100)  # Limit bulk operations
    require_confirmation = Column(Boolean, default=True)  # Force preview before execute

    # Allowed tables (JSON array, null = all tables)
    allowed_tables = Column(JSON)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    connection = relationship("DatabaseConnection", backref="write_permission")
```

---

## API Endpoints

```python
# src/api/endpoints/dml.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session
from src.dml.change_tracker import ChangeTracker, RowChange
from src.dml.dml_generator import DMLGenerator
from src.dml.dml_executor import DMLExecutor
from src.dml.nl_dml_agent import NaturalLanguageDMLAgent

router = APIRouter(prefix="/dml", tags=["DML Operations"])


@router.post("/preview")
async def preview_changes(
    request: DMLPreviewRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Generate DML script from pending changes without executing.

    Returns generated SQL for review.
    """
    generator = DMLGenerator(dialect=request.dialect)

    changes = [RowChange(**c) for c in request.changes]

    sql_script = generator.generate_script(
        changes,
        wrap_in_transaction=request.wrap_in_transaction,
        include_comments=True,
    )

    return {
        "sql": sql_script,
        "change_count": len(changes),
        "summary": _summarize_changes(changes),
    }


@router.post("/execute")
async def execute_changes(
    request: DMLExecuteRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Execute DML changes with transaction support.

    Requires write permission on the connection.
    """
    # Check write permissions
    permission = await _check_write_permission(db, request.connection_id)
    if not permission:
        raise HTTPException(403, "Write operations not allowed on this connection")

    # Validate changes against permissions
    changes = [RowChange(**c) for c in request.changes]
    _validate_changes(changes, permission)

    # Get connection dialect
    connection = await _get_connection(db, request.connection_id)

    executor = DMLExecutor(
        db_session=db,
        dialect=connection.database_type,
        connection_id=request.connection_id,
        user_id=request.user_id,
    )

    result = await executor.execute_changes(changes)

    if not result.success:
        raise HTTPException(400, result.error_message)

    return {
        "success": True,
        "rows_affected": result.rows_affected,
        "executed_sql": result.executed_sql,
    }


@router.post("/preview-affected")
async def preview_affected_rows(
    request: DMLPreviewAffectedRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Preview rows that will be affected by UPDATE/DELETE operations.
    """
    connection = await _get_connection(db, request.connection_id)

    executor = DMLExecutor(
        db_session=db,
        dialect=connection.database_type,
        connection_id=request.connection_id,
    )

    changes = [RowChange(**c) for c in request.changes]
    affected = await executor.preview_affected_rows(changes)

    return {
        "affected_rows": affected,
        "count": len(affected),
    }


@router.post("/natural-language")
async def generate_dml_from_natural_language(
    request: NLDMLRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Generate DML from natural language description.

    Example: "Set all inactive users to deleted status"
    """
    connection = await _get_connection(db, request.connection_id)

    agent = NaturalLanguageDMLAgent(
        ollama_client=get_ollama_client(),
        schema_manager=get_schema_manager(),
        dialect=connection.database_type,
    )

    result = await agent.generate_dml(
        description=request.description,
        table_name=request.table_name,
        connection_id=request.connection_id,
    )

    return result


@router.get("/audit-log")
async def get_audit_log(
    connection_id: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """Get DML audit log entries."""
    query = select(DMLAuditLog).order_by(DMLAuditLog.executed_at.desc()).limit(limit)

    if connection_id:
        query = query.where(DMLAuditLog.connection_id == connection_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/permissions/{connection_id}")
async def get_write_permissions(
    connection_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get write permissions for a connection."""
    permission = await _check_write_permission(db, connection_id)

    if not permission:
        return {
            "connection_id": connection_id,
            "write_enabled": False,
            "allow_insert": False,
            "allow_update": False,
            "allow_delete": False,
        }

    return {
        "connection_id": connection_id,
        "write_enabled": True,
        "allow_insert": permission.allow_insert,
        "allow_update": permission.allow_update,
        "allow_delete": permission.allow_delete,
        "require_where_clause": permission.require_where_clause,
        "max_rows_per_operation": permission.max_rows_per_operation,
        "allowed_tables": permission.allowed_tables,
    }


@router.put("/permissions/{connection_id}")
async def update_write_permissions(
    connection_id: int,
    request: WritePermissionRequest,
    db: AsyncSession = Depends(get_session),
):
    """Update write permissions for a connection."""
    # ... implementation
    pass
```

---

## Safety Features

### 1. Permission System

- Per-connection write permissions (INSERT/UPDATE/DELETE separately)
- Table-level restrictions (whitelist specific tables)
- Row limit per operation (prevent accidental bulk deletes)
- Require WHERE clause for UPDATE/DELETE

### 2. Transaction Support

- All changes wrapped in transactions
- Automatic rollback on error
- Option to execute as single transaction or individual statements

### 3. Preview Before Execute

- Always show generated SQL before execution
- Preview affected rows for UPDATE/DELETE
- Estimated row count warnings

### 4. Audit Trail

- Log all DML operations (success and failure)
- Track user, timestamp, SQL executed, rows affected
- Queryable audit log API

### 5. Validation

- Check foreign key constraints before DELETE
- Validate data types before INSERT/UPDATE
- Warn about nullable constraints

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Create `ChangeTracker` class
- [ ] Create `DMLGenerator` with dialect support
- [ ] Create `DMLExecutor` with transaction support
- [ ] Add database models (DMLAuditLog, WritePermission)
- [ ] Create database migrations
- [ ] Unit tests for core components

### Phase 2: API Endpoints
- [ ] `/dml/preview` endpoint
- [ ] `/dml/execute` endpoint
- [ ] `/dml/preview-affected` endpoint
- [ ] `/dml/permissions` endpoints
- [ ] `/dml/audit-log` endpoint
- [ ] Integration tests

### Phase 3: Frontend - Edit Mode Toggle
- [ ] `EditModeToggle` component
- [ ] `useEditMode` hook
- [ ] Permission check integration
- [ ] Edit mode state management

### Phase 4: Frontend - Inline Editing
- [ ] `EditableCell` component
- [ ] `EditableRow` component
- [ ] `useChangeTracker` hook
- [ ] Visual indicators for modified cells

### Phase 5: Frontend - Add/Delete Operations
- [ ] `AddRowForm` component with schema awareness
- [ ] `DeleteConfirmation` modal
- [ ] Bulk selection for delete

### Phase 6: Frontend - Preview & Execute
- [ ] `DMLPreviewPanel` component
- [ ] `ChangePreview` summary
- [ ] Execute with progress indicator
- [ ] Success/error feedback

### Phase 7: Natural Language DML
- [ ] `NaturalLanguageDMLAgent` implementation
- [ ] `/dml/natural-language` endpoint
- [ ] `NaturalLanguageDML` frontend component
- [ ] Preview affected rows before execute

### Phase 8: Polish & Security
- [ ] Connection settings UI for write permissions
- [ ] Audit log viewer
- [ ] Additional validation rules
- [ ] Documentation and user guide

---

## API Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dml/preview` | POST | Generate DML script without executing |
| `/dml/execute` | POST | Execute DML with transaction support |
| `/dml/preview-affected` | POST | Preview rows affected by UPDATE/DELETE |
| `/dml/natural-language` | POST | Generate DML from natural language |
| `/dml/audit-log` | GET | Get DML operation history |
| `/dml/permissions/{id}` | GET | Get write permissions for connection |
| `/dml/permissions/{id}` | PUT | Update write permissions |

---

## Security Considerations

1. **Permission Required** - Write operations disabled by default per connection
2. **SQL Injection** - Use parameterized queries internally
3. **Bulk Operation Limits** - Configurable max rows per operation
4. **WHERE Clause Required** - Prevent accidental full-table UPDATE/DELETE
5. **Audit Everything** - Complete audit trail for compliance
6. **No DDL** - Never generate DROP, TRUNCATE, ALTER statements

---

## Related Documentation

- [DATA_LINEAGE_PLAN.md](DATA_LINEAGE_PLAN.md) - Track lineage through DML operations
- [MASTER_ROADMAP.md](MASTER_ROADMAP.md) - Overall project roadmap

---

*Document Version: 1.0*
*Created: 2026-02-01*
*Status: Planning*
