from twilio.rest import Client
from config import get_settings

settings = get_settings()
client = Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _fmt(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    return f"+1{digits}" if not digits.startswith("1") else f"+{digits}"


def _send(phone: str, message: str):
    try:
        client.messages.create(body=message, from_=settings.twilio_phone_number, to=_fmt(phone))
        print(f"✅ SMS sent to {phone}")
    except Exception as e:
        print(f"❌ SMS failed: {e}")


def send_welcome(phone: str, first_name: str):
    _send(phone,
        f"Welcome to GreenSniperX, {first_name}! "
        f"Your 7-day trial has started. Log in to explore your dashboard. "
        f"We will text you with important updates. — GreenSniperX")


def send_trial_ending(phone: str, first_name: str, days_left: int):
    day_word = "day" if days_left == 1 else "days"
    _send(phone,
        f"{first_name}, your GreenSniperX trial ends in {days_left} {day_word}. "
        f"Subscribe at greensniperx.com to keep everything running. "
        f"Cancel before Day 7 and you are never charged. — GreenSniperX")


def send_subscribed(phone: str, first_name: str):
    _send(phone,
        f"You are in, {first_name}. GreenSniperX membership is now active. "
        f"Log in to your dashboard to get started. — GreenSniperX")


def send_strategy_received(phone: str, first_name: str):
    _send(phone,
        f"Got it, {first_name}. Your custom strategy request has been received. "
        f"Our team will have it ready within 5 business days. — GreenSniperX")


def send_strategy_delivered(phone: str, strategy_name: str):
    _send(phone,
        f'Your custom strategy "{strategy_name}" is ready. '
        f"Log in to your dashboard to activate it. — GreenSniperX")


def send_affiliate_commission(phone: str, amount: float, referral_name: str):
    _send(phone,
        f"You just earned ${amount:.2f} — {referral_name} subscribed through your link. "
        f"It will be added to your next payout. — GreenSniperX")
