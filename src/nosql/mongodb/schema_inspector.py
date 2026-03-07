"""MongoDB schema inspector - infers collection schemas by sampling documents.

Stores results in DatabaseConnection.schema_cache JSON column using the same
format as the SQL SchemaInspector, so downstream code works unchanged.
"""
import logging
from typing import Any, Dict, List, Optional, Set

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.nosql.base import NoSQLSchemaInspector

logger = logging.getLogger(__name__)


class MongoSchemaInspector(NoSQLSchemaInspector):
    """Infer schema from MongoDB collections by sampling documents."""

    def __init__(self, database: AsyncIOMotorDatabase, sample_size: int = 100):
        self.db = database
        self.sample_size = sample_size

    async def get_schema(self, connection: Any = None) -> Dict[str, Any]:
        """Sample documents from all collections and infer field schemas.

        Returns dict compatible with SchemaCache / schema_cache JSON column.
        """
        collections = await self.db.list_collection_names()
        # Filter out system collections
        collections = [c for c in collections if not c.startswith("system.")]

        tables = {}
        for coll_name in collections:
            try:
                coll_schema = await self._inspect_collection(coll_name)
                tables[coll_name] = coll_schema
            except Exception as e:
                logger.warning(f"Failed to inspect collection {coll_name}: {e}")
                tables[coll_name] = {"columns": [], "row_count": 0}

        return {
            "tables": tables,
            "database_type": "mongodb",
        }

    async def _inspect_collection(self, collection_name: str) -> Dict[str, Any]:
        """Inspect a single collection by sampling documents."""
        coll = self.db[collection_name]

        # Get estimated document count
        try:
            doc_count = await coll.estimated_document_count()
        except Exception:
            doc_count = 0

        # Sample documents using $sample aggregation
        samples = []
        try:
            cursor = coll.aggregate([{"$sample": {"size": self.sample_size}}])
            samples = await cursor.to_list(length=self.sample_size)
        except Exception as e:
            logger.warning(f"$sample failed for {collection_name}, trying find(): {e}")
            try:
                cursor = coll.find().limit(self.sample_size)
                samples = await cursor.to_list(length=self.sample_size)
            except Exception:
                pass

        if not samples:
            return {"columns": [], "row_count": doc_count}

        # Analyze field types across all sampled documents
        field_info: Dict[str, Dict[str, Any]] = {}
        for doc in samples:
            self._analyze_document(doc, field_info, prefix="")

        # Count missing fields: for each known field, check how many docs lack it
        all_field_names = set(field_info.keys())
        for doc in samples:
            doc_fields = self._extract_field_names(doc, prefix="")
            for missing_field in all_field_names - doc_fields:
                field_info[missing_field]["missing_count"] += 1

        # Convert to columns format
        columns = []
        for field_name, info in sorted(field_info.items()):
            types = info["types"]
            primary_type = self._pick_primary_type(types)
            columns.append({
                "name": field_name,
                "type": primary_type,
                "nullable": info["null_count"] > 0 or info["missing_count"] > 0,
            })

        return {
            "columns": columns,
            "row_count": doc_count,
        }

    def _analyze_document(
        self,
        doc: Dict,
        field_info: Dict[str, Dict],
        prefix: str,
    ) -> None:
        """Recursively analyze document fields with dot-notation for nested docs."""
        for key, value in doc.items():
            field_name = f"{prefix}{key}" if prefix else key

            if field_name not in field_info:
                field_info[field_name] = {
                    "types": set(),
                    "null_count": 0,
                    "missing_count": 0,
                }

            info = field_info[field_name]

            if value is None:
                info["null_count"] += 1
                info["types"].add("null")
            else:
                type_name = type(value).__name__
                # Normalize type names
                type_map = {
                    "str": "string",
                    "int": "int",
                    "float": "double",
                    "bool": "bool",
                    "list": "array",
                    "dict": "object",
                    "ObjectId": "objectId",
                    "datetime": "date",
                }
                info["types"].add(type_map.get(type_name, type_name))

                # Recurse into nested documents (max 2 levels)
                if isinstance(value, dict) and prefix.count(".") < 2:
                    self._analyze_document(value, field_info, f"{field_name}.")

    def _extract_field_names(self, doc: Dict, prefix: str) -> Set[str]:
        """Extract all dot-notation field names from a document (matching _analyze_document logic)."""
        names: Set[str] = set()
        for key, value in doc.items():
            field_name = f"{prefix}{key}" if prefix else key
            names.add(field_name)
            if isinstance(value, dict) and prefix.count(".") < 2:
                names.update(self._extract_field_names(value, f"{field_name}."))
        return names

    def _pick_primary_type(self, types: Set[str]) -> str:
        """Pick the most representative type from a set of observed types."""
        types_no_null = types - {"null"}
        if not types_no_null:
            return "null"
        if len(types_no_null) == 1:
            return types_no_null.pop()
        # Mixed types - show as "mixed(type1, type2)"
        return f"mixed({', '.join(sorted(types_no_null))})"

    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Convert schema dict to a string suitable for MongoDB MQL generation prompts."""
        lines = ["DATABASE: MongoDB (MQL)", ""]

        tables = schema.get("tables", {})
        for coll_name, coll_info in tables.items():
            doc_count = coll_info.get("row_count", 0)
            lines.append(f"Collection: {coll_name} (~{doc_count} documents)")

            columns = coll_info.get("columns", [])
            if columns:
                lines.append("  Fields:")
                for col in columns:
                    nullable = " (nullable)" if col.get("nullable") else ""
                    lines.append(f"    - {col['name']}: {col['type']}{nullable}")
            lines.append("")

        return "\n".join(lines)
