"""
CAIP v1 Seed Data Script
Populates 20 safe-category example ads with embeddings for demo.
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
PARTNER_SALT = os.getenv("PARTNER_SALT", "default-salt-change-me")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Example ads data
EXAMPLE_ADS = [
    {
        "title": "Notion - All-in-one workspace",
        "description": "Organize your thoughts and collaborate with your team. Perfect for project management, documentation, and knowledge bases.",
        "landing_url": "https://notion.so",
        "category": "productivity",
        "brand": "Notion"
    },
    {
        "title": "Slack - Team communication",
        "description": "Connect your whole team in one place with instant messaging, file sharing, and integrations.",
        "landing_url": "https://slack.com",
        "category": "communication",
        "brand": "Slack"
    },
    {
        "title": "Figma - Design collaboration",
        "description": "Collaborative interface design platform for creating, prototyping, and sharing designs.",
        "landing_url": "https://figma.com",
        "category": "design",
        "brand": "Figma"
    },
    {
        "title": "GitHub - Code hosting",
        "description": "Build and collaborate on code with version control, CI/CD, and project management.",
        "landing_url": "https://github.com",
        "category": "development",
        "brand": "GitHub"
    },
    {
        "title": "Stripe - Payment processing",
        "description": "Accept payments online with a complete payment platform for businesses.",
        "landing_url": "https://stripe.com",
        "category": "finance",
        "brand": "Stripe"
    },
    {
        "title": "Zapier - Automation",
        "description": "Connect your apps and automate workflows without coding.",
        "landing_url": "https://zapier.com",
        "category": "automation",
        "brand": "Zapier"
    },
    {
        "title": "Calendly - Scheduling",
        "description": "Scheduling made simple with calendar integration and automated reminders.",
        "landing_url": "https://calendly.com",
        "category": "productivity",
        "brand": "Calendly"
    },
    {
        "title": "Loom - Video messaging",
        "description": "Async video communication for teams with instant recording and sharing.",
        "landing_url": "https://loom.com",
        "category": "communication",
        "brand": "Loom"
    },
    {
        "title": "Typeform - Forms & surveys",
        "description": "Create beautiful forms, surveys, and quizzes with conditional logic.",
        "landing_url": "https://typeform.com",
        "category": "tools",
        "brand": "Typeform"
    },
    {
        "title": "Airtable - Flexible database",
        "description": "Database platform with automation, API, and collaborative features.",
        "landing_url": "https://airtable.com",
        "category": "productivity",
        "brand": "Airtable"
    },
    {
        "title": "Mailchimp - Email marketing",
        "description": "Email marketing platform with automation, templates, and analytics.",
        "landing_url": "https://mailchimp.com",
        "category": "marketing",
        "brand": "Mailchimp"
    },
    {
        "title": "HubSpot - CRM platform",
        "description": "Customer relationship management with sales, marketing, and service tools.",
        "landing_url": "https://hubspot.com",
        "category": "sales",
        "brand": "HubSpot"
    },
    {
        "title": "Intercom - Customer messaging",
        "description": "Customer communication platform with chat, support, and analytics.",
        "landing_url": "https://intercom.com",
        "category": "communication",
        "brand": "Intercom"
    },
    {
        "title": "Mixpanel - Product analytics",
        "description": "Understand user behavior with event tracking, funnels, and cohorts.",
        "landing_url": "https://mixpanel.com",
        "category": "analytics",
        "brand": "Mixpanel"
    },
    {
        "title": "Amplitude - Digital analytics",
        "description": "Product analytics platform for understanding user journeys and insights.",
        "landing_url": "https://amplitude.com",
        "category": "analytics",
        "brand": "Amplitude"
    },
    {
        "title": "Segment - Customer data",
        "description": "Unified customer data platform for tracking and analytics.",
        "landing_url": "https://segment.com",
        "category": "data",
        "brand": "Segment"
    },
    {
        "title": "Twilio - Communication API",
        "description": "SMS, voice, and video APIs for building communication features.",
        "landing_url": "https://twilio.com",
        "category": "development",
        "brand": "Twilio"
    },
    {
        "title": "Auth0 - Authentication",
        "description": "Identity and access management with MFA and security features.",
        "landing_url": "https://auth0.com",
        "category": "security",
        "brand": "Auth0"
    },
    {
        "title": "Vercel - Frontend hosting",
        "description": "Frontend hosting and deployment with CI/CD and analytics.",
        "landing_url": "https://vercel.com",
        "category": "development",
        "brand": "Vercel"
    },
    {
        "title": "Supabase - Backend platform",
        "description": "Open source Firebase alternative with database, auth, and storage.",
        "landing_url": "https://supabase.com",
        "category": "development",
        "brand": "Supabase"
    }
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
                    "encoding_format": "float"
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

async def seed_ads():
    """Seed the database with example ads."""
    try:
        # Get or create demo partner
        print("Fetching demo partner...")
        partners_response = supabase.table("partners").select("id").eq(
            "api_key_hash", hashlib.sha256(b"demo_key").hexdigest()
        ).execute()
        
        if not partners_response.data:
            print("Creating demo partner...")
            partner_response = supabase.table("partners").insert({
                "name": "Demo Partner",
                "api_key_hash": hashlib.sha256(b"demo_key").hexdigest()
            }).execute()
            partner_id = partner_response.data[0]["id"]
        else:
            partner_id = partners_response.data[0]["id"]
        
        print(f"Using partner ID: {partner_id}")
        
        # Check if ads already exist
        existing_ads = supabase.table("ads").select("id").eq("partner_id", partner_id).execute()
        if existing_ads.data and len(existing_ads.data) >= 20:
            print(f"Database already has {len(existing_ads.data)} ads, skipping seed")
            return
        
        print(f"Seeding {len(EXAMPLE_ADS)} example ads...")
        
        for i, ad in enumerate(EXAMPLE_ADS):
            # Generate embedding for ad description
            embedding = await get_embedding(ad["description"])
            
            # Insert ad
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
                    "tags": [ad["category"], ad["brand"].lower()]
                },
                "active": True
            }
            
            if embedding:
                ad_data["embedding"] = embedding
            
            try:
                supabase.table("ads").insert(ad_data).execute()
                print(f"✓ Seeded ad {i+1}/{len(EXAMPLE_ADS)}: {ad['title']}")
            except Exception as e:
                print(f"✗ Error seeding ad {i+1}: {e}")
        
        print(f"\n✓ Successfully seeded {len(EXAMPLE_ADS)} example ads!")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(seed_ads())
