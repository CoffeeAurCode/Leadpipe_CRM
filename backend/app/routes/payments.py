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

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in session. Please sign out and sign in again.",
        )

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


@router.get("/subscription-status")
async def subscription_status(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db),
):
    """Return whether the authenticated manager has an active or trialing subscription."""
    manager_id = user["sub"]
    result = (
        db.table("subscriptions")
        .select("status")
        .eq("manager_id", manager_id)
        .in_("status", ["trialing", "active"])
        .limit(1)
        .execute()
    )
    if result.data:
        return {"subscribed": True, "status": result.data[0]["status"]}
    return {"subscribed": False, "status": None}


@router.get("/verify-session")
async def verify_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db),
):
    """
    Verify a completed Stripe checkout session and upsert the subscription row.
    Called by the success page BEFORE redirecting to the CRM — this is a webhook
    fallback that works in both local dev (no CLI forwarding) and production.
    """
    manager_id = user["sub"]

    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["subscription"],
        )
    except stripe.error.StripeError as exc:
        logger.error(f"Stripe session retrieval failed for {session_id}: {exc}")
        raise HTTPException(status_code=400, detail="Invalid or expired session ID.")

    # Confirm this session was created for the authenticated manager
    # session.metadata is a StripeObject (not a plain dict) in Stripe 15.x — use [] not .get()
    metadata = session.metadata
    session_manager_id = metadata["manager_id"] if metadata and "manager_id" in metadata else None
    if session_manager_id != manager_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this account.")

    if session.status != "complete":
        raise HTTPException(status_code=400, detail="Checkout session is not yet complete.")

    # Retrieve subscription (may be an expanded object or just an ID string)
    subscription = session.subscription
    if subscription is None:
        raise HTTPException(status_code=400, detail="No subscription found in this session.")
    if isinstance(subscription, str):
        subscription = stripe.Subscription.retrieve(subscription)

    # ── Ensure manager_profile exists ────────────────────────────────────────────
    # The user may have authenticated on the landing page and never touched the CRM,
    # so the CRM's AuthContext hasn't run yet and the manager_profile row may not exist.
    # The subscriptions table has an FK → manager_profiles, so we must create it first.
    email = user.get("email", "")
    name = email.split("@")[0] if email else "Manager"
    try:
        existing_profile = (
            db.table("manager_profiles")
            .select("id")
            .eq("user_id", manager_id)
            .maybeSingle()
            .execute()
        )
        if not existing_profile.data:
            db.table("manager_profiles").insert({
                "user_id": manager_id,
                "name": name,
            }).execute()
            logger.info(f"Manager profile created for {manager_id} via verify-session")
    except Exception as exc:
        logger.warning(f"Could not ensure manager profile for {manager_id}: {exc}")
        # Non-fatal — continue; if subscriptions has no FK this still works

    # ── Upsert subscription row ───────────────────────────────────────────────
    customer_id = str(session.customer) if session.customer else ""
    sub_data = {
        "manager_id": manager_id,
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription.id,
        "plan": "trial" if subscription.status == "trialing" else "paid",
        "status": subscription.status,
        "trial_ends_at": _unix_to_iso(getattr(subscription, "trial_end", None)),
        "current_period_end": _unix_to_iso(getattr(subscription, "current_period_end", None)),
    }

    try:
        db.table("subscriptions").insert(sub_data).execute()
        logger.info(f"Subscription row created for manager {manager_id} via verify-session")
    except Exception as insert_exc:
        logger.warning(f"Subscription insert failed for {manager_id} (will try update): {insert_exc}")
        try:
            db.table("subscriptions").update({
                "status": subscription.status,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription.id,
                "current_period_end": _unix_to_iso(getattr(subscription, "current_period_end", None)),
                "updated_at": "now()",
            }).eq("manager_id", manager_id).execute()
            logger.info(f"Subscription row updated for manager {manager_id} via verify-session")
        except Exception as update_exc:
            logger.error(f"Subscription update also failed for {manager_id}: {update_exc}")
            raise HTTPException(
                status_code=500,
                detail="Failed to activate subscription. Please contact support.",
            )

    # ── Confirm the row actually exists before telling the client to proceed ──
    check = (
        db.table("subscriptions")
        .select("status")
        .eq("manager_id", manager_id)
        .in_("status", ["trialing", "active"])
        .limit(1)
        .execute()
    )
    if not check.data:
        logger.error(f"Subscription row missing after upsert for manager {manager_id}")
        raise HTTPException(
            status_code=500,
            detail="Subscription could not be confirmed. Please contact support.",
        )

    return {"subscribed": True, "status": subscription.status}


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
