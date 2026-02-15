"""Lineage Conversation Agent - Phase 12.5

Natural language Q&A about schema and lineage with multi-turn support.
Classifies questions and routes to appropriate handlers.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.database.models import QueryHistory, DatabaseConnection, SystemSettings
from src.llm.ollama_client import OllamaClient, get_ollama_client
from src.llm.model_router import ModelRouter, TaskType
from src.security.prompt_sanitizer import sanitize_question_for_prompt

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Types of questions the agent can handle."""
    LINEAGE = "lineage"           # "What feeds into X?", "Where does Y come from?"
    IMPACT = "impact"             # "What breaks if I change X?", "Affected by Y?"
    PATTERN = "pattern"           # "Most used tables?", "Bottlenecks?"
    SCHEMA = "schema"             # "What columns does X have?", "Describe table Y"
    RECOMMENDATION = "recommendation"  # "How to optimize?", "Suggest indexes?"
    GENERAL = "general"           # General questions about the database


@dataclass
class LineageAnswer:
    """Response to a lineage question."""
    question: str
    question_type: str
    answer: str
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    related_tables: List[str] = field(default_factory=list)
    related_queries: List[int] = field(default_factory=list)
    confidence: float = 0.8
    follow_up_suggestions: List[str] = field(default_factory=list)
    generated_at: Optional[str] = None
    llm_used: bool = False

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationContext:
    """Tracks multi-turn conversation state."""
    session_id: str
    connection_id: int
    history: List[Tuple[str, str]] = field(default_factory=list)  # (question, answer)
    mentioned_tables: List[str] = field(default_factory=list)
    mentioned_columns: List[str] = field(default_factory=list)
    last_question_type: Optional[QuestionType] = None
    last_accessed: float = field(default_factory=time.time)  # Unix timestamp

    def touch(self):
        """Update last accessed time."""
        self.last_accessed = time.time()

    def add_turn(self, question: str, answer: str):
        """Add a conversation turn."""
        self.history.append((question, answer))
        # Keep only last 5 turns for context
        if len(self.history) > 5:
            self.history = self.history[-5:]

    def get_context_summary(self) -> str:
        """Get a summary of the conversation context."""
        if not self.history:
            return ""

        context_parts = []
        if self.mentioned_tables:
            context_parts.append(f"Tables discussed: {', '.join(self.mentioned_tables[-5:])}")
        if self.mentioned_columns:
            context_parts.append(f"Columns mentioned: {', '.join(self.mentioned_columns[-5:])}")

        # Add last 2 turns
        if self.history:
            context_parts.append("Recent conversation:")
            for q, a in self.history[-2:]:
                context_parts.append(f"  Q: {q[:100]}...")
                context_parts.append(f"  A: {a[:150]}...")

        return "\n".join(context_parts)


class QuestionClassifier:
    """Classifies questions into types for routing."""

    # Keyword patterns for each question type
    PATTERNS = {
        QuestionType.LINEAGE: [
            r'\b(lineage|trace|origin|source|feed|flow|depend|upstream|downstream)\b',
            r'\bwhere\s+does\s+\w+\s+come\s+from\b',
            r'\bwhat\s+(feeds?|sources?)\s+into\b',
            r'\bdata\s+flow\b',
        ],
        QuestionType.IMPACT: [
            r'\b(impact|affect|break|change|modify|alter|rename|drop)\b',
            r'\bwhat\s+(happens|breaks|changes)\s+if\b',
            r'\baffected\s+by\b',
            r'\bdependent\s+on\b',
        ],
        QuestionType.PATTERN: [
            r'\b(pattern|usage|frequent|common|popular|bottleneck|slow|performance)\b',
            r'\bmost\s+(used|queried|accessed)\b',
            r'\bhow\s+often\b',
            r'\bquery\s+patterns?\b',
        ],
        QuestionType.SCHEMA: [
            r'\b(schema|structure|column|table|field|type|constraint|key|index)\b',
            r'\bwhat\s+(columns?|fields?|tables?)\b',
            r'\bdescribe\s+(table|schema)\b',
            r'\bshow\s+me\s+(the\s+)?(schema|structure|columns?)\b',
        ],
        QuestionType.RECOMMENDATION: [
            r'\b(recommend|suggest|optimize|improve|best\s+practice|should\s+i)\b',
            r'\bhow\s+(can|should|to)\s+(i\s+)?(optimize|improve)\b',
            r'\bwhat\s+indexes?\s+should\b',
        ],
    }

    def classify(self, question: str) -> QuestionType:
        """Classify a question into a type."""
        question_lower = question.lower()

        scores = {qtype: 0 for qtype in QuestionType}

        for qtype, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    scores[qtype] += 1

        # Find the type with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for qtype, score in scores.items():
                if score == max_score:
                    return qtype

        return QuestionType.GENERAL

    def extract_entities(self, question: str) -> Dict[str, List[str]]:
        """Extract table and column names from the question."""
        # Common patterns for table/column references
        entities = {
            'tables': [],
            'columns': [],
        }

        # Look for quoted identifiers
        quoted = re.findall(r'["\'](\w+)["\']', question)

        # Look for "table X" or "X table" patterns
        table_patterns = re.findall(r'\b(?:table|from|join)\s+(\w+)\b', question, re.IGNORECASE)
        table_patterns += re.findall(r'\b(\w+)\s+table\b', question, re.IGNORECASE)

        # Look for "column X" or "X column" patterns
        column_patterns = re.findall(r'\b(?:column|field)\s+(\w+)\b', question, re.IGNORECASE)
        column_patterns += re.findall(r'\b(\w+)\s+(?:column|field)\b', question, re.IGNORECASE)

        # Combine and deduplicate
        entities['tables'] = list(set(table_patterns + [q for q in quoted if len(q) > 2]))
        entities['columns'] = list(set(column_patterns))

        return entities


class LineageConversationAgent:
    """Handles natural language questions about schema and lineage."""

    # Session management settings
    SESSION_TTL_SECONDS = 3600  # 1 hour TTL for inactive sessions
    MAX_SESSIONS = 100  # Maximum concurrent sessions

    def __init__(
        self,
        client: OllamaClient,
        timeout_seconds: float = 15.0,
        model: Optional[str] = None,
    ):
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.model = model  # Model override from settings
        self.classifier = QuestionClassifier()
        self._conversation_contexts: Dict[str, ConversationContext] = {}
        self._last_cleanup = time.time()

    def _cleanup_expired_sessions(self):
        """Remove expired sessions to prevent memory leaks."""
        now = time.time()

        # Only run cleanup every 60 seconds
        if now - self._last_cleanup < 60:
            return

        self._last_cleanup = now
        expired = []

        for session_id, context in self._conversation_contexts.items():
            if now - context.last_accessed > self.SESSION_TTL_SECONDS:
                expired.append(session_id)

        for session_id in expired:
            del self._conversation_contexts[session_id]
            logger.debug(f"Expired conversation session: {session_id}")

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired conversation sessions")

        # If still over limit, remove oldest sessions
        if len(self._conversation_contexts) > self.MAX_SESSIONS:
            sorted_sessions = sorted(
                self._conversation_contexts.items(),
                key=lambda x: x[1].last_accessed
            )
            to_remove = len(self._conversation_contexts) - self.MAX_SESSIONS
            for session_id, _ in sorted_sessions[:to_remove]:
                del self._conversation_contexts[session_id]
            logger.info(f"Evicted {to_remove} oldest sessions (over limit)")

    def _get_or_create_context(
        self,
        session_id: Optional[str],
        connection_id: int,
    ) -> ConversationContext:
        """Get or create a conversation context."""
        # Periodic cleanup
        self._cleanup_expired_sessions()

        if session_id and session_id in self._conversation_contexts:
            context = self._conversation_contexts[session_id]
            context.touch()  # Update last accessed time
            return context

        context = ConversationContext(
            session_id=session_id or "default",
            connection_id=connection_id,
        )
        if session_id:
            self._conversation_contexts[session_id] = context
        return context

    async def ask(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        session_id: Optional[str] = None,
    ) -> LineageAnswer:
        """Answer a question about lineage, schema, or patterns."""
        # Sanitize input to prevent prompt injection
        question = sanitize_question_for_prompt(question)

        # Classify the question
        question_type = self.classifier.classify(question)
        entities = self.classifier.extract_entities(question)

        # Get/create conversation context
        context = self._get_or_create_context(session_id, connection_id)
        context.mentioned_tables.extend(entities['tables'])
        context.mentioned_columns.extend(entities['columns'])

        logger.info(f"Question classified as {question_type.value}: {question[:50]}...")

        # Route to appropriate handler
        try:
            if question_type == QuestionType.LINEAGE:
                answer = await self._answer_lineage_question(question, connection_id, db, context, entities)
            elif question_type == QuestionType.IMPACT:
                answer = await self._answer_impact_question(question, connection_id, db, context, entities)
            elif question_type == QuestionType.PATTERN:
                answer = await self._answer_pattern_question(question, connection_id, db, context)
            elif question_type == QuestionType.SCHEMA:
                answer = await self._answer_schema_question(question, connection_id, db, context, entities)
            elif question_type == QuestionType.RECOMMENDATION:
                answer = await self._answer_recommendation_question(question, connection_id, db, context)
            else:
                answer = await self._answer_general_question(question, connection_id, db, context)

            # Update context
            context.add_turn(question, answer.answer)
            context.last_question_type = question_type

            return answer

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return self._create_error_answer(question, question_type, str(e))

    async def _answer_lineage_question(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        context: ConversationContext,
        entities: Dict[str, List[str]],
    ) -> LineageAnswer:
        """Answer questions about data lineage."""
        # Get relevant queries that mention the entities
        tables = entities['tables'] or context.mentioned_tables[-3:]

        if not tables:
            return LineageAnswer(
                question=question,
                question_type=QuestionType.LINEAGE.value,
                answer="I need a specific table or column name to trace lineage. "
                       "Could you specify which table or column you'd like to trace?",
                follow_up_suggestions=[
                    "What tables are available?",
                    "Show me the schema",
                ],
                confidence=0.5,
            )

        # Find queries involving these tables
        queries = await self._get_queries_for_tables(tables, connection_id, db)

        # Build lineage information
        lineage_info = await self._build_lineage_info(tables, queries, db)

        # Generate answer with LLM
        answer_text = await self._generate_lineage_answer(
            question, tables, lineage_info, context, queries, db
        )

        return LineageAnswer(
            question=question,
            question_type=QuestionType.LINEAGE.value,
            answer=answer_text,
            supporting_data=lineage_info,
            related_tables=tables,
            related_queries=[q.id for q in queries[:5]],
            follow_up_suggestions=self._generate_lineage_followups(tables),
            llm_used=True,
        )

    async def _answer_impact_question(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        context: ConversationContext,
        entities: Dict[str, List[str]],
    ) -> LineageAnswer:
        """Answer questions about impact of changes."""
        tables = entities['tables'] or context.mentioned_tables[-3:]
        columns = entities['columns'] or context.mentioned_columns[-3:]

        if not tables and not columns:
            return LineageAnswer(
                question=question,
                question_type=QuestionType.IMPACT.value,
                answer="To analyze impact, I need to know which table or column you're "
                       "considering changing. Could you specify the table or column name?",
                follow_up_suggestions=[
                    "What happens if I change the 'users' table?",
                    "What queries would be affected by renaming column X?",
                ],
                confidence=0.5,
            )

        # Get queries that would be impacted
        queries = await self._get_queries_for_tables(tables, connection_id, db)

        # Analyze potential impact
        impact_info = {
            'affected_queries': len(queries),
            'tables_analyzed': tables,
            'columns_analyzed': columns,
        }

        # Categorize queries by usage type
        read_queries = [q for q in queries if q.generated_sql and
                        q.generated_sql.strip().upper().startswith('SELECT')]
        write_queries = [q for q in queries if q.generated_sql and
                         not q.generated_sql.strip().upper().startswith('SELECT')]

        impact_info['read_queries'] = len(read_queries)
        impact_info['write_queries'] = len(write_queries)

        # Generate answer
        answer_text = await self._generate_impact_answer(
            question, tables, columns, impact_info, queries, context, db
        )

        return LineageAnswer(
            question=question,
            question_type=QuestionType.IMPACT.value,
            answer=answer_text,
            supporting_data=impact_info,
            related_tables=tables,
            related_queries=[q.id for q in queries[:5]],
            follow_up_suggestions=self._generate_impact_followups(tables, columns),
            llm_used=True,
        )

    async def _answer_pattern_question(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        context: ConversationContext,
    ) -> LineageAnswer:
        """Answer questions about query patterns and usage."""
        # Get query statistics
        stats = await self._get_query_stats(connection_id, db)

        # Generate answer
        answer_text = await self._generate_pattern_answer(question, stats, context, db)

        return LineageAnswer(
            question=question,
            question_type=QuestionType.PATTERN.value,
            answer=answer_text,
            supporting_data=stats,
            related_tables=stats.get('top_tables', []),
            follow_up_suggestions=[
                "Why is this table used so frequently?",
                "Are there any bottlenecks?",
                "How can I optimize the most common queries?",
            ],
            llm_used=True,
        )

    async def _answer_schema_question(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        context: ConversationContext,
        entities: Dict[str, List[str]],
    ) -> LineageAnswer:
        """Answer questions about database schema."""
        tables = entities['tables'] or context.mentioned_tables[-3:]

        # Get schema information
        schema_info = await self._get_schema_info(connection_id, tables, db)

        if not schema_info.get('tables'):
            # Get list of available tables
            all_tables = await self._get_all_tables(connection_id, db)
            return LineageAnswer(
                question=question,
                question_type=QuestionType.SCHEMA.value,
                answer=f"I found {len(all_tables)} tables in this connection. "
                       f"Available tables: {', '.join(all_tables[:20])}"
                       f"{'...' if len(all_tables) > 20 else ''}. "
                       "Which table would you like to know more about?",
                supporting_data={'available_tables': all_tables},
                follow_up_suggestions=[
                    f"Describe the {all_tables[0]} table" if all_tables else "What tables are available?",
                ],
                confidence=0.9,
            )

        # Generate answer
        answer_text = await self._generate_schema_answer(question, schema_info, context, db)

        return LineageAnswer(
            question=question,
            question_type=QuestionType.SCHEMA.value,
            answer=answer_text,
            supporting_data=schema_info,
            related_tables=list(schema_info.get('tables', {}).keys()),
            follow_up_suggestions=self._generate_schema_followups(schema_info),
            llm_used=True,
        )

    async def _answer_recommendation_question(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        context: ConversationContext,
    ) -> LineageAnswer:
        """Answer questions asking for recommendations."""
        # Gather context for recommendations
        stats = await self._get_query_stats(connection_id, db)

        # Generate recommendations
        answer_text = await self._generate_recommendation_answer(question, stats, context, db)

        return LineageAnswer(
            question=question,
            question_type=QuestionType.RECOMMENDATION.value,
            answer=answer_text,
            supporting_data=stats,
            related_tables=stats.get('top_tables', []),
            follow_up_suggestions=[
                "Show me the schema health report",
                "What are the current bottlenecks?",
                "How do I implement these suggestions?",
            ],
            llm_used=True,
        )

    async def _answer_general_question(
        self,
        question: str,
        connection_id: int,
        db: AsyncSession,
        context: ConversationContext,
    ) -> LineageAnswer:
        """Answer general questions about the database."""
        # Get basic database info
        db_info = await self._get_database_info(connection_id, db)

        # Generate answer
        answer_text = await self._generate_general_answer(question, db_info, context, db)

        return LineageAnswer(
            question=question,
            question_type=QuestionType.GENERAL.value,
            answer=answer_text,
            supporting_data=db_info,
            follow_up_suggestions=[
                "What tables are available?",
                "Show me the most used tables",
                "What can I ask about?",
            ],
            llm_used=True,
        )

    # =========================================================================
    # Data Gathering Methods
    # =========================================================================

    async def _get_queries_for_tables(
        self,
        tables: List[str],
        connection_id: int,
        db: AsyncSession,
    ) -> List[QueryHistory]:
        """Get queries that reference specific tables."""
        from sqlalchemy import or_

        if not tables:
            return []

        # Build LIKE conditions using SQLAlchemy ORM (safe from SQL injection)
        like_conditions = [
            QueryHistory.generated_sql.ilike(f"%{table}%")
            for table in tables
        ]

        stmt = (
            select(QueryHistory)
            .where(
                QueryHistory.connection_id == connection_id,
                QueryHistory.generated_sql.isnot(None),
                or_(*like_conditions)
            )
            .order_by(QueryHistory.created_at.desc())
            .limit(50)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _build_lineage_info(
        self,
        tables: List[str],
        queries: List[QueryHistory],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Build lineage information from queries."""
        lineage = {
            'tables': {},
            'relationships': [],
        }

        for table in tables:
            table_info = {
                'query_count': 0,
                'used_in_joins': 0,
                'sample_queries': [],
            }

            for q in queries:
                sql = (q.generated_sql or '').upper()
                if table.upper() in sql:
                    table_info['query_count'] += 1
                    if 'JOIN' in sql:
                        table_info['used_in_joins'] += 1
                    if len(table_info['sample_queries']) < 3:
                        table_info['sample_queries'].append(q.natural_language_query)

            lineage['tables'][table] = table_info

        # Find table relationships through JOINs
        for q in queries:
            sql = (q.generated_sql or '').upper()
            if 'JOIN' in sql:
                # Simple extraction of joined tables
                for t1 in tables:
                    for t2 in tables:
                        if t1 != t2 and t1.upper() in sql and t2.upper() in sql:
                            rel = {'from': t1, 'to': t2, 'type': 'join'}
                            if rel not in lineage['relationships']:
                                lineage['relationships'].append(rel)

        return lineage

    async def _get_query_stats(
        self,
        connection_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Get query pattern statistics."""
        # Get table usage counts
        query = text("""
            SELECT generated_sql, COUNT(*) as count
            FROM query_history
            WHERE connection_id = :conn_id AND generated_sql IS NOT NULL
            GROUP BY generated_sql
            ORDER BY count DESC
            LIMIT 100
        """)

        result = await db.execute(query, {"conn_id": connection_id})
        rows = result.fetchall()

        # Extract table names from queries
        table_counts: Dict[str, int] = {}
        total_queries = 0

        for sql, count in rows:
            total_queries += count
            # Simple table extraction
            tables = re.findall(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
            tables += re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
            for table in tables:
                table_counts[table] = table_counts.get(table, 0) + count

        # Sort by usage
        sorted_tables = sorted(table_counts.items(), key=lambda x: -x[1])

        return {
            'total_queries': total_queries,
            'unique_queries': len(rows),
            'top_tables': [t[0] for t in sorted_tables[:10]],
            'table_usage': dict(sorted_tables[:10]),
        }

    async def _get_schema_info(
        self,
        connection_id: int,
        tables: List[str],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Get schema information for specific tables."""
        # This would ideally query the actual database schema
        # For now, we extract from query history
        schema_info = {'tables': {}}

        if not tables:
            return schema_info

        # Get queries to infer schema
        queries = await self._get_queries_for_tables(tables, connection_id, db)

        for table in tables:
            columns = set()
            for q in queries:
                sql = q.generated_sql or ''
                # Extract column references (simple heuristic)
                # Pattern: table.column or just column in SELECT
                col_pattern = rf'{table}\.(\w+)'
                cols = re.findall(col_pattern, sql, re.IGNORECASE)
                columns.update(cols)

            schema_info['tables'][table] = {
                'columns': list(columns),
                'query_count': len([q for q in queries if table.upper() in (q.generated_sql or '').upper()]),
            }

        return schema_info

    async def _get_all_tables(
        self,
        connection_id: int,
        db: AsyncSession,
    ) -> List[str]:
        """Get all tables referenced in queries."""
        query = text("""
            SELECT DISTINCT generated_sql
            FROM query_history
            WHERE connection_id = :conn_id AND generated_sql IS NOT NULL
            LIMIT 500
        """)

        result = await db.execute(query, {"conn_id": connection_id})
        rows = result.fetchall()

        tables = set()
        for (sql,) in rows:
            found = re.findall(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
            found += re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
            found += re.findall(r'\bINTO\s+(\w+)', sql, re.IGNORECASE)
            found += re.findall(r'\bUPDATE\s+(\w+)', sql, re.IGNORECASE)
            tables.update(found)

        return sorted(list(tables))

    async def _get_database_info(
        self,
        connection_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Get basic database information."""
        # Get connection info
        result = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        )
        conn = result.scalar_one_or_none()

        tables = await self._get_all_tables(connection_id, db)
        stats = await self._get_query_stats(connection_id, db)

        return {
            'connection_name': conn.name if conn else 'Unknown',
            'db_type': conn.db_type if conn else 'Unknown',
            'table_count': len(tables),
            'tables': tables[:20],
            'total_queries': stats.get('total_queries', 0),
        }

    # =========================================================================
    # LLM Answer Generation Methods
    # =========================================================================

    async def _generate_lineage_answer(
        self,
        question: str,
        tables: List[str],
        lineage_info: Dict[str, Any],
        context: ConversationContext,
        queries: List[QueryHistory],
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate an answer about lineage using LLM."""
        prompt = f"""You are a database lineage expert. Answer the user's question about data lineage clearly and concisely.

Question: {question}

Tables being analyzed: {', '.join(tables)}

Lineage Information:
{self._format_dict(lineage_info)}

Recent conversation context:
{context.get_context_summary()}

Provide a clear, concise answer about the data lineage. Explain:
1. How data flows through the tables
2. Key relationships between tables
3. Any notable patterns in how the tables are used

Keep your response under 200 words and focus on directly answering the question."""

        return await self._call_llm(
            prompt, self._fallback_lineage_answer(tables, lineage_info),
            db=db, agent_type="lineage_conversation"
        )

    async def _generate_impact_answer(
        self,
        question: str,
        tables: List[str],
        columns: List[str],
        impact_info: Dict[str, Any],
        queries: List[QueryHistory],
        context: ConversationContext,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate an answer about impact analysis."""
        prompt = f"""You are a database change impact analyst. Answer the user's question about the potential impact of schema changes.

Question: {question}

Objects being analyzed:
- Tables: {', '.join(tables) if tables else 'None specified'}
- Columns: {', '.join(columns) if columns else 'None specified'}

Impact Analysis:
- Total affected queries: {impact_info.get('affected_queries', 0)}
- Read queries affected: {impact_info.get('read_queries', 0)}
- Write queries affected: {impact_info.get('write_queries', 0)}

Recent conversation context:
{context.get_context_summary()}

Provide a clear assessment of:
1. The scope of impact (how many things would be affected)
2. The risk level (low/medium/high)
3. Key considerations before making the change

Keep your response under 200 words."""

        fallback = (
            f"Based on my analysis, changes to {', '.join(tables or columns)} would affect "
            f"{impact_info.get('affected_queries', 0)} queries. "
            f"Of these, {impact_info.get('read_queries', 0)} are read queries and "
            f"{impact_info.get('write_queries', 0)} are write queries. "
            f"I recommend reviewing these queries before making changes."
        )

        return await self._call_llm(prompt, fallback, db=db, agent_type="impact_advisor")

    async def _generate_pattern_answer(
        self,
        question: str,
        stats: Dict[str, Any],
        context: ConversationContext,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate an answer about query patterns."""
        prompt = f"""You are a database usage analyst. Answer the user's question about query patterns and database usage.

Question: {question}

Query Statistics:
- Total queries executed: {stats.get('total_queries', 0)}
- Unique query patterns: {stats.get('unique_queries', 0)}
- Most used tables: {', '.join(stats.get('top_tables', [])[:5])}

Table Usage (query count):
{self._format_dict(stats.get('table_usage', {}))}

Recent conversation context:
{context.get_context_summary()}

Provide insights about:
1. Usage patterns you observe
2. Which tables are most critical
3. Any potential concerns or recommendations

Keep your response under 200 words."""

        fallback = (
            f"Your database has processed {stats.get('total_queries', 0)} queries with "
            f"{stats.get('unique_queries', 0)} unique patterns. "
            f"The most frequently used tables are: {', '.join(stats.get('top_tables', [])[:5])}."
        )

        return await self._call_llm(prompt, fallback, db=db, agent_type="pattern_analyzer")

    async def _generate_schema_answer(
        self,
        question: str,
        schema_info: Dict[str, Any],
        context: ConversationContext,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate an answer about schema."""
        tables_desc = []
        for table, info in schema_info.get('tables', {}).items():
            cols = info.get('columns', [])
            tables_desc.append(f"- {table}: {len(cols)} columns ({', '.join(cols[:5])}{'...' if len(cols) > 5 else ''})")

        prompt = f"""You are a database schema expert. Answer the user's question about the database schema.

Question: {question}

Schema Information:
{chr(10).join(tables_desc) if tables_desc else 'No specific tables found'}

Recent conversation context:
{context.get_context_summary()}

Provide a clear description of:
1. The structure of the requested tables
2. Key columns and their likely purposes
3. How these tables might relate to each other

Keep your response under 200 words."""

        fallback = f"Schema information: {self._format_dict(schema_info)}"

        return await self._call_llm(prompt, fallback, db=db, agent_type="schema_explorer")

    async def _generate_recommendation_answer(
        self,
        question: str,
        stats: Dict[str, Any],
        context: ConversationContext,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate recommendations."""
        prompt = f"""You are a database optimization expert. Answer the user's question with specific, actionable recommendations.

Question: {question}

Current Database State:
- Total queries: {stats.get('total_queries', 0)}
- Most used tables: {', '.join(stats.get('top_tables', [])[:5])}

Recent conversation context:
{context.get_context_summary()}

Provide 2-4 specific, actionable recommendations. For each:
1. What to do
2. Why it would help
3. Expected impact

Keep your response under 250 words."""

        fallback = (
            "Based on your usage patterns, I recommend:\n"
            f"1. Review indexing on high-usage tables: {', '.join(stats.get('top_tables', [])[:3])}\n"
            "2. Analyze slow queries for optimization opportunities\n"
            "3. Consider caching for frequently repeated queries"
        )

        return await self._call_llm(prompt, fallback, db=db, agent_type="recommendation_agent")

    async def _generate_general_answer(
        self,
        question: str,
        db_info: Dict[str, Any],
        context: ConversationContext,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Generate a general answer about the database."""
        prompt = f"""You are a helpful database assistant. Answer the user's general question about their database.

Question: {question}

Database Information:
- Connection: {db_info.get('connection_name', 'Unknown')}
- Database type: {db_info.get('db_type', 'Unknown')}
- Number of tables: {db_info.get('table_count', 0)}
- Total queries executed: {db_info.get('total_queries', 0)}

Available tables: {', '.join(db_info.get('tables', [])[:10])}{'...' if len(db_info.get('tables', [])) > 10 else ''}

Recent conversation context:
{context.get_context_summary()}

Provide a helpful, informative response. If the question is unclear, suggest what kinds of questions you can answer about lineage, impact, patterns, or schema.

Keep your response under 200 words."""

        fallback = (
            f"This is a {db_info.get('db_type', 'database')} connection with "
            f"{db_info.get('table_count', 0)} tables. "
            f"You can ask me about:\n"
            "- Data lineage (where does data come from?)\n"
            "- Impact analysis (what breaks if I change X?)\n"
            "- Usage patterns (what tables are most used?)\n"
            "- Schema information (what columns does table X have?)"
        )

        return await self._call_llm(prompt, fallback, db=db, agent_type="lineage_conversation")

    async def _call_llm(
        self,
        prompt: str,
        fallback: str,
        db: Optional[AsyncSession] = None,
        agent_type: str = "lineage_conversation"
    ) -> str:
        """Call LLM with timeout and fallback."""
        try:
            response = await asyncio.wait_for(
                self.client.generate(
                    prompt=prompt,
                    model=self.model,  # Use configured model from settings
                    temperature=0.3,
                    db=db,
                    agent_type=agent_type,
                ),
                timeout=self.timeout_seconds
            )
            return response.strip() if response else fallback
        except asyncio.TimeoutError:
            logger.warning(f"LLM timeout after {self.timeout_seconds}s, using fallback")
            return fallback
        except Exception as e:
            logger.error(f"LLM error: {e}, using fallback")
            return fallback

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_dict(self, d: Dict[str, Any], indent: int = 0) -> str:
        """Format a dictionary for prompt inclusion."""
        lines = []
        prefix = "  " * indent
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}:")
                lines.append(self._format_dict(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{prefix}{k}: {', '.join(str(x) for x in v[:5])}")
            else:
                lines.append(f"{prefix}{k}: {v}")
        return "\n".join(lines)

    def _fallback_lineage_answer(self, tables: List[str], lineage_info: Dict[str, Any]) -> str:
        """Generate a fallback lineage answer."""
        parts = [f"Lineage analysis for {', '.join(tables)}:"]

        for table, info in lineage_info.get('tables', {}).items():
            parts.append(f"\n{table}:")
            parts.append(f"  - Referenced in {info.get('query_count', 0)} queries")
            parts.append(f"  - Used in joins: {info.get('used_in_joins', 0)} times")

        if lineage_info.get('relationships'):
            parts.append("\nRelationships found:")
            for rel in lineage_info['relationships'][:5]:
                parts.append(f"  - {rel['from']} -> {rel['to']} ({rel['type']})")

        return "\n".join(parts)

    def _generate_lineage_followups(self, tables: List[str]) -> List[str]:
        """Generate follow-up suggestions for lineage questions."""
        suggestions = []
        if tables:
            suggestions.append(f"What would break if I modify {tables[0]}?")
            suggestions.append(f"Show me the most common queries using {tables[0]}")
        suggestions.append("What are the key relationships in my schema?")
        return suggestions[:3]

    def _generate_impact_followups(self, tables: List[str], columns: List[str]) -> List[str]:
        """Generate follow-up suggestions for impact questions."""
        suggestions = ["Show me the migration plan for this change"]
        if tables:
            suggestions.append(f"What's the lineage for {tables[0]}?")
        suggestions.append("How can I minimize the impact?")
        return suggestions[:3]

    def _generate_schema_followups(self, schema_info: Dict[str, Any]) -> List[str]:
        """Generate follow-up suggestions for schema questions."""
        tables = list(schema_info.get('tables', {}).keys())
        suggestions = []
        if tables:
            suggestions.append(f"What queries use {tables[0]}?")
            suggestions.append(f"What's the lineage for {tables[0]}?")
        suggestions.append("Show me the schema health report")
        return suggestions[:3]

    def _create_error_answer(
        self,
        question: str,
        question_type: QuestionType,
        error: str,
    ) -> LineageAnswer:
        """Create an error response."""
        return LineageAnswer(
            question=question,
            question_type=question_type.value,
            answer=f"I encountered an issue while processing your question: {error}. "
                   "Please try rephrasing or asking a more specific question.",
            confidence=0.0,
            follow_up_suggestions=[
                "What tables are available?",
                "Show me the database overview",
            ],
        )


async def get_lineage_conversation_agent(
    db: Optional[AsyncSession] = None,
    model_override: Optional[str] = None,
    timeout_override: Optional[float] = None,
) -> LineageConversationAgent:
    """
    Factory function to create a LineageConversationAgent with proper configuration.

    Uses the ModelRouter to get the configured model for LINEAGE_CONVERSATION task
    from the settings panel.
    """
    client = get_ollama_client()
    model = model_override
    timeout = timeout_override or 15.0

    # Load model and timeout from router if db session is available
    if db is not None:
        try:
            from src.llm.model_router import get_model_router, TaskType

            router = await get_model_router(db)
            if not model:
                model = router.get_model_for_task(TaskType.LINEAGE_CONVERSATION)
            if not timeout_override:
                timeout = router.get_timeout_for_task(TaskType.LINEAGE_CONVERSATION)
            logger.info(f"LineageConversationAgent using model={model}, timeout={timeout}s")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not load model router settings: {e}")

    return LineageConversationAgent(
        client=client,
        timeout_seconds=timeout,
        model=model,
    )
