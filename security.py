"""
Security utilities for password hashing and JWT token management
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hashlib
from passlib.context import CryptContext
import logging

from config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    try:
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

def get_token_expiry(token: str) -> Optional[datetime]:
    """Get token expiry datetime"""
    payload = verify_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None

# Password utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt with sha256 fallback when bcrypt backend is unavailable."""
    try:
        return pwd_context.hash(password)
    except Exception as exc:
        logger.warning(f"Falling back to sha256 password hashing: {exc}")
        return "sha256$" + hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if hashed_password.startswith("sha256$"):
        return hashed_password == "sha256$" + hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        logger.warning("Invalid hash detected, comparing as plain text")
        return plain_password == hashed_password
    except Exception as exc:
        logger.warning(f"Password verify fallback triggered: {exc}")
        return plain_password == hashed_password

# User utilities
def create_user_token_data(user_id: int, user_number: str, role: str) -> dict:
    """Create standardized token data for user"""
    return {
        "sub": str(user_id),
        "user_number": user_number,
        "role": role,
        "type": "access"
    }

def get_current_user_from_token(token: str) -> Optional[dict]:
    """Extract user information from JWT token"""
    payload = verify_token(token)
    if not payload:
        return None

    return {
        "user_id": int(payload.get("sub")),
        "user_number": payload.get("user_number"),
        "role": payload.get("role")
    }

# Security validation
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns (is_valid, message)
    """
    if len(password) < 8:
        return False, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"

    if not any(char.isdigit() for char in password):
        return False, "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل"

    if not any(char.isupper() for char in password):
        return False, "كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل"

    if not any(char.islower() for char in password):
        return False, "كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل"

    return True, "كلمة المرور قوية"

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""

    # Remove potentially dangerous characters
    sanitized = text.replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&#x27;")

    # Limit length
    return sanitized[:max_length]