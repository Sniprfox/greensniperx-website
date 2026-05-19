import resend
from config import get_settings

settings = get_settings()
resend.api_key = settings.resend_api_key


def _send(to: str, subject: str, html: str) -> bool:
    try:
        resend.Emails.send({"from": settings.email_from, "to": to, "subject": subject, "html": html})
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_welcome(email: str, first_name: str) -> bool:
    return _send(email, "Welcome to GreenSniperX — your trial has started", f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;color:#111827">
      <div style="padding:28px 0 12px">
        <span style="font-weight:800;font-size:18px;color:#059669">Green</span>
        <span style="font-weight:800;font-size:18px">SniperX</span>
      </div>
      <h2 style="font-size:22px;font-weight:700;margin-bottom:8px">Welcome, {first_name}. Your 7-day trial has started.</h2>
      <p style="color:#374151;line-height:1.75;margin-bottom:16px">
        While most savings accounts pay you 0.46% a year, GreenSniperX puts your money
        to work in the market every single session — automatically, on your behalf.
      </p>
      <p style="color:#374151;line-height:1.75;margin-bottom:24px">
        Log in to explore your dashboard. When you are ready to connect your account,
        we walk you through every step.
      </p>
      <a href="{settings.frontend_url}/dashboard"
         style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
                padding:12px 24px;border-radius:8px;font-weight:600;font-size:15px">
        Go to My Dashboard
      </a>
      <p style="margin-top:28px;color:#9ca3af;font-size:13px">
        Questions? Reply to this email — we read every one.<br>— The GreenSniperX Team
      </p>
    </div>""")


def send_trial_ending(email: str, first_name: str, days_left: int) -> bool:
    day_word = "day" if days_left == 1 else "days"
    return _send(email, f"Your GreenSniperX trial ends in {days_left} {day_word}", f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;color:#111827">
      <div style="padding:28px 0 12px">
        <span style="font-weight:800;font-size:18px;color:#059669">Green</span>
        <span style="font-weight:800;font-size:18px">SniperX</span>
      </div>
      <h2 style="font-size:22px;font-weight:700;margin-bottom:8px">
        {first_name}, your trial ends in {days_left} {day_word}.
      </h2>
      <p style="color:#374151;line-height:1.75;margin-bottom:24px">
        Subscribe now to keep your strategies running. $199/month — cancel anytime.
      </p>
      <a href="{settings.frontend_url}/#pricing"
         style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
                padding:12px 24px;border-radius:8px;font-weight:600;font-size:15px">
        Subscribe — $199/mo
      </a>
      <p style="margin-top:16px;color:#9ca3af;font-size:13px">
        Cancel before Day 7 and you are never charged.
      </p>
    </div>""")


def send_strategy_delivered(email: str, first_name: str, strategy_name: str) -> bool:
    return _send(email, f"Your custom strategy is ready — {strategy_name}", f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;color:#111827">
      <div style="padding:28px 0 12px">
        <span style="font-weight:800;font-size:18px;color:#059669">Green</span>
        <span style="font-weight:800;font-size:18px">SniperX</span>
      </div>
      <h2 style="font-size:22px;font-weight:700;margin-bottom:8px">Your strategy is ready, {first_name}.</h2>
      <p style="color:#374151;line-height:1.75;margin-bottom:8px">
        <strong>{strategy_name}</strong> has been built, tested, and added to your dashboard.
      </p>
      <a href="{settings.frontend_url}/dashboard"
         style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
                padding:12px 24px;border-radius:8px;font-weight:600;font-size:15px;margin-top:16px">
        View My Strategy
      </a>
    </div>""")


def notify_admin_new_signup(admin_email: str, full_name: str, email: str) -> bool:
    return _send(admin_email, f"New signup — {full_name}", f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto">
      <h2 style="color:#059669">New GreenSniperX Member</h2>
      <p><strong>Name:</strong> {full_name}</p>
      <p><strong>Email:</strong> {email}</p>
      <p style="color:#6b7280;font-size:13px;margin-top:16px">Trial started — Day 8 billing begins automatically via Stripe.</p>
    </div>""")


def notify_admin_custom_strategy(admin_email: str, full_name: str, user_email: str, spec: dict) -> bool:
    return _send(admin_email, f"New Custom Strategy Request — {full_name}", f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto">
      <h2 style="color:#059669">New Custom Strategy Request</h2>
      <p><strong>Member:</strong> {full_name} ({user_email})</p>
      <p><strong>Strategy Name:</strong> {spec.get('name', 'Not specified')}</p>
      <p><strong>Risk Level:</strong> {spec.get('risk_level', 'Not specified')}</p>
      <p><strong>Approach:</strong> {spec.get('approach', 'Not specified')}</p>
      <p><strong>Time Horizon:</strong> {spec.get('time_horizon', 'Not specified')}</p>
      <p><strong>Markets:</strong> {spec.get('markets', 'Not specified')}</p>
      <p><strong>Notes:</strong> {spec.get('special_notes', 'None')}</p>
      <p style="color:#6b7280;font-size:13px;margin-top:16px">Due in 5 business days.</p>
    </div>""")
