"""Tests for NoSQL DML Generator."""
import json
import pytest
from src.dml.nosql_dml_generator import NoSQLDMLGenerator
from src.dml.models import ChangeType, CellChangeSchema, RowChangeSchema


# ── MongoDB ─────────────────────────────────────────────────────────


class TestMongoDMLGenerator:
    def _gen(self):
        return NoSQLDMLGenerator(database_type="mongodb")

    def test_insert(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "Alice", "email": "a@b.com"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        assert len(stmts) == 1
        s = stmts[0]
        assert s.change_type == ChangeType.INSERT
        assert s.table_name == "users"
        assert "insertOne" in s.display_sql
        assert s.native_operation["method"] == "insert_one"
        assert s.native_operation["document"]["name"] == "Alice"

    def test_update(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={"_id": "abc123"},
                changes=[CellChangeSchema(column="name", old_value="Alice", new_value="Bob")],
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "updateOne" in s.display_sql
        assert s.native_operation["method"] == "update_one"
        assert s.native_operation["filter"] == {"_id": "abc123"}
        assert s.native_operation["update"] == {"$set": {"name": "Bob"}}

    def test_delete(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="users",
                primary_key={"_id": "abc123"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "deleteOne" in s.display_sql
        assert s.native_operation["method"] == "delete_one"
        assert s.native_operation["filter"] == {"_id": "abc123"}

    def test_ordering_delete_before_insert(self):
        changes = [
            RowChangeSchema(change_type=ChangeType.INSERT, table_name="t", new_row_data={"x": 1}),
            RowChangeSchema(change_type=ChangeType.DELETE, table_name="t", primary_key={"_id": "1"}),
        ]
        stmts = self._gen().generate_statements(changes)
        assert stmts[0].change_type == ChangeType.DELETE
        assert stmts[1].change_type == ChangeType.INSERT


# ── Cassandra ──────────────────────────────────────────────────────


class TestCassandraDMLGenerator:
    def _gen(self):
        return NoSQLDMLGenerator(database_type="cassandra")

    def test_insert(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"id": 1, "name": "Alice"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "INSERT INTO users" in s.display_sql
        assert s.native_operation["cql"].startswith("INSERT INTO users")
        assert "%s" in s.native_operation["cql"]
        assert 1 in s.native_operation["params"]

    def test_update(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={"id": 1},
                changes=[CellChangeSchema(column="name", old_value="Alice", new_value="Bob")],
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "UPDATE users SET name" in s.display_sql
        assert "WHERE id" in s.display_sql
        assert s.native_operation["params"] == ["Bob", 1]

    def test_delete(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="users",
                primary_key={"id": 1},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "DELETE FROM users WHERE id" in s.display_sql
        assert s.native_operation["params"] == [1]


# ── DynamoDB ───────────────────────────────────────────────────────


class TestDynamoDBDMLGenerator:
    def _gen(self):
        return NoSQLDMLGenerator(database_type="dynamodb")

    def test_insert(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="Users",
                new_row_data={"pk": "user1", "name": "Alice"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert 'INSERT INTO "Users"' in s.display_sql
        assert s.native_operation["partiql"].startswith('INSERT INTO "Users"')

    def test_update(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="Users",
                primary_key={"pk": "user1"},
                changes=[CellChangeSchema(column="name", old_value="Alice", new_value="Bob")],
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert 'UPDATE "Users"' in s.display_sql
        assert "SET name" in s.display_sql
        assert "WHERE pk" in s.display_sql

    def test_delete(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="Users",
                primary_key={"pk": "user1"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert 'DELETE FROM "Users"' in s.display_sql


# ── Elasticsearch ──────────────────────────────────────────────────


class TestElasticsearchDMLGenerator:
    def _gen(self):
        return NoSQLDMLGenerator(database_type="elasticsearch")

    def test_insert(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="users",
                new_row_data={"name": "Alice", "age": 30},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "POST /users/_doc" in s.display_sql
        assert s.native_operation["method"] == "index"
        assert s.native_operation["body"]["name"] == "Alice"

    def test_update(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="users",
                primary_key={"_id": "doc1"},
                changes=[CellChangeSchema(column="name", old_value="Alice", new_value="Bob")],
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "POST /users/_update/doc1" in s.display_sql
        assert s.native_operation["method"] == "update"
        assert s.native_operation["id"] == "doc1"
        assert s.native_operation["body"] == {"doc": {"name": "Bob"}}

    def test_delete(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="users",
                primary_key={"_id": "doc1"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "DELETE /users/_doc/doc1" in s.display_sql
        assert s.native_operation["method"] == "delete"


# ── Redis ──────────────────────────────────────────────────────────


class TestRedisDMLGenerator:
    def _gen(self):
        return NoSQLDMLGenerator(database_type="redis")

    def test_insert_hash(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.INSERT,
                table_name="user:1",
                new_row_data={"name": "Alice", "age": "30"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "HSET user:1" in s.display_sql
        assert s.native_operation["command"] == "HSET"
        assert s.native_operation["mapping"]["name"] == "Alice"

    def test_update_hash(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.UPDATE,
                table_name="user:1",
                primary_key={"key": "user:1"},
                changes=[CellChangeSchema(column="name", old_value="Alice", new_value="Bob")],
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "HSET user:1" in s.display_sql
        assert s.native_operation["mapping"]["name"] == "Bob"

    def test_delete_field(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="user:1",
                primary_key={"key": "user:1"},
                changes=[CellChangeSchema(column="name", old_value="Alice")],
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "HDEL user:1" in s.display_sql
        assert s.native_operation["command"] == "HDEL"
        assert s.native_operation["fields"] == ["name"]

    def test_delete_key(self):
        changes = [
            RowChangeSchema(
                change_type=ChangeType.DELETE,
                table_name="user:1",
                primary_key={"key": "user:1"},
            )
        ]
        stmts = self._gen().generate_statements(changes)
        s = stmts[0]
        assert "DEL user:1" in s.display_sql
        assert s.native_operation["command"] == "DEL"


# ── Unsupported type ───────────────────────────────────────────────


class TestUnsupportedType:
    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported NoSQL"):
            NoSQLDMLGenerator(database_type="neo4j")


# ── Preview script ─────────────────────────────────────────────────


class TestPreviewScript:
    def test_preview_joins_statements(self):
        gen = NoSQLDMLGenerator(database_type="mongodb")
        changes = [
            RowChangeSchema(change_type=ChangeType.INSERT, table_name="t", new_row_data={"x": 1}),
            RowChangeSchema(change_type=ChangeType.DELETE, table_name="t", primary_key={"_id": "1"}),
        ]
        preview = gen.generate_preview_script(changes)
        assert "deleteOne" in preview
        assert "insertOne" in preview
        # DELETE should come before INSERT in preview
        del_pos = preview.index("deleteOne")
        ins_pos = preview.index("insertOne")
        assert del_pos < ins_pos
