"""
Stripe payment routes:
  POST /payments/create-checkout-session — create a Stripe Checkout for subscription
  POST /payments/webhook — handle Stripe webhook events (idempotent)
"""
import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from supabase import Client
from app.config import settings
from app.db.session import get_service_db
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Request / Response models ────────────────────────────────

class CheckoutRequest(BaseModel):
    """Body for creating a checkout session."""
    pass  # manager_id and email come from the JWT


class CheckoutResponse(BaseModel):
    checkout_url: str


# ── Helpers ──────────────────────────────────────────────────

def _is_duplicate_event(db: Client, event_id: str, event_type: str) -> bool:
    """Returns True if this Stripe event was already processed (idempotency)."""
    try:
        db.table("stripe_events").insert({
            "event_id": event_id,
            "event_type": event_type,
        }).execute()
        return False
    except Exception:
        return True


def _get_or_create_stripe_customer(email: str, manager_id: str) -> str:
    """Find existing Stripe customer by email or create a new one."""
    existing = stripe.Customer.list(email=email, limit=1)
    if existing.data:
        return existing.data[0].id

    customer = stripe.Customer.create(
        email=email,
        metadata={"manager_id": manager_id},
    )
    return customer.id


# ── Routes ───────────────────────────────────────────────────

@router.post("/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db),
):
    """
    Create a Stripe Checkout Session with:
    - 14-day free trial
    - $1 card verification (setup fee)
    - Subscription to the configured price
    """
    manager_id = user["sub"]
    email = user.get("email", "")

    # Check if already subscribed
    existing = (
        db.table("subscriptions")
        .select("id, status")
        .eq("manager_id", manager_id)
        .in_("status", ["trialing", "active"])
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription.",
        )

    customer_id = _get_or_create_stripe_customer(email, manager_id)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        mode="subscription",
        line_items=[
            # $1 one-time card verification fee (must match subscription currency)
            {
                "price_data": {
                    "currency": "cad",
                    "product_data": {"name": "Card Verification Fee"},
                    "unit_amount": 100,  # $1.00 CAD
                },
                "quantity": 1,
            },
            # Recurring subscription
            {
                "price": settings.STRIPE_PRICE_ID,
                "quantity": 1,
            },
        ],
        subscription_data={
            "trial_period_days": 14,
            "metadata": {"manager_id": manager_id},
        },
        metadata={"manager_id": manager_id},
        success_url=f"{settings.LANDING_PAGE_URL}/pricing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.LANDING_PAGE_URL}/pricing?canceled=true",
    )

    return CheckoutResponse(checkout_url=session.url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Client = Depends(get_service_db),
):
    """
    Handle Stripe webhook events. Validates signature, ensures idempotency,
    and updates the subscriptions table.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency check
    if _is_duplicate_event(db, event["id"], event["type"]):
        logger.info(f"Skipping duplicate Stripe event: {event['id']}")
        return {"status": "already_processed"}

    event_type = event["type"]
    # Parse as plain dict — Stripe 15.x model objects don't support .get()
    import json as _json
    raw = _json.loads(payload)
    data = raw["data"]["object"]

    logger.info(f"Processing Stripe event: {event_type} ({event['id']})")

    try:
        if event_type == "customer.subscription.created":
            manager_id = data.get("metadata", {}).get("manager_id")
            if manager_id:
                sub_data = {
                    "stripe_customer_id": data["customer"],
                    "stripe_subscription_id": data["id"],
                    "plan": "trial",
                    "status": "trialing",
                    "trial_ends_at": _unix_to_iso(data.get("trial_end")),
                    "current_period_end": _unix_to_iso(data.get("current_period_end")),
                }
                try:
                    db.table("subscriptions").insert({"manager_id": manager_id, **sub_data}).execute()
                except Exception:
                    # Row exists (manual/seed record) — update it with real Stripe IDs
                    db.table("subscriptions").update({**sub_data, "updated_at": "now()"}) \
                        .eq("manager_id", manager_id).execute()

        elif event_type == "customer.subscription.updated":
            stripe_sub_id = data["id"]
            update_data = {
                "status": data["status"],
                "current_period_end": _unix_to_iso(data.get("current_period_end")),
                "updated_at": "now()",
            }
            if data["status"] == "active":
                update_data["plan"] = "paid"

            db.table("subscriptions") \
                .update(update_data) \
                .eq("stripe_subscription_id", stripe_sub_id) \
                .execute()

        elif event_type == "customer.subscription.deleted":
            stripe_sub_id = data["id"]
            db.table("subscriptions") \
                .update({"status": "canceled", "updated_at": "now()"}) \
                .eq("stripe_subscription_id", stripe_sub_id) \
                .execute()

        elif event_type == "invoice.payment_succeeded":
            stripe_sub_id = data.get("subscription")
            if stripe_sub_id:
                db.table("subscriptions") \
                    .update({"status": "active", "plan": "paid", "updated_at": "now()"}) \
                    .eq("stripe_subscription_id", stripe_sub_id) \
                    .execute()

        elif event_type == "invoice.payment_failed":
            stripe_sub_id = data.get("subscription")
            if stripe_sub_id:
                db.table("subscriptions") \
                    .update({"status": "past_due", "updated_at": "now()"}) \
                    .eq("stripe_subscription_id", stripe_sub_id) \
                    .execute()

    except Exception as e:
        logger.error(f"Webhook handler error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {type(e).__name__}: {e}")

    return {"status": "ok"}


def _unix_to_iso(ts: int | None) -> str | None:
    """Convert a Unix timestamp to ISO 8601 string, or None."""
    if ts is None:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
