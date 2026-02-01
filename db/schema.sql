-- CAIP v1 Database Schema for Supabase with pgvector
-- Run this in Supabase SQL Editor after enabling pgvector extension

-- Ensure all objects are created in public schema
SET search_path = public;

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

-- Seed data moved to db/seed.sql to keep schema-only changes here.
