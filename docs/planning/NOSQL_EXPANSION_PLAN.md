# NoSQL Database Expansion Plan

## Overview

This document outlines the plan for expanding Database Guru's support for NoSQL databases, enabling users to query document stores, key-value stores, wide-column stores, and search engines using natural language.

**Status**: Planning
**Priority**: MEDIUM
**Estimated Effort**: ~6,000 lines of code
**Est. Duration**: 6-8 weeks

---

## Goals

1. **MongoDB Support** - Full MQL generation, aggregation pipelines, document queries
2. **Redis Support** - Key-value operations, data structure commands, search
3. **Cassandra Support** - CQL generation for wide-column queries
4. **DynamoDB Support** - AWS NoSQL with PartiQL and native API
5. **Elasticsearch Support** - Search queries, aggregations, analytics
6. **Unified Interface** - Natural language works across all NoSQL types

---

## Current State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CURRENT NOSQL SUPPORT                             │
└─────────────────────────────────────────────────────────────────────────────┘

  Database        Connection    Query Support    Status
  ─────────────────────────────────────────────────────────
  MongoDB         ✅ Yes        ❌ No            NotImplementedError
  Redis           ❌ No         ❌ No            Not started
  Cassandra       ❌ No         ❌ No            Not started
  DynamoDB        ❌ No         ❌ No            Not started
  Elasticsearch   ❌ No         ❌ No            Not started
```

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NOSQL QUERY ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                         Natural Language Query
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   NoSQL Query Router    │
                    │                         │
                    │  • Detect database type │
                    │  • Route to generator   │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │            │           │           │            │
        ▼            ▼           ▼           ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ MongoDB  │ │  Redis   │ │Cassandra │ │ DynamoDB │ │  Elastic │
  │ MQL Gen  │ │ Cmd Gen  │ │ CQL Gen  │ │PartiQL/  │ │ DSL Gen  │
  │          │ │          │ │          │ │ API Gen  │ │          │
  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
       │            │            │            │            │
       ▼            ▼            ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ pymongo  │ │  redis   │ │cassandra │ │  boto3   │ │elastic-  │
  │          │ │          │ │ -driver  │ │          │ │ search   │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## NoSQL Database Comparison

| Database | Query Language | Data Model | Best For |
|----------|---------------|------------|----------|
| **MongoDB** | MQL (JSON-like) | Document | Flexible schemas, nested data |
| **Redis** | Commands | Key-Value + Data Structures | Caching, real-time, queues |
| **Cassandra** | CQL (SQL-like) | Wide-Column | Time series, high write throughput |
| **DynamoDB** | PartiQL / API | Key-Value + Document | Serverless, AWS integration |
| **Elasticsearch** | Query DSL (JSON) | Document (search-optimized) | Full-text search, analytics |

---

## Phase 18.1: MongoDB Support (~1,500 lines)

### MongoDB Query Language (MQL)

MongoDB uses JSON-like query syntax with operators:

```javascript
// Find documents
db.users.find({ status: "active", age: { $gte: 21 } })

// Aggregation pipeline
db.orders.aggregate([
  { $match: { status: "completed" } },
  { $group: { _id: "$customer_id", total: { $sum: "$amount" } } },
  { $sort: { total: -1 } },
  { $limit: 10 }
])

// Update documents
db.users.updateMany(
  { status: "pending" },
  { $set: { status: "active" } }
)
```

### Natural Language to MQL Examples

| Natural Language | Generated MQL |
|-----------------|---------------|
| "Find all active users" | `db.users.find({ status: "active" })` |
| "Show orders over $100 from last month" | `db.orders.find({ amount: { $gt: 100 }, date: { $gte: ISODate("...") } })` |
| "Top 10 customers by total spending" | Aggregation pipeline with $group, $sort, $limit |
| "Count products by category" | `db.products.aggregate([{ $group: { _id: "$category", count: { $sum: 1 } } }])` |
| "Update all expired subscriptions to inactive" | `db.subscriptions.updateMany({ expiry: { $lt: new Date() } }, { $set: { status: "inactive" } })` |

### MongoDB Components

```python
# src/nosql/mongodb/
├── __init__.py
├── mql_generator.py       # Natural language to MQL
├── schema_inspector.py    # Infer schema from documents
├── aggregation_builder.py # Build aggregation pipelines
├── query_executor.py      # Execute queries via pymongo
└── result_formatter.py    # Format results for display
```

#### MQL Generator

```python
# src/nosql/mongodb/mql_generator.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.llm.ollama_client import OllamaClient


class MQLOperationType(str, Enum):
    FIND = "find"
    FIND_ONE = "findOne"
    AGGREGATE = "aggregate"
    COUNT = "count"
    DISTINCT = "distinct"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class MQLQuery:
    """Represents a generated MongoDB query."""
    operation: MQLOperationType
    collection: str
    query: Dict[str, Any]           # Filter/match conditions
    projection: Optional[Dict] = None
    pipeline: Optional[List[Dict]] = None  # For aggregations
    sort: Optional[Dict] = None
    limit: Optional[int] = None
    skip: Optional[int] = None
    update: Optional[Dict] = None   # For update operations


class MQLGenerator:
    """
    Generates MongoDB Query Language (MQL) from natural language.
    """

    SYSTEM_PROMPT = """You are a MongoDB query generator. Convert natural language
queries into MongoDB Query Language (MQL).

Rules:
1. Use proper MongoDB operators ($eq, $gt, $gte, $lt, $lte, $in, $regex, etc.)
2. For complex queries, use aggregation pipelines
3. Handle date comparisons with ISODate()
4. Use proper projection to limit returned fields when appropriate
5. Include sort, limit, skip when the query implies ordering or pagination

Schema context will be provided. Generate valid MQL for the specified collection.

Return JSON format:
{
    "operation": "find|findOne|aggregate|count|distinct",
    "collection": "collection_name",
    "query": { ... },
    "projection": { ... } or null,
    "pipeline": [ ... ] or null,
    "sort": { ... } or null,
    "limit": number or null,
    "explanation": "Brief explanation of the query"
}"""

    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    async def generate(
        self,
        natural_language: str,
        collection: str,
        schema: Optional[Dict] = None,
        sample_documents: Optional[List[Dict]] = None,
    ) -> MQLQuery:
        """Generate MQL from natural language."""

        schema_context = self._format_schema(schema, sample_documents)

        prompt = f"""
{self.SYSTEM_PROMPT}

Collection: {collection}

Schema/Sample Documents:
{schema_context}

User Query: {natural_language}

Generate the MongoDB query:
"""

        response = await self.ollama.generate(prompt, temperature=0.1)
        return self._parse_response(response)

    async def generate_aggregation(
        self,
        natural_language: str,
        collection: str,
        schema: Optional[Dict] = None,
    ) -> List[Dict]:
        """Generate aggregation pipeline from natural language."""

        prompt = f"""
Generate a MongoDB aggregation pipeline for:
"{natural_language}"

Collection: {collection}
Schema: {self._format_schema(schema)}

Return only the pipeline array as valid JSON:
[
  {{ "$match": {{ ... }} }},
  {{ "$group": {{ ... }} }},
  ...
]
"""

        response = await self.ollama.generate(prompt, temperature=0.1)
        return self._parse_pipeline(response)

    def _format_schema(
        self,
        schema: Optional[Dict],
        samples: Optional[List[Dict]] = None
    ) -> str:
        """Format schema information for prompt."""
        if schema:
            return f"Schema: {schema}"
        elif samples:
            # Infer schema from samples
            return f"Sample documents:\n{samples[:3]}"
        return "Schema not available - infer from query context"

    def _parse_response(self, response: str) -> MQLQuery:
        """Parse LLM response into MQLQuery."""
        import json

        # Extract JSON from response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"Could not parse MQL response: {response}")

        return MQLQuery(
            operation=MQLOperationType(data.get("operation", "find")),
            collection=data.get("collection", ""),
            query=data.get("query", {}),
            projection=data.get("projection"),
            pipeline=data.get("pipeline"),
            sort=data.get("sort"),
            limit=data.get("limit"),
            skip=data.get("skip"),
        )
```

#### Schema Inspector

```python
# src/nosql/mongodb/schema_inspector.py

from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from pymongo.database import Database


class MongoSchemaInspector:
    """
    Infers schema from MongoDB collections by sampling documents.
    """

    def __init__(self, client: MongoClient, database: str):
        self.client = client
        self.db: Database = client[database]

    async def get_collections(self) -> List[str]:
        """Get list of collections in the database."""
        return self.db.list_collection_names()

    async def infer_schema(
        self,
        collection: str,
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """
        Infer schema by sampling documents from collection.

        Returns schema with field names, types, and example values.
        """
        coll = self.db[collection]

        # Sample documents
        samples = list(coll.aggregate([
            {"$sample": {"size": sample_size}}
        ]))

        if not samples:
            return {"fields": [], "sample_count": 0}

        # Analyze field types across samples
        field_info = {}

        for doc in samples:
            self._analyze_document(doc, field_info, prefix="")

        # Convert to schema format
        schema = {
            "collection": collection,
            "document_count": coll.estimated_document_count(),
            "sample_size": len(samples),
            "fields": [
                {
                    "name": name,
                    "types": list(info["types"]),
                    "nullable": info["null_count"] > 0,
                    "example": info.get("example"),
                }
                for name, info in field_info.items()
            ]
        }

        return schema

    def _analyze_document(
        self,
        doc: Dict,
        field_info: Dict,
        prefix: str
    ):
        """Recursively analyze document fields."""
        for key, value in doc.items():
            field_name = f"{prefix}{key}" if prefix else key

            if field_name not in field_info:
                field_info[field_name] = {
                    "types": set(),
                    "null_count": 0,
                    "example": None,
                }

            info = field_info[field_name]

            if value is None:
                info["null_count"] += 1
                info["types"].add("null")
            else:
                type_name = type(value).__name__
                info["types"].add(type_name)

                if info["example"] is None and value is not None:
                    info["example"] = value

                # Recurse into nested documents
                if isinstance(value, dict):
                    self._analyze_document(value, field_info, f"{field_name}.")

    async def get_indexes(self, collection: str) -> List[Dict]:
        """Get indexes for a collection."""
        coll = self.db[collection]
        return list(coll.index_information().values())

    async def get_sample_documents(
        self,
        collection: str,
        count: int = 5
    ) -> List[Dict]:
        """Get sample documents for context."""
        coll = self.db[collection]
        return list(coll.find().limit(count))
```

#### Query Executor

```python
# src/nosql/mongodb/query_executor.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import time

from src.nosql.mongodb.mql_generator import MQLQuery, MQLOperationType


@dataclass
class MongoQueryResult:
    """Result of a MongoDB query execution."""
    success: bool
    documents: List[Dict[str, Any]]
    count: int
    execution_time_ms: float
    error_message: Optional[str] = None
    query_stats: Optional[Dict] = None


class MongoQueryExecutor:
    """
    Executes MongoDB queries safely.
    """

    def __init__(self, client: MongoClient, database: str):
        self.client = client
        self.db = client[database]

    async def execute(
        self,
        query: MQLQuery,
        max_documents: int = 1000,
    ) -> MongoQueryResult:
        """Execute a MongoDB query."""
        start_time = time.time()

        try:
            collection = self.db[query.collection]

            if query.operation == MQLOperationType.FIND:
                result = await self._execute_find(collection, query, max_documents)
            elif query.operation == MQLOperationType.FIND_ONE:
                result = await self._execute_find_one(collection, query)
            elif query.operation == MQLOperationType.AGGREGATE:
                result = await self._execute_aggregate(collection, query, max_documents)
            elif query.operation == MQLOperationType.COUNT:
                result = await self._execute_count(collection, query)
            elif query.operation == MQLOperationType.DISTINCT:
                result = await self._execute_distinct(collection, query)
            else:
                raise ValueError(f"Unsupported operation: {query.operation}")

            execution_time = (time.time() - start_time) * 1000

            return MongoQueryResult(
                success=True,
                documents=result,
                count=len(result),
                execution_time_ms=execution_time,
            )

        except PyMongoError as e:
            return MongoQueryResult(
                success=False,
                documents=[],
                count=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )

    async def _execute_find(
        self,
        collection,
        query: MQLQuery,
        max_documents: int
    ) -> List[Dict]:
        """Execute find query."""
        cursor = collection.find(
            query.query,
            query.projection
        )

        if query.sort:
            cursor = cursor.sort(list(query.sort.items()))
        if query.skip:
            cursor = cursor.skip(query.skip)

        limit = min(query.limit or max_documents, max_documents)
        cursor = cursor.limit(limit)

        return list(cursor)

    async def _execute_find_one(
        self,
        collection,
        query: MQLQuery
    ) -> List[Dict]:
        """Execute findOne query."""
        doc = collection.find_one(query.query, query.projection)
        return [doc] if doc else []

    async def _execute_aggregate(
        self,
        collection,
        query: MQLQuery,
        max_documents: int
    ) -> List[Dict]:
        """Execute aggregation pipeline."""
        pipeline = query.pipeline or []

        # Add limit if not present
        has_limit = any("$limit" in stage for stage in pipeline)
        if not has_limit:
            pipeline.append({"$limit": max_documents})

        return list(collection.aggregate(pipeline))

    async def _execute_count(
        self,
        collection,
        query: MQLQuery
    ) -> List[Dict]:
        """Execute count query."""
        count = collection.count_documents(query.query)
        return [{"count": count}]

    async def _execute_distinct(
        self,
        collection,
        query: MQLQuery
    ) -> List[Dict]:
        """Execute distinct query."""
        field = query.projection.get("field") if query.projection else "_id"
        values = collection.distinct(field, query.query)
        return [{"field": field, "values": values, "count": len(values)}]
```

---

## Phase 18.2: Redis Support (~1,000 lines)

### Redis Command Generation

Redis uses commands rather than queries:

```redis
# String operations
GET user:1001:name
SET user:1001:status "active"
MGET user:1001:name user:1001:email

# Hash operations
HGETALL user:1001
HGET user:1001 email
HMSET user:1001 name "John" status "active"

# List operations
LRANGE recent_orders 0 9
LPUSH notifications "New message"

# Set operations
SMEMBERS user:1001:roles
SINTER premium_users active_users

# Sorted set operations
ZRANGE leaderboard 0 9 WITHSCORES
ZRANGEBYSCORE orders_by_date 1704067200 1706745600

# Search (RediSearch)
FT.SEARCH idx:products "@category:{electronics} @price:[0 100]"
```

### Natural Language to Redis Examples

| Natural Language | Generated Redis Command |
|-----------------|------------------------|
| "Get user 1001's profile" | `HGETALL user:1001` |
| "Show last 10 orders" | `LRANGE recent_orders 0 9` |
| "Top 10 on leaderboard" | `ZREVRANGE leaderboard 0 9 WITHSCORES` |
| "Find all active premium users" | `SINTER premium_users active_users` |
| "Search products under $100 in electronics" | `FT.SEARCH idx:products "@category:{electronics} @price:[0 100]"` |

### Redis Components

```python
# src/nosql/redis/
├── __init__.py
├── command_generator.py   # Natural language to Redis commands
├── key_pattern_analyzer.py # Analyze key naming patterns
├── data_type_detector.py  # Detect value types (string, hash, list, etc.)
├── command_executor.py    # Execute commands via redis-py
└── result_formatter.py    # Format results for display
```

#### Command Generator

```python
# src/nosql/redis/command_generator.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class RedisDataType(str, Enum):
    STRING = "string"
    HASH = "hash"
    LIST = "list"
    SET = "set"
    ZSET = "zset"
    STREAM = "stream"
    JSON = "json"


@dataclass
class RedisCommand:
    """Represents a Redis command."""
    command: str
    args: List[str]
    data_type: RedisDataType
    is_write: bool = False

    def to_string(self) -> str:
        """Convert to Redis command string."""
        return f"{self.command} {' '.join(self.args)}"


class RedisCommandGenerator:
    """
    Generates Redis commands from natural language.
    """

    SYSTEM_PROMPT = """You are a Redis command generator. Convert natural language
into Redis commands.

Rules:
1. Identify the data type (string, hash, list, set, sorted set, stream)
2. Use appropriate commands (GET, HGETALL, LRANGE, SMEMBERS, ZRANGE, etc.)
3. Handle key patterns (user:*, order:*, etc.)
4. For searches, use RediSearch FT.SEARCH syntax if available
5. Be mindful of read vs write operations

Key patterns in this database:
{key_patterns}

Return JSON:
{{
    "command": "COMMAND_NAME",
    "args": ["arg1", "arg2"],
    "data_type": "string|hash|list|set|zset",
    "is_write": false,
    "explanation": "What this command does"
}}"""

    def __init__(self, ollama_client, key_patterns: Optional[Dict] = None):
        self.ollama = ollama_client
        self.key_patterns = key_patterns or {}

    async def generate(
        self,
        natural_language: str,
        context: Optional[Dict] = None,
    ) -> RedisCommand:
        """Generate Redis command from natural language."""

        prompt = f"""
{self.SYSTEM_PROMPT.format(key_patterns=self.key_patterns)}

User Query: {natural_language}

Generate the Redis command:
"""

        response = await self.ollama.generate(prompt, temperature=0.1)
        return self._parse_response(response)

    def _parse_response(self, response: str) -> RedisCommand:
        """Parse LLM response into RedisCommand."""
        import json

        data = json.loads(response)

        return RedisCommand(
            command=data["command"],
            args=data["args"],
            data_type=RedisDataType(data["data_type"]),
            is_write=data.get("is_write", False),
        )
```

---

## Phase 18.3: Cassandra Support (~1,000 lines)

### Cassandra Query Language (CQL)

CQL is SQL-like but with NoSQL constraints:

```sql
-- Select queries
SELECT * FROM users WHERE user_id = 123;
SELECT * FROM events WHERE date = '2024-01-15' AND hour >= 10;

-- Aggregations (limited)
SELECT COUNT(*) FROM orders WHERE status = 'completed';

-- Time-series queries
SELECT * FROM sensor_data
WHERE sensor_id = 'temp-001'
AND timestamp >= '2024-01-01'
AND timestamp < '2024-02-01';

-- Allow filtering (use with caution)
SELECT * FROM products WHERE category = 'electronics' ALLOW FILTERING;
```

### Natural Language to CQL Examples

| Natural Language | Generated CQL |
|-----------------|---------------|
| "Get user 123's profile" | `SELECT * FROM users WHERE user_id = 123` |
| "Show today's events after 10am" | `SELECT * FROM events WHERE date = '...' AND hour >= 10` |
| "Temperature readings for sensor temp-001 in January" | Time-series query with timestamp range |
| "Count completed orders" | `SELECT COUNT(*) FROM orders WHERE status = 'completed'` |

### Cassandra Components

```python
# src/nosql/cassandra/
├── __init__.py
├── cql_generator.py       # Natural language to CQL
├── schema_inspector.py    # Get keyspace/table info
├── partition_analyzer.py  # Analyze partition keys for efficient queries
├── query_executor.py      # Execute via cassandra-driver
└── result_formatter.py
```

---

## Phase 18.4: DynamoDB Support (~1,200 lines)

### DynamoDB Query Methods

DynamoDB supports multiple query approaches:

```python
# PartiQL (SQL-like)
SELECT * FROM Users WHERE pk = 'USER#123'
SELECT * FROM Orders WHERE pk = 'ORDER#2024' AND sk BEGINS_WITH 'ITEM#'

# Native API (Query)
table.query(
    KeyConditionExpression=Key('pk').eq('USER#123'),
    FilterExpression=Attr('status').eq('active')
)

# Native API (Scan with filter)
table.scan(
    FilterExpression=Attr('category').eq('electronics')
)

# GSI Query
table.query(
    IndexName='status-index',
    KeyConditionExpression=Key('status').eq('active')
)
```

### Natural Language to DynamoDB Examples

| Natural Language | Generated Query |
|-----------------|-----------------|
| "Get user 123" | `SELECT * FROM Users WHERE pk = 'USER#123'` |
| "All orders for customer 456" | Query on GSI or begins_with on sort key |
| "Active users created this month" | GSI query + filter expression |
| "Products in electronics category" | Scan with filter (warn about cost) |

### DynamoDB Components

```python
# src/nosql/dynamodb/
├── __init__.py
├── partiql_generator.py   # Natural language to PartiQL
├── api_generator.py       # Generate boto3 query/scan calls
├── table_analyzer.py      # Analyze table structure, GSIs
├── query_optimizer.py     # Choose best access pattern
├── query_executor.py      # Execute via boto3
└── cost_estimator.py      # Estimate RCU cost
```

---

## Phase 18.5: Elasticsearch Support (~1,300 lines)

### Elasticsearch Query DSL

```json
// Match query
{
  "query": {
    "match": { "title": "database guru" }
  }
}

// Bool query with filters
{
  "query": {
    "bool": {
      "must": [
        { "match": { "category": "technology" } }
      ],
      "filter": [
        { "range": { "price": { "lte": 100 } } },
        { "term": { "in_stock": true } }
      ]
    }
  }
}

// Aggregations
{
  "aggs": {
    "by_category": {
      "terms": { "field": "category.keyword" },
      "aggs": {
        "avg_price": { "avg": { "field": "price" } }
      }
    }
  }
}
```

### Natural Language to Elasticsearch Examples

| Natural Language | Generated Query |
|-----------------|-----------------|
| "Search for database tutorials" | Match query on title/content |
| "Products under $100 in stock" | Bool query with range and term filters |
| "Average price by category" | Terms aggregation with avg sub-aggregation |
| "Recent articles about AI" | Bool with match + date range |

### Elasticsearch Components

```python
# src/nosql/elasticsearch/
├── __init__.py
├── dsl_generator.py       # Natural language to Query DSL
├── index_analyzer.py      # Analyze mappings and settings
├── aggregation_builder.py # Build aggregation queries
├── query_executor.py      # Execute via elasticsearch-py
└── result_highlighter.py  # Format search results with highlights
```

---

## Unified NoSQL Interface

### Base Classes

```python
# src/nosql/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class NoSQLType(str, Enum):
    MONGODB = "mongodb"
    REDIS = "redis"
    CASSANDRA = "cassandra"
    DYNAMODB = "dynamodb"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class NoSQLQueryResult:
    """Unified result format for all NoSQL queries."""
    success: bool
    data: List[Dict[str, Any]]
    count: int
    execution_time_ms: float
    query_representation: str  # The generated query/command
    database_type: NoSQLType
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class NoSQLQueryGenerator(ABC):
    """Base class for NoSQL query generators."""

    database_type: NoSQLType

    @abstractmethod
    async def generate(
        self,
        natural_language: str,
        collection: str,
        schema: Optional[Dict] = None,
    ) -> Any:
        """Generate database-specific query from natural language."""
        pass


class NoSQLExecutor(ABC):
    """Base class for NoSQL query executors."""

    @abstractmethod
    async def execute(self, query: Any) -> NoSQLQueryResult:
        """Execute the generated query."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is valid."""
        pass


class NoSQLSchemaInspector(ABC):
    """Base class for schema inspection."""

    @abstractmethod
    async def get_collections(self) -> List[str]:
        """Get list of collections/tables/indexes."""
        pass

    @abstractmethod
    async def get_schema(self, collection: str) -> Dict[str, Any]:
        """Get schema/structure for a collection."""
        pass
```

### NoSQL Router

```python
# src/nosql/router.py

from typing import Optional
from src.nosql.base import NoSQLType, NoSQLQueryGenerator, NoSQLExecutor
from src.nosql.mongodb.mql_generator import MQLGenerator
from src.nosql.mongodb.query_executor import MongoQueryExecutor
from src.nosql.redis.command_generator import RedisCommandGenerator
# ... other imports


class NoSQLRouter:
    """
    Routes natural language queries to appropriate NoSQL generators.
    """

    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self._generators = {}
        self._executors = {}

    def register_generator(
        self,
        db_type: NoSQLType,
        generator: NoSQLQueryGenerator
    ):
        """Register a query generator for a database type."""
        self._generators[db_type] = generator

    def register_executor(
        self,
        db_type: NoSQLType,
        executor: NoSQLExecutor
    ):
        """Register an executor for a database type."""
        self._executors[db_type] = executor

    async def generate_and_execute(
        self,
        natural_language: str,
        db_type: NoSQLType,
        collection: str,
        schema: Optional[dict] = None,
    ):
        """Generate query and execute it."""
        generator = self._generators.get(db_type)
        executor = self._executors.get(db_type)

        if not generator or not executor:
            raise ValueError(f"No generator/executor for {db_type}")

        # Generate query
        query = await generator.generate(
            natural_language,
            collection,
            schema,
        )

        # Execute query
        result = await executor.execute(query)

        return result
```

---

## Database Models

```python
# src/database/models.py additions

class NoSQLConnection(Base):
    """NoSQL database connection configuration."""
    __tablename__ = "nosql_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    database_type = Column(String(50), nullable=False)  # mongodb, redis, etc.

    # Connection details
    host = Column(String(255), nullable=False)
    port = Column(Integer)
    database = Column(String(255))  # Database/keyspace name
    username = Column(String(255))
    password_encrypted = Column(Text)

    # Type-specific config
    extra_config = Column(JSON)  # SSL, auth mechanism, etc.

    # AWS-specific (for DynamoDB)
    aws_region = Column(String(50))
    aws_access_key_encrypted = Column(Text)
    aws_secret_key_encrypted = Column(Text)

    # Schema cache
    schema_cache = Column(JSON)
    schema_cached_at = Column(DateTime)

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## API Endpoints

```python
# src/api/endpoints/nosql.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session
from src.nosql.router import NoSQLRouter
from src.nosql.base import NoSQLType

router = APIRouter(prefix="/nosql", tags=["NoSQL"])


@router.post("/query")
async def execute_nosql_query(
    request: NoSQLQueryRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Execute a natural language query against a NoSQL database.
    """
    # Get connection
    connection = await get_nosql_connection(db, request.connection_id)

    # Get router
    router = get_nosql_router(connection)

    # Generate and execute
    result = await router.generate_and_execute(
        natural_language=request.query,
        db_type=NoSQLType(connection.database_type),
        collection=request.collection,
    )

    return {
        "success": result.success,
        "data": result.data,
        "count": result.count,
        "execution_time_ms": result.execution_time_ms,
        "generated_query": result.query_representation,
        "database_type": result.database_type.value,
    }


@router.get("/connections/{connection_id}/collections")
async def list_collections(
    connection_id: int,
    db: AsyncSession = Depends(get_session),
):
    """List collections/tables for a NoSQL connection."""
    connection = await get_nosql_connection(db, connection_id)
    inspector = get_schema_inspector(connection)

    collections = await inspector.get_collections()

    return {"collections": collections}


@router.get("/connections/{connection_id}/schema/{collection}")
async def get_collection_schema(
    connection_id: int,
    collection: str,
    db: AsyncSession = Depends(get_session),
):
    """Get schema/structure for a collection."""
    connection = await get_nosql_connection(db, connection_id)
    inspector = get_schema_inspector(connection)

    schema = await inspector.get_schema(collection)

    return schema


@router.post("/connections")
async def create_nosql_connection(
    request: CreateNoSQLConnectionRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create a new NoSQL database connection."""
    # Validate connection
    # ... test connection ...

    connection = NoSQLConnection(
        name=request.name,
        database_type=request.database_type,
        host=request.host,
        port=request.port,
        database=request.database,
        # ... other fields
    )

    db.add(connection)
    await db.commit()

    return {"id": connection.id, "status": "created"}


@router.post("/connections/{connection_id}/test")
async def test_nosql_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Test a NoSQL connection."""
    connection = await get_nosql_connection(db, connection_id)
    executor = get_executor(connection)

    success = await executor.test_connection()

    return {"connection_id": connection_id, "success": success}
```

---

## Frontend Components

### NoSQL Connection Modal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Add NoSQL Connection                                                 [X]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Database Type                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [MongoDB]  [Redis]  [Cassandra]  [DynamoDB]  [Elasticsearch]        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Connection Name *    [                              ]                      │
│                                                                             │
│  Host *               [  localhost                   ]                      │
│  Port                 [  27017                       ]                      │
│  Database             [  mydb                        ]                      │
│                                                                             │
│  ── Authentication ──────────────────────────────────────────────────────   │
│  Username             [                              ]                      │
│  Password             [  ••••••••                    ]                      │
│                                                                             │
│  ── Advanced ────────────────────────────────────────────────────────────   │
│  ☐ Use SSL/TLS                                                             │
│  ☐ Replica Set       [                              ]                      │
│                                                                             │
│  [Test Connection]                          [Cancel]  [Save Connection]    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### NoSQL Query Interface

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NoSQL Query                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Connection: [MongoDB: Production ▼]    Collection: [users ▼]              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Find all premium users who signed up in the last 30 days            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                       [Ask]                 │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Generated Query (MQL):                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ db.users.find({                                                     │   │
│  │   "subscription": "premium",                                        │   │
│  │   "created_at": { "$gte": ISODate("2024-01-02") }                  │   │
│  │ })                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Results (47 documents)                              Execution: 23ms        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ { "_id": "...", "name": "John Doe", "subscription": "premium", ... }│   │
│  │ { "_id": "...", "name": "Jane Smith", "subscription": "premium", ...│   │
│  │ ...                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 18.1: MongoDB Support (Weeks 1-2)
- [ ] MQL Generator with aggregation support
- [ ] Schema inspector (infer from samples)
- [ ] Query executor with pymongo
- [ ] API endpoints for MongoDB
- [ ] Frontend collection browser
- [ ] Integration tests

### Phase 18.2: Redis Support (Week 3)
- [ ] Command generator for all data types
- [ ] Key pattern analyzer
- [ ] Command executor with redis-py
- [ ] Support for RediSearch (optional)
- [ ] API endpoints for Redis
- [ ] Integration tests

### Phase 18.3: Cassandra Support (Week 4)
- [ ] CQL generator with partition-aware queries
- [ ] Schema inspector for keyspaces/tables
- [ ] Query executor with cassandra-driver
- [ ] Warn about expensive queries (ALLOW FILTERING)
- [ ] API endpoints for Cassandra
- [ ] Integration tests

### Phase 18.4: DynamoDB Support (Weeks 5-6)
- [ ] PartiQL generator
- [ ] Native API generator (boto3)
- [ ] Table analyzer (GSIs, partition keys)
- [ ] Query optimizer (choose best access pattern)
- [ ] Cost estimator (RCU usage)
- [ ] API endpoints for DynamoDB
- [ ] Integration tests

### Phase 18.5: Elasticsearch Support (Weeks 6-7)
- [ ] Query DSL generator
- [ ] Aggregation builder
- [ ] Index analyzer
- [ ] Result highlighter
- [ ] API endpoints for Elasticsearch
- [ ] Integration tests

### Phase 18.6: Frontend & Polish (Week 8)
- [ ] NoSQL connection modal
- [ ] Collection/index browser
- [ ] Query interface with syntax highlighting
- [ ] Result viewers (document, table, JSON)
- [ ] Documentation and user guide

---

## Dependencies

### Python Packages

```
pymongo>=4.6.0           # MongoDB
redis>=5.0.0             # Redis
cassandra-driver>=3.28.0 # Cassandra
boto3>=1.34.0            # DynamoDB
elasticsearch>=8.12.0    # Elasticsearch
```

---

## API Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/nosql/query` | POST | Execute natural language query |
| `/nosql/connections` | GET | List NoSQL connections |
| `/nosql/connections` | POST | Create NoSQL connection |
| `/nosql/connections/{id}` | DELETE | Delete connection |
| `/nosql/connections/{id}/test` | POST | Test connection |
| `/nosql/connections/{id}/collections` | GET | List collections |
| `/nosql/connections/{id}/schema/{coll}` | GET | Get collection schema |

---

## Challenges & Considerations

### 1. Schema-less Nature
- NoSQL databases often don't have fixed schemas
- Need to infer structure from sample documents
- Handle schema variations gracefully

### 2. Query Limitations
- Each NoSQL has different query capabilities
- Some operations require full scans (expensive)
- Need to warn users about costly queries

### 3. Data Model Differences
- Document vs Key-Value vs Wide-Column vs Search
- Natural language needs to map to very different paradigms
- May need to ask clarifying questions

### 4. Aggregations
- Complex aggregations vary significantly by database
- MongoDB pipelines vs Elasticsearch aggregations vs DynamoDB limitations

### 5. Write Operations
- Should integrate with Edit Mode (Phase 17)
- Different syntax for inserts/updates per database

---

## Related Documentation

- [EDIT_MODE_DML_PLAN.md](EDIT_MODE_DML_PLAN.md) - Write operations (will need NoSQL support)
- [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) - LLM providers for query generation
- [MASTER_ROADMAP.md](MASTER_ROADMAP.md) - Overall project roadmap

---

*Document Version: 1.0*
*Created: 2026-02-01*
*Status: Planning*
