from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_membership_price_id: str
    stripe_custom_strategy_price_id: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    resend_api_key: str
    email_from: str = "GreenSniperX <hello@greensniperx.com>"
    admin_email: str

    frontend_url: str = "https://greensniperx.com"
    environment: str = "production"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()
