"""
Production-ready FastAPI Backend for Accounting Office Web App
Complete API server with database, authentication, and security features
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded
import logging
from typing import Optional

from config import settings
from database import init_database, get_db, close_database_connections
from models import User, UserRole
from crud import UserCRUD, ContactCRUD, AuditLogCRUD
from security import (
    create_access_token,
    create_user_token_data,
)
from platform_api import router as platform_router
from middleware import (
    limiter,
    rate_limit_exceeded_handler,
    security_middleware,
    authentication_middleware,
    get_current_user,
    require_role,
    require_any_role
)
from logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger("app.main")

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Accounting Office API...")

    # Initialize database
    try:
        init_database()
        db = next(get_db())
        try:
            defaults = [
                ("CL-2401", "Delta Supplies", UserRole.CLIENT, None, "client@example.com"),
                ("US-3021", "Ahmed Sameh", UserRole.WORKER, "123456", "worker@example.com"),
                ("AD-9001", "System Admin", UserRole.ADMIN, "123456", "admin@example.com"),
                ("SP-4401", "Tech Support", UserRole.TECHNICAL_SUPPORT, "123456", "support@example.com"),
            ]
            created_any = False
            for user_number, name, role, password, email in defaults:
                if not UserCRUD.get_user_by_user_number(db, user_number):
                    UserCRUD.create_user(db, user_number, name, role, password, email)
                    created_any = True
            if created_any:
                logger.info("Seeded default users")
        finally:
            db.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down Accounting Office API...")
    await close_database_connections()

# FastAPI App
app = FastAPI(
    title=settings.app_name,
    description="Production-ready API for accounting office management system",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.middleware("http")(security_middleware)
app.middleware("http")(authentication_middleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.include_router(platform_router)

# ============ Pydantic Models ============

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime, timedelta

class LoginRequest(BaseModel):
    user_number: str
    password: str = ""

    @field_validator('password')
    @classmethod
    def password_must_be_valid(cls, v):
        """Allow empty password for clients"""
        return v or ""

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict
    expires_in: int

class RegisterRequest(BaseModel):
    user_number: str
    name: str
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.CLIENT

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    subject: str
    message: str

class ContactResponse(BaseModel):
    message: str
    status: str
    contact_id: int

class UserResponse(BaseModel):
    id: int
    name: str
    user_number: str
    email: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime

class ContactListResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    subject: str
    message: str
    status: str
    created_at: datetime
    user: Optional[UserResponse]

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: datetime

# ============ Mock Database ============
# In production, use a real database like PostgreSQL

USERS_DB = {
    "10001": {  # Client registration number
        "id": 1,
        "name": "شركة النيل للتجارة",
        "user_number": "10001",
        "password": "client123",
        "role": "client",
        "email": "client@example.com"
    },
    "20001": {  # Worker mobile number
        "id": 2,
        "name": "أحمد علي محمد",
        "user_number": "20001",
        "password": "worker123",
        "role": "worker",
        "email": "worker@example.com"
    },
    "30001": {  # Admin number
        "id": 3,
        "name": "مدير النظام",
        "user_number": "30001",
        "password": "admin123",
        "role": "admin",
        "email": "admin@example.com"
    },
    "40001": {  # Technical Support number
        "id": 4,
        "name": "فريق الدعم الفني",
        "user_number": "40001",
        "password": "support123",
        "role": "technical_support",
        "email": "support@example.com"
    }
}

CONTACTS_DB = []

# ============ API Endpoints ============


@app.get("/api/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity test"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "unhealthy",
        version=settings.app_version,
        database=db_status,
        timestamp=datetime.utcnow()
    )

@app.get("/api/check-user/{user_number}")
@limiter.limit("10/minute")
async def check_user(request: Request, user_number: str, db: Session = Depends(get_db)):
    """Check if user exists and return their role (used by frontend)"""
    try:
        user = UserCRUD.get_user_by_user_number(db, user_number)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المستخدم غير موجود"
            )

        # Log access attempt
        AuditLogCRUD.create_audit_log(
            db=db,
            user_id=user.id,
            action="user_check",
            resource="user",
            resource_id=user.id,
            ip_address=request.client.host,
            details=f"Checked user role: {user.role.value}"
        )

        # Return user info without sensitive data
        user_response = {
            "id": user.id,
            "name": user.name,
            "user_number": user.user_number,
            "role": user.role.value,
            "is_active": user.is_active
        }

        return {"user": user_response}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking user {user_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في الخادم"
        )

@app.post("/api/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint with role-based authentication"""
    try:
        user = UserCRUD.authenticate_user(db, login_data.user_number, login_data.password)

        if not user:
            # Log failed login attempt
            AuditLogCRUD.create_audit_log(
                db=db,
                user_id=None,
                action="login_failed",
                resource="auth",
                ip_address=request.client.host,
                details=f"Failed login attempt for user_number: {login_data.user_number}"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="رقم المستخدم أو كلمة المرور غير صحيحة"
            )

        # Create access token
        token_data = create_user_token_data(user.id, user.user_number, user.role.value)
        access_token = create_access_token(token_data)

        # Log successful login
        AuditLogCRUD.create_audit_log(
            db=db,
            user_id=user.id,
            action="login_success",
            resource="auth",
            ip_address=request.client.host,
            details=f"User {user.user_number} logged in with role {user.role.value}"
        )

        # Remove password hash from response
        user_response = {
            "id": user.id,
            "name": user.name,
            "user_number": user.user_number,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response,
            expires_in=settings.access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for user {login_data.user_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في الخادم"
        )

@app.post("/api/register", response_model=LoginResponse)
@limiter.limit("3/minute")
async def register(request: Request, register_data: RegisterRequest, db: Session = Depends(get_db)):
    """User registration endpoint"""
    try:
        # Check if user number already exists
        existing_user = UserCRUD.get_user_by_user_number(db, register_data.user_number)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="رقم المستخدم مستخدم بالفعل"
            )

        # Create new user
        user = UserCRUD.create_user(
            db=db,
            user_number=register_data.user_number,
            name=register_data.name,
            role=register_data.role,
            password=register_data.password,
            email=register_data.email
        )

        # Create access token
        token_data = create_user_token_data(user.id, user.user_number, user.role.value)
        access_token = create_access_token(token_data)

        # Log registration
        AuditLogCRUD.create_audit_log(
            db=db,
            user_id=user.id,
            action="user_registered",
            resource="user",
            resource_id=user.id,
            ip_address=request.client.host,
            details=f"New user registered: {user.user_number} with role {user.role.value}"
        )

        user_response = {
            "id": user.id,
            "name": user.name,
            "user_number": user.user_number,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response,
            expires_in=settings.access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في التسجيل"
        )

@app.post("/api/contact", response_model=ContactResponse)
@limiter.limit("10/minute")
async def submit_contact(request: Request, contact_data: ContactRequest, db: Session = Depends(get_db)):
    """Contact form submission endpoint"""
    try:
        # Get user if authenticated
        user_id = None
        current_user = get_current_user(request)
        if current_user:
            user_id = current_user.get("user_id")

        # Create contact
        contact = ContactCRUD.create_contact(
            db=db,
            name=contact_data.name,
            email=contact_data.email,
            phone=contact_data.phone,
            subject=contact_data.subject,
            message=contact_data.message,
            user_id=user_id
        )

        # Log contact submission
        AuditLogCRUD.create_audit_log(
            db=db,
            user_id=user_id,
            action="contact_submitted",
            resource="contact",
            resource_id=contact.id,
            ip_address=request.client.host,
            details=f"Contact form submitted: {contact.subject}"
        )

        return ContactResponse(
            message="تم استقبال رسالتك بنجاح. سنتواصل معك قريباً",
            status="success",
            contact_id=contact.id
        )

    except Exception as e:
        logger.error(f"Contact submission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في إرسال الرسالة"
        )

@app.get("/api/contacts", response_model=List[ContactListResponse])
@require_any_role("admin", "technical_support")
async def get_contacts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all contacts (admin and support staff only)"""
    try:
        contacts = ContactCRUD.get_contacts(
            db=db,
            skip=skip,
            limit=limit,
            status=status_filter
        )

        # Log access
        current_user = get_current_user(request)
        AuditLogCRUD.create_audit_log(
            db=db,
            user_id=current_user.get("user_id"),
            action="contacts_viewed",
            resource="contact",
            ip_address=request.client.host,
            details=f"Viewed {len(contacts)} contacts"
        )

        return contacts

    except Exception as e:
        logger.error(f"Error fetching contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في استرجاع البيانات"
        )

@app.get("/api/users/{user_id}", response_model=UserResponse)
@require_role("admin")
async def get_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Get user details (admin only)"""
    try:
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المستخدم غير موجود"
            )

        # Log access
        current_user = get_current_user(request)
        AuditLogCRUD.create_audit_log(
            db=db,
            user_id=current_user.get("user_id"),
            action="user_viewed",
            resource="user",
            resource_id=user.id,
            ip_address=request.client.host
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في استرجاع البيانات"
        )

@app.get("/test-simple")
async def test_simple():
    """Simple test endpoint without dependencies"""
    return {"message": "Simple test works", "timestamp": datetime.utcnow()}

# ============ Error Handlers ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "خطأ داخلي في الخادم",
            "status_code": 500,
            "path": str(request.url)
        }
    )

# ============ Run Configuration ============
if __name__ == "__main__":
    import uvicorn

    # Run with: python main.py
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.debug,
        workers=settings.workers
    )
