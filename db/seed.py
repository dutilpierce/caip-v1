"""
CAIP v1 Seed Data Script (primary seeder)
Seeds demo partner, policy profile, and ads using public schema only.
"""

import os
import sys
import asyncio
import hashlib
from typing import Optional, List

import httpx
from supabase import create_client, Client

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DEMO_PARTNER_NAME = "Demo Partner"
DEMO_PARTNER_KEY = "demo_key"
DEFAULT_POLICY_PROFILE = {
    "blocked_categories": ["gambling", "weapons", "adult"],
    "requires_explicit_intent_categories": ["finance", "health"],
    "max_sponsored_per_session": 3,
    "min_turns_between_sponsored": 2,
    "disclosure_mode": "sponsored_suggestion",
}

# Example ads data
EXAMPLE_ADS = [
    {
        "title": "Notion - All-in-one workspace",
        "description": "Organize your thoughts and collaborate with your team. Perfect for project management, documentation, and knowledge bases.",
        "landing_url": "https://notion.so",
        "category": "productivity",
        "brand": "Notion",
    },
    {
        "title": "Slack - Team communication",
        "description": "Connect your whole team in one place with instant messaging, file sharing, and integrations.",
        "landing_url": "https://slack.com",
        "category": "communication",
        "brand": "Slack",
    },
    {
        "title": "Figma - Design collaboration",
        "description": "Collaborative interface design platform for creating, prototyping, and sharing designs.",
        "landing_url": "https://figma.com",
        "category": "design",
        "brand": "Figma",
    },
    {
        "title": "GitHub - Code hosting",
        "description": "Build and collaborate on code with version control, CI/CD, and project management.",
        "landing_url": "https://github.com",
        "category": "development",
        "brand": "GitHub",
    },
    {
        "title": "Stripe - Payment processing",
        "description": "Accept payments online with a complete payment platform for businesses.",
        "landing_url": "https://stripe.com",
        "category": "finance",
        "brand": "Stripe",
    },
    {
        "title": "Zapier - Automation",
        "description": "Connect your apps and automate workflows without coding.",
        "landing_url": "https://zapier.com",
        "category": "automation",
        "brand": "Zapier",
    },
    {
        "title": "Calendly - Scheduling",
        "description": "Scheduling made simple with calendar integration and automated reminders.",
        "landing_url": "https://calendly.com",
        "category": "productivity",
        "brand": "Calendly",
    },
    {
        "title": "Loom - Video messaging",
        "description": "Async video communication for teams with instant recording and sharing.",
        "landing_url": "https://loom.com",
        "category": "communication",
        "brand": "Loom",
    },
    {
        "title": "Typeform - Forms & surveys",
        "description": "Create beautiful forms, surveys, and quizzes with conditional logic.",
        "landing_url": "https://typeform.com",
        "category": "tools",
        "brand": "Typeform",
    },
    {
        "title": "Airtable - Flexible database",
        "description": "Database platform with automation, API, and collaborative features.",
        "landing_url": "https://airtable.com",
        "category": "productivity",
        "brand": "Airtable",
    },
    {
        "title": "Mailchimp - Email marketing",
        "description": "Email marketing platform with automation, templates, and analytics.",
        "landing_url": "https://mailchimp.com",
        "category": "marketing",
        "brand": "Mailchimp",
    },
    {
        "title": "HubSpot - CRM platform",
        "description": "Customer relationship management with sales, marketing, and service tools.",
        "landing_url": "https://hubspot.com",
        "category": "sales",
        "brand": "HubSpot",
    },
    {
        "title": "Intercom - Customer messaging",
        "description": "Customer communication platform with chat, support, and analytics.",
        "landing_url": "https://intercom.com",
        "category": "communication",
        "brand": "Intercom",
    },
    {
        "title": "Mixpanel - Product analytics",
        "description": "Understand user behavior with event tracking, funnels, and cohorts.",
        "landing_url": "https://mixpanel.com",
        "category": "analytics",
        "brand": "Mixpanel",
    },
    {
        "title": "Amplitude - Digital analytics",
        "description": "Product analytics platform for understanding user journeys and insights.",
        "landing_url": "https://amplitude.com",
        "category": "analytics",
        "brand": "Amplitude",
    },
    {
        "title": "Segment - Customer data",
        "description": "Unified customer data platform for tracking and analytics.",
        "landing_url": "https://segment.com",
        "category": "data",
        "brand": "Segment",
    },
    {
        "title": "Twilio - Communication API",
        "description": "SMS, voice, and video APIs for building communication features.",
        "landing_url": "https://twilio.com",
        "category": "development",
        "brand": "Twilio",
    },
    {
        "title": "Auth0 - Authentication",
        "description": "Identity and access management with MFA and security features.",
        "landing_url": "https://auth0.com",
        "category": "security",
        "brand": "Auth0",
    },
    {
        "title": "Vercel - Frontend hosting",
        "description": "Frontend hosting and deployment with CI/CD and analytics.",
        "landing_url": "https://vercel.com",
        "category": "development",
        "brand": "Vercel",
    },
    {
        "title": "Supabase - Backend platform",
        "description": "Open source Firebase alternative with database, auth, and storage.",
        "landing_url": "https://supabase.com",
        "category": "development",
        "brand": "Supabase",
    },
]

async def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using OpenAI API."""
    if not OPENAI_API_KEY:
        print("Warning: OpenAI API key not set, skipping embeddings")
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "text-embedding-3-small",
                    "input": text,
                    "encoding_format": "float",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def sha256_hex(value: str) -> str:
    """Return a 64-character SHA-256 hex digest."""
    return hashlib.sha256(value.encode()).hexdigest()

def ensure_sha256_hex(value: str, field_name: str) -> str:
    """Validate a 64-character lowercase SHA-256 hex string."""
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field_name} must be 64-character SHA-256 hex")
    return value

def get_demo_partner_hash() -> str:
    return ensure_sha256_hex(sha256_hex(DEMO_PARTNER_KEY), "api_key_hash")

def get_or_create_partner() -> str:
    partner_hash = get_demo_partner_hash()
    response = supabase.table("partners").select("id").eq(
        "api_key_hash", partner_hash
    ).limit(1).execute()

    if response.data:
        return response.data[0]["id"]

    partner_response = supabase.table("partners").insert({
        "name": DEMO_PARTNER_NAME,
        "api_key_hash": partner_hash,
    }).execute()
    return partner_response.data[0]["id"]

def get_or_create_policy_profile(partner_id: str) -> str:
    response = supabase.table("policy_profiles").select("id").eq(
        "partner_id", partner_id
    ).limit(1).execute()

    if response.data:
        return response.data[0]["id"]

    profile_response = supabase.table("policy_profiles").insert({
        "partner_id": partner_id,
        **DEFAULT_POLICY_PROFILE,
    }).execute()
    return profile_response.data[0]["id"]

def set_partner_default_policy(partner_id: str, policy_profile_id: str) -> None:
    supabase.table("partners").update({
        "default_policy_profile_id": policy_profile_id
    }).eq("id", partner_id).execute()

async def seed_ads():
    """Seed the database with demo partner, policy profile, and ads."""
    try:
        print("Seeding demo partner...")
        partner_id = get_or_create_partner()
        print(f"Using partner ID: {partner_id}")

        print("Seeding policy profile...")
        policy_profile_id = get_or_create_policy_profile(partner_id)
        set_partner_default_policy(partner_id, policy_profile_id)

        existing_ads = supabase.table("ads").select("id,title").eq(
            "partner_id", partner_id
        ).execute()
        existing_titles = {row["title"] for row in (existing_ads.data or [])}

        print(f"Seeding {len(EXAMPLE_ADS)} example ads...")

        for i, ad in enumerate(EXAMPLE_ADS):
            if ad["title"] in existing_titles:
                print(f"↷ Skipping existing ad: {ad['title']}")
                continue

            embedding = await get_embedding(ad["description"])

            ad_data = {
                "partner_id": partner_id,
                "title": ad["title"],
                "description": ad["description"],
                "landing_url": ad["landing_url"],
                "category": ad["category"],
                "brand": ad["brand"],
                "payout_model": "cpm",
                "bid_cents": 500,
                "metadata": {
                    "features": [],
                    "tags": [ad["category"], ad["brand"].lower()],
                },
                "active": True,
            }

            if embedding:
                ad_data["embedding"] = embedding

            try:
                supabase.table("ads").insert(ad_data).execute()
                print(f"✓ Seeded ad {i+1}/{len(EXAMPLE_ADS)}: {ad['title']}")
            except Exception as e:
                print(f"✗ Error seeding ad {i+1}: {e}")

        print("\n✓ Seed run complete.")
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(seed_ads())