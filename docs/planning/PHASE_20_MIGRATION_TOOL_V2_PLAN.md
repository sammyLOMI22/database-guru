Plan: Extended Schema Objects in Migration Toolkit                                                                                                 

 Context

 The migration toolkit (Phase 20) currently only handles tables, columns, PKs, FKs, and indexes. Real-world databases also contain views, sequences,
 check constraints, stored procedures/functions, triggers, and enums. This plan adds support for all of these as optional, user-toggled objects
 across all layers: introspection → caching → comparison → script generation → planning → API → frontend.

 Dialect Capability Matrix

 ┌───────────────────┬────────────┬───────┬────────┬───────┬────────┬────────┐
 │      Object       │ PostgreSQL │ MySQL │ SQLite │ MSSQL │ Oracle │ DuckDB │
 ├───────────────────┼────────────┼───────┼────────┼───────┼────────┼────────┤
 │ Views             │     Y      │   Y   │   Y    │   Y   │   Y    │   Y    │
 ├───────────────────┼────────────┼───────┼────────┼───────┼────────┼────────┤
 │ Sequences         │     Y      │   -   │   -    │   Y   │   Y    │   Y    │
 ├───────────────────┼────────────┼───────┼────────┼───────┼────────┼────────┤
 │ Check Constraints │     Y      │   Y   │   -    │   Y   │   Y    │   -    │
 ├───────────────────┼────────────┼───────┼────────┼───────┼────────┼────────┤
 │ Procedures/Funcs  │     Y      │   Y   │   -    │   Y   │   Y    │   -    │
 ├───────────────────┼────────────┼───────┼────────┼───────┼────────┼────────┤
 │ Triggers          │     Y      │   Y   │   Y    │   Y   │   Y    │   -    │
 ├───────────────────┼────────────┼───────┼────────┼───────┼────────┼────────┤
 │ Enums             │     Y      │   -   │   -    │   -   │   -    │   -    │
 └───────────────────┴────────────┴───────┴────────┴───────┴────────┴────────┘

 Unsupported combos return empty lists. UI disables toggles for unsupported dialects.

 ---
 Implementation Steps

 Step 1: Schema Inspector — new introspection methods

 File: src/core/schema_inspector.py

 Add a DIALECT_CAPABILITIES dict at module level (the matrix above, keyed by dialect string).

 Add 6 new async methods to SchemaInspector:
 - get_views(session, schema_name) → List[Dict] with keys: name, definition
 - get_sequences(session, schema_name) → List[Dict] with keys: name, data_type, start_value, increment, min_value, max_value
 - get_check_constraints(session, schema_name) → List[Dict] with keys: table_name, constraint_name, definition
 - get_routines(session, schema_name) → List[Dict] with keys: name, type (procedure/function), language, definition, return_type
 - get_triggers(session, schema_name) → List[Dict] with keys: name, table_name, timing, event, definition
 - get_enums(session, schema_name) → List[Dict] with keys: name, values

 Each method has dialect-specific SQL branches (same pattern as existing get_tables, get_columns, etc.) using self._execute_query(). Unsupported
 dialects return [].

 Key SQL queries per dialect (abbreviated):
 - Views: PG information_schema.views, MySQL information_schema.views, SQLite sqlite_master WHERE type='view', MSSQL sys.views + OBJECT_DEFINITION,
 Oracle user_views
 - Sequences: PG pg_sequences, MSSQL sys.sequences, Oracle user_sequences, DuckDB duckdb_sequences()
 - Check constraints: PG pg_constraint WHERE contype='c', MySQL information_schema.check_constraints, MSSQL sys.check_constraints, Oracle
 user_constraints WHERE constraint_type='C'
 - Routines: PG information_schema.routines + pg_get_functiondef, MySQL information_schema.routines, MSSQL sys.objects WHERE type IN
 ('P','FN','TF','IF'), Oracle user_objects + DBMS_METADATA
 - Triggers: PG/MySQL information_schema.triggers, SQLite sqlite_master WHERE type='trigger', MSSQL sys.triggers, Oracle user_triggers
 - Enums: PG pg_type + pg_enum, all others return []

 Update get_full_schema() signature:
 async def get_full_schema(
     self, session, schema_name=None, include_samples=True,
     include_views=False, include_sequences=False,
     include_check_constraints=False, include_routines=False,
     include_triggers=False, include_enums=False,
 ) -> Dict[str, Any]:

 After the existing table/relationship loop (line ~206), conditionally call each new method and add results to the schema dict under new top-level
 keys ("views", "sequences", etc.). Update summary with new counts.

 Step 2: Schema Cache — forward flags, update fingerprint

 File: src/core/schema_cache.py

 get_schema(): Add include_flags: Optional[Dict[str, bool]] = None parameter. Build a flags suffix for the cache key:
 "schema:{id}:{name}:{sorted_flag_keys}". Forward flags to SchemaInspector.get_full_schema().

 create_fingerprint_from_schema_dict(): After existing table fingerprinting, append entries for new objects when present:
 for view in sorted(schema_data.get("views", []), key=lambda v: v["name"]):
     fingerprint_parts.append(f"view:{view['name']}")
 # ... similarly for sequences, routines, triggers, enums

 Step 3: Schema Comparator — new diff dataclasses + compare logic

 File: src/migration/schema_comparator.py

 New dataclasses (all with to_dict() method):
 - ViewDiff(view_name, diff_type, source_definition, target_definition, risk_level="low")
 - SequenceDiff(sequence_name, diff_type, source_state, target_state, risk_level="low")
 - CheckConstraintDiff(table_name, constraint_name, diff_type, source_definition, target_definition, risk_level="low")
 - RoutineDiff(routine_name, routine_type, diff_type, source_definition, target_definition, risk_level="medium")
 - TriggerDiff(trigger_name, table_name, diff_type, source_definition, target_definition, risk_level="medium")
 - EnumDiff(enum_name, diff_type, source_values, target_values, risk_level="low")

 Extend SchemaDiff: Add 6 new List fields (default field(default_factory=list)). Update to_dict() and from_dict() to serialize/deserialize them.
 Since defaults are empty lists, existing serialized data deserializes fine (backward compatible).

 Extend SchemaComparator.compare(): After existing table comparison, add comparison methods for each object type. Pattern: match by name → detect
 added/removed/modified. For views/routines/triggers, "modified" = definition text differs (after whitespace normalization). For enums, compare value
  lists. For sequences, compare start/increment/min/max.

 Update diff_summary and overall_risk computation to include new diffs.

 Step 4: Script Generator — DDL for extended objects

 File: src/migration/script_generator.py

 Execution order in _generate_up() (after existing header/FK-disable):
 1. Enums — CREATE TYPE name AS ENUM (...) (PG only; before tables that reference them)
 2. Sequences — CREATE SEQUENCE name ... (before tables with DEFAULT nextval)
 3. Tables — existing logic (CREATE, ALTER, DROP)
 4. Check constraints — ALTER TABLE x ADD CONSTRAINT name CHECK (expr)
 5. Views — CREATE [OR REPLACE] VIEW name AS ... (after tables they reference)
 6. Routines — Emit full definition body with comment: -- NOTE: dialect-specific, may need manual adaptation
 7. Triggers — Same approach as routines, last because they may call functions
 8. FK re-enable (existing)

 _generate_down(): Reverse order — DROP TRIGGER, DROP ROUTINE, DROP VIEW, DROP CHECK CONSTRAINT, (existing table rollbacks), DROP SEQUENCE, DROP
 TYPE.

 _generate_verify(): Check existence in system catalogs (dialect-specific queries, same pattern as existing table verification).

 New private methods: _generate_enums_up/down, _generate_sequences_up/down, _generate_check_constraints_up/down, _generate_views_up/down,
 _generate_routines_up/down, _generate_triggers_up/down.

 Routine/trigger bodies are emitted as-is with a clear comment that cross-dialect translation is not automatic.

 Step 5: Backup Script Generator — extended objects in backup

 File: src/migration/backup_script_generator.py

 Update generate() to accept the extended schema dict. After existing table DDL generation, add sections for each object type present in the schema
 dict. Same execution order as Step 4.

 Update _generate_restore() to DROP extended objects in reverse order before dropping tables.

 Update _generate_verify() with existence checks for extended objects.

 Update BackupScripts dataclass: no field changes needed (backup_sql/restore_sql/verify_sql already hold the full output). Just update table_count to
  also report object counts in warnings or summary.

 Step 6: Migration Planner — new step types

 File: src/migration/migration_planner.py

 Add optional object_type: Optional[str] = None field to MigrationStep dataclass (values: "table", "view", "sequence", "check_constraint", "routine",
  "trigger", "enum"). Update to_dict().

 Extend _generate_deterministic_steps(): after table steps, generate steps for each extended object type in dependency order (enums/sequences first,
 triggers last). Each step has appropriate risk_level, lock_type, estimated_duration.

 Update _assess_complexity_deterministic() to factor in non-table changes.

 Step 7: Pydantic Schemas — request/response extensions

 File: src/models/schemas.py

 Add include flags to request models (all default False for backward compat):
 - SchemaDiffRequest: add include_views, include_sequences, include_check_constraints, include_routines, include_triggers, include_enums
 - BackupScriptRequest: same flags
 - GenerateScriptsRequest: same flags

 Extend response models with optional new diff lists:
 - SchemaDiffResponse: add view_diffs, sequence_diffs, check_constraint_diffs, routine_diffs, trigger_diffs, enum_diffs (all List[dict] = [])

 Step 8: API Endpoints — thread flags through

 File: src/api/endpoints/migration.py

 Update _get_schema_for_connection(): Accept include_flags: Optional[Dict[str, bool]] = None and pass to SchemaCache.get_schema().

 Update compare_schemas: Extract flags from request, pass to _get_schema_for_connection() for both source and target. The comparator will compare
 whatever objects are present.

 Update generate_backup_scripts: Extract flags from request, pass to _get_schema_for_connection(). The backup generator will emit DDL for whatever
 objects are in the schema.

 Update create_scripts: Extract flags from request, pass through so the script generator emits DDL for extended objects when present in the diff
 snapshot.

 Step 9: Frontend Types + API

 Files: frontend/src/types/migration.ts, frontend/src/services/migrationApi.ts

 New types:
 interface SchemaObjectFlags {
   include_views?: boolean;
   include_sequences?: boolean;
   include_check_constraints?: boolean;
   include_routines?: boolean;
   include_triggers?: boolean;
   include_enums?: boolean;
 }
 interface ViewDiff { view_name: string; diff_type: string; ... }
 // + SequenceDiff, CheckConstraintDiff, RoutineDiff, TriggerDiff, EnumDiff

 Extend SchemaDiffResponse with optional new diff arrays.

 Update API methods: compareDatabases(), generateBackupScripts(), generateScripts() — accept optional SchemaObjectFlags and spread into request body.

 Step 10: Frontend — shared toggle component

 New file: frontend/src/components/migration/SchemaObjectToggles.tsx

 Reusable component:
 interface Props {
   flags: SchemaObjectFlags;
   onChange: (flags: SchemaObjectFlags) => void;
   dialect?: string; // disables unsupported options
 }

 Renders 6 checkboxes in a 2x3 grid inside a collapsible "Include Extended Objects" section. Uses the DIALECT_CAPABILITIES matrix to disable
 unsupported options with a tooltip.

 Step 11: Frontend — integrate toggles into panels

 Files:
 - frontend/src/components/migration/SchemaDiffPanel.tsx — Add SchemaObjectToggles below source/target selectors. Pass flags in handleCompare().
 Display new diff sections (views, sequences, etc.) below table diffs.
 - frontend/src/components/migration/BackupScriptPanel.tsx — Add SchemaObjectToggles below connection/dialect selectors. Pass flags in
 handleGenerate().
 - frontend/src/components/migration/ScriptGeneratorPanel.tsx — Add SchemaObjectToggles below dialect selector. Pass flags in handleGenerate().

 ---
 Key Design Decisions

 1. All flags default False — zero behavioral change for existing callers
 2. Routine/trigger bodies emitted as-is — no cross-dialect translation attempted (PL/pgSQL ≠ T-SQL ≠ PL/SQL); wrapped with "may need manual
 adaptation" comments
 3. Enums are PostgreSQL-only — MySQL ENUM is column-level (already in column type strings), not a standalone DDL object
 4. Cache key includes flags — avoids complexity of merging partial schema results
 5. SchemaDiff new fields default to empty lists — existing serialized diffs deserialize without breaking

 Verification

 1. Backend smoke test: python -c "from src.core.schema_inspector import SchemaInspector, DIALECT_CAPABILITIES; print(DIALECT_CAPABILITIES)"
 2. Introspection test: Connect to a real PostgreSQL/SQLite database with views, run get_full_schema(include_views=True) and verify views appear
 3. Comparator test: Create two schemas with different views, run compare(), verify view_diffs populated
 4. Script generation test: Generate backup scripts with include_views=True against a real database, verify CREATE VIEW appears in backup.sql
 5. Frontend test: cd frontend && npx tsc --noEmit — verify no type errors
 6. API test: curl -X POST /api/migration/backup -d '{"connection_id": 1, "include_views": true}' — verify views in output
 7. Run existing tests: ./run_tests.sh — verify nothing regresses