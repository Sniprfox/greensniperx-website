from supabase import create_client, Client
from config import get_settings

settings = get_settings()

# For verifying user tokens
supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

# For server-side DB operations (bypasses row level security)
supabase_admin: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
