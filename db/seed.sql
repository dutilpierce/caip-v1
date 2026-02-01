-- CAIP v1 Seed Data (public schema only)
-- Run this after db/schema.sql
-- api_key_hash and user_hash must be SHA-256 hex (64 chars).
-- Never store raw partner keys or raw user IDs in these columns.

-- Seed partner
INSERT INTO partners (name, api_key_hash) VALUES
    ('Demo Partner', 'a49a424504e3a3d9ec9155e0d52f3b690c160451ae971df9ccabeae363c5ae40')
ON CONFLICT (api_key_hash) DO NOTHING;

-- Seed policy profile
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
