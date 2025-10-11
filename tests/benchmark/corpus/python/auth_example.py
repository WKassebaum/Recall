"""Authentication and authorization utilities.

This module provides JWT-based authentication and role-based authorization.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt


class TokenManager:
    """Manage JWT tokens for user authentication."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize token manager.

        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT signing algorithm
        """
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, user_id: str, expires_delta: timedelta | None = None) -> str:
        """Create a new JWT token.

        Args:
            user_id: User identifier
            expires_delta: Token expiration time

        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[str]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class PasswordHasher:
    """Secure password hashing utilities."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password with salt.

        Args:
            password: Plain text password

        Returns:
            Hashed password with salt
        """
        salt = secrets.token_hex(32)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return f"{salt}${pwd_hash.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password
            hashed: Hashed password with salt

        Returns:
            True if password matches, False otherwise
        """
        try:
            salt, pwd_hash = hashed.split("$")
            new_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            )
            return new_hash.hex() == pwd_hash
        except ValueError:
            return False


class RoleChecker:
    """Role-based authorization utilities."""

    ROLE_HIERARCHY = {
        "admin": 3,
        "moderator": 2,
        "user": 1,
        "guest": 0,
    }

    @classmethod
    def has_permission(cls, user_role: str, required_role: str) -> bool:
        """Check if user has required permission level.

        Args:
            user_role: User's role
            required_role: Required role for action

        Returns:
            True if user has sufficient permission
        """
        user_level = cls.ROLE_HIERARCHY.get(user_role, 0)
        required_level = cls.ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level
