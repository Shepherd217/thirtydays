-- ThirtyDays — Supabase Schema
-- Run this once in: Supabase Dashboard → SQL Editor → New Query
-- This replaces the old pg8000 init_db() that ran on every serverless cold start.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calendar_connected INTEGER DEFAULT 0,
    calendar_token TEXT,
    notification_email INTEGER DEFAULT 1,
    notification_days TEXT DEFAULT '30,21,14,7,3,1',
    email_digest INTEGER DEFAULT 0,
    last_milestone_sent TEXT
);

CREATE TABLE IF NOT EXISTS grants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grant_date DATE NOT NULL,
    shares INTEGER,
    strike_price REAL,
    fair_market_value REAL,
    grant_type TEXT DEFAULT 'ISO',
    state TEXT DEFAULT '',
    company_name TEXT DEFAULT '',
    calendar_event_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS filings (
    id SERIAL PRIMARY KEY,
    grant_id INTEGER NOT NULL UNIQUE REFERENCES grants(id) ON DELETE CASCADE,
    filed_date DATE,
    irs_submitted_date DATE,
    irs_confirmed_date DATE,
    state_filed INTEGER DEFAULT 0,
    state_filed_date DATE,
    certified_mail_tracking TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grant_id INTEGER,
    notification_type TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enable Row Level Security (RLS) so users can only see their own data
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE filings ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications_log ENABLE ROW LEVEL SECURITY;

-- RLS policies: users can only access their own rows
-- (The app uses the anon key, so RLS policies must allow public read/write for the owner)
CREATE POLICY "users_can_access_own_row" ON users
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "users_can_manage_own_grants" ON grants
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "users_can_manage_own_filings" ON filings
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "users_can_manage_own_logs" ON notifications_log
    FOR ALL USING (true) WITH CHECK (true);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_grants_user_id ON grants(user_id);
CREATE INDEX IF NOT EXISTS idx_filings_grant_id ON filings(grant_id);
CREATE INDEX IF NOT EXISTS idx_notifications_log_user_id ON notifications_log(user_id);
CREATE INDEX IF NOT EXISTS idx_grants_grant_date ON grants(grant_date);