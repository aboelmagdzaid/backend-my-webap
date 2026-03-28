"""
Middleware for security, rate limiting, and request processing
"""

from functools import wraps
import logging
import time
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from security import get_current_user_from_token

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_requests}/{settings.rate_limit_window} seconds"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("Rate limit exceeded for %s", get_remote_address(request))
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too many requests",
            "message": "?? ????? ???? ??????? ?? ???????. ???? ???????? ??????",
        },
    )


async def security_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    logger.info("%s %s completed in %.3fs", request.method, request.url.path, time.time() - start_time)
    return response


async def authentication_middleware(request: Request, call_next):
    public_exact_paths = {
        "/",
        "/api/health",
        "/api/login",
        "/api/register",
        "/api/contact",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/test-simple",
    }
    public_prefixes = (
        "/api/check-user/",
    )

    if request.url.path in public_exact_paths or request.url.path.startswith(public_prefixes):
        return await call_next(request)

    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    user_data = get_current_user_from_token(token)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    request.state.user = user_data
    return await call_next(request)


def get_current_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)


def require_role(required_role: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if request is None:
                request = next((value for value in kwargs.values() if isinstance(value, Request)), None)
            if request is None:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Request object not found")

            user = get_current_user(request)
            if not user or user.get("role") != required_role:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_role(*required_roles: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if request is None:
                request = next((value for value in kwargs.values() if isinstance(value, Request)), None)
            if request is None:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Request object not found")

            user = get_current_user(request)
            if not user or user.get("role") not in required_roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
