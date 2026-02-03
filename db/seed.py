"""
CAIP v1 Seed Data Script (primary seeder)
Seeds demo partner, policy profile, and ads using public schema only.
Uses Supabase REST endpoints to avoid client dependency issues in Replit.
"""

import os
import sys
import json
import hashlib
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

SUPABASE_REST_BASE = f"{SUPABASE_URL.rstrip('/')}/rest/v1"

DEMO_PARTNER_NAME = "Demo Partner"
DEMO_PARTNER_KEY = "demo_key"
DEFAULT_POLICY_PROFILE = {
    "blocked_categories": ["gambling", "weapons", "adult"],
    "requires_explicit_intent_categories": ["finance", "health"],
    "max_sponsored_per_session": 3,
    "min_turns_between_sponsored": 2,
    "disclosure_mode": "sponsored_suggestion",
}

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

def sha256_hex(value: str) -> str:
    """Return a 64-character SHA-256 hex digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def ensure_sha256_hex(value: str, field_name: str) -> str:
    """Validate a 64-character lowercase SHA-256 hex string."""
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field_name} must be 64-character SHA-256 hex")
    return value

def get_demo_partner_hash() -> str:
    return ensure_sha256_hex(sha256_hex(DEMO_PARTNER_KEY), "api_key_hash")

def _request_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {raw}") from e
    except URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

def _supabase_headers(prefer: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers

def supabase_request(
    method: str,
    path: str,
    params: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    prefer: Optional[str] = None,
) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{SUPABASE_REST_BASE}/{path}{query}"
    return _request_json(method, url, _supabase_headers(prefer=prefer), body=body)

def get_embedding(text: str) -> Optional[List[float]]:
    if not OPENAI_API_KEY:
        print("Warning: OpenAI API key not set, skipping embeddings")
        return None

    body = {
        "model": "text-embedding-3-small",
        "input": text,
        "encoding_format": "float",
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        data = _request_json("POST", "https://api.openai.com/v1/embeddings", headers, body)
        return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def get_or_create_partner() -> str:
    partner_hash = get_demo_partner_hash()
    response = supabase_request(
        "GET",
        "partners",
        params={"select": "id", "api_key_hash": f"eq.{partner_hash}", "limit": "1"},
    )
    if response:
        return response[0]["id"]

    created = supabase_request(
        "POST",
        "partners",
        params={"on_conflict": "api_key_hash"},
        body={"name": DEMO_PARTNER_NAME, "api_key_hash": partner_hash},
        prefer="resolution=merge-duplicates,return=representation",
    )
    if created:
        return created[0]["id"]

    response = supabase_request(
        "GET",
        "partners",
        params={"select": "id", "api_key_hash": f"eq.{partner_hash}", "limit": "1"},
    )
    if response:
        return response[0]["id"]
    raise RuntimeError("Failed to create or fetch Demo Partner")

def get_or_create_policy_profile(partner_id: str) -> str:
    response = supabase_request(
        "GET",
        "policy_profiles",
        params={"select": "id", "partner_id": f"eq.{partner_id}", "limit": "1"},
    )
    if response:
        return response[0]["id"]

    created = supabase_request(
        "POST",
        "policy_profiles",
        body={"partner_id": partner_id, **DEFAULT_POLICY_PROFILE},
        prefer="return=representation",
    )
    if created:
        return created[0]["id"]
    raise RuntimeError("Failed to create policy profile")

def set_partner_default_policy(partner_id: str, policy_profile_id: str) -> None:
    supabase_request(
        "PATCH",
        "partners",
        params={"id": f"eq.{partner_id}"},
        body={"default_policy_profile_id": policy_profile_id},
        prefer="return=representation",
    )

def get_existing_ad_titles(partner_id: str) -> set:
    response = supabase_request(
        "GET",
        "ads",
        params={"select": "title", "partner_id": f"eq.{partner_id}"},
    )
    return {row["title"] for row in (response or [])}

def insert_ad(partner_id: str, ad: Dict[str, str], embedding: Optional[List[float]]) -> None:
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
    supabase_request("POST", "ads", body=ad_data, prefer="return=representation")

def seed_ads() -> None:
    try:
        print("Seeding demo partner...")
        partner_id = get_or_create_partner()
        print(f"Using partner ID: {partner_id}")

        print("Seeding policy profile...")
        policy_profile_id = get_or_create_policy_profile(partner_id)
        set_partner_default_policy(partner_id, policy_profile_id)

        existing_titles = get_existing_ad_titles(partner_id)
        print(f"Seeding {len(EXAMPLE_ADS)} example ads...")

        for i, ad in enumerate(EXAMPLE_ADS):
            if ad["title"] in existing_titles:
                print(f"↷ Skipping existing ad: {ad['title']}")
                continue

            embedding = get_embedding(ad["description"])
            try:
                insert_ad(partner_id, ad, embedding)
                print(f"✓ Seeded ad {i+1}/{len(EXAMPLE_ADS)}: {ad['title']}")
            except Exception as e:
                print(f"✗ Error seeding ad {i+1}: {e}")

        print("\n✓ Seed run complete.")
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed_ads()