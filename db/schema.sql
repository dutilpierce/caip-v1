-- CAIP v1 Database Schema for Supabase with pgvector
-- Run this in Supabase SQL Editor after enabling pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Partners table
CREATE TABLE IF NOT EXISTS partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(64) NOT NULL UNIQUE,
    default_policy_profile_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_partners_api_key_hash ON partners(api_key_hash);

-- Policy Profiles table
CREATE TABLE IF NOT EXISTS policy_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    blocked_categories JSONB DEFAULT '[]',
    requires_explicit_intent_categories JSONB DEFAULT '[]',
    max_sponsored_per_session INT DEFAULT 3,
    min_turns_between_sponsored INT DEFAULT 2,
    disclosure_mode VARCHAR(50) DEFAULT 'sponsored_suggestion',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_policy_profiles_partner_id ON policy_profiles(partner_id);

-- Ads table with pgvector embedding
CREATE TABLE IF NOT EXISTS ads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    landing_url VARCHAR(2048) NOT NULL,
    category VARCHAR(100) NOT NULL,
    brand VARCHAR(255),
    payout_model VARCHAR(50),
    bid_cents INT,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ads_partner_id ON ads(partner_id);
CREATE INDEX idx_ads_category ON ads(category);
CREATE INDEX idx_ads_active ON ads(active);
CREATE INDEX idx_ads_embedding ON ads USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Coupons table
CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ad_id UUID NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_coupons_ad_id ON coupons(ad_id);
CREATE INDEX idx_coupons_code ON coupons(code);

-- Events table for logging impressions, clicks, feedback
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    session_id VARCHAR(255) NOT NULL,
    user_hash VARCHAR(64),
    event_type VARCHAR(50) NOT NULL,
    ad_id UUID REFERENCES ads(id) ON DELETE SET NULL,
    intent_label VARCHAR(255),
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_partner_id ON events(partner_id);
CREATE INDEX idx_events_session_id ON events(session_id);
CREATE INDEX idx_events_user_hash ON events(user_hash);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_ad_id ON events(ad_id);
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- Function for pgvector similarity search
CREATE OR REPLACE FUNCTION match_ads(
    query_embedding vector,
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    id UUID,
    title VARCHAR,
    description TEXT,
    landing_url VARCHAR,
    category VARCHAR,
    brand VARCHAR,
    payout_model VARCHAR,
    bid_cents INT,
    metadata JSONB,
    embedding vector,
    active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ads.id,
        ads.title,
        ads.description,
        ads.landing_url,
        ads.category,
        ads.brand,
        ads.payout_model,
        ads.bid_cents,
        ads.metadata,
        ads.embedding,
        ads.active,
        ads.created_at,
        ads.updated_at,
        1 - (ads.embedding <=> query_embedding) AS similarity
    FROM ads
    WHERE ads.active = TRUE
    AND ads.embedding IS NOT NULL
    AND 1 - (ads.embedding <=> query_embedding) > similarity_threshold
    ORDER BY ads.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Seed data: 20 safe-category example ads
INSERT INTO partners (name, api_key_hash) VALUES
    ('Demo Partner', SHA256('demo_key'::bytea)::text)
ON CONFLICT (api_key_hash) DO NOTHING;

INSERT INTO policy_profiles (partner_id, blocked_categories, requires_explicit_intent_categories, max_sponsored_per_session, min_turns_between_sponsored, disclosure_mode)
SELECT id, '["gambling", "weapons", "adult"]'::jsonb, '["finance", "health"]'::jsonb, 3, 2, 'sponsored_suggestion'
FROM partners WHERE name = 'Demo Partner'
ON CONFLICT DO NOTHING;

-- Update partner default policy
UPDATE partners SET default_policy_profile_id = (
    SELECT id FROM policy_profiles WHERE partner_id = partners.id LIMIT 1
)
WHERE name = 'Demo Partner';

-- Insert 20 safe-category example ads (without embeddings initially)
INSERT INTO ads (partner_id, title, description, landing_url, category, brand, payout_model, bid_cents, metadata, active)
SELECT 
    p.id,
    ad.title,
    ad.description,
    ad.landing_url,
    ad.category,
    ad.brand,
    'cpm',
    500,
    ad.metadata,
    TRUE
FROM partners p,
(VALUES
    ('Notion - All-in-one workspace', 'Organize your thoughts and collaborate with your team', 'https://notion.so', 'productivity', 'Notion', '{"features": ["docs", "databases", "kanban"]}'::jsonb),
    ('Slack - Team communication', 'Connect your whole team in one place', 'https://slack.com', 'communication', 'Slack', '{"features": ["messaging", "integrations", "search"]}'::jsonb),
    ('Figma - Design tool', 'Collaborative interface design platform', 'https://figma.com', 'design', 'Figma', '{"features": ["prototyping", "collaboration", "components"]}'::jsonb),
    ('GitHub - Code hosting', 'Build and collaborate on code', 'https://github.com', 'development', 'GitHub', '{"features": ["repos", "ci/cd", "actions"]}'::jsonb),
    ('Stripe - Payment processing', 'Accept payments online', 'https://stripe.com', 'finance', 'Stripe', '{"features": ["payments", "invoicing", "analytics"]}'::jsonb),
    ('Zapier - Automation', 'Connect your apps and automate workflows', 'https://zapier.com', 'automation', 'Zapier', '{"features": ["workflows", "integrations", "templates"]}'::jsonb),
    ('Calendly - Scheduling', 'Scheduling made simple', 'https://calendly.com', 'productivity', 'Calendly', '{"features": ["scheduling", "integrations", "analytics"]}'::jsonb),
    ('Loom - Video messaging', 'Async video communication', 'https://loom.com', 'communication', 'Loom', '{"features": ["recording", "sharing", "transcripts"]}'::jsonb),
    ('Typeform - Forms', 'Beautiful forms and surveys', 'https://typeform.com', 'tools', 'Typeform', '{"features": ["surveys", "quizzes", "logic"]}'::jsonb),
    ('Airtable - Database', 'Flexible database platform', 'https://airtable.com', 'productivity', 'Airtable', '{"features": ["databases", "automation", "api"]}'::jsonb),
    ('Mailchimp - Email marketing', 'Email marketing made easy', 'https://mailchimp.com', 'marketing', 'Mailchimp', '{"features": ["campaigns", "automation", "analytics"]}'::jsonb),
    ('HubSpot - CRM', 'Customer relationship management', 'https://hubspot.com', 'sales', 'HubSpot', '{"features": ["crm", "marketing", "sales"]}'::jsonb),
    ('Intercom - Customer communication', 'Customer messaging platform', 'https://intercom.com', 'communication', 'Intercom', '{"features": ["chat", "support", "analytics"]}'::jsonb),
    ('Mixpanel - Analytics', 'Product analytics platform', 'https://mixpanel.com', 'analytics', 'Mixpanel', '{"features": ["events", "funnels", "cohorts"]}'::jsonb),
    ('Amplitude - Analytics', 'Digital analytics platform', 'https://amplitude.com', 'analytics', 'Amplitude', '{"features": ["events", "dashboards", "insights"]}'::jsonb),
    ('Segment - CDP', 'Customer data platform', 'https://segment.com', 'data', 'Segment', '{"features": ["tracking", "destinations", "api"]}'::jsonb),
    ('Twilio - Communication API', 'SMS and voice APIs', 'https://twilio.com', 'development', 'Twilio', '{"features": ["sms", "voice", "video"]}'::jsonb),
    ('Auth0 - Authentication', 'Identity and access management', 'https://auth0.com', 'security', 'Auth0', '{"features": ["authentication", "authorization", "mfa"]}'::jsonb),
    ('Vercel - Hosting', 'Frontend hosting and deployment', 'https://vercel.com', 'development', 'Vercel', '{"features": ["hosting", "ci/cd", "analytics"]}'::jsonb),
    ('Supabase - Backend', 'Open source Firebase alternative', 'https://supabase.com', 'development', 'Supabase', '{"features": ["database", "auth", "storage"]}'::jsonb)
) AS ad(title, description, landing_url, category, brand, metadata)
WHERE p.name = 'Demo Partner'
ON CONFLICT DO NOTHING;
