NoSQL DML (Edit Mode) Support                                                                                                          
                                                                                                                                        
 Context                                                                                                                                

 Edit mode (Phase 18) currently only works for SQL databases. The frontend gate was removed but the backend still blocks NoSQL at
 DMLValidator line 53-56. The reason it was SQL-only: each NoSQL DB has a completely different write API (MongoDB document ops, Redis
 commands, CQL, PartiQL, ES REST). No shared grammar means we need per-DB write handlers.

 The good news: edit mode sends structured RowChangeSchema (table + primary_key + cell changes), NOT natural language. So we can
 deterministically translate to native write ops — no LLM needed.

 Architecture

 API endpoint (dml.py)
   → DMLValidator (modified: allow NoSQL, add NoSQL-specific checks)
   → SQL path:   DMLGenerator → DMLExecutor         (unchanged)
   → NoSQL path: NoSQLDMLGenerator → NoSQLDMLExecutor (NEW)

 Files to Modify

 ┌──────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │           File           │                                                Change                                                 │
 ├──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ src/dml/dml_validator.py │ Remove NoSQL block (lines 53-56). Add NoSQL identifier regex. Add Redis HASH-type check.              │
 ├──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ src/dml/constants.py     │ Add NOSQL_TYPES set, NOSQL_SAFE_IDENT_RE pattern                                                      │
 ├──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ src/dml/models.py        │ Add native_operation: Optional[Dict] = None to DMLStatement                                           │
 ├──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ src/api/endpoints/dml.py │ Branch preview/execute to NoSQLDMLGenerator/NoSQLDMLExecutor for NoSQL connections. Add NoSQL support │
 │                          │  to table-info endpoint.                                                                              │
 └──────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────┘

 Files to Create

 ┌───────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────┐
 │                 File                  │                                  Purpose                                  │
 ├───────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
 │ src/dml/nosql_dml_generator.py        │ Translates RowChangeSchema → native write ops per DB type                 │
 ├───────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
 │ src/dml/nosql_dml_executor.py         │ Executes native ops using existing client pools, with transaction support │
 ├───────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
 │ tests/dml/test_nosql_dml_generator.py │ Unit tests for all 5 DB generators                                        │
 ├───────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
 │ tests/dml/test_nosql_dml_executor.py  │ Unit tests with mocked client pools                                       │
 └───────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────┘

 Per-DB Write Mapping

 MongoDB

 - INSERT: db.collection.insertOne({...new_row_data})
 - UPDATE: db.collection.updateOne({_id: pk}, {$set: {field: new_val}})
 - DELETE: db.collection.deleteOne({_id: pk})
 - Transaction: start_session() + start_transaction() → full rollback on failure
 - Note: String _id values must be converted to ObjectId when appropriate

 Cassandra

 - INSERT: INSERT INTO table (cols) VALUES (vals) (CQL)
 - UPDATE: UPDATE table SET col = val WHERE pk = pkval
 - DELETE: DELETE FROM table WHERE pk = pkval
 - Transaction: BatchStatement(LOGGED) — atomic within single partition; sequential cross-partition
 - Note: Must validate all partition key columns present in primary_key

 DynamoDB

 - INSERT: INSERT INTO "table" VALUE {'pk': 'val', ...} (PartiQL)
 - UPDATE: UPDATE "table" SET col = 'val' WHERE pk = 'pkval'
 - DELETE: DELETE FROM "table" WHERE pk = 'pkval'
 - Transaction: transact_write_items() for up to 25 items; chunked beyond that
 - Note: PartiQL handles type serialization automatically

 Elasticsearch

 - INSERT: POST /index/_doc with body
 - UPDATE: POST /index/_update/{_id} with {doc: {field: val}}
 - DELETE: DELETE /index/_doc/{_id}
 - Transaction: None — sequential execution, report partial failures
 - Note: _id is always the primary key

 Redis (HASH type only)

 - INSERT: HSET key field1 val1 field2 val2
 - UPDATE: HSET key field new_value
 - DELETE (field): HDEL key field / DELETE (row): DEL key
 - Transaction: MULTI/EXEC pipeline
 - Limitation: Only HASH keys support edit mode. Validator checks key type before allowing writes.

 Preview

 Same DMLPreviewResponse shape — display_sql holds human-readable native syntax (MQL, CQL, PartiQL, REST notation, Redis commands).
 Frontend needs no changes.

 Implementation Order

 1. Extend DMLStatement model with native_operation field
 2. Update constants.py with NoSQL types and identifier regex
 3. Create nosql_dml_generator.py — all 5 DB generators
 4. Create nosql_dml_executor.py — execution with per-DB client pool access
 5. Modify dml_validator.py — remove NoSQL block, add NoSQL-specific validation
 6. Modify dml.py endpoints — add NoSQL branching
 7. Add tests for generator and executor
 8. No frontend changes needed

 Verification

 1. Run existing DML tests: ./run_tests.sh tests/dml/ — must still pass (SQL path unchanged)
 2. Run new tests: pytest tests/dml/test_nosql_dml_generator.py tests/dml/test_nosql_dml_executor.py
 3. Manual: create a MongoDB/SQLite connection, configure write permissions via shield icon, enter edit mode, preview + execute an
 update