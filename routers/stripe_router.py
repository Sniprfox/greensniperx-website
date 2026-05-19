import stripe
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from db.supabase import supabase_admin
from middleware.auth import get_current_user
from services import sms as sms_svc
from services import email as email_svc
from config import get_settings

settings = get_settings()
stripe.api_key = settings.stripe_secret_key
router = APIRouter(prefix="/api/stripe", tags=["stripe"])


# ── START $199/MO CHECKOUT ────────────────────────────────────
@router.post("/create-subscription")
async def create_subscription(user=Depends(get_current_user)):
    try:
        sub = supabase_admin.table("subscriptions").select("stripe_customer_id") \
            .eq("user_id", user["id"]).single().execute()
        customer_id = (sub.data or {}).get("stripe_customer_id")

        if not customer_id:
            cust = stripe.Customer.create(
                email=user.get("email", ""),
                name=user.get("full_name", ""),
                metadata={"user_id": user["id"]},
            )
            customer_id = cust.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": settings.stripe_membership_price_id, "quantity": 1}],
            subscription_data={
                "trial_period_days": 7,
                "metadata": {"user_id": user["id"]},
            },
            success_url=f"{settings.frontend_url}/dashboard?subscribed=true",
            cancel_url=f"{settings.frontend_url}/#pricing",
            metadata={"user_id": user["id"]},
        )
        return {"url": session.url}
    except Exception as e:
        print(f"Checkout error: {e}")
        raise HTTPException(500, "Could not start checkout.")


# ── $249 CUSTOM STRATEGY PURCHASE ────────────────────────────
class StrategyPurchase(BaseModel):
    spec: dict = {}


@router.post("/purchase-custom-strategy")
async def purchase_strategy(body: StrategyPurchase, user=Depends(get_current_user)):
    try:
        sub = supabase_admin.table("subscriptions").select("stripe_customer_id") \
            .eq("user_id", user["id"]).single().execute()
        customer_id = (sub.data or {}).get("stripe_customer_id")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="payment",
            line_items=[{"price": settings.stripe_custom_strategy_price_id, "quantity": 1}],
            success_url=f"{settings.frontend_url}/dashboard?custom=purchased",
            cancel_url=f"{settings.frontend_url}/dashboard",
            metadata={
                "user_id": user["id"],
                "type": "custom_strategy",
                "spec": json.dumps(body.spec),
            },
        )
        return {"url": session.url}
    except Exception as e:
        print(f"Strategy purchase error: {e}")
        raise HTTPException(500, "Could not start payment.")


# ── STRIPE WEBHOOK ────────────────────────────────────────────
@router.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid webhook signature.")

    data  = event["data"]["object"]
    etype = event["type"]

    if etype == "customer.subscription.created":
        user_id = data["metadata"].get("user_id")
        if user_id:
            supabase_admin.table("subscriptions").upsert({
                "user_id": user_id,
                "stripe_customer_id": data["customer"],
                "stripe_sub_id": data["id"],
                "status": data["status"],
                "trial_end": _ts(data.get("trial_end")),
                "current_period_end": _ts(data.get("current_period_end")),
            }, on_conflict="user_id").execute()

    elif etype == "customer.subscription.updated":
        user_id = data["metadata"].get("user_id")
        supabase_admin.table("subscriptions").update({
            "status": data["status"],
            "current_period_end": _ts(data.get("current_period_end")),
        }).eq("stripe_sub_id", data["id"]).execute()

        if data["status"] == "active" and user_id:
            supabase_admin.table("profiles").update({"plan": "active"}).eq("id", user_id).execute()
            profile = supabase_admin.table("profiles").select("phone, full_name") \
                .eq("id", user_id).single().execute()
            if profile.data and profile.data.get("phone"):
                sms_svc.send_subscribed(
                    profile.data["phone"],
                    (profile.data.get("full_name") or "").split()[0] or "there"
                )

    elif etype == "customer.subscription.deleted":
        user_id = data["metadata"].get("user_id")
        supabase_admin.table("subscriptions").update({
            "status": "cancelled", "cancelled_at": "now()"
        }).eq("stripe_sub_id", data["id"]).execute()
        if user_id:
            supabase_admin.table("profiles").update({"plan": "cancelled"}).eq("id", user_id).execute()

    elif etype == "invoice.payment_succeeded":
        if data.get("billing_reason") == "subscription_create":
            sub = supabase_admin.table("subscriptions") \
                .select("user_id").eq("stripe_sub_id", data.get("subscription", "")).execute()
            if sub.data:
                _pay_affiliate(sub.data[0]["user_id"])

    elif etype == "checkout.session.completed":
        if data.get("metadata", {}).get("type") == "custom_strategy":
            user_id = data["metadata"]["user_id"]
            spec = json.loads(data["metadata"].get("spec", "{}"))
            supabase_admin.table("custom_strategies").insert({
                "user_id": user_id,
                "stripe_payment": data.get("payment_intent"),
                "name": spec.get("name", "Custom Strategy"),
                "risk_level": spec.get("risk_level"),
                "approach": spec.get("approach"),
                "time_horizon": spec.get("time_horizon"),
                "markets": spec.get("markets"),
                "special_notes": spec.get("special_notes"),
                "status": "pending",
            }).execute()
            profile = supabase_admin.table("profiles").select("phone, full_name") \
                .eq("id", user_id).single().execute()
            if profile.data:
                first = (profile.data.get("full_name") or "there").split()[0]
                if profile.data.get("phone"):
                    sms_svc.send_strategy_received(profile.data["phone"], first)
                email_svc.notify_admin_custom_strategy(
                    settings.admin_email,
                    profile.data.get("full_name", ""),
                    "", spec
                )

    return {"received": True}


# ── BILLING PORTAL ────────────────────────────────────────────
@router.post("/billing-portal")
async def billing_portal(user=Depends(get_current_user)):
    sub = supabase_admin.table("subscriptions").select("stripe_customer_id") \
        .eq("user_id", user["id"]).single().execute()
    customer_id = (sub.data or {}).get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(404, "No billing account found.")
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/dashboard",
    )
    return {"url": session.url}


# ── HELPERS ───────────────────────────────────────────────────
def _ts(unix_ts):
    if not unix_ts:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


def _pay_affiliate(new_member_id: str):
    try:
        member = supabase_admin.table("profiles").select("referred_by, full_name") \
            .eq("id", new_member_id).single().execute()
        referrer_id = (member.data or {}).get("referred_by")
        if not referrer_id:
            return
        commission = 39.80
        aff = supabase_admin.table("affiliates").select("*").eq("user_id", referrer_id).single().execute()
        if aff.data:
            supabase_admin.table("affiliates").update({
                "total_referrals": aff.data["total_referrals"] + 1,
                "active_referrals": aff.data["active_referrals"] + 1,
                "total_earned": float(aff.data["total_earned"]) + commission,
                "pending_payout": float(aff.data["pending_payout"]) + commission,
            }).eq("user_id", referrer_id).execute()
        referrer = supabase_admin.table("profiles").select("phone, full_name") \
            .eq("id", referrer_id).single().execute()
        if referrer.data and referrer.data.get("phone"):
            sms_svc.send_affiliate_commission(
                referrer.data["phone"], commission,
                (member.data or {}).get("full_name", "Someone")
            )
    except Exception as e:
        print(f"Affiliate error: {e}")
