import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db.models import Org, Plan, User
from packages.common.logging import get_logger
from services.api.deps import get_db


router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET", "")
log = get_logger("stripe-webhooks")


PLAN_WEEKLY_LIMITS = {"basic": 2, "pro": 3, "premium": 5}
PRICE_TO_PLAN = {
    price_id: plan_id
    for plan_id, price_id in {
        "basic": os.getenv("STRIPE_PRICE_BASIC"),
        "pro": os.getenv("STRIPE_PRICE_PRO"),
        "premium": os.getenv("STRIPE_PRICE_PREMIUM"),
    }.items()
    if price_id
}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", ".")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, endpoint_secret)
    except ValueError as exc:
        # Bad payload
        raise HTTPException(400, f"Invalid payload: {exc}")
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(400, f"Invalid signature: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(400, f"Invalid webhook: {exc}")

    event_type = event.get("type")
    log.debug("Received Stripe event", extra={"type": event_type})

    try:
        if event_type == "checkout.session.completed":
            handle_checkout_completed(db, event["data"]["object"])
        elif event_type in {"customer.subscription.updated", "subscription.updated"}:
            handle_subscription_updated(db, event["data"]["object"])
        elif event_type == "invoice.payment_failed":
            handle_invoice_payment_failed(db, event["data"]["object"])
        else:
            log.debug("Ignoring Stripe event", extra={"type": event_type})
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        log.exception("Failed processing Stripe webhook")
        raise HTTPException(500, "Failed to process webhook") from exc

    return {"received": True}


def handle_checkout_completed(db: Session, session: dict) -> None:
    plan_key = (session.get("metadata") or {}).get("planId")
    if not plan_key:
        raise HTTPException(400, "Missing plan metadata on checkout session")
    plan = plan_from_key(plan_key)
    if plan is None:
        raise HTTPException(400, f"Unknown planId '{plan_key}'")

    weekly_limit = PLAN_WEEKLY_LIMITS[plan_key]
    customer_id: Optional[str] = session.get("customer")
    subscription_id: Optional[str] = session.get("subscription")

    org = None
    if subscription_id:
        org = db.query(Org).filter(Org.stripe_subscription_id == subscription_id).one_or_none()
    if org is None and customer_id:
        org = db.query(Org).filter(Org.stripe_customer_id == customer_id).one_or_none()

    name = (
        ((session.get("customer_details") or {}).get("name"))
        or ((session.get("customer_details") or {}).get("email"))
        or session.get("customer_email")
        or f"Org {customer_id}" if customer_id else "New Org"
    )

    if org is None:
        org = Org(
            name=name,
            plan=plan,
            weekly_limit=weekly_limit,
            status="active",
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
        )
        db.add(org)
    else:
        org.name = name or org.name
        org.plan = plan
        org.weekly_limit = weekly_limit
        org.status = "active"
        if customer_id:
            org.stripe_customer_id = customer_id
        if subscription_id:
            org.stripe_subscription_id = subscription_id

    db.flush()

    email = (
        (session.get("customer_details") or {}).get("email")
        or session.get("customer_email")
    )
    if email:
        ensure_user_for_org(db, org.id, email)

    if subscription_id:
        update_subscription_metadata(subscription_id, org.id, plan_key)


def handle_subscription_updated(db: Session, subscription: dict) -> None:
    subscription_id = subscription.get("id")
    if not subscription_id:
        raise HTTPException(400, "Subscription payload missing id")

    org = db.query(Org).filter(Org.stripe_subscription_id == subscription_id).one_or_none()
    if org is None:
        metadata = subscription.get("metadata") or {}
        org_id = metadata.get("org_id") or metadata.get("orgId")
        if org_id:
            org = db.get(Org, int(org_id))
    if org is None:
        log.warning("No org found for subscription update", extra={"subscription_id": subscription_id})
        return

    plan_key = determine_plan_from_subscription(subscription)
    if not plan_key:
        log.warning(
            "Unable to determine plan for subscription update",
            extra={"subscription_id": subscription_id},
        )
        return

    plan = plan_from_key(plan_key)
    if plan is None:
        log.warning("Unknown plan key on subscription update", extra={"plan_key": plan_key})
        return

    org.plan = plan
    org.weekly_limit = PLAN_WEEKLY_LIMITS[plan_key]
    org.status = "active"


def handle_invoice_payment_failed(db: Session, invoice: dict) -> None:
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        log.warning("Invoice missing subscription id; cannot suspend org")
        return

    org = db.query(Org).filter(Org.stripe_subscription_id == subscription_id).one_or_none()
    if org is None:
        log.warning(
            "No org found for failed payment",
            extra={"subscription_id": subscription_id},
        )
        return

    org.status = "suspended"


def plan_from_key(plan_key: str) -> Optional[Plan]:
    try:
        return Plan(plan_key)
    except ValueError:
        return None


def ensure_user_for_org(db: Session, org_id: int, email: str) -> None:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(org_id=org_id, email=email, status="active")
        db.add(user)
    else:
        user.org_id = org_id
        if user.status != "active":
            user.status = "active"


def determine_plan_from_subscription(subscription: dict) -> Optional[str]:
    metadata = subscription.get("metadata") or {}
    plan_key = metadata.get("planId") or metadata.get("plan_id")
    if plan_key in PLAN_WEEKLY_LIMITS:
        return plan_key

    items = (subscription.get("items") or {}).get("data") or []
    for item in items:
        price = (item or {}).get("price") or {}
        price_id = price.get("id")
        if price_id and price_id in PRICE_TO_PLAN:
            return PRICE_TO_PLAN[price_id]
    return None


def update_subscription_metadata(subscription_id: str, org_id: int, plan_key: str) -> None:
    try:
        stripe.Subscription.modify(
            subscription_id,
            metadata={"org_id": str(org_id), "planId": plan_key},
        )
    except Exception as exc:
        log.warning(
            "Failed to update subscription metadata",
            extra={"subscription_id": subscription_id, "error": str(exc)},
        )
