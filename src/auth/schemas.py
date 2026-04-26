"""Pydantic schemas for authentication"""
import re
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# Passwords that satisfy length/complexity but are still trivially guessable.
_COMMON_PASSWORDS = frozenset({
    "password123", "password1234", "admin12345", "letmein1234",
    "welcome1234", "changeme123", "qwerty12345", "abc12345678",
})


def validate_password_complexity(v: str) -> str:
    """Shared password complexity check.

    Reused by `UserCreate` (self-service) and `AdminUserCreate` (admin
    endpoints) so the rules can't drift between the two paths.
    """
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit.")
    if v.lower() in _COMMON_PASSWORDS:
        raise ValueError("This password is too common. Please choose a stronger one.")
    return v


class UserCreate(BaseModel):
    """Request model for user registration"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)


class UserLogin(BaseModel):
    """Request model for user login"""
    username: str = Field(..., description="Username or email")
    password: str


class UserResponse(BaseModel):
    """Response model for user info"""
    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    # True after an operator-driven password reset; the frontend uses this to
    # route the user into a forced-change screen before letting them do
    # anything else with the session.
    must_change_password: bool = False

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response model for JWT token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    """Request model for self-service password change."""
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)


