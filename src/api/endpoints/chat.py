"""Chat session endpoints for Database Guru"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.api.dependencies import get_db
from src.database.models import ChatSession, ChatMessage, DatabaseConnection, FileSource

from src.llm.conversational_memory_agent import get_memory_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response Models
class ChatSessionCreate(BaseModel):
    """Request model for creating a chat session"""
    name: str = Field(..., min_length=1, max_length=255)
    connection_ids: List[int] = Field(default_factory=list)
    file_source_ids: List[int] = Field(default_factory=list)
    user_id: Optional[str] = None


class ChatSessionUpdate(BaseModel):
    """Request model for updating a chat session"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    connection_ids: Optional[List[int]] = None
    file_source_ids: Optional[List[int]] = None


class ConnectionInfo(BaseModel):
    """Connection information for chat response"""
    id: int
    name: str
    database_type: str
    database_name: str


class FileSourceInfo(BaseModel):
    """File source information for chat response"""
    id: int
    name: str
    file_type: str
    original_filename: str
    row_count: Optional[int] = None


class ChatSessionResponse(BaseModel):
    """Response model for chat session"""
    id: str
    name: str
    user_id: Optional[str]
    active_connection_ids: List[int]
    connections: List[ConnectionInfo]
    active_file_source_ids: List[int] = Field(default_factory=list)
    file_sources: List[FileSourceInfo] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_active_at: str
    message_count: int = 0

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """Request model for creating a chat message"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    query_history_id: Optional[int] = None
    databases_used: Optional[List[dict]] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat message"""
    id: int
    chat_session_id: str
    role: str
    content: str
    query_history_id: Optional[int]
    databases_used: Optional[List[dict]]
    created_at: str

    class Config:
        from_attributes = True


# Endpoints
@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session"""
    try:
        # Validate connection IDs if provided
        if session_data.connection_ids:
            result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(session_data.connection_ids)
                )
            )
            valid_connections = result.scalars().all()

            if len(valid_connections) != len(session_data.connection_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more connection IDs are invalid"
                )

        # Validate file source IDs if provided
        if session_data.file_source_ids:
            file_result = await db.execute(
                select(FileSource).where(
                    FileSource.id.in_(session_data.file_source_ids),
                    FileSource.processing_status == 'ready',
                )
            )
            valid_files = file_result.scalars().all()
            if len(valid_files) != len(session_data.file_source_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more file source IDs are invalid or not ready"
                )

        # Create new chat session
        new_session = ChatSession(
            name=session_data.name,
            user_id=session_data.user_id,
            active_connection_ids=session_data.connection_ids,
            active_file_source_ids=session_data.file_source_ids or [],
        )

        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        # Get connection details
        connections = []
        if new_session.active_connection_ids:
            connection_ids = new_session.active_connection_ids
            if isinstance(connection_ids, int):
                connection_ids = [connection_ids]
            elif not isinstance(connection_ids, list):
                connection_ids = list(connection_ids) if connection_ids else []

            result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(connection_ids)
                )
            )
            connections = [
                ConnectionInfo(
                    id=conn.id,
                    name=conn.name,
                    database_type=conn.database_type,
                    database_name=conn.database_name,
                )
                for conn in result.scalars().all()
            ]

        # Get file source details
        file_sources = await _get_session_file_sources(new_session, db)

        # Ensure active_connection_ids in response is always a list
        active_conn_ids = new_session.active_connection_ids
        if isinstance(active_conn_ids, int):
            active_conn_ids = [active_conn_ids]
        elif not isinstance(active_conn_ids, list):
            active_conn_ids = list(active_conn_ids) if active_conn_ids else []

        return ChatSessionResponse(
            id=new_session.id,
            name=new_session.name,
            user_id=new_session.user_id,
            active_connection_ids=active_conn_ids,
            connections=connections,
            active_file_source_ids=new_session.active_file_source_ids or [],
            file_sources=file_sources,
            created_at=new_session.created_at.isoformat(),
            updated_at=new_session.updated_at.isoformat(),
            last_active_at=new_session.last_active_at.isoformat(),
            message_count=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat session: {str(e)}"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions"""
    try:
        query = select(ChatSession).order_by(desc(ChatSession.last_active_at))

        if user_id:
            query = query.where(ChatSession.user_id == user_id)

        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        sessions = result.scalars().all()

        # Build response with connection details
        response_sessions = []
        for session in sessions:
            # Get connection details
            connections = []
            if session.active_connection_ids:
                # Ensure active_connection_ids is a list (defensive against bad data)
                connection_ids = session.active_connection_ids
                if isinstance(connection_ids, int):
                    connection_ids = [connection_ids]
                elif not isinstance(connection_ids, list):
                    connection_ids = list(connection_ids) if connection_ids else []

                conn_result = await db.execute(
                    select(DatabaseConnection).where(
                        DatabaseConnection.id.in_(connection_ids)
                    )
                )
                connections = [
                    ConnectionInfo(
                        id=conn.id,
                        name=conn.name,
                        database_type=conn.database_type,
                        database_name=conn.database_name,
                    )
                    for conn in conn_result.scalars().all()
                ]

            # Count messages
            msg_count_result = await db.execute(
                select(ChatMessage).where(ChatMessage.chat_session_id == session.id)
            )
            message_count = len(msg_count_result.scalars().all())

            # Ensure active_connection_ids in response is always a list
            active_conn_ids = session.active_connection_ids
            if isinstance(active_conn_ids, int):
                active_conn_ids = [active_conn_ids]
            elif not isinstance(active_conn_ids, list):
                active_conn_ids = list(active_conn_ids) if active_conn_ids else []

            # Get file source details
            file_sources = await _get_session_file_sources(session, db)

            response_sessions.append(
                ChatSessionResponse(
                    id=session.id,
                    name=session.name,
                    user_id=session.user_id,
                    active_connection_ids=active_conn_ids,
                    connections=connections,
                    active_file_source_ids=session.active_file_source_ids or [],
                    file_sources=file_sources,
                    created_at=session.created_at.isoformat(),
                    updated_at=session.updated_at.isoformat(),
                    last_active_at=session.last_active_at.isoformat(),
                    message_count=message_count,
                )
            )

        return response_sessions

    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chat sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific chat session"""
    try:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Get connection details
        connections = []
        if session.active_connection_ids:
            # Ensure active_connection_ids is a list (defensive against bad data)
            connection_ids = session.active_connection_ids
            if isinstance(connection_ids, int):
                connection_ids = [connection_ids]
            elif not isinstance(connection_ids, list):
                connection_ids = list(connection_ids) if connection_ids else []

            conn_result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(connection_ids)
                )
            )
            connections = [
                ConnectionInfo(
                    id=conn.id,
                    name=conn.name,
                    database_type=conn.database_type,
                    database_name=conn.database_name,
                )
                for conn in conn_result.scalars().all()
            ]

        # Count messages
        msg_count_result = await db.execute(
            select(ChatMessage).where(ChatMessage.chat_session_id == session.id)
        )
        message_count = len(msg_count_result.scalars().all())

        # Ensure active_connection_ids in response is always a list
        active_conn_ids = session.active_connection_ids
        if isinstance(active_conn_ids, int):
            active_conn_ids = [active_conn_ids]
        elif not isinstance(active_conn_ids, list):
            active_conn_ids = list(active_conn_ids) if active_conn_ids else []

        # Get file source details
        file_sources = await _get_session_file_sources(session, db)

        return ChatSessionResponse(
            id=session.id,
            name=session.name,
            user_id=session.user_id,
            active_connection_ids=active_conn_ids,
            connections=connections,
            active_file_source_ids=session.active_file_source_ids or [],
            file_sources=file_sources,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            last_active_at=session.last_active_at.isoformat(),
            message_count=message_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat session: {str(e)}"
        )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    update_data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a chat session"""
    try:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Update fields
        if update_data.name is not None:
            session.name = update_data.name

        if update_data.connection_ids is not None:
            # Validate connection IDs
            conn_result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(update_data.connection_ids)
                )
            )
            valid_connections = conn_result.scalars().all()

            if len(valid_connections) != len(update_data.connection_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more connection IDs are invalid"
                )

            session.active_connection_ids = update_data.connection_ids

        session.updated_at = datetime.utcnow()
        session.last_active_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)

        # Get connection details
        connections = []
        if session.active_connection_ids:
            # Ensure active_connection_ids is a list (defensive against bad data)
            connection_ids = session.active_connection_ids
            if isinstance(connection_ids, int):
                connection_ids = [connection_ids]
            elif not isinstance(connection_ids, list):
                connection_ids = list(connection_ids) if connection_ids else []

            conn_result = await db.execute(
                select(DatabaseConnection).where(
                    DatabaseConnection.id.in_(connection_ids)
                )
            )
            connections = [
                ConnectionInfo(
                    id=conn.id,
                    name=conn.name,
                    database_type=conn.database_type,
                    database_name=conn.database_name,
                )
                for conn in conn_result.scalars().all()
            ]

        # Count messages
        msg_count_result = await db.execute(
            select(ChatMessage).where(ChatMessage.chat_session_id == session.id)
        )
        message_count = len(msg_count_result.scalars().all())

        # Ensure active_connection_ids in response is always a list
        active_conn_ids = session.active_connection_ids
        if isinstance(active_conn_ids, int):
            active_conn_ids = [active_conn_ids]
        elif not isinstance(active_conn_ids, list):
            active_conn_ids = list(active_conn_ids) if active_conn_ids else []

        return ChatSessionResponse(
            id=session.id,
            name=session.name,
            user_id=session.user_id,
            active_connection_ids=active_conn_ids,
            connections=connections,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            last_active_at=session.last_active_at.isoformat(),
            message_count=message_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update chat session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat session: {str(e)}"
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all associated messages"""
    try:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Delete all messages first (to avoid FK constraint issues)
        await db.execute(
            delete(ChatMessage).where(ChatMessage.chat_session_id == session_id)
        )

        # Now delete the session
        await db.delete(session)
        await db.commit()

        logger.info(f"Deleted chat session {session_id} and all associated messages")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {str(e)}"
        )


# Message endpoints
@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a chat session"""
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        if not session_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Get messages
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()

        return [
            ChatMessageResponse(
                id=msg.id,
                chat_session_id=msg.chat_session_id,
                role=msg.role,
                content=msg.content,
                query_history_id=msg.query_history_id,
                databases_used=msg.databases_used,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat messages: {str(e)}"
        )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat message"""
    try:
        # Verify session exists and update last_active_at
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Create message
        new_message = ChatMessage(
            chat_session_id=session_id,
            role=message_data.role,
            content=message_data.content,
            query_history_id=message_data.query_history_id,
            databases_used=message_data.databases_used,
        )

        db.add(new_message)

        # Update session last_active_at
        session.last_active_at = datetime.utcnow()

        await db.commit()
        await db.refresh(new_message)

        return ChatMessageResponse(
            id=new_message.id,
            chat_session_id=new_message.chat_session_id,
            role=new_message.role,
            content=new_message.content,
            query_history_id=new_message.query_history_id,
            databases_used=new_message.databases_used,
            created_at=new_message.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat message: {str(e)}"
        )


# Conversational Memory Endpoints
@router.get("/sessions/{session_id}/context")
async def get_conversation_context(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get conversational context for a chat session

    Returns the recent queries that will be used for context-aware generation.
    """
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Get memory agent and retrieve context
        memory_agent = get_memory_agent()
        context = await memory_agent.get_context(session_id, db)

        return {
            "session_id": session_id,
            "context": memory_agent.format_context_for_display(context),
            "window_size": context.context_window_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation context: {str(e)}"
        )


@router.delete("/sessions/{session_id}/context", status_code=status.HTTP_200_OK)
async def clear_conversation_context(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Clear conversational context for a chat session

    This deletes all messages in the session, providing a fresh start.
    The session itself is preserved.
    """
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Delete all messages in the session
        await db.execute(
            delete(ChatMessage).where(ChatMessage.chat_session_id == session_id)
        )
        await db.commit()

        logger.info(f"Cleared conversation context for session {session_id}")

        return {
            "success": True,
            "message": f"Cleared conversation context for session {session_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear conversation context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear conversation context: {str(e)}"
        )


# =============================================================================
# Phase 13: File Source Management Endpoints
# =============================================================================

class SessionFilesResponse(BaseModel):
    """Response for session file operations"""
    success: bool
    session_id: str
    active_file_source_ids: List[int]
    file_sources: List[FileSourceInfo]


@router.post("/sessions/{session_id}/files/{file_id}", response_model=SessionFilesResponse)
async def add_file_to_session(
    session_id: str,
    file_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a file source to a chat session (Phase 13).

    The file must exist and be in 'ready' status to be added.
    """
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Verify file source exists and is ready
        file_result = await db.execute(
            select(FileSource).where(
                FileSource.id == file_id,
                FileSource.processing_status == 'ready',
            )
        )
        file_source = file_result.scalar_one_or_none()

        if not file_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File source {file_id} not found or not ready"
            )

        # Add file to session's active files
        current_files = session.active_file_source_ids or []
        if file_id not in current_files:
            session.active_file_source_ids = current_files + [file_id]
            session.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(session)

            logger.info(f"Added file source {file_id} to session {session_id}")

        # Get all active file sources for response
        file_sources = await _get_session_file_sources(session, db)

        return SessionFilesResponse(
            success=True,
            session_id=session_id,
            active_file_source_ids=session.active_file_source_ids or [],
            file_sources=file_sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add file to session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add file to session: {str(e)}"
        )


@router.delete("/sessions/{session_id}/files/{file_id}", response_model=SessionFilesResponse)
async def remove_file_from_session(
    session_id: str,
    file_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a file source from a chat session (Phase 13).

    This only removes the file from the session's active sources.
    The file itself is not deleted.
    """
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Remove file from session's active files
        current_files = session.active_file_source_ids or []
        if file_id in current_files:
            session.active_file_source_ids = [f for f in current_files if f != file_id]
            session.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(session)

            logger.info(f"Removed file source {file_id} from session {session_id}")

        # Get remaining active file sources for response
        file_sources = await _get_session_file_sources(session, db)

        return SessionFilesResponse(
            success=True,
            session_id=session_id,
            active_file_source_ids=session.active_file_source_ids or [],
            file_sources=file_sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove file from session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove file from session: {str(e)}"
        )


@router.get("/sessions/{session_id}/files", response_model=SessionFilesResponse)
async def get_session_files(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active file sources for a chat session (Phase 13).
    """
    try:
        # Verify session exists
        session_result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found"
            )

        # Get active file sources
        file_sources = await _get_session_file_sources(session, db)

        return SessionFilesResponse(
            success=True,
            session_id=session_id,
            active_file_source_ids=session.active_file_source_ids or [],
            file_sources=file_sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session files: {str(e)}"
        )


async def _get_session_file_sources(
    session: ChatSession,
    db: AsyncSession,
) -> List[FileSourceInfo]:
    """Helper to get file source info for a session."""
    file_sources = []
    file_ids = session.active_file_source_ids or []

    if file_ids:
        result = await db.execute(
            select(FileSource).where(
                FileSource.id.in_(file_ids),
                FileSource.processing_status == 'ready',
            )
        )
        for fs in result.scalars().all():
            file_sources.append(FileSourceInfo(
                id=fs.id,
                name=fs.name,
                file_type=fs.file_type,
                original_filename=fs.original_filename,
                row_count=fs.row_count,
            ))

    return file_sources
