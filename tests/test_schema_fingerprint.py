"""
Tests for schema cache fingerprinting

These tests verify that schema fingerprinting correctly detects database
structure changes and invalidates stale cache entries.
"""
import pytest
from src.core.schema_cache import SchemaCache


class TestSchemaFingerprint:
    """Test schema fingerprint creation and comparison"""

    def test_same_schema_same_fingerprint(self):
        """Identical schemas should produce identical fingerprints"""
        schema1 = {
            "tables": {
                "orders": {
                    "columns": [
                        {"name": "order_id"},
                        {"name": "customer_id"},
                        {"name": "total_amount"},
                        {"name": "status"}
                    ]
                }
            }
        }
        schema2 = {
            "tables": {
                "orders": {
                    "columns": [
                        {"name": "order_id"},
                        {"name": "customer_id"},
                        {"name": "total_amount"},
                        {"name": "status"}
                    ]
                }
            }
        }

        fp1 = SchemaCache.create_fingerprint_from_schema_dict(schema1)
        fp2 = SchemaCache.create_fingerprint_from_schema_dict(schema2)

        assert fp1 == fp2
        assert len(fp1) == 16  # 16-char hex fingerprint

    def test_different_tables_different_fingerprint(self):
        """Adding/removing tables should change fingerprint"""
        schema_orders_only = {
            "tables": {
                "orders": {
                    "columns": [{"name": "order_id"}, {"name": "customer_id"}]
                }
            }
        }
        schema_with_customers = {
            "tables": {
                "orders": {
                    "columns": [{"name": "order_id"}, {"name": "customer_id"}]
                },
                "customers": {
                    "columns": [{"name": "id"}, {"name": "name"}, {"name": "state"}]
                }
            }
        }

        fp1 = SchemaCache.create_fingerprint_from_schema_dict(schema_orders_only)
        fp2 = SchemaCache.create_fingerprint_from_schema_dict(schema_with_customers)

        assert fp1 != fp2

    def test_different_columns_different_fingerprint(self):
        """Adding/removing columns should change fingerprint"""
        schema_without_state = {
            "tables": {
                "customers": {
                    "columns": [{"name": "id"}, {"name": "name"}]
                }
            }
        }
        schema_with_state = {
            "tables": {
                "customers": {
                    "columns": [{"name": "id"}, {"name": "name"}, {"name": "state"}]
                }
            }
        }

        fp1 = SchemaCache.create_fingerprint_from_schema_dict(schema_without_state)
        fp2 = SchemaCache.create_fingerprint_from_schema_dict(schema_with_state)

        assert fp1 != fp2

    def test_column_order_independent(self):
        """Column order shouldn't affect fingerprint"""
        schema1 = {
            "tables": {
                "orders": {
                    "columns": [
                        {"name": "order_id"},
                        {"name": "customer_id"},
                        {"name": "status"}
                    ]
                }
            }
        }
        schema2 = {
            "tables": {
                "orders": {
                    "columns": [
                        {"name": "status"},
                        {"name": "order_id"},
                        {"name": "customer_id"}
                    ]
                }
            }
        }

        fp1 = SchemaCache.create_fingerprint_from_schema_dict(schema1)
        fp2 = SchemaCache.create_fingerprint_from_schema_dict(schema2)

        assert fp1 == fp2

    def test_table_order_independent(self):
        """Table order shouldn't affect fingerprint"""
        schema1 = {
            "tables": {
                "orders": {"columns": [{"name": "id"}]},
                "customers": {"columns": [{"name": "id"}]}
            }
        }
        schema2 = {
            "tables": {
                "customers": {"columns": [{"name": "id"}]},
                "orders": {"columns": [{"name": "id"}]}
            }
        }

        fp1 = SchemaCache.create_fingerprint_from_schema_dict(schema1)
        fp2 = SchemaCache.create_fingerprint_from_schema_dict(schema2)

        assert fp1 == fp2

    def test_empty_schema_fingerprint(self):
        """Empty schema should produce valid fingerprint"""
        schema = {"tables": {}}

        fp = SchemaCache.create_fingerprint_from_schema_dict(schema)

        assert fp is not None
        assert len(fp) == 16

    def test_renamed_column_different_fingerprint(self):
        """Renaming a column should change fingerprint"""
        schema_old = {
            "tables": {
                "orders": {
                    "columns": [{"name": "order_id"}, {"name": "cust_id"}]
                }
            }
        }
        schema_new = {
            "tables": {
                "orders": {
                    "columns": [{"name": "order_id"}, {"name": "customer_id"}]
                }
            }
        }

        fp1 = SchemaCache.create_fingerprint_from_schema_dict(schema_old)
        fp2 = SchemaCache.create_fingerprint_from_schema_dict(schema_new)

        assert fp1 != fp2


class TestSchemaCacheInvalidation:
    """Test that cache invalidation clears both schema and fingerprint"""

    def test_invalidate_clears_fingerprint_pattern(self):
        """invalidate_schema should clear fingerprint keys too"""
        from src.llm.mapping_cache import get_mapping_cache

        cache = get_mapping_cache()

        # Set up test data
        cache.set("schema:123:test_db", {"tables": {}}, ttl=300)
        cache.set("schema_fp:123:test_db", "abc123", ttl=300)

        # Verify data exists
        assert cache.get("schema:123:test_db") is not None
        assert cache.get("schema_fp:123:test_db") is not None

        # Invalidate
        SchemaCache.invalidate_schema(connection_id=123, connection_name="test_db")

        # Both should be gone
        assert cache.get("schema:123:test_db") is None
        assert cache.get("schema_fp:123:test_db") is None
