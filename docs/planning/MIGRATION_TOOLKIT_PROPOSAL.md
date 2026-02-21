# Proposal: Database Migration Toolkit

**Status**: PROPOSED
**Priority**: HIGH (User Requested)
**Dependencies**: Phase 11 (Lineage), Phase 12 (Lineage Intelligence)

---

## 1. Overview
The **Migration Toolkit** is a suite of tools designed to help users safely evolve their database schemas. It moves Database Guru from a "Read-Only" analysis tool to a "DevOps" companion for database engineering.

## 2. Core Features

### 🔍 2.1 Schema Diff (The "What")
A tool to compare two distinct schema states and generate a structured "Diff Report".

*   **Inputs**:
    *   Source A (e.g., "Production DB")
    *   Source B (e.g., "Staging DB" or "schema.sql" file)
*   **Outputs**:
    *   **Visual Diff**: Graphical representation of added/removed/modified tables and columns.
    *   **Drift Analysis**: Identify configuration drift (e.g., index missing in Prod).

### 📋 2.2 Migration Planner (The "How")
An Agentic workflow that takes a "Diff" or a "Goal" and plans the safe execution path.

*   **Capability**:
    *   **Dependency Ordering**: Knows to create `Users` before `Orders`.
    *   **Data Preservation**: Detects if a "column rename" is actually a "drop + add" and warns about data loss.
    *   **Locking Awareness**: Suggests "Online Schema Change" patterns for large tables.

### 🛠️ 2.3 Script Generator (The "Action")
Auto-generates the actual SQL code for the migration.

*   **Artifacts**:
    *   `up.sql`: The forward migration.
    *   `down.sql`: The rollback script.
    *   `verify.sql`: A script to assert the migration succeeded.
*   **Multi-Dialect**: Generates specific SQL for all supported target databases:

| Dialect | Identifier Quoting | ADD Column | Type/Nullability Change | FK Handling | Notes |
|---------|-------------------|------------|------------------------|-------------|-------|
| PostgreSQL | `"double"` | `ADD COLUMN` | `ALTER COLUMN ... TYPE ... USING` / `SET/DROP NOT NULL` | none needed | ANSI standard |
| MySQL | `` `backtick` `` | `ADD COLUMN` | `MODIFY COLUMN` | `SET FOREIGN_KEY_CHECKS` | |
| SQLite | `"double"` | `ADD COLUMN` | Table recreate pattern | none | No `ALTER COLUMN` support |
| DuckDB | `"double"` | `ADD COLUMN` | `ALTER COLUMN ... TYPE` | none needed | PostgreSQL-compatible |
| **SQL Server** | `[bracket]` | `ADD col` | `ALTER COLUMN col type NULL/NOT NULL` | `sp_MSforeachtable` NOCHECK/CHECK | Driver: `pymssql` |
| **Oracle** | `"double"` | `ADD (col type)` | `MODIFY (col type)` | PL/SQL loop over `all_constraints` | Driver: `oracledb` (thin mode); no `IF EXISTS` — uses exception blocks |

### 🧪 2.4 Data Migration Assistant
For changes that require moving data, not just schema.

*   **Features**:
    *   `INSERT INTO ... SELECT ...` generation.
    *   Batching strategies for large data moves.
    *   Validation queries (Row count matches, Sum matches).

---

## 3. User Experience (UX)

1.  **"Compare" Tab**: User selects "Source" and "Target".
2.  **Review Differences**: App shows a "Git-like" view of the schema.
3.  **"Generate Migration"**: User clicks a button.
4.  **Agent Planning**:
    *   *Agent*: "I see you renamed 'status' to 'order_status'. Should I migrate the data?"
    *   *User*: "Yes."
5.  **Code Review**: App presents the SQL scripts.
6.  **Simulation**: (If Phase 18 is active) Run the script in a transaction to verify.

---

## 4. Technical Architecture

*   **New Module**: `src/migration/*`
*   **Diff Engine**: Leverage `alembic`'s autogenerate logic programmatically, or build a custom comparator using our `SchemaCache`.
*   **LLM Role**:
    *   The LLM is NOT used for the *raw diff* (too error prone).
    *   The LLM IS used for **Explaining user intent** (e.g., "Rename" vs "Drop/Add") and **Writing complex data backfill scripts**.

## 5. Integration with Roadmap

*   **Relates to Phase 18 (Edit Mode)**: Migration execution is a form of DML.
*   **Relates to Phase 12 (Lineage)**: Use Lineage to warn about breaking downstream views/dashboards.
*   **Relates to Security**: **CRITICAL** dependency. Migrations require DDL permissions.


## 7. Constraint Handling Strategy (Deep Dive)

Data migration often fails due to violations of Foreign Key (FK), Unique, or Not Null constraints. The toolkit employs a multi-layered strategy to handle these:

### 7.1 The "Order of Operations" (Topological Sort)
The Migration Planner will build a dependency graph of all tables based on Foreign Keys.
*   **Strategy**: Always migrate "Parent" tables (referenced) before "Child" tables (referencing).
*   **Example**: `Users` -> `Orders` -> `OrderItems`.

### 7.2 Handling Circular Dependencies
When Table A references Table B, and Table B references Table A:
1.  **Method A: Deferred Constraints** (Postgres/Oracle): Wrap the migration in a transaction and set `SET CONSTRAINTS ALL DEFERRED`.
2.  **Method B: Null-then-Update**:
    *   Step 1: Insert into Table A with the FK column set to `NULL`.
    *   Step 2: Insert into Table B.
    *   Step 3: `UPDATE` Table A to set the correct FK value.
3.  **Method C: Disable/Enable** (MySQL/SQLite):
    *   `SET FOREIGN_KEY_CHECKS = 0;`
    *   Perform Migration.
    *   `SET FOREIGN_KEY_CHECKS = 1;` (Triggers immediate validation).
4.  **Method D: Bulk disable via stored procedure** (SQL Server / MSSQL):
    *   `EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';`
    *   Perform Migration.
    *   `EXEC sp_MSforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT ALL';`
5.  **Method E: PL/SQL loop** (Oracle):
    *   Loop over `all_constraints WHERE constraint_type = 'R'` and `DISABLE` each.
    *   Perform Migration.
    *   Loop again and `ENABLE` each constraint.

### 7.3 "Pre-Flight" Soft Validation
Before attempting the migration, the Agent runs **ReadOnly** validation queries on the *Source* data to find rows that *will* fail.

*   **Orphan Detection**:
    ```sql
    -- Find Orders that reference a missing User
    SELECT count(*) FROM Orders o
    LEFT JOIN Users u ON o.user_id = u.id
    WHERE u.id IS NULL;
    ```
*   **Duplicate Detection**:
    ```sql
    -- Check for future Unique Constraint violations
    SELECT email, count(*) FROM Users GROUP BY email HAVING count(*) > 1;
    ```
*   **Action Plan**: If violators are found, the Agent suggests:
    *   *Exclude*: "Skip these 5 rows?"
    *   *Default*: "Map missing User IDs to a 'System User' (ID 0)?"
    *   *Fix*: "Generate a cleanup script to delete orphans?"

## 8. Next Steps
1.  Prototype `SchemaDiff` using current `SchemaCache`.
2.  Design the "Migration Plan" JSON structure.
3.  Build a "Constraint Checker" to validate foreign keys during planning.