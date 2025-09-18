from fastapi import APIRouter, Request, HTTPException
import os, stripe

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET", "")

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", ".")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    try:
        stripe.Webhook.construct_event(payload, sig, endpoint_secret)
    except Exception as e:
        raise HTTPException(400, f"Invalid webhook: {e}")
    # TODO: handle checkout.session.completed, subscription.updated, invoice.payment_failed
    return {"received": True}
