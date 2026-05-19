from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import os

from config import get_settings
from routers import auth, stripe_router

settings = get_settings()


# ── TRIAL REMINDER JOB ────────────────────────────────────────
def send_trial_reminders():
    """Runs every hour — texts members whose trial ends within 24 hours."""
    from datetime import datetime, timezone, timedelta
    from db.supabase import supabase_admin
    from services import sms as sms_svc

    try:
        now    = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=25)

        rows = supabase_admin.table("subscriptions") \
            .select("user_id, trial_end, profiles(full_name, phone)") \
            .eq("status", "trialing") \
            .lte("trial_end", cutoff.isoformat()) \
            .gte("trial_end", now.isoformat()) \
            .execute()

        for row in rows.data or []:
            profile   = (row.get("profiles") or [{}])
            profile   = profile[0] if isinstance(profile, list) else profile
            phone     = profile.get("phone")
            full_name = profile.get("full_name") or "there"
            first     = full_name.split()[0]
            trial_end = row["trial_end"]
            hours_left = (
                datetime.fromisoformat(trial_end.replace("Z", "+00:00")) - now
            ).total_seconds() / 3600
            days_left = 1 if hours_left <= 24 else 2
            if phone:
                sms_svc.send_trial_ending(phone, first, days_left)

        print(f"✅ Trial reminders checked — {len(rows.data or [])} users")
    except Exception as e:
        print(f"❌ Trial reminder error: {e}")


# ── APP LIFESPAN ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_trial_reminders, "interval", hours=1)
    scheduler.start()
    print("✅ GreenSniperX is live")
    yield
    scheduler.shutdown()


# ── CREATE APP ───────────────────────────────────────────────
app = FastAPI(
    title="GreenSniperX",
    docs_url=None,   # Hide API docs in production
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://greensniperx.com",
        "https://www.greensniperx.com",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTES ───────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(stripe_router.router)


# ── HEALTH CHECK ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "GreenSniperX"}


# ── SERVE LANDING PAGE ────────────────────────────────────────
public = os.path.join(os.path.dirname(__file__), "public")
if os.path.exists(public):
    app.mount("/assets", StaticFiles(directory=public), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve(full_path: str):
        return FileResponse(os.path.join(public, "index.html"))
