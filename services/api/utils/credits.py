"""
Credit Management System
Handles credit tracking, usage logging, and quota enforcement for the recontent platform.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from db.models import (
    CreditBalance, UsageLog, ActionType, User, Org, Plan
)
from packages.common.logging import get_logger

log = get_logger("credits")

# Credit costs for different actions
CREDIT_COSTS = {
    ActionType.IMAGE_GENERATION: 2,
    ActionType.IMAGE_EDITING: 1,
    ActionType.CONTENT_GENERATION: 1,
    ActionType.POST_COMBINATION: 3,
    ActionType.SOCIAL_POSTS: 1,
}

# Monthly credit limits by plan
PLAN_MONTHLY_CREDITS = {
    Plan.BASIC: 50,
    Plan.PRO: 200,
    Plan.PREMIUM: 500,
}


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits for an action"""
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits: need {required}, have {available}")


def get_current_period_dates() -> tuple[datetime, datetime]:
    """Get the start and end dates for the current monthly billing period"""
    now = datetime.utcnow()
    # Start on the 1st of the current month
    period_start = datetime(now.year, now.month, 1)
    # End on the 1st of next month
    if now.month == 12:
        period_end = datetime(now.year + 1, 1, 1)
    else:
        period_end = datetime(now.year, now.month + 1, 1)
    
    return period_start, period_end


def get_or_create_credit_balance(db: Session, org_id: int) -> CreditBalance:
    """Get or create the credit balance record for an org"""
    period_start, period_end = get_current_period_dates()
    
    balance = db.query(CreditBalance).filter(CreditBalance.org_id == org_id).first()
    
    if not balance:
        # Get org to determine plan
        org = db.get(Org, org_id)
        if not org:
            raise ValueError(f"Org {org_id} not found")
        
        initial_credits = PLAN_MONTHLY_CREDITS.get(org.plan, 50)
        
        balance = CreditBalance(
            org_id=org_id,
            available_credits=initial_credits,
            used_this_period=0,
            period_start=period_start,
            period_end=period_end
        )
        db.add(balance)
        db.flush()
    else:
        # Check if we need to reset for a new period
        if balance.period_end <= datetime.utcnow():
            org = db.get(Org, org_id)
            new_credits = PLAN_MONTHLY_CREDITS.get(org.plan, 50)
            
            balance.available_credits = new_credits
            balance.used_this_period = 0
            balance.period_start = period_start
            balance.period_end = period_end
            balance.updated_at = datetime.utcnow()
    
    return balance


def check_credits_available(db: Session, user_id: int, action_type: ActionType) -> bool:
    """Check if user has enough credits for the specified action"""
    user = db.get(User, user_id)
    if not user:
        return False
    
    cost = CREDIT_COSTS.get(action_type, 1)
    balance = get_or_create_credit_balance(db, user.org_id)
    
    return balance.available_credits >= cost


def consume_credits(
    db: Session, 
    user_id: int, 
    action_type: ActionType,
    job_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> UsageLog:
    """
    Consume credits for an action and log the usage.
    Raises InsufficientCreditsError if not enough credits available.
    """
    user = db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    cost = CREDIT_COSTS.get(action_type, 1)
    balance = get_or_create_credit_balance(db, user.org_id)
    
    if balance.available_credits < cost:
        raise InsufficientCreditsError(cost, balance.available_credits)
    
    # Deduct credits
    balance.available_credits -= cost
    balance.used_this_period += cost
    balance.updated_at = datetime.utcnow()
    
    # Log the usage
    usage_log = UsageLog(
        user_id=user_id,
        org_id=user.org_id,
        action_type=action_type,
        credits_used=cost,
        job_id=job_id,
        asset_id=asset_id,
        extra_data=metadata or {}
    )
    
    db.add(usage_log)
    
    log.info(f"Credits consumed", extra={
        "user_id": user_id,
        "org_id": user.org_id,
        "action_type": action_type.value,
        "credits_used": cost,
        "remaining_credits": balance.available_credits
    })
    
    return usage_log


def get_credit_status(db: Session, user_id: int) -> Dict:
    """Get detailed credit status for a user"""
    user = db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    balance = get_or_create_credit_balance(db, user.org_id)
    
    # Get usage breakdown for current period
    period_start, period_end = get_current_period_dates()
    
    usage_breakdown = db.query(
        UsageLog.action_type,
        func.sum(UsageLog.credits_used).label('total_credits')
    ).filter(
        and_(
            UsageLog.org_id == user.org_id,
            UsageLog.timestamp >= period_start,
            UsageLog.timestamp < period_end
        )
    ).group_by(UsageLog.action_type).all()
    
    breakdown_dict = {
        action_type.value: int(total_credits) 
        for action_type, total_credits in usage_breakdown
    }
    
    # Get org plan details
    org = db.get(Org, user.org_id)
    plan_limit = PLAN_MONTHLY_CREDITS.get(org.plan, 50)
    
    return {
        "available_credits": balance.available_credits,
        "used_this_period": balance.used_this_period,
        "plan_limit": plan_limit,
        "usage_percentage": (balance.used_this_period / plan_limit * 100) if plan_limit > 0 else 0,
        "period_start": balance.period_start.isoformat(),
        "period_end": balance.period_end.isoformat(),
        "plan": org.plan.value,
        "usage_breakdown": breakdown_dict,
        "costs": {action.value: cost for action, cost in CREDIT_COSTS.items()}
    }


def get_recent_usage(db: Session, user_id: int, days: int = 30) -> list:
    """Get recent usage history for a user"""
    user = db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    usage_logs = db.query(UsageLog).filter(
        and_(
            UsageLog.user_id == user_id,
            UsageLog.timestamp >= since_date
        )
    ).order_by(UsageLog.timestamp.desc()).limit(100).all()
    
    return [
        {
            "timestamp": log.timestamp.isoformat(),
            "action_type": log.action_type.value,
            "credits_used": log.credits_used,
            "job_id": log.job_id,
            "asset_id": log.asset_id,
            "metadata": log.extra_data
        }
        for log in usage_logs
    ]


def refund_credits(
    db: Session,
    user_id: int,
    action_type: ActionType,
    job_id: Optional[int] = None,
    reason: str = "refund"
) -> bool:
    """
    Refund credits for a failed or cancelled operation.
    Returns True if refund was successful.
    """
    user = db.get(User, user_id)
    if not user:
        return False
    
    cost = CREDIT_COSTS.get(action_type, 1)
    balance = get_or_create_credit_balance(db, user.org_id)
    
    # Add credits back
    balance.available_credits += cost
    balance.used_this_period = max(0, balance.used_this_period - cost)
    balance.updated_at = datetime.utcnow()
    
    # Log the refund
    refund_log = UsageLog(
        user_id=user_id,
        org_id=user.org_id,
        action_type=action_type,
        credits_used=-cost,  # Negative for refund
        job_id=job_id,
        extra_data={"type": "refund", "reason": reason}
    )
    
    db.add(refund_log)
    
    log.info(f"Credits refunded", extra={
        "user_id": user_id,
        "org_id": user.org_id,
        "action_type": action_type.value,
        "credits_refunded": cost,
        "new_balance": balance.available_credits,
        "reason": reason
    })
    
    return True