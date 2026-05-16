# Database Guru — Graph Database Support Spec

## 1. Purpose

Database Guru should support graph databases as a first-class database type, beginning with Neo4j. The feature should help developers connect to graph databases, understand graph structure, visualize connected data, generate and explain graph queries, and receive modeling/performance guidance.

The goal is not to merely add another connector. The goal is to make Database Guru useful for relationship-heavy systems where the most important question is:

> How are these things connected?

## 2. Product Positioning

### Feature Name

**Graph Mode**

### Product Promise

Database Guru Graph Mode helps developers inspect, query, visualize, and improve graph databases using AI-assisted reasoning.

### Primary Value

Graph databases can be difficult to understand because their structure is less obvious than relational tables. Graph Mode turns labels, relationships, properties, and query paths into an understandable visual and conversational workflow.

### Target Users

- Backend engineers working with Neo4j or similar graph databases
- Data engineers building knowledge graphs or recommendation systems
- Security engineers analyzing identity, access, dependency, or risk graphs
- AI engineers building retrieval, memory, or entity relationship systems
- Product engineers debugging relationship-heavy application data

## 3. MVP Scope

The MVP should support **Neo4j only**.

### Included in MVP

1. Neo4j connection management
2. Graph schema introspection
3. Label, relationship, and property discovery
4. AI-generated schema summary
5. Cypher Query Lab
6. Natural-language-to-Cypher query generation
7. Cypher explanation
8. Query execution with safety controls
9. Basic visual graph explorer
10. Modeling and performance recommendations
11. Index and constraint inspection
12. Query history

### Excluded from MVP

- Amazon Neptune support
- Memgraph support
- ArangoDB support
- JanusGraph support
- Gremlin support
- GraphQL generation
- Automatic graph migration tooling
- Production write-query execution without explicit confirmation
- Multi-user collaboration
- Full graph analytics algorithms
- Automated ETL from relational databases into graph databases

## 4. User Stories

### Connection Management

As a developer, I want to connect Database Guru to a Neo4j database so I can inspect and query graph data.

Acceptance criteria:

- User can enter Neo4j connection URI, username, password, and database name.
- User can test the connection before saving.
- Credentials are stored securely.
- Saved connections can be edited or deleted.
- Failed connections return useful error messages.

### Schema Discovery

As a developer, I want Database Guru to discover node labels, relationship types, and properties so I can understand my graph model.

Acceptance criteria:

- App displays all node labels.
- App displays all relationship types.
- App displays relationship patterns such as `(:User)-[:PURCHASED]->(:Product)`.
- App displays common properties per node label and relationship type.
- App displays approximate counts for labels and relationships.
- App warns if graph metadata queries are expensive or incomplete.

### Graph Visualization

As a developer, I want to visually explore the graph so I can understand connected data.

Acceptance criteria:

- User can select a starting node label.
- User can filter by property.
- User can expand relationships from selected nodes.
- User can control traversal depth.
- User can filter relationship types.
- User can click a node to view properties.
- User can click a relationship to view properties.
- App limits result size to prevent UI overload.

### Query Lab

As a developer, I want to write and run Cypher queries so I can inspect graph data.

Acceptance criteria:

- User can write Cypher queries in an editor.
- User can execute read-only queries.
- Results can be displayed as table, JSON, or graph.
- Query execution has timeout and row/node limits.
- Dangerous write queries require explicit confirmation or are blocked in MVP.
- Query errors are explained in plain English.

### AI Query Generation

As a developer, I want to describe a graph question in plain English and have Database Guru generate Cypher.

Acceptance criteria:

- User can enter a plain-English request.
- App uses discovered schema context when generating Cypher.
- Generated query includes an explanation.
- Generated query defaults to read-only unless the user explicitly asks for a write operation.
- App warns when a requested query does not match known schema.

### Query Explanation

As a developer, I want Database Guru to explain Cypher queries so I can understand what they do.

Acceptance criteria:

- User can paste or select a Cypher query.
- App explains matched nodes, relationships, filters, aggregations, and return values.
- App flags likely performance issues.
- App suggests indexes or query rewrites when appropriate.

### Modeling Advisor

As a developer, I want Database Guru to suggest graph modeling improvements so I can avoid bad graph structures.

Acceptance criteria:

- App identifies possible anti-patterns.
- App suggests when data should be a node vs. property vs. relationship.
- App explains recommendations clearly.
- App avoids making schema changes automatically.

## 5. Functional Requirements

## 5.1 Connection Layer

### Supported MVP Database

- Neo4j 5.x compatible server
- Bolt protocol
- Optional encrypted connection support

### Connection Fields

- Connection name
- URI
- Username
- Password
- Database name
- Encryption enabled/disabled
- Read-only mode enabled/disabled

### Connection Security

- Passwords must never be logged.
- Passwords should be encrypted at rest.
- Connection test should avoid mutating data.
- App should support read-only mode by default.

## 5.2 Schema Introspection

The app should run Neo4j metadata queries to gather:

- Node labels
- Relationship types
- Relationship direction patterns
- Property keys per label
- Property keys per relationship type
- Approximate counts
- Indexes
- Constraints

### Example Introspection Queries

```cypher
CALL db.labels();
```

```cypher
CALL db.relationshipTypes();
```

```cypher
CALL db.schema.nodeTypeProperties();
```

```cypher
CALL db.schema.relTypeProperties();
```

```cypher
SHOW INDEXES;
```

```cypher
SHOW CONSTRAINTS;
```

### Relationship Pattern Discovery

The system should detect common relationship patterns using limited sampling.

Example:

```cypher
MATCH (a)-[r]->(b)
RETURN labels(a) AS sourceLabels,
       type(r) AS relationshipType,
       labels(b) AS targetLabels,
       count(*) AS count
ORDER BY count DESC
LIMIT 100;
```

## 5.3 Graph Schema Model

Internally, Database Guru should normalize graph schema into a provider-independent model.

```typescript
export interface GraphSchema {
  provider: 'neo4j';
  databaseName: string;
  labels: GraphNodeLabel[];
  relationships: GraphRelationshipType[];
  patterns: GraphRelationshipPattern[];
  indexes: GraphIndex[];
  constraints: GraphConstraint[];
  collectedAt: string;
}

export interface GraphNodeLabel {
  name: string;
  estimatedCount?: number;
  properties: GraphProperty[];
}

export interface GraphRelationshipType {
  name: string;
  estimatedCount?: number;
  properties: GraphProperty[];
}

export interface GraphRelationshipPattern {
  sourceLabels: string[];
  relationshipType: string;
  targetLabels: string[];
  estimatedCount?: number;
}

export interface GraphProperty {
  name: string;
  types: string[];
  nullable?: boolean;
  indexed?: boolean;
  sampleValues?: unknown[];
}

export interface GraphIndex {
  name: string;
  entityType: 'NODE' | 'RELATIONSHIP';
  labelsOrTypes: string[];
  properties: string[];
  type?: string;
  state?: string;
}

export interface GraphConstraint {
  name: string;
  entityType: 'NODE' | 'RELATIONSHIP';
  labelsOrTypes: string[];
  properties: string[];
  type: string;
}
```

## 5.4 Query Lab

### Query Input

The Query Lab should support:

- Cypher editor
- Syntax highlighting
- Query validation where possible
- Run query button
- Explain query button
- Generate query from prompt
- Save query
- Query history

### Result Views

The user should be able to switch among:

1. Table view
2. JSON view
3. Graph view

### Query Safety

By default, MVP should allow only read queries.

Allowed patterns:

- `MATCH`
- `OPTIONAL MATCH`
- `RETURN`
- `WITH`
- `WHERE`
- `ORDER BY`
- `LIMIT`
- `CALL` for approved metadata procedures

Blocked or confirmation-required patterns:

- `CREATE`
- `MERGE`
- `DELETE`
- `DETACH DELETE`
- `SET`
- `REMOVE`
- `DROP`
- `LOAD CSV`
- `CALL apoc.*` unless explicitly allowed

### Query Execution Limits

Every query should have:

- Timeout limit
- Max records limit
- Max visualized nodes limit
- Max visualized relationships limit
- Optional automatic `LIMIT` injection for generated read queries

## 5.5 AI Features

Graph Mode should use AI only after collecting schema context.

### AI Context Packet

When asking the LLM to generate or explain Cypher, send a compact context packet:

```json
{
  "databaseType": "neo4j",
  "schema": {
    "labels": ["User", "Product", "Category"],
    "relationshipTypes": ["PURCHASED", "VIEWED", "BELONGS_TO"],
    "patterns": [
      "(:User)-[:PURCHASED]->(:Product)",
      "(:Product)-[:BELONGS_TO]->(:Category)"
    ],
    "indexedProperties": [
      "User.email",
      "Product.sku"
    ]
  },
  "safetyMode": "readOnly"
}
```

### AI Query Generation Prompt Behavior

The LLM should:

- Generate Neo4j Cypher only.
- Use only known labels and relationship types when possible.
- Ask for clarification only when the user request cannot map to the known schema.
- Prefer read-only queries.
- Include `LIMIT` by default.
- Explain assumptions.
- Avoid destructive operations.

### AI Query Explanation Behavior

The LLM should explain:

- Starting point of the query
- Node labels involved
- Relationship types involved
- Traversal direction
- Filters
- Aggregations
- Return values
- Performance concerns
- Suggested indexes

## 5.6 Visual Graph Explorer

### Core UI Behaviors

- Select a starting label.
- Search/filter nodes by property.
- Select a node.
- Expand outgoing relationships.
- Expand incoming relationships.
- Expand both directions.
- Limit depth.
- Limit node count.
- Filter relationship type.
- Hide labels.
- Pin nodes.
- Reset graph.

### Visualization Library Options

Recommended options:

- React Flow for controlled graph UI
- Cytoscape.js for graph-specific layout algorithms
- Sigma.js for larger graph rendering
- D3 only if custom behavior is needed

For MVP, **Cytoscape.js** is likely the strongest fit because it is purpose-built for graph visualization.

### Graph View Data Contract

```typescript
export interface GraphVisualizationData {
  nodes: GraphVizNode[];
  edges: GraphVizEdge[];
  truncated: boolean;
  warnings: string[];
}

export interface GraphVizNode {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
  displayName?: string;
}

export interface GraphVizEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}
```

## 6. Non-Functional Requirements

### Performance

- Schema introspection should complete quickly on small-to-medium graphs.
- Expensive operations should use sampling.
- Query execution should support server-side timeout when available.
- Visualization should cap rendered nodes and edges.

### Security

- Store credentials securely.
- Never send passwords to the AI layer.
- Never log full connection strings with credentials.
- Default to read-only query execution.
- Require confirmation for write operations in later versions.

### Reliability

- Connection errors should be readable.
- Query errors should preserve raw database error details and include a plain-English explanation.
- App should fail safely if schema introspection is incomplete.

### Extensibility

The graph support layer should be provider-agnostic internally, even though MVP only supports Neo4j.

Future providers should be added through adapters:

```typescript
export interface GraphDatabaseAdapter {
  provider: GraphProvider;
  testConnection(config: GraphConnectionConfig): Promise<ConnectionTestResult>;
  introspectSchema(connectionId: string): Promise<GraphSchema>;
  executeQuery(connectionId: string, query: GraphQueryRequest): Promise<GraphQueryResult>;
  explainQuery?(connectionId: string, query: string): Promise<GraphQueryPlan>;
}
```

## 7. Suggested Architecture

## 7.1 High-Level Components

```text
Frontend
  ├── Connection Manager
  ├── Graph Schema Explorer
  ├── Visual Graph Explorer
  ├── Cypher Query Lab
  └── Guru Advice Panel

Backend
  ├── Graph Connection Service
  ├── Graph Adapter Interface
  ├── Neo4j Adapter
  ├── Schema Introspection Service
  ├── Query Safety Service
  ├── Query Execution Service
  ├── AI Context Builder
  └── AI Graph Guru Service

Database
  ├── Saved connections
  ├── Cached graph schemas
  ├── Query history
  └── Saved prompts/queries
```

## 7.2 Backend Services

### GraphConnectionService

Responsibilities:

- Create connection
- Test connection
- Update connection
- Delete connection
- Retrieve connection config
- Decrypt credentials at runtime only

### Neo4jGraphAdapter

Responsibilities:

- Connect using Neo4j driver
- Run metadata queries
- Execute Cypher queries
- Normalize Neo4j records into Database Guru result format
- Return visual graph data when nodes/relationships are present

### GraphSchemaService

Responsibilities:

- Trigger schema introspection
- Cache schema snapshots
- Compare schema snapshots later
- Build compact schema summaries for AI

### GraphQuerySafetyService

Responsibilities:

- Classify Cypher as read/write/admin/unknown
- Block disallowed query patterns
- Add defensive limits where appropriate
- Flag risky queries before execution

### GraphGuruAIService

Responsibilities:

- Generate Cypher from natural language
- Explain Cypher
- Summarize schema
- Suggest modeling improvements
- Suggest index improvements

## 8. API Endpoints

Assuming REST API.

### Create Graph Connection

```http
POST /api/graph/connections
```

Request:

```json
{
  "name": "Local Neo4j",
  "provider": "neo4j",
  "uri": "bolt://localhost:7687",
  "username": "neo4j",
  "password": "password",
  "databaseName": "neo4j",
  "encrypted": false,
  "readOnly": true
}
```

### Test Graph Connection

```http
POST /api/graph/connections/test
```

### Introspect Schema

```http
POST /api/graph/connections/{connectionId}/introspect
```

### Get Cached Schema

```http
GET /api/graph/connections/{connectionId}/schema
```

### Execute Query

```http
POST /api/graph/connections/{connectionId}/query
```

Request:

```json
{
  "query": "MATCH (n:User) RETURN n LIMIT 25",
  "params": {},
  "resultMode": "auto",
  "maxRecords": 100,
  "timeoutMs": 5000
}
```

### Generate Cypher

```http
POST /api/graph/connections/{connectionId}/ai/generate-cypher
```

Request:

```json
{
  "prompt": "Show me users who purchased products in the same category more than once.",
  "readOnly": true
}
```

### Explain Cypher

```http
POST /api/graph/connections/{connectionId}/ai/explain-cypher
```

Request:

```json
{
  "query": "MATCH (u:User)-[:PURCHASED]->(p:Product) RETURN u, count(p) LIMIT 25"
}
```

### Get Modeling Advice

```http
POST /api/graph/connections/{connectionId}/ai/modeling-advice
```

## 9. Data Persistence Model

### graph_connections

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| name | text | User-facing name |
| provider | text | `neo4j` for MVP |
| uri | text | Sanitized URI |
| username | text | DB username |
| encrypted_password | text | Encrypted secret |
| database_name | text | Neo4j database |
| encrypted | boolean | Whether Bolt encryption is enabled |
| read_only | boolean | Default true |
| created_at | timestamp | Created timestamp |
| updated_at | timestamp | Updated timestamp |

### graph_schema_snapshots

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| connection_id | uuid | FK to graph_connections |
| schema_json | jsonb | Normalized GraphSchema |
| created_at | timestamp | Collection timestamp |

### graph_query_history

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| connection_id | uuid | FK to graph_connections |
| query | text | Cypher query |
| params_json | jsonb | Query params |
| status | text | success/error/blocked |
| duration_ms | integer | Runtime |
| error_message | text | Nullable |
| created_at | timestamp | Execution timestamp |

### saved_graph_queries

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| connection_id | uuid | FK to graph_connections |
| name | text | Query name |
| description | text | Optional |
| query | text | Cypher query |
| created_at | timestamp | Created timestamp |
| updated_at | timestamp | Updated timestamp |

## 10. UI Specification

## 10.1 Navigation

Graph Mode should appear as a database type or workspace section.

```text
Database Guru
  ├── SQL Connections
  ├── Graph Connections
  │     ├── Overview
  │     ├── Schema
  │     ├── Visual Graph
  │     ├── Query Lab
  │     └── Guru Advice
  └── Settings
```

## 10.2 Connection Screen

Fields:

- Connection name
- Provider dropdown
- URI
- Username
- Password
- Database name
- Encryption toggle
- Read-only mode toggle
- Test connection button
- Save button

## 10.3 Graph Overview Screen

Show:

- Provider
- Database name
- Last introspected date
- Number of labels
- Number of relationship types
- Number of indexes
- Number of constraints
- Top relationship patterns
- AI-generated schema summary

## 10.4 Schema Screen

Sections:

1. Node Labels
2. Relationship Types
3. Relationship Patterns
4. Properties
5. Indexes
6. Constraints

Example display:

```text
(:User)
Properties:
- id: String, indexed
- email: String, unique
- createdAt: DateTime

(:User)-[:PURCHASED]->(:Product)
Estimated count: 92,100
```

## 10.5 Visual Graph Screen

Left panel:

- Starting label selector
- Property filter
- Relationship filter
- Direction selector
- Depth selector
- Node limit
- Run/expand button

Center:

- Interactive graph canvas

Right panel:

- Selected node/relationship details
- Expand controls
- AI explanation of selected subgraph

## 10.6 Query Lab Screen

Top:

- Natural language prompt input
- Generate Cypher button

Middle:

- Cypher editor
- Run button
- Explain button
- Save query button

Bottom:

- Results tabs: Table, JSON, Graph
- Warnings/errors
- AI explanation panel

## 10.7 Guru Advice Screen

Show cards for:

- Modeling suggestions
- Index suggestions
- Query performance suggestions
- Data quality warnings
- Relationship anti-patterns

Example advice card:

```text
Possible high-degree node issue

Some Product nodes may have thousands of incoming VIEWED relationships. Queries that expand from Product to User could become expensive.

Suggestion:
Start queries from a selective User or time-filtered event node when possible.
```

## 11. Graph Modeling Advice Rules

The first version can combine rule-based checks with AI-generated explanations.

### Rule-Based Checks

#### Missing Index on Common Lookup Property

If a label has properties like `id`, `email`, `slug`, `sku`, or `externalId` and no index exists, suggest an index.

#### Overloaded Node Label

If a node label has many unrelated properties, suggest reviewing whether multiple concepts are being combined.

#### Relationship With Too Many Properties

If a relationship type has many event-like properties, suggest turning the event into a node.

Example:

```text
(:User)-[:WATCHED {timestamp, device, location, rating, duration, sessionId}]->(:Movie)
```

Could become:

```text
(:User)-[:PERFORMED]->(:WatchEvent)-[:FOR_MOVIE]->(:Movie)
```

#### Missing Relationship Direction Convention

If the same concept appears in multiple directions, warn about inconsistent modeling.

#### Orphan Nodes

If a label has many nodes with no relationships, warn that the graph may contain disconnected data.

## 12. Query Safety Design

### Safety Classifier

Every query should be classified before execution.

```typescript
export type GraphQuerySafetyLevel =
  | 'read_only'
  | 'write'
  | 'admin'
  | 'dangerous'
  | 'unknown';
```

### MVP Behavior

| Safety Level | Behavior |
|---|---|
| read_only | Allow |
| write | Block by default |
| admin | Block |
| dangerous | Block |
| unknown | Block or require manual review |

### Dangerous Keywords

- DELETE
- DETACH DELETE
- DROP
- REMOVE
- SET
- CREATE
- MERGE
- LOAD CSV
- CALL dbms
- CALL apoc

Note: Keyword detection is not enough by itself, but it is acceptable for MVP if paired with conservative blocking.

## 13. Error Handling

### Connection Errors

Show:

- Could not reach database
- Authentication failed
- Unknown database
- SSL/encryption mismatch
- Driver version issue

### Query Errors

Show:

- Raw Neo4j error message
- Plain-English explanation
- Suggested fix

Example:

```text
Neo4j could not find the label `Customer`.

Your graph schema contains `User`, but not `Customer`. Try replacing `Customer` with `User`, or refresh schema if the database changed recently.
```

## 14. Observability

Track internally:

- Connection test success/failure
- Introspection duration
- Query execution duration
- Blocked query count
- AI query generation count
- Query error types
- Visualization truncation count

Do not log:

- Passwords
- Secrets
- Full connection strings with credentials
- Sensitive query result data unless explicit local-only logging is configured

## 15. Testing Strategy

### Unit Tests

- Query safety classifier
- Schema normalization
- Neo4j record mapping
- AI context builder
- Prompt construction
- Result transformation

### Integration Tests

Use a Docker Compose Neo4j instance.

Test:

- Connection success
- Connection failure
- Schema introspection
- Query execution
- Query blocking
- Graph visualization data conversion

### UI Tests

- Create connection flow
- Schema screen renders labels and relationships
- Query Lab executes read query
- Dangerous query is blocked
- Visual graph renders nodes and relationships

## 16. Local Development Docker Compose

```yaml
services:
  neo4j:
    image: neo4j:5-community
    container_name: database-guru-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

## 17. Example Seed Data

```cypher
CREATE (u1:User {id: 'u1', email: 'sam@example.com', name: 'Sam'});
CREATE (u2:User {id: 'u2', email: 'alex@example.com', name: 'Alex'});
CREATE (p1:Product {id: 'p1', sku: 'SKU-001', name: 'Graph Book'});
CREATE (p2:Product {id: 'p2', sku: 'SKU-002', name: 'Database Course'});
CREATE (c1:Category {id: 'c1', name: 'Education'});

MATCH (u1:User {id: 'u1'}), (p1:Product {id: 'p1'})
CREATE (u1)-[:PURCHASED {purchasedAt: datetime()}]->(p1);

MATCH (u1:User {id: 'u1'}), (p2:Product {id: 'p2'})
CREATE (u1)-[:VIEWED {viewedAt: datetime()}]->(p2);

MATCH (p1:Product {id: 'p1'}), (c1:Category {id: 'c1'})
CREATE (p1)-[:BELONGS_TO]->(c1);

MATCH (p2:Product {id: 'p2'}), (c1:Category {id: 'c1'})
CREATE (p2)-[:BELONGS_TO]->(c1);

MATCH (u1:User {id: 'u1'}), (u2:User {id: 'u2'})
CREATE (u1)-[:FRIEND_OF]->(u2);
```

## 18. Implementation Phases

## Phase 1 — Foundation

- Add graph connection model
- Add Neo4j driver integration
- Add connection test endpoint
- Add secure credential storage
- Add read-only config default

Deliverable:

User can save and test a Neo4j connection.

## Phase 2 — Schema Introspection

- Add introspection queries
- Normalize schema into GraphSchema
- Cache schema snapshots
- Display schema overview UI

Deliverable:

User can inspect labels, relationships, properties, indexes, and constraints.

## Phase 3 — Query Lab

- Add Cypher editor
- Add read-only query execution
- Add query safety classifier
- Add table/JSON results
- Add query history

Deliverable:

User can safely run Cypher read queries.

## Phase 4 — AI Assistance

- Add schema context builder
- Add natural-language-to-Cypher generation
- Add Cypher explanation
- Add error explanation
- Add query performance advice

Deliverable:

User can generate and understand Cypher with AI help.

## Phase 5 — Visual Graph Explorer

- Add graph result transformer
- Add graph canvas
- Add node/relationship detail panel
- Add expand controls
- Add traversal depth and limit controls

Deliverable:

User can visually explore graph data.

## Phase 6 — Guru Advice

- Add rule-based modeling checks
- Add AI-generated recommendations
- Add index suggestion cards
- Add anti-pattern detection

Deliverable:

User receives useful graph modeling and performance guidance.

## 19. Future Enhancements

### Additional Providers

- Memgraph
- Amazon Neptune
- ArangoDB
- JanusGraph
- Postgres Apache AGE

### Advanced Query Support

- Gremlin generation
- OpenCypher provider abstraction
- Query plan visualization
- Cost estimation
- Query rewrite suggestions

### Advanced Visualization

- Shortest path finder
- Community detection
- Centrality analysis
- Timeline graph exploration
- Large graph clustering
- Saved graph views

### Relational-to-Graph Advisor

Database Guru could inspect relational tables and suggest a graph model.

Example:

```text
users table → (:User)
orders table → (:Order)
products table → (:Product)
order_items table → (:Order)-[:CONTAINS]->(:Product)
```

### AI/Agent Knowledge Graph Mode

For AI development workflows, Database Guru could inspect memory graphs, context graphs, entity graphs, and agent dependency graphs.

This could connect strongly to agentic coding tools and AI operating system concepts.

## 20. MVP Definition of Done

The MVP is complete when:

- User can create and test a Neo4j connection.
- User can introspect graph schema.
- User can view labels, relationships, properties, indexes, and constraints.
- User can run safe read-only Cypher queries.
- User can generate Cypher from natural language using schema context.
- User can explain Cypher queries.
- User can view query results as table and JSON.
- User can visualize graph query results.
- User can receive basic modeling/index advice.
- Dangerous write/admin queries are blocked by default.

## 21. Recommended Tech Stack

### Backend

- Java Spring Boot or Node.js/TypeScript
- Neo4j official driver
- PostgreSQL for app metadata
- Encrypted credential storage
- LLM provider abstraction

### Frontend

- React
- TypeScript
- Monaco Editor for Cypher editing
- Cytoscape.js for graph visualization
- TanStack Query for API state
- Tailwind/shadcn style component layer if already used

### Local Development

- Docker Compose
- Neo4j container
- Seed script
- Mock LLM mode for repeatable tests

## 22. Suggested Repo Structure

```text
database-guru/
  apps/
    web/
    api/
  packages/
    graph-core/
      adapters/
        neo4j/
      schema/
      query-safety/
      visualization/
    ai-core/
      prompts/
      context-builders/
  specs/
    graph-database-support.md
  docker-compose.yml
```

## 23. Open Questions

1. Should Graph Mode be a paid feature or included in the core app?
2. Should write queries ever be allowed, or should the tool remain read-only by philosophy?
3. Should Database Guru support local-only LLMs for sensitive database environments?
4. Should graph visualization be optimized for small debugging graphs or large analytics graphs?
5. Should relational-to-graph modeling be part of this feature or a separate feature later?
6. Should Query Lab support saved prompt templates?
7. Should the app support team-shared connections?

## 24. Product North Star

Graph Mode should make a developer feel like they can finally see and understand the invisible relationship structure inside their database.

The ideal user reaction is:

> I knew the data was connected, but now I can actually see what is going on.

