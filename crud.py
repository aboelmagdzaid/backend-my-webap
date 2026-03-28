"""
CRUD operations for database entities.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditLog,
    Contact,
    Payment,
    PaymentStatus,
    ResourceVersion,
    SignInLog,
    Subscription,
    SystemSnapshot,
    Task,
    TaskComment,
    TaskStatus,
    User,
    UserRole,
)
from security import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserCRUD:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_user_number(db: Session, user_number: str) -> Optional[User]:
        return db.query(User).filter(User.user_number == user_number).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_users_by_role(db: Session, role: UserRole):
        return db.query(User).filter(User.role == role).all()

    @staticmethod
    def list_users(db: Session, role: Optional[UserRole] = None):
        query = db.query(User)
        if role:
            query = query.filter(User.role == role)
        return query.order_by(User.created_at.desc()).all()

    @staticmethod
    def create_user(db: Session, user_number: str, name: str, role: UserRole, password: Optional[str] = None, email: Optional[str] = None) -> User:
        user = User(
            user_number=user_number,
            name=name,
            role=role,
            password_hash=hash_password(password) if password else None,
            email=email,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, user_number: str, password: str) -> Optional[User]:
        user = UserCRUD.get_user_by_user_number(db, user_number)
        if not user or not user.is_active:
            return None
        if user.role == UserRole.CLIENT:
            return user
        if user.password_hash and verify_password(password, user.password_hash):
            return user
        return None


class ContactCRUD:
    @staticmethod
    def create_contact(db: Session, name: str, email: str, phone: str, subject: str, message: str, user_id: Optional[int] = None) -> Contact:
        contact = Contact(user_id=user_id, name=name, email=email, phone=phone, subject=subject, message=message)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def get_contact_by_id(db: Session, contact_id: int) -> Optional[Contact]:
        return db.query(Contact).filter(Contact.id == contact_id).first()

    @staticmethod
    def get_contacts(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None, user_id: Optional[int] = None):
        query = db.query(Contact)
        if status:
            query = query.filter(Contact.status == status)
        if user_id:
            query = query.filter(Contact.user_id == user_id)
        return query.order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()


class AuditLogCRUD:
    @staticmethod
    def create_audit_log(db: Session, user_id: Optional[int], action: str, resource: str, resource_id: Optional[int] = None, details: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> AuditLog:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def get_audit_logs(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None, action: Optional[str] = None, resource: Optional[str] = None):
        query = db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource == resource)
        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


class SignInLogCRUD:
    @staticmethod
    def create(db: Session, user_id: Optional[int], user_number: str, role: Optional[str], success: bool, ip_address: Optional[str], user_agent: Optional[str]) -> SignInLog:
        row = SignInLog(user_id=user_id, user_number=user_number, role=role, success=success, ip_address=ip_address, user_agent=user_agent)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list(db: Session, limit: int = 100):
        return db.query(SignInLog).order_by(SignInLog.created_at.desc()).limit(limit).all()


class VersionCRUD:
    @staticmethod
    def create_version(db: Session, resource_type: str, resource_id: int, change_type: str, snapshot: dict[str, Any], changed_by_id: Optional[int]) -> ResourceVersion:
        last_version = db.query(ResourceVersion).filter(ResourceVersion.resource_type == resource_type, ResourceVersion.resource_id == resource_id).order_by(ResourceVersion.version_number.desc()).first()
        version_number = 1 if last_version is None else last_version.version_number + 1
        row = ResourceVersion(
            resource_type=resource_type,
            resource_id=resource_id,
            version_number=version_number,
            change_type=change_type,
            snapshot_json=json.dumps(snapshot, default=str, ensure_ascii=False),
            changed_by_id=changed_by_id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list_versions(db: Session, resource_type: str, resource_id: int):
        return db.query(ResourceVersion).filter(ResourceVersion.resource_type == resource_type, ResourceVersion.resource_id == resource_id).order_by(ResourceVersion.version_number.desc()).all()


class TaskCRUD:
    @staticmethod
    def create_task(db: Session, task_number: str, title: str, task_type: str, description: str, client_id: int, created_by_id: int, worker_id: Optional[int] = None, due_date=None, attachments=None) -> Task:
        task = Task(
            task_number=task_number,
            title=title,
            task_type=task_type,
            description=description,
            client_id=client_id,
            created_by_id=created_by_id,
            worker_id=worker_id,
            due_date=due_date,
            attachments_json=json.dumps(attachments or [], ensure_ascii=False),
            latest_activity="Task created",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task(db: Session, task_id: int, include_deleted: bool = False) -> Optional[Task]:
        query = db.query(Task).filter(Task.id == task_id)
        if not include_deleted:
            query = query.filter(Task.is_deleted.is_(False))
        return query.first()

    @staticmethod
    def list_tasks(db: Session, *, client_id: Optional[int] = None, worker_id: Optional[int] = None, status: Optional[TaskStatus] = None, task_type: Optional[str] = None, include_deleted: bool = False):
        query = db.query(Task)
        if client_id:
            query = query.filter(Task.client_id == client_id)
        if worker_id:
            query = query.filter(Task.worker_id == worker_id)
        if status:
            query = query.filter(Task.status == status)
        if task_type:
            query = query.filter(Task.task_type == task_type)
        if not include_deleted:
            query = query.filter(Task.is_deleted.is_(False))
        return query.order_by(Task.created_at.desc()).all()

    @staticmethod
    def update_task(db: Session, task: Task, updates: dict[str, Any]) -> Task:
        for key, value in updates.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)
        task.latest_activity = "Task updated"
        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def soft_delete_task(db: Session, task: Task):
        task.is_deleted = True
        task.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def restore_task(db: Session, task: Task):
        task.is_deleted = False
        task.deleted_at = None
        db.commit()
        db.refresh(task)
        return task


class TaskCommentCRUD:
    @staticmethod
    def create_comment(db: Session, task_id: int, user_id: int, message: str) -> TaskComment:
        row = TaskComment(task_id=task_id, user_id=user_id, message=message)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list_comments(db: Session, task_id: int):
        return db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()


class PaymentCRUD:
    @staticmethod
    def create_payment(db: Session, payment_number: str, client_id: int, created_by_id: int, amount: Decimal, method: str, task_id: Optional[int] = None, due_date=None, notes: Optional[str] = None, status: PaymentStatus = PaymentStatus.PENDING, is_subscription_fee: bool = False) -> Payment:
        row = Payment(
            payment_number=payment_number,
            client_id=client_id,
            created_by_id=created_by_id,
            amount=amount,
            method=method,
            task_id=task_id,
            due_date=due_date,
            notes=notes,
            status=status,
            is_subscription_fee=is_subscription_fee,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_payment(db: Session, payment_id: int, include_deleted: bool = False) -> Optional[Payment]:
        query = db.query(Payment).filter(Payment.id == payment_id)
        if not include_deleted:
            query = query.filter(Payment.is_deleted.is_(False))
        return query.first()

    @staticmethod
    def list_payments(db: Session, client_id: Optional[int] = None, task_id: Optional[int] = None, status: Optional[PaymentStatus] = None, include_deleted: bool = False):
        query = db.query(Payment)
        if client_id:
            query = query.filter(Payment.client_id == client_id)
        if task_id:
            query = query.filter(Payment.task_id == task_id)
        if status:
            query = query.filter(Payment.status == status)
        if not include_deleted:
            query = query.filter(Payment.is_deleted.is_(False))
        return query.order_by(Payment.created_at.desc()).all()

    @staticmethod
    def update_status(db: Session, payment: Payment, status_value: PaymentStatus, approved_by_id: Optional[int] = None):
        payment.status = status_value
        payment.approved_by_id = approved_by_id
        if status_value == PaymentStatus.PAID:
            payment.paid_at = datetime.utcnow()
        payment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def soft_delete_payment(db: Session, payment: Payment):
        payment.is_deleted = True
        payment.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def restore_payment(db: Session, payment: Payment):
        payment.is_deleted = False
        payment.deleted_at = None
        db.commit()
        db.refresh(payment)
        return payment


class SubscriptionCRUD:
    @staticmethod
    def create_subscription(db: Session, client_id: int, plan_name: str, billing_cycle: str, amount: Decimal, next_billing_date, status: str = "active", auto_add_fee: bool = True) -> Subscription:
        row = Subscription(client_id=client_id, plan_name=plan_name, billing_cycle=billing_cycle, amount=amount, next_billing_date=next_billing_date, status=status, auto_add_fee=auto_add_fee)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_subscription(db: Session, subscription_id: int) -> Optional[Subscription]:
        return db.query(Subscription).filter(Subscription.id == subscription_id).first()

    @staticmethod
    def list_subscriptions(db: Session, client_id: Optional[int] = None):
        query = db.query(Subscription)
        if client_id:
            query = query.filter(Subscription.client_id == client_id)
        return query.order_by(Subscription.created_at.desc()).all()


class ApprovalCRUD:
    @staticmethod
    def create_approval(db: Session, approval_number: str, request_type: str, requested_by_id: int, summary: str, payload: Optional[dict[str, Any]] = None, task_id: Optional[int] = None, payment_id: Optional[int] = None) -> ApprovalRequest:
        row = ApprovalRequest(
            approval_number=approval_number,
            request_type=request_type,
            requested_by_id=requested_by_id,
            summary=summary,
            payload_json=json.dumps(payload or {}, default=str, ensure_ascii=False),
            task_id=task_id,
            payment_id=payment_id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_approval(db: Session, approval_id: int) -> Optional[ApprovalRequest]:
        return db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()

    @staticmethod
    def list_approvals(db: Session, status: Optional[ApprovalStatus] = None):
        query = db.query(ApprovalRequest)
        if status:
            query = query.filter(ApprovalRequest.status == status)
        return query.order_by(ApprovalRequest.created_at.desc()).all()

    @staticmethod
    def review_approval(db: Session, approval: ApprovalRequest, status_value: ApprovalStatus, reviewed_by_id: int, decision_notes: Optional[str] = None):
        approval.status = status_value
        approval.reviewed_by_id = reviewed_by_id
        approval.decision_notes = decision_notes
        approval.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def get_payload(approval: ApprovalRequest) -> dict[str, Any]:
        if not approval.payload_json:
            return {}
        try:
            return json.loads(approval.payload_json)
        except json.JSONDecodeError:
            return {}


class SnapshotCRUD:
    @staticmethod
    def create_snapshot(db: Session, name: str, notes: Optional[str], created_by_id: Optional[int]) -> SystemSnapshot:
        row = SystemSnapshot(name=name, notes=notes, created_by_id=created_by_id)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list_snapshots(db: Session):
        return db.query(SystemSnapshot).order_by(SystemSnapshot.created_at.desc()).all()
