"""Conversational Memory Agent for context-aware query generation"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChatMessage, QueryHistory
from src.security.prompt_sanitizer import (
    create_safe_context_prompt,
    sanitize_question_for_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Represents conversation context for query generation"""
    messages: List[Dict[str, Any]]
    has_context: bool
    context_window_size: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "messages": self.messages,
            "has_context": self.has_context,
            "context_window_size": self.context_window_size
        }


class ConversationalMemoryAgent:
    """
    Agent that provides conversational context for SQL generation

    This agent retrieves recent queries from the chat session and builds
    context-aware prompts that allow users to refine queries naturally.

    Example:
        User: "Show me all products"
        → SELECT * FROM products

        User: "Filter by electronics"
        → Agent remembers context
        → SELECT * FROM products WHERE category = 'electronics'

        User: "Sort by price"
        → SELECT * FROM products WHERE category = 'electronics' ORDER BY price
    """

    def __init__(self, context_window: int = 3):
        """
        Initialize conversational memory agent

        Args:
            context_window: Number of previous queries to include in context
        """
        self.context_window = context_window
        logger.info(f"ConversationalMemoryAgent initialized with window size {context_window}")

    async def get_context(
        self,
        session_id: str,
        db: AsyncSession
    ) -> ConversationContext:
        """
        Get conversation context for a chat session

        Args:
            session_id: Chat session ID
            db: Database session

        Returns:
            ConversationContext with recent messages
        """
        try:
            # Query recent messages with their query history
            query = (
                select(ChatMessage, QueryHistory)
                .join(
                    QueryHistory,
                    ChatMessage.query_history_id == QueryHistory.id,
                    isouter=True
                )
                .where(ChatMessage.chat_session_id == session_id)
                .where(ChatMessage.role == "user")  # Only user messages
                .order_by(ChatMessage.created_at.desc())
                .limit(self.context_window)
            )

            result = await db.execute(query)
            rows = result.all()

            # Build context messages (reverse to oldest-first order)
            messages = []
            for chat_msg, query_hist in reversed(rows):
                message = {
                    "question": chat_msg.content,
                    "timestamp": chat_msg.created_at.isoformat() if chat_msg.created_at else None
                }

                # Add SQL and result info if available
                if query_hist:
                    message["sql"] = query_hist.generated_sql
                    message["executed"] = query_hist.executed
                    message["success"] = query_hist.executed and not query_hist.error_message
                    if query_hist.result_count is not None:
                        message["result_count"] = query_hist.result_count

                messages.append(message)

            has_context = len(messages) > 0

            logger.info(
                f"Retrieved {len(messages)} context messages for session {session_id}"
            )

            return ConversationContext(
                messages=messages,
                has_context=has_context,
                context_window_size=len(messages)
            )

        except Exception as e:
            logger.error(f"Error retrieving conversation context: {str(e)}")
            # Return empty context on error
            return ConversationContext(
                messages=[],
                has_context=False,
                context_window_size=0
            )

    def build_context_prompt(
        self,
        question: str,
        context: ConversationContext
    ) -> str:
        """
        Build context-aware prompt for SQL generation with security sanitization

        This method uses structured prompts with XML-like delimiters and input
        sanitization to prevent prompt injection attacks.

        Args:
            question: Current user question
            context: Conversation context

        Returns:
            Enhanced question with conversation context (sanitized)
        """
        if not context.has_context:
            # No context - sanitize and return question
            return sanitize_question_for_prompt(question)

        # Use secure prompt builder with sanitization
        try:
            return create_safe_context_prompt(
                question=question,
                context_messages=context.messages,
                max_context_size=self.context_window
            )
        except Exception as e:
            logger.error(f"Error creating safe context prompt: {str(e)}")
            # Fallback to sanitized question only
            return sanitize_question_for_prompt(question)

    def should_use_context(self, question: str) -> bool:
        """
        Determine if question likely refers to previous context

        Args:
            question: User question

        Returns:
            True if question appears to reference previous queries
        """
        question_lower = question.lower().strip()

        # Strong indicators of context reference (pronouns and directives)
        strong_indicators = [
            "that", "it", "them", "those", "these",
            "also", "too", "same", "previous", "last"
        ]

        # Check for strong indicators
        for indicator in strong_indicators:
            if indicator in question_lower:
                return True

        # Modification keywords that indicate refining a previous query
        # Only trigger context if they START the question (e.g., "Filter by price")
        # Don't trigger if they appear in the middle (e.g., "Show filtered results")
        modification_keywords = [
            "filter", "sort", "order", "add", "include", "exclude", "remove"
        ]

        # Check if modification keywords START the question
        for keyword in modification_keywords:
            if question_lower.startswith(keyword):
                return True

        # Check for short questions (likely refinements) - but not if they're complete sentences
        words = question.split()
        if len(words) <= 3 and not question_lower.startswith(("show", "get", "list", "find", "select")):
            return True

        return False

    async def clear_context(
        self,
        session_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Clear conversation context for a session

        This doesn't delete messages, but could be used to mark a context boundary.
        For now, it's a placeholder for future functionality.

        Args:
            session_id: Chat session ID
            db: Database session

        Returns:
            True if successful
        """
        logger.info(f"Context clear requested for session {session_id}")
        # Note: For now, context is always retrieved from DB
        # Future: Could add a context boundary marker
        return True

    def format_context_for_display(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Format context for frontend display

        Args:
            context: Conversation context

        Returns:
            Formatted context for UI
        """
        return {
            "has_context": context.has_context,
            "window_size": context.context_window_size,
            "messages": [
                {
                    "question": msg["question"],
                    "sql": msg.get("sql", ""),
                    "success": msg.get("success", False),
                    "timestamp": msg.get("timestamp")
                }
                for msg in context.messages
            ]
        }


# Singleton instance
_memory_agent: Optional[ConversationalMemoryAgent] = None


def get_memory_agent(context_window: int = 3) -> ConversationalMemoryAgent:
    """
    Get or create singleton memory agent instance

    Args:
        context_window: Number of previous queries to include

    Returns:
        ConversationalMemoryAgent instance
    """
    global _memory_agent

    if _memory_agent is None:
        _memory_agent = ConversationalMemoryAgent(context_window=context_window)

    return _memory_agent
