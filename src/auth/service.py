"""Authentication service — password hashing, JWT creation/validation, user CRUD"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user registration, login, and JWT token management."""

    def __init__(self, settings: Settings):
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_minutes = settings.JWT_EXPIRATION_MINUTES

    # ── Password helpers ──────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    # ── JWT helpers ───────────────────────────────────────────────────

    def create_access_token(self, user_id: int, username: str) -> tuple[str, int]:
        """Create JWT token. Returns (token, expires_in_seconds)."""
        expires_delta = timedelta(minutes=self.expiration_minutes)
        expire = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, int(expires_delta.total_seconds())

    def decode_token(self, token: str) -> Optional[dict]:
        """Decode and validate JWT token. Returns payload or None."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    # ── User CRUD ─────────────────────────────────────────────────────

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username_or_email(self, db: AsyncSession, identifier: str) -> Optional[User]:
        """Look up user by username or email (for login)."""
        result = await db.execute(
            select(User).where(
                or_(User.username == identifier, User.email == identifier)
            )
        )
        return result.scalar_one_or_none()

    async def register(self, db: AsyncSession, email: str, username: str, password: str) -> User:
        """Register a new user. Raises ValueError if email/username taken."""
        existing = await db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email or username already registered")

        user = User(
            email=email,
            username=username,
            hashed_password=self.hash_password(password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"User registered: {username} ({email})")
        return user

    async def authenticate(self, db: AsyncSession, username: str, password: str) -> Optional[User]:
        """Validate credentials. Returns User or None."""
        user = await self.get_user_by_username_or_email(db, username)
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
