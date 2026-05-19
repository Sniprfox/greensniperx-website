from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from db.supabase import supabase_admin
from config import get_settings

settings = get_settings()
bearer = HTTPBearer()


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token")
    except JWTError:
        raise HTTPException(401, "Session expired. Please log in again.")

    result = (
        supabase_admin.table("profiles")
        .select("*, subscriptions(status, trial_end, current_period_end)")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(401, "User not found")

    return result.data


async def require_active(user=Depends(get_current_user)):
    from datetime import datetime, timezone
    sub = (user.get("subscriptions") or [{}])
    sub = sub[0] if isinstance(sub, list) and sub else {}
    status = sub.get("status", "")
    trial_end = sub.get("trial_end")
    now = datetime.now(timezone.utc)
    trial_ok = False
    if trial_end:
        try:
            trial_ok = datetime.fromisoformat(trial_end.replace("Z", "+00:00")) > now
        except Exception:
            pass
    if status in ("active", "trialing") or trial_ok:
        return user
    raise HTTPException(403, "Subscribe to access this. greensniperx.com/#pricing")
