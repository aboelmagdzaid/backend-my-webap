"""
Database models for Accounting Office API
SQLAlchemy models for users, contacts, and other entities
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User role enumeration"""
    CLIENT = "client"
    WORKER = "worker"
    ADMIN = "admin"
    TECHNICAL_SUPPORT = "technical_support"


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    user_number = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)  # NULL for clients who don't need password
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contacts = relationship("Contact", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, user_number={self.user_number}, role={self.role})>"


class Contact(Base):
    """Contact form submissions"""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="contacts")

    def __repr__(self):
        return f"<Contact(id={self.id}, subject={self.subject}, status={self.status})>"


class AuditLog(Base):
    """Audit log for important actions"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    resource = Column(String(255), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"