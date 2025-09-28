"""
Credits API Router
Provides endpoints for viewing credit status, usage history, and managing credits.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from db.models import User, ActionType
from services.api.deps import get_db, get_current_user
from services.api.utils.credits import (
    get_credit_status,
    get_recent_usage,
    CREDIT_COSTS,
    PLAN_MONTHLY_CREDITS
)

router = APIRouter()

# Pydantic models for responses
class CreditStatus(BaseModel):
    available_credits: int
    used_this_period: int
    plan_limit: int
    usage_percentage: float
    period_start: str
    period_end: str
    plan: str
    usage_breakdown: dict
    costs: dict

class UsageEntry(BaseModel):
    timestamp: str
    action_type: str
    credits_used: int
    job_id: Optional[int]
    asset_id: Optional[int]
    metadata: dict

class UsageHistory(BaseModel):
    entries: List[UsageEntry]
    total_entries: int

class CreditPricing(BaseModel):
    action_costs: dict
    plan_limits: dict


@router.get("/status", response_model=CreditStatus)
def get_user_credit_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current credit status for the authenticated user"""
    return get_credit_status(db, current_user.id)


@router.get("/usage", response_model=UsageHistory)
def get_usage_history(
    days: int = Query(30, ge=1, le=90, description="Number of days of history to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage history for the authenticated user"""
    entries_data = get_recent_usage(db, current_user.id, days)
    
    entries = [
        UsageEntry(
            timestamp=entry["timestamp"],
            action_type=entry["action_type"],
            credits_used=entry["credits_used"],
            job_id=entry["job_id"],
            asset_id=entry["asset_id"],
            metadata=entry["metadata"]
        )
        for entry in entries_data
    ]
    
    return UsageHistory(
        entries=entries,
        total_entries=len(entries)
    )


@router.get("/pricing", response_model=CreditPricing)
def get_credit_pricing():
    """Get credit costs for different actions and plan limits"""
    return CreditPricing(
        action_costs={action.value: cost for action, cost in CREDIT_COSTS.items()},
        plan_limits={plan.value: limit for plan, limit in PLAN_MONTHLY_CREDITS.items()}
    )


@router.get("/check/{action_type}")
def check_action_credits(
    action_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if user has enough credits for a specific action"""
    try:
        action_enum = ActionType(action_type)
    except ValueError:
        valid_actions = [action.value for action in ActionType]
        return {
            "error": f"Invalid action type. Valid actions: {valid_actions}"
        }
    
    from services.api.utils.credits import check_credits_available
    
    has_credits = check_credits_available(db, current_user.id, action_enum)
    cost = CREDIT_COSTS.get(action_enum, 1)
    status = get_credit_status(db, current_user.id)
    
    return {
        "action_type": action_type,
        "has_credits": has_credits,
        "cost": cost,
        "available_credits": status["available_credits"],
        "sufficient": status["available_credits"] >= cost
    }