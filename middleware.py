"""
Middleware for security, rate limiting, and request processing
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging
import time
from typing import Callable

from config import settings
from security import verify_token, get_current_user_from_token

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_requests}/{settings.rate_limit_window}"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler"""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too many requests",
            "message": "تم تجاوز الحد المسموح من الطلبات. يرجى المحاولة لاحقاً",
            "retry_after": exc.retry_after
        }
    )


async def security_middleware(request: Request, call_next):
    """Security middleware for logging and basic security checks"""
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path} from {get_remote_address(request)}")

    # Add security headers
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Add HSTS in production
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Log response time
    process_time = time.time() - start_time
    logger.info(f"Request processed in {process_time:.3f}s")

    return response


async def authentication_middleware(request: Request, call_next):
    """Authentication middleware for protected routes"""
    # Skip authentication for certain paths
    public_paths = [
        "/",
        "/api/health",
        "/api/login",
        "/api/check-user",
        "/api/register",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]

    if request.url.path in public_paths:
        return await call_next(request)

    # Check for authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = authorization.split(" ")[1]
    user_data = get_current_user_from_token(token)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Add user data to request state
    request.state.user = user_data

    return await call_next(request)


def get_current_user(request: Request) -> dict:
    """Get current user from request state"""
    return getattr(request.state, 'user', None)


def require_role(required_role: str):
    """Decorator to require specific role"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )

            user = get_current_user(request)
            if not user or user.get('role') != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*required_roles: str):
    """Decorator to require any of the specified roles"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )

            user = get_current_user(request)
            if not user or user.get('role') not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator