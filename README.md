# CAIP v1 - Conversational Ad Integration Platform

A sophisticated middleware for integrating elegant, policy-compliant sponsored suggestions into conversational AI experiences. Built with FastAPI, Supabase, pgvector, and a premium React UI.

## Overview

CAIP v1 is a production-ready platform that enables seamless monetization of conversational AI through tasteful, user-respecting sponsored suggestions. The platform emphasizes privacy, policy compliance, and user control.

**Key Features:**
- **Semantic Ad Matching**: pgvector-based cosine similarity search for contextually relevant ads
- **Policy Filtering**: Blocked categories, explicit intent requirements, and disclosure rules
- **Frequency Caps**: Max sponsored per session and minimum turns between suggestions
- **Privacy-First**: SHA256 user ID hashing, no raw transcript storage by default
- **Interactive Q&A**: Users can ask questions about sponsored options without leaving chat
- **Premium UI**: Elegant, minimal sponsored card design with user controls
- **Sub-200ms Decisioning**: Fast policy evaluation and ad selection

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  - Chat interface with message history                  │
│  - Placement mode toggles (Subtle/Direct/Interactive)   │
│  - Sponsored card with disclosure and controls          │
└─────────────────────┬───────────────────────────────────┘
                      │ /v1/chat, /v1/events, /v1/sponsored/ask
┌─────────────────────▼───────────────────────────────────┐
│              FastAPI Backend (Python)                    │
│  - LLM proxy with OpenAI integration                     │
│  - Decisioning engine with policy enforcement           │
│  - Event logging and analytics                          │
└─────────────────────┬───────────────────────────────────┘
                      │ Supabase SDK
┌─────────────────────▼───────────────────────────────────┐
│         Supabase (PostgreSQL + pgvector)                │
│  - partners, policy_profiles, ads, coupons, events      │
│  - pgvector embeddings for semantic search              │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- Supabase account (free tier available)
- OpenAI API key (optional, for embeddings and LLM)

### 1. Supabase Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Copy your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from Project Settings → API
3. Enable pgvector extension:
   - Go to SQL Editor
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`
4. Run the schema migration:
   - Copy contents of `db/schema.sql`
   - Paste into SQL Editor and execute

### 2. Environment Setup

Create a `.env` file in the project root:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
PARTNER_SALT=your-random-40-character-string
CAIP_ENV=dev
OPENAI_API_KEY=your_openai_api_key
```

### 3. Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Seed example ads
python db/seed.py

# Run FastAPI server
uvicorn server.caip_backend:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

- **Swagger Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. Frontend Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Visit http://localhost:3000/demo to see the chat interface

## API Endpoints

### POST /v1/chat

Main endpoint for proxying chat requests and returning optional sponsored units.

**Request:**
```json
{
  "partner_key": "demo_key",
  "session_id": "session-123",
  "user_id": "user@example.com",
  "messages": [
    {"role": "user", "content": "How do I start a podcast?"}
  ],
  "placement_mode": "subtle"
}
```

**Response:**
```json
{
  "assistant_message": "Here are the steps to start a podcast...",
  "sponsored_unit": {
    "ad_id": "ad-123",
    "title": "Anchor - Podcast Hosting",
    "description": "Easy podcast hosting and distribution",
    "landing_url": "https://anchor.fm",
    "category": "media",
    "brand": "Anchor",
    "disclosure": "Sponsored suggestion",
    "why_shown": "Shown because you asked about starting a podcast.",
    "coupon_code": "PODCAST20"
  },
  "session_id": "session-123",
  "intent_label": "podcast"
}
```

### POST /v1/events

Log user events for reporting and learning.

**Request:**
```json
{
  "partner_key": "demo_key",
  "session_id": "session-123",
  "event_type": "impression",
  "ad_id": "ad-123",
  "intent_label": "podcast",
  "properties": {"placement_mode": "subtle"}
}
```

**Event Types:**
- `impression`: Sponsored unit displayed
- `click`: User clicked on sponsored unit
- `feedback`: User provided feedback
- `sponsored_ask`: User asked question about ad

### POST /v1/sponsored/ask

Interactive Q&A about a sponsored option.

**Request:**
```json
{
  "partner_key": "demo_key",
  "ad_id": "ad-123",
  "question": "Does it work on Mac?",
  "session_id": "session-123"
}
```

**Response:**
```json
{
  "answer": "Yes, it works on Mac, Windows, and Linux.",
  "ad_id": "ad-123"
}
```

## Database Schema

### partners
- `id` (UUID): Primary key
- `name` (VARCHAR): Partner name
- `api_key_hash` (VARCHAR): Hashed API key for authentication
- `default_policy_profile_id` (UUID): Default policy profile

### policy_profiles
- `id` (UUID): Primary key
- `partner_id` (UUID): Foreign key to partners
- `blocked_categories` (JSONB): Categories that should never be served
- `requires_explicit_intent_categories` (JSONB): Categories requiring explicit user request
- `max_sponsored_per_session` (INT): Maximum sponsored units per session
- `min_turns_between_sponsored` (INT): Minimum conversation turns between sponsored units
- `disclosure_mode` (VARCHAR): Disclosure label type

### ads
- `id` (UUID): Primary key
- `partner_id` (UUID): Foreign key to partners
- `title` (VARCHAR): Ad title
- `description` (TEXT): Ad description
- `landing_url` (VARCHAR): Destination URL
- `category` (VARCHAR): Ad category
- `brand` (VARCHAR): Brand name
- `payout_model` (VARCHAR): Pricing model (cpm, cpc, etc.)
- `bid_cents` (INT): Bid amount in cents
- `metadata` (JSONB): Additional ad metadata
- `embedding` (vector(1536)): OpenAI embedding for semantic search
- `active` (BOOLEAN): Whether ad is active

### coupons
- `id` (UUID): Primary key
- `ad_id` (UUID): Foreign key to ads
- `code` (VARCHAR): Coupon code
- `expires_at` (TIMESTAMP): Expiration date

### events
- `id` (UUID): Primary key
- `partner_id` (UUID): Foreign key to partners
- `session_id` (VARCHAR): Session identifier
- `user_hash` (VARCHAR): SHA256 hashed user ID
- `event_type` (VARCHAR): Type of event
- `ad_id` (UUID): Foreign key to ads
- `intent_label` (VARCHAR): Extracted intent label
- `properties` (JSONB): Event-specific properties
- `created_at` (TIMESTAMP): Event timestamp

## Decisioning Engine

The decisioning engine enforces policies and determines whether to show sponsored content:

1. **Partner Validation**: Verify partner key and fetch policy profile
2. **Intent Extraction**: Extract intent label from conversation using LLM
3. **Embedding Generation**: Generate vector embedding for intent text
4. **Policy Checks**:
   - Check if intent matches blocked categories → reject
   - Check if explicit intent required → validate user explicitly asked
5. **Frequency Caps**:
   - Check max sponsored per session → reject if exceeded
   - Check min turns between sponsored → reject if too soon
6. **Semantic Matching**: Use pgvector to find best matching ads
7. **Ad Selection**: Return highest-scoring active ad
8. **Event Logging**: Log impression event with properties

**Performance Target**: < 200ms excluding upstream LLM calls

## Sponsored Card UI

The premium sponsored card includes:

- **Neutral Title**: No hype, descriptive
- **Utility Bullets**: Benefits, not specs (max 3)
- **Exploratory CTAs**: "See details", "Compare", "Ask about this"
- **Disclosure Label**: Quiet, 10-11px, muted gray
- **Why You're Seeing This**: Expandable explanation
- **User Controls**: Hide, Less like this, Turn off sponsored

**Placement Rules:**
- Never inline with main answer
- Never at top of response
- Always after main answer
- Separated by whitespace/divider
- Labeled "Optional recommendations"

## Privacy & Security

- **User ID Hashing**: SHA256(user_id + partner_salt) → no raw user IDs stored
- **No Raw Transcripts**: Conversation content not stored by default
- **Intent Labels**: Only derived intent labels stored
- **Embeddings**: Vector embeddings stored for semantic matching, not raw text
- **Event Logging**: Minimal event properties, no sensitive data

## Testing

Run the test suite:

```bash
pytest server/test_caip.py -v
```

Tests cover:
- User ID hashing consistency
- Policy filtering (blocked categories, explicit intent)
- Frequency cap enforcement
- Disclosure label generation
- Embedding generation
- Intent extraction
- Event logging

## Deployment

### Local Development

```bash
# Terminal 1: Backend
uvicorn server.caip_backend:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
npm run dev
```

### Production Deployment

**Backend (Replit/Railway/Render):**
1. Push code to repository
2. Set environment variables
3. Run: `uvicorn server.caip_backend:app --host 0.0.0.0 --port 8000`

**Frontend (Vercel/Netlify):**
1. Connect repository
2. Build command: `npm run build`
3. Output directory: `dist`

## Configuration

### Placement Modes

- **Subtle**: Minimal disclosure, quiet styling
- **Direct**: Clear "Sponsored" label, prominent placement
- **Interactive**: Includes "Ask about this" CTA for Q&A

### Disclosure Modes

- `sponsored_suggestion`: "Sponsored suggestion"
- `partner_option`: "Partner option"
- `paid_recommendation`: "Paid recommendation"

### Policy Examples

**Conservative (Finance):**
```json
{
  "blocked_categories": ["gambling", "weapons", "adult"],
  "requires_explicit_intent_categories": ["finance", "health", "legal"],
  "max_sponsored_per_session": 2,
  "min_turns_between_sponsored": 3,
  "disclosure_mode": "paid_recommendation"
}
```

**Moderate (General):**
```json
{
  "blocked_categories": ["weapons", "adult"],
  "requires_explicit_intent_categories": ["health"],
  "max_sponsored_per_session": 3,
  "min_turns_between_sponsored": 2,
  "disclosure_mode": "sponsored_suggestion"
}
```

## Troubleshooting

### Embeddings Not Generated
- Verify OpenAI API key is set
- Check API key has embeddings access
- Review API usage and rate limits

### No Sponsored Units Showing
- Check policy_profiles for blocked categories
- Verify ads exist and are active
- Check frequency caps haven't been exceeded
- Review event logs for decisioning details

### Slow Response Times
- Monitor pgvector search performance
- Check OpenAI API latency
- Review database indexes
- Consider caching embeddings

## Microcopy Library

### Section Headers
- Optional recommendations
- Options to consider
- If you want, here are a few relevant options

### Disclosure Labels
- Sponsored suggestion
- Partner option
- Paid recommendation

### CTAs
- See details
- Compare with others
- Ask about this
- View option

### User Controls
- Hide this
- Less like this
- Turn off sponsored suggestions

## License

MIT

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the development team.
