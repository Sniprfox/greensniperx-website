from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from db.supabase import supabase, supabase_admin
from services import email as email_svc
from services import sms as sms_svc
from config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    referral_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── SIGN UP ──────────────────────────────────────────────────
@router.post("/signup")
async def signup(body: SignupRequest):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    try:
        response = supabase.auth.sign_up({
            "email": body.email,
            "password": body.password,
            "options": {"data": {
                "full_name": body.full_name,
                "phone": body.phone,
            }}
        })

        if not response.user:
            raise HTTPException(400, "Could not create account. This email may already be registered.")

        user_id = response.user.id
        first_name = body.full_name.split()[0]

        # Handle referral
        if body.referral_code:
            ref = supabase_admin.table("profiles").select("id") \
                .eq("referral_code", body.referral_code.upper()).execute()
            if ref.data:
                supabase_admin.table("profiles").update({"referred_by": ref.data[0]["id"]}) \
                    .eq("id", user_id).execute()

        # Create subscription record
        supabase_admin.table("subscriptions").insert({"user_id": user_id, "status": "trialing"}).execute()

        # Create affiliate record
        supabase_admin.table("affiliates").insert({"user_id": user_id}).execute()

        # Welcome email + SMS
        email_svc.send_welcome(body.email, first_name)
        if body.phone:
            sms_svc.send_welcome(body.phone, first_name)

        # Notify admin
        email_svc.notify_admin_new_signup(settings.admin_email, body.full_name, body.email)

        return {
            "message": "Account created. Your 7-day trial has started.",
            "session": response.session,
            "user": {"id": user_id, "email": body.email, "full_name": body.full_name}
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(500, "Something went wrong. Please try again.")


# ── LOG IN ────────────────────────────────────────────────────
@router.post("/login")
async def login(body: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
        if not response.user:
            raise HTTPException(401, "Invalid email or password.")

        profile = supabase_admin.table("profiles") \
            .select("*, subscriptions(status, trial_end, current_period_end)") \
            .eq("id", response.user.id).single().execute()

        return {"session": response.session, "user": profile.data}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid email or password.")


# ── LOG OUT ───────────────────────────────────────────────────
@router.post("/logout")
async def logout():
    supabase.auth.sign_out()
    return {"message": "Logged out."}


# ── FORGOT PASSWORD ───────────────────────────────────────────
@router.post("/forgot-password")
async def forgot_password(email: str):
    try:
        supabase.auth.reset_password_email(
            email,
            options={"redirect_to": f"{settings.frontend_url}/reset-password"}
        )
    except Exception:
        pass
    return {"message": "If that email exists, a reset link has been sent."}
