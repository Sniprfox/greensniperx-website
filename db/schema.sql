-- ============================================================
-- GreenSniperX Website Schema
-- Paste this into: supabase.com → SQL Editor → Run
-- ============================================================

-- ─── PROFILES ────────────────────────────────────────────────
-- Supabase Auth handles passwords. This stores extra info.
CREATE TABLE IF NOT EXISTS public.profiles (
  id            UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name     VARCHAR(255),
  phone         VARCHAR(20),
  plan          VARCHAR(20) DEFAULT 'trial',
  simple_mode   BOOLEAN DEFAULT false,
  referral_code VARCHAR(20) UNIQUE,
  referred_by   UUID REFERENCES public.profiles(id),
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Auto-create profile when someone signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, phone, referral_code)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'phone',
    upper(substring(md5(random()::text) from 1 for 6))
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ─── SUBSCRIPTIONS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.subscriptions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE,
  stripe_customer_id  VARCHAR(255) UNIQUE,
  stripe_sub_id       VARCHAR(255) UNIQUE,
  status              VARCHAR(30) DEFAULT 'trialing',
  trial_start         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  trial_end           TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
  current_period_end  TIMESTAMP WITH TIME ZONE,
  cancelled_at        TIMESTAMP WITH TIME ZONE,
  created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── CUSTOM STRATEGY REQUESTS ────────────────────────────────
CREATE TABLE IF NOT EXISTS public.custom_strategies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  stripe_payment  VARCHAR(255),
  name            VARCHAR(255),
  risk_level      VARCHAR(30),
  approach        TEXT,
  time_horizon    VARCHAR(100),
  markets         TEXT,
  special_notes   TEXT,
  chat_transcript TEXT,
  status          VARCHAR(30) DEFAULT 'pending',
  submitted_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  due_date        TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '5 days'),
  delivered_at    TIMESTAMP WITH TIME ZONE
);

-- ─── AFFILIATES ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.affiliates (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE,
  total_referrals  INTEGER DEFAULT 0,
  active_referrals INTEGER DEFAULT 0,
  total_earned     DECIMAL(10,2) DEFAULT 0,
  pending_payout   DECIMAL(10,2) DEFAULT 0,
  paid_out         DECIMAL(10,2) DEFAULT 0,
  created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.referral_events (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id   UUID REFERENCES public.profiles(id),
  referred_user UUID REFERENCES public.profiles(id),
  commission    DECIMAL(10,2) DEFAULT 39.80,
  status        VARCHAR(20) DEFAULT 'pending',
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── WAIT LIST (for people who want to be notified) ──────────
CREATE TABLE IF NOT EXISTS public.waitlist (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email      VARCHAR(255) UNIQUE NOT NULL,
  full_name  VARCHAR(255),
  phone      VARCHAR(20),
  source     VARCHAR(100),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── CONTACT / SUPPORT MESSAGES ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.contact_messages (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       VARCHAR(255),
  email      VARCHAR(255),
  message    TEXT,
  replied    BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── ROW LEVEL SECURITY ──────────────────────────────────────
ALTER TABLE public.profiles           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_strategies  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.affiliates         ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Own profile" ON public.profiles
  FOR ALL USING (auth.uid() = id);

CREATE POLICY "Own subscription" ON public.subscriptions
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Own strategies" ON public.custom_strategies
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Own affiliate" ON public.affiliates
  FOR ALL USING (auth.uid() = user_id);

-- ─── INDEXES ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_subs_user     ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_strat_user    ON public.custom_strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_aff_user      ON public.affiliates(user_id);
CREATE INDEX IF NOT EXISTS idx_waitlist_email ON public.waitlist(email);
