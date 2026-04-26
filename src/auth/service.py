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


def bump_password_version(user: User) -> None:
    """Increment ``password_version`` so every outstanding JWT for this user
    is rejected on its next request. Safe to call regardless of whether
    AUTH_TOKEN_VERSIONING_ENABLED is on — the bump is a cheap counter
    increment that has no effect when verification ignores the claim.

    Callers are responsible for committing the surrounding transaction.
    """
    current = int(getattr(user, "password_version", 1) or 1)
    user.password_version = current + 1


async def check_password_history(
    db: AsyncSession,
    user: User,
    new_password: str,
    *,
    depth: int,
) -> bool:
    """Return True when ``new_password`` matches one of the user's last
    ``depth`` passwords (current + history). Caller decides what to do.

    Bcrypt compares are expensive, so we cap the lookup at ``depth`` rows
    and short-circuit on the first match. ``depth <= 0`` disables the check.
    """
    if depth <= 0:
        return False
    # Always reject if it matches the *current* hash, regardless of depth.
    if user.hashed_password and bcrypt.checkpw(
        new_password.encode("utf-8"), user.hashed_password.encode("utf-8")
    ):
        return True
    from src.auth.models import PasswordHistory  # local import to avoid cycle
    rows = await db.execute(
        select(PasswordHistory.hashed_password)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.replaced_at.desc())
        .limit(depth)
    )
    for previous in rows.scalars().all():
        if bcrypt.checkpw(new_password.encode("utf-8"), previous.encode("utf-8")):
            return True
    return False


async def record_password_history(
    db: AsyncSession,
    user: User,
    *,
    depth: int,
) -> None:
    """Append the user's *current* hash to history before it's overwritten,
    and trim the table back to ``depth`` rows so it stays bounded.

    No-op when depth <= 0 — keeps the table empty when the feature is off.
    Caller writes the new hash to ``user.hashed_password`` after this call.
    """
    if depth <= 0:
        return
    from src.auth.models import PasswordHistory  # local import to avoid cycle
    if user.hashed_password:
        db.add(PasswordHistory(user_id=user.id, hashed_password=user.hashed_password))
        await db.flush()
    # Trim: keep the most recent ``depth`` rows, delete the rest.
    rows = await db.execute(
        select(PasswordHistory.id)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.replaced_at.desc())
    )
    ids = list(rows.scalars().all())
    if len(ids) > depth:
        from sqlalchemy import delete
        await db.execute(
            delete(PasswordHistory).where(PasswordHistory.id.in_(ids[depth:]))
        )


async def count_active_admins(db: AsyncSession) -> int:
    """Count users who are both is_admin=True and is_active=True. Used by the
    admin-quorum guard (Phase D3) to block locking out the last admin."""
    from sqlalchemy import func as _func
    rows = await db.execute(
        select(_func.count())
        .select_from(User)
        .where(User.is_admin.is_(True), User.is_active.is_(True))
    )
    return int(rows.scalar() or 0)

logger = logging.getLogger(__name__)

# Pre-computed dummy hash for constant-time authentication (prevents timing attacks)
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode("utf-8")


class AuthService:
    """Handles user registration, login, and JWT token management."""

    def __init__(self, settings: Settings):
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_minutes = settings.JWT_EXPIRATION_MINUTES
        # Phase A — token versioning. Read once at construction time so a
        # mid-session config change doesn't half-stamp the claim. Cheap to
        # rebuild the service on a settings reload.
        self.token_versioning_enabled = bool(getattr(settings, "AUTH_TOKEN_VERSIONING_ENABLED", False))

    # ── Password helpers ──────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    # ── JWT helpers ───────────────────────────────────────────────────

    def create_access_token(
        self,
        user_id: int,
        username: str,
        *,
        password_version: Optional[int] = None,
    ) -> tuple[str, int]:
        """Create JWT token. Returns (token, expires_in_seconds).

        When AUTH_TOKEN_VERSIONING_ENABLED is on and a ``password_version`` is
        provided, the JWT carries a ``pv`` claim that get_current_user will
        compare against the user's current value. Tokens minted while the
        flag was off carry no ``pv`` and are accepted as legacy until they
        expire — the flip is non-destructive.
        """
        expires_delta = timedelta(minutes=self.expiration_minutes)
        expire = datetime.now(timezone.utc) + expires_delta
        payload: dict = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        if self.token_versioning_enabled and password_version is not None:
            payload["pv"] = int(password_version)
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
        await db.flush()
        await db.refresh(user)
        logger.info(f"User registered: {username} ({email})")
        return user

    async def authenticate(self, db: AsyncSession, username: str, password: str) -> Optional[User]:
        """Validate credentials. Returns User or None.

        Always runs bcrypt comparison to prevent timing-based user enumeration.
        """
        user = await self.get_user_by_username_or_email(db, username)
        hash_to_check = user.hashed_password if user else _DUMMY_HASH
        password_valid = self.verify_password(password, hash_to_check)
        if not user or not password_valid:
            return None
        if not user.is_active:
            return None
        return user
