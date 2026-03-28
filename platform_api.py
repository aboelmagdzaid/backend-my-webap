
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crud import (
    ApprovalCRUD,
    AuditLogCRUD,
    PaymentCRUD,
    SignInLogCRUD,
    SnapshotCRUD,
    SubscriptionCRUD,
    TaskCommentCRUD,
    TaskCRUD,
    UserCRUD,
    VersionCRUD,
)
from database import get_db
from middleware import get_current_user
from models import ApprovalStatus, PaymentStatus, TaskStatus, UserRole

router = APIRouter(prefix="/api", tags=["platform"])


class TaskCreateRequest(BaseModel):
    title: str
    task_type: str
    description: str
    client_id: int
    worker_id: Optional[int] = None
    due_date: Optional[date] = None
    attachments: List[str] = []


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    task_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    worker_id: Optional[int] = None
    due_date: Optional[date] = None
    latest_activity: Optional[str] = None
    attachments: Optional[List[str]] = None


class CommentCreateRequest(BaseModel):
    message: str


class PaymentCreateRequest(BaseModel):
    client_id: int
    amount: Decimal
    method: str
    task_id: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class SubscriptionCreateRequest(BaseModel):
    client_id: int
    plan_name: str
    billing_cycle: str = "monthly"
    amount: Decimal
    next_billing_date: Optional[date] = None
    status: str = "active"
    auto_add_fee: bool = True


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalStatus
    notes: Optional[str] = None


class SnapshotCreateRequest(BaseModel):
    name: str
    notes: Optional[str] = None

def now_code(prefix: str) -> str:
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"


def current_user_or_401(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def require_roles(request: Request, *roles: str) -> dict:
    user = current_user_or_401(request)
    if user.get("role") not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def to_user_dict(user) -> dict:
    return {"id": user.id, "name": user.name, "user_number": user.user_number, "email": user.email, "role": user.role.value, "is_active": user.is_active, "created_at": user.created_at.isoformat() if user.created_at else None}


def to_task_dict(task, db: Session) -> dict:
    comments = TaskCommentCRUD.list_comments(db, task.id)
    return {
        "id": task.id,
        "task_number": task.task_number,
        "title": task.title,
        "task_type": task.task_type,
        "description": task.description,
        "status": task.status.value,
        "client_id": task.client_id,
        "worker_id": task.worker_id,
        "created_by_id": task.created_by_id,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "attachments": task.attachments_json,
        "latest_activity": task.latest_activity,
        "is_deleted": task.is_deleted,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "comments": [{"id": c.id, "task_id": c.task_id, "user_id": c.user_id, "message": c.message, "created_at": c.created_at.isoformat() if c.created_at else None} for c in comments],
    }


def to_payment_dict(payment) -> dict:
    return {"id": payment.id, "payment_number": payment.payment_number, "client_id": payment.client_id, "task_id": payment.task_id, "created_by_id": payment.created_by_id, "approved_by_id": payment.approved_by_id, "amount": float(payment.amount), "method": payment.method, "status": payment.status.value, "due_date": payment.due_date.isoformat() if payment.due_date else None, "paid_at": payment.paid_at.isoformat() if payment.paid_at else None, "notes": payment.notes, "is_subscription_fee": payment.is_subscription_fee, "is_deleted": payment.is_deleted, "created_at": payment.created_at.isoformat() if payment.created_at else None}

def to_subscription_dict(subscription) -> dict:
    return {"id": subscription.id, "client_id": subscription.client_id, "plan_name": subscription.plan_name, "billing_cycle": subscription.billing_cycle, "amount": float(subscription.amount), "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None, "status": subscription.status, "auto_add_fee": subscription.auto_add_fee}


def to_approval_dict(approval) -> dict:
    return {"id": approval.id, "approval_number": approval.approval_number, "request_type": approval.request_type, "status": approval.status.value, "requested_by_id": approval.requested_by_id, "reviewed_by_id": approval.reviewed_by_id, "task_id": approval.task_id, "payment_id": approval.payment_id, "summary": approval.summary, "payload_json": approval.payload_json, "decision_notes": approval.decision_notes, "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None, "created_at": approval.created_at.isoformat() if approval.created_at else None}


def advance_billing_date(current: Optional[date], billing_cycle: str) -> date:
    base_date = current or date.today()
    if billing_cycle == "yearly":
        return base_date + timedelta(days=365)
    if billing_cycle == "quarterly":
        return base_date + timedelta(days=90)
    return base_date + timedelta(days=30)


@router.get("/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    user = UserCRUD.get_user_by_id(db, int(current["user_id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_user_dict(user)


@router.get("/users")
async def list_users(request: Request, role: Optional[UserRole] = None, db: Session = Depends(get_db)):
    require_roles(request, "admin", "technical_support")
    return [to_user_dict(user) for user in UserCRUD.list_users(db, role=role)]


@router.get("/tasks")
async def list_tasks(request: Request, status_filter: Optional[TaskStatus] = None, task_type: Optional[str] = None, client_id: Optional[int] = None, worker_id: Optional[int] = None, include_deleted: bool = False, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    effective_client = client_id
    effective_worker = worker_id
    if current["role"] == "client":
        effective_client = int(current["user_id"])
    elif current["role"] == "worker":
        effective_worker = int(current["user_id"])
    elif current["role"] not in {"admin", "technical_support"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    tasks = TaskCRUD.list_tasks(db, client_id=effective_client, worker_id=effective_worker, status=status_filter, task_type=task_type, include_deleted=include_deleted)
    return [to_task_dict(task, db) for task in tasks]

@router.post("/tasks")
async def create_task(request: Request, payload: TaskCreateRequest, db: Session = Depends(get_db)):
    current = require_roles(request, "client", "admin", "technical_support")
    if current["role"] == "client" and int(current["user_id"]) != payload.client_id:
        raise HTTPException(status_code=403, detail="Clients can only create their own tasks")
    task = TaskCRUD.create_task(db, now_code("TASK"), payload.title, payload.task_type, payload.description, payload.client_id, int(current["user_id"]), payload.worker_id, payload.due_date, payload.attachments)
    VersionCRUD.create_version(db, "task", task.id, "created", {"title": task.title, "status": task.status.value}, int(current["user_id"]))
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "task_created", "task", task.id, task.title, request.client.host)
    return to_task_dict(task, db)


@router.get("/tasks/{task_id}")
async def get_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    task = TaskCRUD.get_task(db, task_id, include_deleted=True)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current["role"] == "client" and task.client_id != int(current["user_id"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current["role"] == "worker" and task.worker_id != int(current["user_id"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return to_task_dict(task, db)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, request: Request, payload: TaskUpdateRequest, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    task = TaskCRUD.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    updates = payload.model_dump(exclude_none=True)
    if "attachments" in updates:
        updates["attachments_json"] = updates.pop("attachments")

    if current["role"] == "worker":
        if task.worker_id != int(current["user_id"]):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        approval = ApprovalCRUD.create_approval(db, now_code("APR"), "task_update", int(current["user_id"]), f"Worker requested update for task {task.task_number}", payload=updates, task_id=task.id)
        AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "task_update_requested", "approval", approval.id, approval.summary, request.client.host)
        return {"message": "Task update sent for approval", "approval": to_approval_dict(approval)}

    require_roles(request, "admin", "technical_support")
    VersionCRUD.create_version(db, "task", task.id, "updated_before", {"title": task.title, "description": task.description, "status": task.status.value}, int(current["user_id"]))
    updated = TaskCRUD.update_task(db, task, updates)
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "task_updated", "task", task.id, updated.latest_activity, request.client.host)
    return to_task_dict(updated, db)


@router.post("/tasks/{task_id}/comments")
async def add_task_comment(task_id: int, request: Request, payload: CommentCreateRequest, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    task = TaskCRUD.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    comment = TaskCommentCRUD.create_comment(db, task.id, int(current["user_id"]), payload.message)
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "task_comment_added", "task", task.id, payload.message[:120], request.client.host)
    return {"id": comment.id, "message": comment.message, "created_at": comment.created_at}

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    current = require_roles(request, "admin", "technical_support")
    task = TaskCRUD.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    TaskCRUD.soft_delete_task(db, task)
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "task_soft_deleted", "task", task.id, task.task_number, request.client.host)
    return {"message": "Task soft deleted"}


@router.post("/recovery/tasks/{task_id}/restore")
async def restore_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    current = require_roles(request, "technical_support")
    task = TaskCRUD.get_task(db, task_id, include_deleted=True)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    TaskCRUD.restore_task(db, task)
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "task_restored", "task", task.id, task.task_number, request.client.host)
    return {"message": "Task restored"}


@router.get("/payments")
async def list_payments(request: Request, status_filter: Optional[PaymentStatus] = None, client_id: Optional[int] = None, task_id: Optional[int] = None, include_deleted: bool = False, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    effective_client = client_id
    if current["role"] == "client":
        effective_client = int(current["user_id"])
    elif current["role"] not in {"worker", "admin", "technical_support"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    payments = PaymentCRUD.list_payments(db, client_id=effective_client, task_id=task_id, status=status_filter, include_deleted=include_deleted)
    return [to_payment_dict(payment) for payment in payments]


@router.post("/payments")
async def create_payment(request: Request, payload: PaymentCreateRequest, db: Session = Depends(get_db)):
    current = require_roles(request, "worker", "admin", "technical_support")
    is_admin_like = current["role"] in {"admin", "technical_support"}
    status_value = PaymentStatus.APPROVED if is_admin_like else PaymentStatus.PENDING
    payment = PaymentCRUD.create_payment(db, now_code("PAY"), payload.client_id, int(current["user_id"]), payload.amount, payload.method, payload.task_id, payload.due_date, payload.notes, status=status_value)
    VersionCRUD.create_version(db, "payment", payment.id, "created", {"amount": float(payment.amount), "status": payment.status.value}, int(current["user_id"]))
    if not is_admin_like:
        approval = ApprovalCRUD.create_approval(db, now_code("APR"), "payment_create", int(current["user_id"]), f"Worker added payment {payment.payment_number}", {"payment_id": payment.id}, payment_id=payment.id, task_id=payload.task_id)
        AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "payment_create_requested", "approval", approval.id, approval.summary, request.client.host)
        return {"message": "Payment submitted for approval", "payment": to_payment_dict(payment), "approval": to_approval_dict(approval)}
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "payment_created", "payment", payment.id, payment.payment_number, request.client.host)
    return to_payment_dict(payment)


@router.post("/payments/{payment_id}/pay")
async def mark_payment_as_paid(payment_id: int, request: Request, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    payment = PaymentCRUD.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if current["role"] == "client" and payment.client_id != int(current["user_id"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current["role"] not in {"client", "admin", "technical_support"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    PaymentCRUD.update_status(db, payment, PaymentStatus.PAID, approved_by_id=int(current["user_id"]))
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "payment_marked_paid", "payment", payment.id, payment.payment_number, request.client.host)
    return to_payment_dict(payment)

@router.delete("/payments/{payment_id}")
async def delete_payment(payment_id: int, request: Request, db: Session = Depends(get_db)):
    current = require_roles(request, "admin", "technical_support")
    payment = PaymentCRUD.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    PaymentCRUD.soft_delete_payment(db, payment)
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "payment_soft_deleted", "payment", payment.id, payment.payment_number, request.client.host)
    return {"message": "Payment soft deleted"}


@router.post("/recovery/payments/{payment_id}/restore")
async def restore_payment(payment_id: int, request: Request, db: Session = Depends(get_db)):
    current = require_roles(request, "technical_support")
    payment = PaymentCRUD.get_payment(db, payment_id, include_deleted=True)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    PaymentCRUD.restore_payment(db, payment)
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "payment_restored", "payment", payment.id, payment.payment_number, request.client.host)
    return {"message": "Payment restored"}


@router.get("/subscriptions")
async def list_subscriptions(request: Request, client_id: Optional[int] = None, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    effective_client = client_id
    if current["role"] == "client":
        effective_client = int(current["user_id"])
    elif current["role"] not in {"admin", "technical_support"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    subs = SubscriptionCRUD.list_subscriptions(db, effective_client)
    return [to_subscription_dict(sub) for sub in subs]


@router.post("/subscriptions")
async def create_subscription(request: Request, payload: SubscriptionCreateRequest, db: Session = Depends(get_db)):
    current = require_roles(request, "admin", "technical_support")
    subscription = SubscriptionCRUD.create_subscription(db, payload.client_id, payload.plan_name, payload.billing_cycle, payload.amount, payload.next_billing_date or date.today(), payload.status, payload.auto_add_fee)
    VersionCRUD.create_version(db, "subscription", subscription.id, "created", {"plan_name": subscription.plan_name, "amount": float(subscription.amount)}, int(current["user_id"]))
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "subscription_created", "subscription", subscription.id, subscription.plan_name, request.client.host)
    return to_subscription_dict(subscription)


@router.post("/subscriptions/{subscription_id}/generate-fee")
async def generate_subscription_fee(subscription_id: int, request: Request, db: Session = Depends(get_db)):
    current = require_roles(request, "admin", "technical_support")
    subscription = SubscriptionCRUD.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    payment = PaymentCRUD.create_payment(db, now_code("PAY"), subscription.client_id, int(current["user_id"]), subscription.amount, "subscription_auto", None, subscription.next_billing_date, f"Auto-generated fee for {subscription.plan_name}", status=PaymentStatus.APPROVED, is_subscription_fee=True)
    subscription.next_billing_date = advance_billing_date(subscription.next_billing_date, subscription.billing_cycle)
    db.commit()
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "subscription_fee_generated", "payment", payment.id, payment.payment_number, request.client.host)
    return {"subscription": to_subscription_dict(subscription), "payment": to_payment_dict(payment)}


@router.get("/approvals")
async def list_approvals(request: Request, status_filter: Optional[ApprovalStatus] = None, db: Session = Depends(get_db)):
    require_roles(request, "admin", "technical_support")
    return [to_approval_dict(row) for row in ApprovalCRUD.list_approvals(db, status_filter)]


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(approval_id: int, request: Request, payload: "ApprovalDecisionRequest", db: Session = Depends(get_db)):
    current = require_roles(request, "admin", "technical_support")
    approval = ApprovalCRUD.get_approval(db, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    ApprovalCRUD.review_approval(db, approval, payload.decision, int(current["user_id"]), payload.notes)
    if approval.request_type == "task_update" and approval.task_id and payload.decision == ApprovalStatus.APPROVED:
        task = TaskCRUD.get_task(db, approval.task_id)
        if task:
            updates = ApprovalCRUD.get_payload(approval)
            VersionCRUD.create_version(db, "task", task.id, "approved_update_before", {"title": task.title, "description": task.description, "status": task.status.value}, int(current["user_id"]))
            TaskCRUD.update_task(db, task, updates)
    if approval.request_type == "payment_create" and approval.payment_id:
        payment = PaymentCRUD.get_payment(db, approval.payment_id)
        if payment:
            PaymentCRUD.update_status(db, payment, PaymentStatus.APPROVED if payload.decision == ApprovalStatus.APPROVED else PaymentStatus.REJECTED, approved_by_id=int(current["user_id"]))
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "approval_reviewed", "approval", approval.id, f"Decision: {payload.decision.value}", request.client.host)
    return to_approval_dict(approval)

@router.get("/audit-logs")
async def get_audit_logs(request: Request, user_id: Optional[int] = None, action: Optional[str] = None, resource: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    if current["role"] in {"admin", "technical_support"}:
        logs = AuditLogCRUD.get_audit_logs(db, limit=limit, user_id=user_id, action=action, resource=resource)
    else:
        logs = AuditLogCRUD.get_audit_logs(db, limit=limit, user_id=int(current["user_id"]))
    return [{"id": log.id, "user_id": log.user_id, "action": log.action, "resource": log.resource, "resource_id": log.resource_id, "details": log.details, "ip_address": log.ip_address, "created_at": log.created_at.isoformat() if log.created_at else None} for log in logs]


@router.get("/signins")
async def get_signins(request: Request, limit: int = 100, db: Session = Depends(get_db)):
    require_roles(request, "technical_support")
    rows = SignInLogCRUD.list(db, limit=limit)
    return [{"id": row.id, "user_id": row.user_id, "user_number": row.user_number, "role": row.role, "success": row.success, "ip_address": row.ip_address, "user_agent": row.user_agent, "created_at": row.created_at.isoformat() if row.created_at else None} for row in rows]


@router.get("/recovery/tasks")
async def recovery_tasks(request: Request, db: Session = Depends(get_db)):
    require_roles(request, "technical_support")
    tasks = TaskCRUD.list_tasks(db, include_deleted=True)
    return [to_task_dict(task, db) for task in tasks if task.is_deleted]


@router.get("/recovery/payments")
async def recovery_payments(request: Request, db: Session = Depends(get_db)):
    require_roles(request, "technical_support")
    payments = PaymentCRUD.list_payments(db, include_deleted=True)
    return [to_payment_dict(payment) for payment in payments if payment.is_deleted]


@router.get("/snapshots")
async def list_snapshots(request: Request, db: Session = Depends(get_db)):
    require_roles(request, "technical_support")
    return [{"id": row.id, "name": row.name, "notes": row.notes, "created_by_id": row.created_by_id, "created_at": row.created_at.isoformat() if row.created_at else None} for row in SnapshotCRUD.list_snapshots(db)]


@router.post("/snapshots")
async def create_snapshot(request: Request, payload: SnapshotCreateRequest, db: Session = Depends(get_db)):
    current = require_roles(request, "technical_support")
    row = SnapshotCRUD.create_snapshot(db, payload.name, payload.notes, int(current["user_id"]))
    AuditLogCRUD.create_audit_log(db, int(current["user_id"]), "snapshot_created", "snapshot", row.id, row.name, request.client.host)
    return {"id": row.id, "name": row.name, "notes": row.notes, "created_at": row.created_at}


@router.get("/reports/summary")
async def reports_summary(request: Request, db: Session = Depends(get_db)):
    current = current_user_or_401(request)
    tasks = TaskCRUD.list_tasks(db, client_id=int(current["user_id"]) if current["role"] == "client" else None, worker_id=int(current["user_id"]) if current["role"] == "worker" else None)
    payments = PaymentCRUD.list_payments(db, client_id=int(current["user_id"]) if current["role"] == "client" else None)
    return {
        "tasks_total": len(tasks),
        "tasks_pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
        "tasks_in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
        "tasks_completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        "payments_total": len(payments),
        "payments_due_total": float(sum(p.amount for p in payments if p.status in {PaymentStatus.PENDING, PaymentStatus.APPROVED})),
        "payments_paid_total": float(sum(p.amount for p in payments if p.status == PaymentStatus.PAID)),
    }
