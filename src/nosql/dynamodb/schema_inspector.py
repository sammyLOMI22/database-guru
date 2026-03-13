"""DynamoDB schema inspector - discovers tables, keys, and sample attributes."""
import logging
from typing import Any, Dict

from src.nosql.base import NoSQLSchemaInspector

logger = logging.getLogger(__name__)

SAMPLE_LIMIT = 50


class DynamoDBSchemaInspector(NoSQLSchemaInspector):
    """Inspect DynamoDB table schemas using describe_table and scan sampling."""

    def __init__(self, session, region: str):
        self.session = session  # aioboto3.Session
        self.region = region

    async def get_schema(self, connection: Any = None) -> Dict[str, Any]:
        """List tables, describe each, sample items for attribute discovery."""
        tables = {}

        async with self.session.client("dynamodb", region_name=self.region) as client:
            # List all tables
            table_names = []
            last_table = None
            while True:
                kwargs = {"Limit": 100}
                if last_table:
                    kwargs["ExclusiveStartTableName"] = last_table
                resp = await client.list_tables(**kwargs)
                table_names.extend(resp.get("TableNames", []))
                last_table = resp.get("LastEvaluatedTableName")
                if not last_table:
                    break

            # Describe each table and sample items
            for table_name in table_names:
                try:
                    tables[table_name] = await self._inspect_table(client, table_name)
                except Exception as e:
                    logger.warning(f"Failed to inspect DynamoDB table {table_name}: {e}")
                    tables[table_name] = {"columns": [], "row_count": 0}

        return {
            "tables": tables,
            "database_type": "dynamodb",
            "region": self.region,
        }

    async def _inspect_table(self, client, table_name: str) -> Dict[str, Any]:
        """Describe a table and sample items for attribute inference."""
        desc = await client.describe_table(TableName=table_name)
        table_desc = desc["Table"]

        # Extract key schema
        key_schema = table_desc.get("KeySchema", [])
        attr_defs = {a["AttributeName"]: a["AttributeType"] for a in table_desc.get("AttributeDefinitions", [])}

        columns = []
        for ks in key_schema:
            name = ks["AttributeName"]
            columns.append({
                "name": name,
                "type": self._dynamo_type_to_str(attr_defs.get(name, "S")),
                "nullable": False,
                "kind": ks["KeyType"].lower(),  # HASH or RANGE
            })

        # Sample items for additional attribute discovery
        try:
            scan_resp = await client.scan(TableName=table_name, Limit=SAMPLE_LIMIT)
            items = scan_resp.get("Items", [])
            known_names = {c["name"] for c in columns}

            attr_types: Dict[str, set] = {}
            for item in items:
                for attr_name, attr_val in item.items():
                    if attr_name not in known_names:
                        dynamo_type = list(attr_val.keys())[0] if isinstance(attr_val, dict) else "S"
                        if attr_name not in attr_types:
                            attr_types[attr_name] = set()
                        attr_types[attr_name].add(dynamo_type)

            for attr_name, types in sorted(attr_types.items()):
                primary_type = types.pop() if len(types) == 1 else "mixed"
                columns.append({
                    "name": attr_name,
                    "type": self._dynamo_type_to_str(primary_type),
                    "nullable": True,
                    "kind": "regular",
                })
        except Exception as e:
            logger.warning(f"Failed to sample DynamoDB table {table_name}: {e}")

        item_count = table_desc.get("ItemCount", 0)

        # GSI info
        gsis = []
        for gsi in table_desc.get("GlobalSecondaryIndexes", []):
            gsi_keys = [k["AttributeName"] for k in gsi.get("KeySchema", [])]
            gsis.append({"name": gsi["IndexName"], "keys": gsi_keys})

        return {
            "columns": columns,
            "row_count": item_count,
            "gsi": gsis,
        }

    def _dynamo_type_to_str(self, dynamo_type: str) -> str:
        type_map = {
            "S": "string", "N": "number", "B": "binary",
            "BOOL": "boolean", "NULL": "null",
            "L": "list", "M": "map",
            "SS": "string_set", "NS": "number_set", "BS": "binary_set",
        }
        return type_map.get(dynamo_type, dynamo_type)

    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Format DynamoDB schema for PartiQL generation prompts."""
        lines = [
            f"DATABASE: Amazon DynamoDB (PartiQL)",
            f"Region: {schema.get('region', 'unknown')}",
            "",
        ]

        for table_name, info in schema.get("tables", {}).items():
            item_count = info.get("row_count", 0)
            lines.append(f"Table: {table_name} (~{item_count} items)")

            columns = info.get("columns", [])
            pk_cols = [c for c in columns if c.get("kind") == "hash"]
            sk_cols = [c for c in columns if c.get("kind") == "range"]
            reg_cols = [c for c in columns if c.get("kind") == "regular"]

            if pk_cols:
                lines.append(f"  Partition Key: {pk_cols[0]['name']} ({pk_cols[0]['type']})")
            if sk_cols:
                lines.append(f"  Sort Key: {sk_cols[0]['name']} ({sk_cols[0]['type']})")
            if reg_cols:
                lines.append("  Attributes:")
                for col in reg_cols[:20]:  # Limit attribute list
                    lines.append(f"    - {col['name']}: {col['type']}")

            gsis = info.get("gsi", [])
            if gsis:
                lines.append("  GSIs:")
                for gsi in gsis:
                    lines.append(f"    - {gsi['name']}: keys={gsi['keys']}")
            lines.append("")

        lines.append("PartiQL Notes:")
        lines.append("- Use SELECT * FROM \"TableName\" WHERE pk = 'value'")
        lines.append("- Table names must be double-quoted")
        lines.append("- Include partition key in WHERE clause")
        lines.append("- No JOIN, no subqueries")

        return "\n".join(lines)
