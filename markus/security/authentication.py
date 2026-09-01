"""
Markus AI — Authentication

Simple session-based authentication with role management.
Uses JWT tokens for API authentication.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours for local-first use


class User:
    """User model."""

    def __init__(self, id: str, username: str, hashed_password: str, role: str = "admin"):
        self.id = id
        self.username = username
        self.hashed_password = hashed_password
        self.role = role
        self.created_at = datetime.now().isoformat()


class AuthManager:
    """
    Local authentication manager.

    For the initial build, uses an in-memory user store with
    JWT tokens. Can be upgraded to Better Auth + OAuth later.
    """

    def __init__(self):
        self._users: dict[str, User] = {}
        self._sessions: dict[str, dict] = {}

        # Create default admin user
        self._create_default_user()
        logger.info("Auth Manager initialized")

    def _create_default_user(self):
        """Create a default admin user for local-first use."""
        user_id = str(uuid4())
        hashed = pwd_context.hash("markus")
        user = User(id=user_id, username="admin", hashed_password=hashed, role="admin")
        self._users[user.username] = user
        logger.info("Default admin user created (username: admin, password: markus)")

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate a user and return a JWT token."""
        user = self._users.get(username)
        if not user or not pwd_context.verify(password, user.hashed_password):
            return None

        token = self._create_token(user)
        logger.info(f"User authenticated: {username}")
        return token

    def _create_token(self, user: User) -> str:
        """Create a JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
        }
        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify a JWT token and return the payload."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    def register(self, username: str, password: str, role: str = "user") -> Optional[User]:
        """Register a new user."""
        if username in self._users:
            return None

        user_id = str(uuid4())
        hashed = pwd_context.hash(password)
        user = User(id=user_id, username=username, hashed_password=hashed, role=role)
        self._users[user.username] = user
        logger.info(f"User registered: {username} (role: {role})")
        return user

    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self._users.get(username)

    def list_users(self) -> list[dict]:
        """List all users (without sensitive data)."""
        return [
            {"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at}
            for u in self._users.values()
        ]


# Singleton
auth_manager = AuthManager()
