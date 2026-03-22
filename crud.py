"""
CRUD operations for database entities
User, Contact, and Audit log operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from models import User, Contact, AuditLog, UserRole
from security import hash_password, verify_password

logger = logging.getLogger(__name__)


# User CRUD operations
class UserCRUD:
    """User CRUD operations"""

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_user_number(db: Session, user_number: str) -> Optional[User]:
        """Get user by user number"""
        return db.query(User).filter(User.user_number == user_number).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_users_by_role(db: Session, role: UserRole) -> List[User]:
        """Get all users with specific role"""
        return db.query(User).filter(User.role == role).all()

    @staticmethod
    def create_user(
        db: Session,
        user_number: str,
        name: str,
        role: UserRole,
        password: Optional[str] = None,
        email: Optional[str] = None
    ) -> User:
        """Create new user"""
        # Hash password if provided
        password_hash = hash_password(password) if password else None

        user = User(
            user_number=user_number,
            name=name,
            role=role,
            password_hash=password_hash,
            email=email
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Created user: {user.user_number} with role {role}")
        return user

    @staticmethod
    def authenticate_user(db: Session, user_number: str, password: str) -> Optional[User]:
        """Authenticate user with user number and password"""
        user = UserCRUD.get_user_by_user_number(db, user_number)

        if not user:
            return None

        # Clients don't need password
        if user.role == UserRole.CLIENT:
            return user

        # Other roles require password verification
        if user.password_hash and verify_password(password, user.password_hash):
            return user

        return None

    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
        """Update user information"""
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if key == "password" and value:
                setattr(user, "password_hash", hash_password(value))
            elif hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        logger.info(f"Updated user: {user.user_number}")
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Delete user"""
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            return False

        db.delete(user)
        db.commit()

        logger.info(f"Deleted user: {user.user_number}")
        return True


# Contact CRUD operations
class ContactCRUD:
    """Contact CRUD operations"""

    @staticmethod
    def create_contact(
        db: Session,
        name: str,
        email: str,
        phone: str,
        subject: str,
        message: str,
        user_id: Optional[int] = None
    ) -> Contact:
        """Create new contact submission"""
        contact = Contact(
            user_id=user_id,
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )

        db.add(contact)
        db.commit()
        db.refresh(contact)

        logger.info(f"Created contact: {contact.id} - {contact.subject}")
        return contact

    @staticmethod
    def get_contact_by_id(db: Session, contact_id: int) -> Optional[Contact]:
        """Get contact by ID"""
        return db.query(Contact).filter(Contact.id == contact_id).first()

    @staticmethod
    def get_contacts(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Contact]:
        """Get contacts with optional filtering"""
        query = db.query(Contact)

        if status:
            query = query.filter(Contact.status == status)
        if user_id:
            query = query.filter(Contact.user_id == user_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_contact_status(db: Session, contact_id: int, status: str) -> Optional[Contact]:
        """Update contact status"""
        contact = ContactCRUD.get_contact_by_id(db, contact_id)
        if not contact:
            return None

        contact.status = status
        contact.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(contact)

        logger.info(f"Updated contact {contact_id} status to {status}")
        return contact

    @staticmethod
    def delete_contact(db: Session, contact_id: int) -> bool:
        """Delete contact"""
        contact = ContactCRUD.get_contact_by_id(db, contact_id)
        if not contact:
            return False

        db.delete(contact)
        db.commit()

        logger.info(f"Deleted contact: {contact_id}")
        return True


# Audit Log CRUD operations
class AuditLogCRUD:
    """Audit log CRUD operations"""

    @staticmethod
    def create_audit_log(
        db: Session,
        user_id: Optional[int],
        action: str,
        resource: str,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create audit log entry"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        return audit_log

    @staticmethod
    def get_audit_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None
    ) -> List[AuditLog]:
        """Get audit logs with optional filtering"""
        query = db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource == resource)

        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()