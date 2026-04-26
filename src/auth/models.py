"""User model for authentication"""
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Index
from src.database.connection import Base


class User(Base):
    """Application user for authentication and resource ownership."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    # Set to True after an operator resets the password via the admin UI.
    # The login response surfaces this flag so the frontend forces a change
    # before any other action; the change-password endpoint clears it.
    must_change_password = Column(Boolean, default=False, nullable=False, server_default="0")
    # Phase A token versioning. JWTs issued while AUTH_TOKEN_VERSIONING_ENABLED
    # carry this value as the `pv` claim; bumping the column instantly
    # invalidates every outstanding token for the user. Bumped on password
    # change, admin reset, and (when their flags are on) deactivate / logout.
    password_version = Column(Integer, default=1, nullable=False, server_default="1")

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class PasswordResetToken(Base):
    """One-shot password reset token (Phase C of auth hardening).

    The plaintext token never lives in the DB — only the bcrypt hash.
    Tokens are single-use (used_at is set on redemption) and TTL-bounded
    (expires_at). Redemption verifies the bcrypt hash, expiry, and unused
    state in that order, then sets the new password and bumps
    password_version to invalidate any other live sessions.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_reset_token_user_used", "user_id", "used_at"),
    )
