# Phase 15: Context Intelligence

**Feature**: RAG-powered domain knowledge enhancement for SQL generation
**Branch**: `context-intelligence`
**Priority**: HIGH
**Estimated Effort**: ~6,500 lines | 3-4 weeks
**Prerequisites**: Phase 12 Lineage Intelligence (complete)

---

## 1. Vision

Transform Database Guru from a schema-aware query assistant into a **domain-aware intelligence platform** that understands business context, terminology, and best practices through:

1. **Document Context** - PDFs, markdown, text files with business knowledge
2. **Glossary Terms** - Business term definitions mapped to SQL expressions
3. **Example Queries** - Curated Q&A pairs demonstrating correct SQL
4. **Column Annotations** - Human descriptions for cryptic column names
5. **External APIs** (Future) - MCP servers or REST APIs for dynamic context

**Key Principle**: Local-first using ChromaDB. Cloud options later. All context is optional and additive.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           CONTEXT INTELLIGENCE ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │              USER QUERY                      │
                    │  "Show me all active customers from Texas"   │
                    └─────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTEXT RETRIEVAL LAYER                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Glossary   │  │  Documents  │  │  Examples   │  │  Column     │  │  External   │   │
│  │  Terms      │  │  (RAG)      │  │  Queries    │  │  Annotations│  │  APIs       │   │
│  │             │  │             │  │             │  │             │  │  (Future)   │   │
│  │ "active" →  │  │ PDF chunks  │  │ Q&A pairs   │  │ cust_stat → │  │             │   │
│  │ status='A'  │  │ w/embeddings│  │ matched     │  │ "Customer   │  │             │   │
│  │ AND last_   │  │             │  │ by semantic │  │  Status"    │  │             │   │
│  │ order>90d   │  │             │  │ similarity  │  │             │  │             │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │                │          │
│         └────────────────┴────────────────┴────────────────┴────────────────┘          │
│                                           │                                             │
│                                           ▼                                             │
│                           ┌─────────────────────────────────┐                           │
│                           │    CONTEXT AGGREGATOR           │                           │
│                           │    - Merge & deduplicate        │                           │
│                           │    - Rank by relevance          │                           │
│                           │    - Apply token budget         │                           │
│                           └─────────────────────────────────┘                           │
│                                           │                                             │
└───────────────────────────────────────────┼─────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           EXISTING PROMPT PIPELINE                                        │
│                                                                                           │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐         │
│  │  SYSTEM   │ + │ RETRIEVED │ + │  SCHEMA   │ + │  INTENT   │ + │  DYNAMIC  │         │
│  │  PROMPT   │   │  CONTEXT  │   │  LAYER    │   │  LAYER    │   │  EXAMPLES │         │
│  │           │   │  (NEW!)   │   │           │   │           │   │           │         │
│  │ (prompts. │   │ Glossary, │   │ Tables,   │   │ Query     │   │ Schema-   │         │
│  │  py)      │   │ docs,     │   │ columns,  │   │ type,     │   │ specific  │         │
│  │           │   │ examples  │   │ FKs       │   │ filters   │   │ few-shot  │         │
│  └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘         │
│                                           │                                             │
│                                           ▼                                             │
│                           ┌─────────────────────────────────┐                           │
│                           │        LLM GENERATION           │                           │
│                           │        (Ollama/qwen2.5-coder)   │                           │
│                           └─────────────────────────────────┘                           │
│                                           │                                             │
│                                           ▼                                             │
│                           ┌─────────────────────────────────┐                           │
│                           │        SQL OUTPUT               │                           │
│                           │   SELECT * FROM customers       │                           │
│                           │   WHERE status = 'A'            │                           │
│                           │   AND last_order_date >=        │                           │
│                           │       NOW() - INTERVAL '90 days'│                           │
│                           │   AND state = 'TX'              │                           │
│                           └─────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase Breakdown

```
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│  Phase 15.1           │    │  Phase 15.2           │    │  Phase 15.3           │
│  VECTOR STORE         │───▶│  DOCUMENT INGESTION   │───▶│  GLOSSARY & TERMS     │
│  INFRASTRUCTURE       │    │  & CHUNKING           │    │  MANAGEMENT           │
│                       │    │                       │    │                       │
│  • ChromaDB setup     │    │  • PDF/MD/TXT parsing │    │  • Term CRUD          │
│  • Collection mgmt    │    │  • Smart chunking     │    │  • SQL expression map │
│  • Per-DB vs global   │    │  • Embedding + store  │    │  • Term detection     │
│  • Async wrapper      │    │  • Metadata tracking  │    │  • Auto-expansion     │
│                       │    │                       │    │                       │
│  ~600 lines           │    │  ~800 lines           │    │  ~700 lines           │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│  Phase 15.4           │    │  Phase 15.5           │    │  Phase 15.6           │
│  EXAMPLE QUERY        │───▶│  COLUMN ANNOTATIONS   │───▶│  RAG INTEGRATION      │
│  LIBRARY              │    │                       │    │  WITH PIPELINE        │
│                       │    │                       │    │                       │
│  • Q&A pair storage   │    │  • Column description │    │  • Context retrieval  │
│  • Semantic matching  │    │  • Code mappings      │    │  • Prompt injection   │
│  • Category tagging   │    │  • Sample values      │    │  • Token budgeting    │
│  • Auto-learning      │    │  • Searchable         │    │  • build_chat_msgs    │
│                       │    │                       │    │                       │
│  ~700 lines           │    │  ~500 lines           │    │  ~900 lines           │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────┐    ┌───────────────────────┐
│  Phase 15.7           │    │  Phase 15.8           │
│  FRONTEND MGMT UI     │    │  MCP/EXTERNAL API     │
│                       │    │  INTEGRATION (FUTURE) │
│  • Document upload    │    │                       │
│  • Glossary editor    │    │  • MCP server support │
│  • Example curator    │    │  • REST API sources   │
│  • Column annotator   │    │  • Real-time context  │
│  • Context preview    │    │  • Auth handling      │
│                       │    │                       │
│  ~1,200 lines         │    │  ~800 lines           │
└───────────────────────┘    └───────────────────────┘
```

---

## 4. Phase 15.1: Vector Store Infrastructure

### 4.1 Purpose

Set up ChromaDB as the local vector store for all context types, with support for per-database and global scoping.

### 4.2 User Stories

1. As a developer, I want a simple async interface to store and query embeddings
2. As a DBA, I want context scoped to specific database connections
3. As an admin, I want global context that applies to all databases

### 4.3 Implementation

#### 4.3.1 ContextVectorStore Class (`src/context/vector_store.py`)

```python
"""
Context Vector Store - ChromaDB wrapper for context intelligence.

Uses ChromaDB for local vector storage with:
- Per-connection collections for database-specific context
- Global collection for cross-database context
- Async wrapper for non-blocking operations
- Integration with existing EmbeddingService
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.cache.embedding_service import get_embedding_service, EmbeddingService
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context stored in vector store."""
    DOCUMENT = "document"       # PDF, markdown, text chunks
    GLOSSARY = "glossary"       # Business term definitions
    EXAMPLE = "example"         # Example Q&A pairs
    ANNOTATION = "annotation"   # Column annotations


class ContextScope(str, Enum):
    """Scope of context."""
    GLOBAL = "global"           # Applies to all connections
    CONNECTION = "connection"   # Applies to specific connection


@dataclass
class ContextDocument:
    """A document/chunk stored in the vector store."""
    id: str
    content: str
    context_type: ContextType
    scope: ContextScope
    connection_id: Optional[int] = None  # None for global
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ContextSearchResult:
    """Result from context search."""
    document: ContextDocument
    similarity: float
    rank: int


class ContextVectorStore:
    """
    ChromaDB-backed vector store for context intelligence.

    Collection naming:
    - context_global_{type} - Global context by type
    - context_conn_{id}_{type} - Connection-specific context
    """

    GLOBAL_COLLECTION_PATTERN = "context_global_{context_type}"
    CONNECTION_COLLECTION_PATTERN = "context_conn_{connection_id}_{context_type}"

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self._settings = Settings()
        if persist_directory is None:
            persist_directory = str(Path("./data/chromadb").absolute())

        self.persist_directory = persist_directory
        self._embedding_service = embedding_service
        self._client: Optional[chromadb.PersistentClient] = None
        self._collections: Dict[str, chromadb.Collection] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize ChromaDB client and embedding service."""
        if self._initialized:
            return True

        try:
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            if self._embedding_service is None:
                self._embedding_service = get_embedding_service()
            await self._embedding_service.initialize()

            self._initialized = True
            logger.info("ContextVectorStore initialization complete")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize ContextVectorStore: {e}")
            return False

    async def add_document(self, document: ContextDocument) -> bool:
        """Add a document to the vector store."""
        # Implementation details...

    async def search(
        self,
        query: str,
        context_type: ContextType,
        scope: ContextScope,
        connection_id: Optional[int] = None,
        limit: int = 5,
        min_similarity: float = 0.6,
    ) -> List[ContextSearchResult]:
        """Search for similar documents."""
        # Implementation details...

    async def search_all_scopes(
        self,
        query: str,
        context_type: ContextType,
        connection_id: int,
        limit: int = 5,
        min_similarity: float = 0.6,
    ) -> List[ContextSearchResult]:
        """Search both global and connection-specific context."""
        # Implementation details...


# Singleton
_vector_store: Optional[ContextVectorStore] = None

async def get_context_vector_store() -> ContextVectorStore:
    """Get or create singleton ContextVectorStore."""
    global _vector_store
    if _vector_store is None:
        _vector_store = ContextVectorStore()
        await _vector_store.initialize()
    return _vector_store
```

#### 4.3.2 Database Model Extensions (`src/database/models.py`)

```python
class ContextSource(Base):
    """Tracks uploaded context sources (documents, etc.)"""
    __tablename__ = "context_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # document, glossary, example, annotation
    scope = Column(String(20), nullable=False)  # global, connection
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True, index=True)

    # File metadata
    file_name = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Processing status
    status = Column(String(20), default="pending")  # pending, processing, ready, error
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Vector store reference
    vector_collection = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_context_source_type_scope', 'source_type', 'scope'),
        Index('idx_context_source_conn', 'connection_id'),
    )
```

### 4.4 Tests

```python
# tests/test_context_vector_store.py

class TestContextVectorStore:
    async def test_initialize(self): ...
    async def test_add_and_search_document(self): ...
    async def test_global_vs_connection_scope(self): ...
    async def test_search_all_scopes(self): ...
    async def test_delete_document(self): ...
    async def test_similarity_threshold(self): ...
```

**Lines**: ~600 (backend: 450, tests: 150)

---

## 5. Phase 15.2: Document Ingestion & Chunking

### 5.1 Purpose

Support uploading and processing PDFs, markdown, and text files with smart chunking for optimal retrieval.

### 5.2 User Stories

1. As a business analyst, I want to upload our data dictionary PDF
2. As a developer, I want to add markdown documentation about our schema
3. As an admin, I want automatic chunking with appropriate overlap

### 5.3 Implementation

#### 5.3.1 DocumentProcessor Class (`src/context/document_processor.py`)

```python
"""
Document Processor - Ingestion and chunking for context documents.

Supports:
- PDF files (using pdfplumber or PyPDF2)
- Markdown files
- Plain text files

Chunking strategies:
- Semantic chunking (respects paragraph/section boundaries)
- Overlap for context continuity
- Metadata preservation
"""

class ChunkingStrategy(str, Enum):
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"


@dataclass
class DocumentChunk:
    id: str
    content: str
    chunk_index: int
    total_chunks: int
    source_id: str
    source_name: str
    metadata: Dict[str, Any]
    start_char: int
    end_char: int
    section_title: Optional[str] = None


@dataclass
class ProcessedDocument:
    source_id: str
    source_name: str
    file_type: str
    total_characters: int
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processed_at: str


class DocumentProcessor:
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_OVERLAP = 200
    MIN_CHUNK_SIZE = 100

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_OVERLAP,
        strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    async def process_file(
        self,
        file_path: str,
        source_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessedDocument:
        """Process a file into chunks."""
        # Implementation...

    async def process_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str,
        source_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessedDocument:
        """Process file from bytes (for upload handling)."""
        # Implementation...
```

#### 5.3.2 API Endpoints

```python
# src/api/endpoints/context.py

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    scope: ContextScope = Form(...),
    connection_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> ContextSourceResponse:
    """Upload a document for context."""

@router.get("/documents")
async def list_documents(
    scope: Optional[ContextScope] = None,
    connection_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
) -> List[ContextSourceResponse]:
    """List uploaded documents."""

@router.delete("/documents/{source_id}")
async def delete_document(
    source_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a document."""
```

**Lines**: ~800 (backend: 600, tests: 200)

---

## 6. Phase 15.3: Glossary & Term Management

### 6.1 Purpose

Enable defining business terms that map to SQL expressions, automatically detected and expanded in queries.

### 6.2 User Stories

1. As a business analyst, I want to define "active customer" = `status = 'A' AND last_order_date >= NOW() - INTERVAL '90 days'`
2. As a developer, I want the system to automatically detect when I use these terms
3. As an admin, I want to manage terms per-database or globally

### 6.3 Implementation

#### 6.3.1 GlossaryManager (`src/context/glossary_manager.py`)

```python
@dataclass
class GlossaryTerm:
    id: str
    term: str                     # "active customer"
    definition: str               # Human-readable definition
    sql_expression: Optional[str] # "status = 'A' AND last_order > NOW() - 90 days"
    synonyms: List[str]           # ["active client", "current customer"]
    scope: ContextScope
    connection_id: Optional[int]
    tables: List[str]             # Tables this term applies to
    columns: List[str]            # Columns referenced
    examples: List[str]           # Example usage
    created_at: str
    updated_at: str


class GlossaryManager:
    async def add_term(
        self,
        term: str,
        definition: str,
        sql_expression: Optional[str],
        scope: ContextScope,
        connection_id: Optional[int],
        synonyms: Optional[List[str]] = None,
        tables: Optional[List[str]] = None,
        db_session: AsyncSession = None,
    ) -> GlossaryTerm:
        """Add a new glossary term."""

    async def detect_terms(
        self,
        query: str,
        connection_id: int,
    ) -> List[GlossaryTerm]:
        """Detect glossary terms in a natural language query."""

    async def expand_terms(
        self,
        query: str,
        detected_terms: List[GlossaryTerm],
    ) -> str:
        """Expand a query with term definitions."""

    async def get_sql_conditions(
        self,
        detected_terms: List[GlossaryTerm],
    ) -> Dict[str, str]:
        """Get SQL conditions for detected terms."""
```

#### 6.3.2 Database Model

```python
class GlossaryEntry(Base):
    __tablename__ = "glossary_entries"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(255), nullable=False, index=True)
    definition = Column(Text, nullable=False)
    sql_expression = Column(Text, nullable=True)
    synonyms = Column(JSON, default=list)
    scope = Column(String(20), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True, index=True)
    tables = Column(JSON, default=list)
    columns = Column(JSON, default=list)
    examples = Column(JSON, default=list)
    vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_glossary_scope_conn', 'scope', 'connection_id'),
    )
```

#### 6.3.3 API Endpoints

```python
@router.post("/glossary/terms")
async def create_glossary_term(...) -> GlossaryTermResponse

@router.get("/glossary/terms")
async def list_glossary_terms(...) -> List[GlossaryTermResponse]

@router.put("/glossary/terms/{term_id}")
async def update_glossary_term(...) -> GlossaryTermResponse

@router.delete("/glossary/terms/{term_id}")
async def delete_glossary_term(...) -> dict

@router.post("/glossary/detect")
async def detect_terms_in_query(...) -> List[GlossaryTermResponse]
```

**Lines**: ~700 (backend: 500, tests: 200)

---

## 7. Phase 15.4: Example Query Library

### 7.1 Purpose

Store curated Q&A pairs that demonstrate correct SQL for domain-specific questions, matched semantically to user queries.

### 7.2 Implementation

#### 7.2.1 ExampleQueryManager (`src/context/example_manager.py`)

```python
@dataclass
class ExampleQuery:
    id: str
    question: str            # "How do I find customers who ordered last month?"
    sql: str                 # "SELECT * FROM customers WHERE ..."
    explanation: str         # Why this SQL works
    category: str            # "customer_queries", "sales_analysis"
    tags: List[str]
    scope: ContextScope
    connection_id: Optional[int]
    tables_used: List[str]
    database_type: str
    quality_score: float     # 1.0 = curated, lower = auto-learned
    usage_count: int


class ExampleQueryManager:
    async def add_example(...) -> ExampleQuery
    async def find_similar_examples(query, connection_id, limit=3) -> List[Tuple[ExampleQuery, float]]
    async def auto_learn_example(query_history_id) -> Optional[ExampleQuery]
    async def format_examples_for_prompt(examples, max_tokens) -> str
```

#### 7.2.2 Database Model

```python
class ExampleQueryEntry(Base):
    __tablename__ = "example_queries"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    sql = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    tags = Column(JSON, default=list)
    scope = Column(String(20), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    tables_used = Column(JSON, default=list)
    database_type = Column(String(50), nullable=False)
    quality_score = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    source_query_id = Column(Integer, ForeignKey("query_history.id"), nullable=True)
    vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Lines**: ~700 (backend: 500, tests: 200)

---

## 8. Phase 15.5: Column Annotations

### 8.1 Purpose

Allow human descriptions for cryptic column names, including code value mappings.

### 8.2 Implementation

#### 8.2.1 ColumnAnnotationManager (`src/context/column_annotation_manager.py`)

```python
@dataclass
class ColumnAnnotation:
    id: str
    connection_id: int
    table_name: str
    column_name: str
    business_name: str           # "Customer Status"
    description: str             # "Indicates whether customer is active"
    code_values: Dict[str, str]  # {"A": "Active", "I": "Inactive"}
    sample_values: List[str]
    data_type_note: Optional[str]
    related_columns: List[str]
    tags: List[str]


class ColumnAnnotationManager:
    async def add_annotation(...) -> ColumnAnnotation
    async def get_annotations_for_schema(connection_id, tables) -> Dict[str, Dict[str, ColumnAnnotation]]
    async def search_annotations(query, connection_id) -> List[ColumnAnnotation]
    async def format_for_schema_prompt(annotations) -> str
    async def auto_detect_code_columns(connection_id) -> List[Dict]
```

#### 8.2.2 Database Model

```python
class ColumnAnnotationEntry(Base):
    __tablename__ = "column_annotations"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    table_name = Column(String(255), nullable=False, index=True)
    column_name = Column(String(255), nullable=False, index=True)
    business_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    code_values = Column(JSON, default=dict)
    sample_values = Column(JSON, default=list)
    data_type_note = Column(Text, nullable=True)
    related_columns = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_column_annotation_unique', 'connection_id', 'table_name', 'column_name', unique=True),
    )
```

**Lines**: ~500 (backend: 350, tests: 150)

---

## 9. Phase 15.6: RAG Integration with Query Pipeline

### 9.1 Purpose

Integrate all context sources into the existing prompt pipeline with intelligent retrieval and token budgeting.

### 9.2 Implementation

#### 9.2.1 ContextRetriever (`src/context/context_retriever.py`)

```python
@dataclass
class RetrievedContext:
    """Aggregated context for a query."""
    documents: List[ContextSearchResult]
    glossary_terms: List[GlossaryTerm]
    examples: List[Tuple[ExampleQuery, float]]
    annotations: Dict[str, Dict[str, ColumnAnnotation]]

    formatted_context: str
    formatted_glossary: str
    formatted_examples: str
    formatted_annotations: str

    total_tokens_used: int
    token_budget: int
    retrieval_time_ms: float
    sources_queried: List[str]


class ContextRetriever:
    def __init__(
        self,
        vector_store: ContextVectorStore,
        document_manager: DocumentContextManager,
        glossary_manager: GlossaryManager,
        example_manager: ExampleQueryManager,
        annotation_manager: ColumnAnnotationManager,
        default_token_budget: int = 2000,
    ): ...

    async def retrieve(
        self,
        query: str,
        connection_id: int,
        schema_tables: List[str],
        database_type: str,
        token_budget: Optional[int] = None,
        include_documents: bool = True,
        include_glossary: bool = True,
        include_examples: bool = True,
        include_annotations: bool = True,
    ) -> RetrievedContext:
        """Retrieve all relevant context for a query."""
```

#### 9.2.2 Integration with prompts.py

```python
# Update src/llm/prompts.py

def build_chat_messages(
    question: str,
    schema: str,
    database_type: str = "postgresql",
    conversation_history: list = None,
    row_limit: int = 100,
    examples: str = "",
    intent_result: "QueryIntentResult" = None,
    retrieved_context: "RetrievedContext" = None,  # NEW
) -> list:
    """Build chat messages with context injection."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history
    if conversation_history:
        messages.extend(conversation_history)

    # NEW: Inject retrieved context
    context_sections = []
    if retrieved_context:
        if retrieved_context.formatted_glossary:
            context_sections.append(f"""
═══════════════════════════════════════════════════════════════
BUSINESS TERMINOLOGY
═══════════════════════════════════════════════════════════════
{retrieved_context.formatted_glossary}
""")

        if retrieved_context.formatted_annotations:
            context_sections.append(f"""
═══════════════════════════════════════════════════════════════
COLUMN DEFINITIONS
═══════════════════════════════════════════════════════════════
{retrieved_context.formatted_annotations}
""")

        if retrieved_context.formatted_context:
            context_sections.append(f"""
═══════════════════════════════════════════════════════════════
RELEVANT CONTEXT
═══════════════════════════════════════════════════════════════
{retrieved_context.formatted_context}
""")

    # Build user message with context prepended
    user_message = build_sql_prompt(question, schema, database_type, examples, row_limit)
    if context_sections:
        user_message = "\n".join(context_sections) + "\n" + user_message

    messages.append({"role": "user", "content": user_message})
    return messages
```

#### 9.2.3 Integration with SelfCorrectingAgent

```python
# Update src/llm/self_correcting_agent.py

class SelfCorrectingAgent:
    async def process_query(
        self,
        question: str,
        connection: DatabaseConnection,
        session_id: Optional[str] = None,
        enable_context: bool = True,  # NEW
    ) -> QueryResult:

        # NEW: Retrieve context if enabled
        retrieved_context = None
        if enable_context and self._settings.ENABLE_CONTEXT_INTELLIGENCE:
            try:
                retriever = await self._get_context_retriever()
                retrieved_context = await retriever.retrieve(
                    query=question,
                    connection_id=connection.id,
                    schema_tables=schema_tables,
                    database_type=connection.database_type,
                )

                self.trace.add_step(
                    "context",
                    f"Retrieved {len(retrieved_context.glossary_terms)} terms, "
                    f"{len(retrieved_context.examples)} examples",
                    icon="📚"
                )
            except Exception as e:
                logger.warning(f"Context retrieval failed: {e}")

        # Build messages with context
        messages = build_chat_messages(
            question=question,
            schema=schema_str,
            database_type=connection.database_type,
            retrieved_context=retrieved_context,  # NEW
        )
```

**Lines**: ~900 (backend: 700, tests: 200)

---

## 10. Phase 15.7: Frontend Management UI

### 10.1 Purpose

Provide a user-friendly interface for managing all context types.

### 10.2 Components

| Component | Purpose |
|-----------|---------|
| `ContextManagementPanel.tsx` | Main tabbed panel |
| `DocumentsTab.tsx` | Upload/manage documents |
| `GlossaryTab.tsx` | Add/edit glossary terms |
| `ExamplesTab.tsx` | Curate example queries |
| `AnnotationsTab.tsx` | Document column meanings |
| `ContextPreviewTab.tsx` | Test context retrieval |

### 10.3 Implementation

```typescript
// frontend/src/components/context/ContextManagementPanel.tsx

interface ContextManagementPanelProps {
  connectionId?: number;
  connectionName?: string;
}

export function ContextManagementPanel({
  connectionId,
  connectionName,
}: ContextManagementPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('documents');
  const [scope, setScope] = useState<'global' | 'connection'>('global');

  return (
    <div className="flex flex-col h-full">
      {/* Scope Toggle */}
      <div className="p-4 border-b flex items-center justify-between">
        <h2 className="text-lg font-semibold">Context Intelligence</h2>
        <ScopeToggle value={scope} onChange={setScope} connectionName={connectionName} />
      </div>

      {/* Tab Navigation */}
      <div className="border-b">
        <TabList>
          {TABS.map(tab => (
            <Tab key={tab.id} active={activeTab === tab.id} onClick={() => setActiveTab(tab.id)}>
              {tab.icon} {tab.label}
            </Tab>
          ))}
        </TabList>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'documents' && <DocumentsTab scope={scope} connectionId={connectionId} />}
        {activeTab === 'glossary' && <GlossaryTab scope={scope} connectionId={connectionId} />}
        {activeTab === 'examples' && <ExamplesTab scope={scope} connectionId={connectionId} />}
        {activeTab === 'annotations' && <AnnotationsTab connectionId={connectionId} />}
        {activeTab === 'preview' && <ContextPreviewTab connectionId={connectionId} />}
      </div>
    </div>
  );
}
```

**Lines**: ~1,200 (frontend: 1,000, API types: 200)

---

## 11. Phase 15.8: MCP/External API Integration (Future)

### 11.1 Purpose

Enable dynamic context retrieval from external sources via MCP servers or REST APIs.

### 11.2 Planned Support

- **MCP Servers**: Connect to Model Context Protocol servers
- **REST APIs**: Custom endpoints for dynamic context
- **Data Catalogs**: Integration with enterprise metadata tools

*Deferred to future implementation.*

---

## 12. Configuration

### 12.1 New Settings (`src/config/settings.py`)

```python
# Context Intelligence Settings
ENABLE_CONTEXT_INTELLIGENCE: bool = True
CONTEXT_VECTOR_STORE_PATH: str = "./data/chromadb"
CONTEXT_DEFAULT_TOKEN_BUDGET: int = 2000
CONTEXT_MIN_SIMILARITY: float = 0.6
CONTEXT_MAX_DOCUMENTS: int = 3
CONTEXT_MAX_EXAMPLES: int = 2
CONTEXT_ENABLE_GLOSSARY: bool = True
CONTEXT_ENABLE_EXAMPLES: bool = True
CONTEXT_ENABLE_ANNOTATIONS: bool = True
CONTEXT_ENABLE_DOCUMENTS: bool = True
```

### 12.2 SystemSettings Extensions

```python
# Add to SystemSettings model
enable_context_intelligence = Column(Boolean, default=True, nullable=False)
context_token_budget = Column(Integer, default=2000, nullable=False)
context_min_similarity = Column(Float, default=0.6, nullable=False)
context_max_documents = Column(Integer, default=3, nullable=False)
context_max_examples = Column(Integer, default=2, nullable=False)
```

---

## 13. Dependencies

### 13.1 Backend (New)

```
chromadb>=0.4.0           # Local vector store
pdfplumber>=0.10.0        # PDF text extraction (or PyPDF2>=3.0.0)
```

### 13.2 Existing (Reused)

- `src/cache/embedding_service.py` - Ollama embeddings (nomic-embed-text)
- `src/cache/semantic_cache.py` - Similarity patterns
- `src/core/connection_pool_manager.py` - Singleton patterns

---

## 14. Files Summary

### 14.1 New Files (~5,200 lines)

| File | Purpose | Lines |
|------|---------|-------|
| `src/context/vector_store.py` | ChromaDB wrapper | ~450 |
| `src/context/document_processor.py` | Document chunking | ~350 |
| `src/context/document_manager.py` | Document lifecycle | ~250 |
| `src/context/glossary_manager.py` | Business terms | ~350 |
| `src/context/example_manager.py` | Example queries | ~350 |
| `src/context/column_annotation_manager.py` | Column docs | ~250 |
| `src/context/context_retriever.py` | Unified retrieval | ~400 |
| `src/context/__init__.py` | Package init | ~50 |
| `src/api/endpoints/context.py` | Context API | ~300 |
| `frontend/src/components/context/*.tsx` | UI components | ~900 |
| `frontend/src/services/contextApi.ts` | API client | ~100 |
| `tests/test_*.py` | Tests | ~950 |
| `docs/guides/CONTEXT_INTELLIGENCE_GUIDE.md` | User guide | ~300 |

### 14.2 Modified Files (~500 lines)

| File | Changes |
|------|---------|
| `src/database/models.py` | Add ContextSource, GlossaryEntry, ExampleQueryEntry, ColumnAnnotationEntry |
| `src/llm/prompts.py` | Update build_chat_messages for context injection |
| `src/llm/self_correcting_agent.py` | Integrate ContextRetriever |
| `src/config/settings.py` | Add context intelligence settings |
| `src/main.py` | Initialize context services in lifespan |
| `frontend/src/App.tsx` | Add Context tab to navigation |
| `CLAUDE.md` | Document new agents |
| `.claude/AGENTS.md` | Add context agents |

**Grand Total**: ~5,700 lines

---

## 15. Implementation Schedule

```
Week 1
├── Day 1-2: Phase 15.1 - Vector Store Infrastructure
│   ├── ContextVectorStore class
│   ├── ChromaDB integration
│   ├── Database models
│   └── Tests
│
├── Day 3-4: Phase 15.2 - Document Ingestion
│   ├── DocumentProcessor
│   ├── PDF/MD/TXT support
│   ├── Chunking strategies
│   └── Tests

Week 2
├── Day 1-2: Phase 15.3 - Glossary Management
│   ├── GlossaryManager
│   ├── Term detection
│   ├── API endpoints
│   └── Tests
│
├── Day 3-4: Phase 15.4 - Example Query Library
│   ├── ExampleQueryManager
│   ├── Semantic matching
│   ├── Auto-learning
│   └── Tests

Week 3
├── Day 1: Phase 15.5 - Column Annotations
│   ├── ColumnAnnotationManager
│   ├── Code value mapping
│   └── Tests
│
├── Day 2-3: Phase 15.6 - RAG Integration
│   ├── ContextRetriever
│   ├── Token budgeting
│   ├── Prompt integration
│   └── Tests
│
├── Day 4-5: Phase 15.7 - Frontend UI
│   ├── ContextManagementPanel
│   ├── Document upload
│   ├── Glossary editor
│   ├── Preview tool
│   └── Integration

Week 4
├── Day 1-2: Integration Testing & Polish
│   ├── E2E tests
│   ├── Performance tuning
│   └── Documentation
│
├── Day 3-5: (Optional) Phase 15.8 Planning
│   └── MCP/External API design
```

---

## 16. Success Criteria

| Feature | Success Metric |
|---------|----------------|
| Vector Store | <100ms embedding storage, <50ms retrieval |
| Document Processing | Handles PDFs up to 50 pages |
| Glossary | Detects 90%+ of defined terms in queries |
| Examples | Finds semantically similar examples with 0.7+ accuracy |
| RAG Integration | Context improves SQL accuracy by 15%+ |
| UI | All CRUD operations functional |

### Performance Targets

- Context retrieval: <200ms total
- Document chunking: <5s for 50-page PDF
- Embedding generation: Uses existing service (~50-200ms)

---

## 17. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ChromaDB size growth | Implement retention policy, max 10,000 chunks per collection |
| Token budget exceeded | Prioritized truncation, always include glossary first |
| Slow retrieval | Parallel retrieval across context types |
| Irrelevant context | High similarity threshold (0.6+), user feedback loop |
| PDF extraction quality | Fallback to PyPDF2, skip unreadable pages |

---

## 18. Critical Files Reference

| File | Purpose |
|------|---------|
| `src/cache/embedding_service.py` | Reuse for vector embeddings |
| `src/llm/prompts.py` | Integration point for context injection |
| `src/lineage/lineage_narrator.py` | Pattern for LLM agents |
| `src/database/models.py` | Add new models |
| `docs/planning/LINEAGE_INTELLIGENCE_PLAN.md` | Template format reference |
