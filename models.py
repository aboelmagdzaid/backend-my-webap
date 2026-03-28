"""
Database models for Accounting Office API
SQLAlchemy models for users, contacts, logs, tasks, payments, subscriptions, approvals, and support tooling
"""

import enum
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, enum.Enum):
    CLIENT = "client"
    WORKER = "worker"
    ADMIN = "admin"
    TECHNICAL_SUPPORT = "technical_support"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    user_number = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contacts = relationship("Contact", back_populates="user")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="contacts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    resource = Column(String(255), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SignInLog(Base):
    __tablename__ = "sign_in_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_number = Column(String(50), nullable=True)
    role = Column(String(50), nullable=True)
    success = Column(Boolean, default=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    task_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    due_date = Column(Date, nullable=True)
    attachments_json = Column(Text, nullable=True)
    latest_activity = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String(50), unique=True, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String(100), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    is_subscription_fee = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_name = Column(String(255), nullable=False)
    billing_cycle = Column(String(50), nullable=False, default="monthly")
    amount = Column(Numeric(12, 2), nullable=False)
    next_billing_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    auto_add_fee = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    approval_number = Column(String(50), unique=True, index=True, nullable=False)
    request_type = Column(String(100), nullable=False)
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    summary = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=True)
    decision_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResourceVersion(Base):
    __tablename__ = "resource_versions"

    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer, nullable=False)
    version_number = Column(Integer, nullable=False)
    change_type = Column(String(50), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemSnapshot(Base):
    __tablename__ = "system_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
