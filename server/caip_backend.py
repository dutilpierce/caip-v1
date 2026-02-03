"""
CAIP v1 - Conversational Ad Integration Platform
FastAPI backend with Supabase integration, pgvector semantic matching,
policy filtering, and premium sponsored suggestions.
"""

import os
import json
import hashlib
import logging
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from functools import lru_cache
import asyncio

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
PARTNER_SALT = os.getenv("PARTNER_SALT", "default-salt-change-me")
CAIP_ENV = os.getenv("CAIP_ENV", "dev")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Validate required env vars
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")

SUPABASE_REST_BASE = f"{SUPABASE_URL.rstrip('/')}/rest/v1"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="CAIP v1 - Conversational Ad Integration Platform",
    description="Middleware for elegant sponsored suggestions in conversational AI",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATA MODELS
# ============================================================================

class Message(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    partner_key: str = Field(..., description="Partner API key")
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    messages: List[Message] = Field(..., description="Message history")
    placement_mode: Optional[str] = Field("subtle", description="Placement mode: subtle, direct, interactive")

class SponsoredUnit(BaseModel):
    ad_id: str
    title: str
    description: str
    landing_url: str
    category: str
    brand: str
    disclosure: str
    why_shown: str
    coupon_code: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ChatResponse(BaseModel):
    assistant_message: str
    sponsored_unit: Optional[SponsoredUnit] = None
    session_id: str
    intent_label: Optional[str] = None

class EventRequest(BaseModel):
    partner_key: str
    session_id: str
    event_type: str = Field(..., description="impression, click, feedback, etc.")
    ad_id: Optional[str] = None
    user_id: Optional[str] = None
    intent_label: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

class SponsoredAskRequest(BaseModel):
    partner_key: str
    ad_id: str
    question: str
    session_id: str

class SponsoredAskResponse(BaseModel):
    answer: str
    ad_id: str

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def hash_user_id(user_id: str) -> str:
    """Hash user ID with partner salt for privacy."""
    combined = f"{user_id}:{PARTNER_SALT}"
    return hashlib.sha256(combined.encode()).hexdigest()

def ensure_sha256_hex(value: Optional[str], field_name: str) -> Optional[str]:
    """Validate a 64-character lowercase SHA-256 hex string."""
    if value is None:
        return None
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be 64-character SHA-256 hex"
        )
    return value

def normalize_ip(request: Optional[Request]) -> Optional[str]:
    """
    Normalize client IP for storage/logging.
    - Prefer x-forwarded-for (first IP), then cf-connecting-ip, true-client-ip, request.client.host
    - Trim whitespace
    - Truncate to 64 chars if needed
    - Return None if missing/invalid
    """
    if request is None:
        return None

    def _extract(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        first = value.split(",")[0].strip()
        if not first:
            return None
        if len(first) > 64:
            return first[:64]
        return first

    candidate = (
        _extract(request.headers.get("x-forwarded-for"))
        or _extract(request.headers.get("cf-connecting-ip"))
        or _extract(request.headers.get("true-client-ip"))
        or _extract(request.client.host if request.client else None)
    )

    if not candidate:
        return None

    if len(candidate) > 64:
        return candidate[:64]

    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None

    return candidate

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
    url = f"{SUPABASE_REST_BASE}/{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                url,
                headers=_supabase_headers(prefer=prefer),
                params=params,
                json=body,
            )
            response.raise_for_status()
            if not response.text:
                return None
            return response.json()
    except httpx.HTTPError as exc:
        logger.error(f"Supabase REST error ({method} {path}): {exc}")
        raise

def supabase_rpc(function_name: str, body: Optional[Dict[str, Any]] = None) -> Any:
    return supabase_request("POST", f"rpc/{function_name}", body=body)

@lru_cache(maxsize=128)
def get_partner_config(partner_key: str) -> Optional[Dict[str, Any]]:
    """Get partner configuration and policy profile from Supabase."""
    try:
        response = supabase_request(
            "GET",
            "partners",
            params={
                "select": "*,policy_profiles(*)",
                "api_key_hash": f"eq.{hashlib.sha256(partner_key.encode()).hexdigest()}",
                "limit": "1",
            },
        )
        if response:
            return response[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching partner config: {e}")
        return None

async def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for text using OpenAI API."""
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, skipping embedding")
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
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

async def get_intent_label(messages: List[Message]) -> Optional[str]:
    """Extract intent label from conversation using LLM."""
    if not OPENAI_API_KEY:
        return None
    
    try:
        # Build conversation context
        conversation = "\n".join([f"{m.role}: {m.content}" for m in messages[-3:]])
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Extract a single-word intent label from the conversation. Return only the label, no explanation."
                        },
                        {
                            "role": "user",
                            "content": conversation
                        }
                    ],
                    "max_tokens": 10,
                    "temperature": 0.3
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error extracting intent label: {e}")
        return None

async def proxy_llm_chat(messages: List[Message]) -> str:
    """Proxy chat request to OpenAI API."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="LLM service not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error proxying LLM chat: {e}")
        raise HTTPException(status_code=503, detail="LLM service error")

# ============================================================================
# DECISIONING ENGINE
# ============================================================================

class DecisioningEngine:
    """Core decisioning logic for sponsored suggestions."""
    
    def __init__(self, partner_config: Dict[str, Any]):
        self.partner_config = partner_config
        self.policy = partner_config.get("policy_profiles", [{}])[0] if partner_config else {}
    
    def check_blocked_categories(self, intent: str) -> bool:
        """Check if intent matches blocked categories."""
        blocked = self.policy.get("blocked_categories", [])
        if not blocked:
            return False
        return any(cat.lower() in intent.lower() for cat in blocked)
    
    def check_explicit_intent_requirement(self, intent: str) -> bool:
        """Check if explicit intent is required for this category."""
        required = self.policy.get("requires_explicit_intent_categories", [])
        if not required:
            return False
        return any(cat.lower() in intent.lower() for cat in required)
    
    def check_frequency_caps(self, session_id: str, user_hash: str) -> bool:
        """Check frequency caps for session and user."""
        try:
            max_per_session = self.policy.get("max_sponsored_per_session", 3)
            min_turns = self.policy.get("min_turns_between_sponsored", 2)
            
            # Count impressions in current session
            impressions = supabase_request(
                "GET",
                "events",
                params={
                    "select": "id",
                    "session_id": f"eq.{session_id}",
                    "event_type": "eq.impression",
                },
            ) or []
            
            if len(impressions) >= max_per_session:
                logger.info(f"Frequency cap reached for session {session_id}")
                return False
            
            # Check min turns between sponsored
            recent_events = supabase_request(
                "GET",
                "events",
                params={
                    "select": "event_type",
                    "session_id": f"eq.{session_id}",
                    "order": "created_at.desc",
                    "limit": str(min_turns),
                },
            ) or []
            
            for event in recent_events:
                if event.get("event_type") == "impression":
                    logger.info(f"Min turns between sponsored not met for session {session_id}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking frequency caps: {e}")
            return True  # Allow if check fails
    
    async def find_best_ad(self, intent_embedding: Optional[List[float]], intent: str) -> Optional[Dict[str, Any]]:
        """Find best matching ad using pgvector semantic search."""
        if not intent_embedding:
            logger.warning("No embedding available for semantic search")
            return None
        
        try:
            # Use pgvector cosine similarity search
            response = await asyncio.to_thread(
                supabase_rpc,
                "match_ads",
                {
                    "query_embedding": intent_embedding,
                    "match_count": 5,
                    "similarity_threshold": 0.5,
                },
            )
            
            if response and len(response) > 0:
                # Filter by active status and category
                for ad in response:
                    if ad.get("active") and not self.check_blocked_categories(ad.get("category", "")):
                        return ad
            
            return None
        except Exception as e:
            logger.error(f"Error finding best ad: {e}")
            return None
    
    def get_disclosure_label(self) -> str:
        """Get appropriate disclosure label based on policy."""
        mode = self.policy.get("disclosure_mode", "sponsored_suggestion")
        labels = {
            "sponsored_suggestion": "Sponsored suggestion",
            "partner_option": "Partner option",
            "paid_recommendation": "Paid recommendation"
        }
        return labels.get(mode, "Sponsored suggestion")

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "environment": CAIP_ENV}

@app.get("/docs")
async def swagger_docs():
    """Swagger documentation redirect."""
    return JSONResponse({"message": "Visit /docs for API documentation"})

@app.post("/v1/chat")
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """
    Main chat endpoint that proxies to LLM and optionally returns sponsored unit.
    
    Flow:
    1. Validate partner and get policy config
    2. Extract intent and generate embedding
    3. Proxy chat to LLM
    4. Apply decisioning logic to determine if sponsored unit should be shown
    5. If eligible, find best matching ad via pgvector
    6. Return response with optional sponsored unit
    """
    start_time = datetime.now()
    
    try:
        # Validate partner
        partner_config = get_partner_config(payload.partner_key)
        if not partner_config:
            raise HTTPException(status_code=401, detail="Invalid partner key")
        
        partner_id = partner_config.get("id")
        
        # Hash user ID for privacy
        user_hash = hash_user_id(payload.user_id or payload.session_id)
        ensure_sha256_hex(user_hash, "user_hash")
        
        # Extract intent and generate embedding
        intent_label = await get_intent_label(payload.messages)
        intent_text = payload.messages[-1].content if payload.messages else ""
        intent_embedding = await get_embedding(intent_text)
        
        # Proxy chat to LLM
        assistant_message = await proxy_llm_chat(payload.messages)
        
        # Initialize decisioning engine
        engine = DecisioningEngine(partner_config)
        
        # Determine if sponsored unit should be shown
        sponsored_unit = None
        
        # Check if we should show sponsored content
        if not engine.check_blocked_categories(intent_label or ""):
            if engine.check_frequency_caps(payload.session_id, user_hash):
                # Find best matching ad
                ad = await engine.find_best_ad(intent_embedding, intent_label or "")
                
                if ad:
                    # Get coupon if available
                    coupon = None
                    try:
                        coupon_response = supabase_request(
                            "GET",
                            "coupons",
                            params={
                                "select": "code",
                                "ad_id": f"eq.{ad['id']}",
                                "limit": "1",
                            },
                        )
                        if coupon_response:
                            coupon = coupon_response[0].get("code")
                    except Exception as e:
                        logger.error(f"Error fetching coupon: {e}")
                    
                    # Build sponsored unit
                    sponsored_unit = SponsoredUnit(
                        ad_id=ad["id"],
                        title=ad.get("title", ""),
                        description=ad.get("description", ""),
                        landing_url=ad.get("landing_url", ""),
                        category=ad.get("category", ""),
                        brand=ad.get("brand", ""),
                        disclosure=engine.get_disclosure_label(),
                        why_shown=f"Shown because you asked about {intent_label or 'this topic'}.",
                        coupon_code=coupon,
                        metadata=ad.get("metadata", {})
                    )
                    
                    # Log impression event
                    try:
                        supabase_request("POST", "events", body={
                            "partner_id": partner_id,
                            "session_id": payload.session_id,
                            "user_hash": user_hash,
                            "event_type": "impression",
                            "ad_id": ad["id"],
                            "intent_label": intent_label,
                            "properties": {
                                "placement_mode": payload.placement_mode,
                                "ip_address": normalize_ip(request) or "unknown",
                                "decisioning_ms": (datetime.now() - start_time).total_seconds() * 1000
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error logging impression: {e}")
        
        # Log response time
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Chat response generated in {response_time_ms:.2f}ms")
        
        return ChatResponse(
            assistant_message=assistant_message,
            sponsored_unit=sponsored_unit,
            session_id=payload.session_id,
            intent_label=intent_label
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /v1/chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/events")
async def log_event(payload: EventRequest, request: Request):
    """
    Log user events (impressions, clicks, feedback) for reporting and learning.
    """
    try:
        # Validate partner
        partner_config = get_partner_config(payload.partner_key)
        if not partner_config:
            raise HTTPException(status_code=401, detail="Invalid partner key")
        
        partner_id = partner_config.get("id")
        
        # Hash user ID
        user_hash = hash_user_id(payload.user_id or payload.session_id) if payload.user_id else None
        ensure_sha256_hex(user_hash, "user_hash")
        base_properties = payload.properties or {}
        
        # Insert event
        supabase_request("POST", "events", body={
            "partner_id": partner_id,
            "session_id": payload.session_id,
            "user_hash": user_hash,
            "event_type": payload.event_type,
            "ad_id": payload.ad_id,
            "intent_label": payload.intent_label,
            "properties": {
                **base_properties,
                "ip_address": normalize_ip(request) or "unknown"
            }
        })
        
        logger.info(f"Event logged: {payload.event_type} for session {payload.session_id}")
        
        return {"success": True, "event_type": payload.event_type}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /v1/events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/sponsored/ask")
async def sponsored_ask(payload: SponsoredAskRequest, request: Request) -> SponsoredAskResponse:
    """
    Interactive follow-up Q&A about sponsored options.
    Answers questions about an ad using ad metadata and constrained LLM prompt.
    """
    try:
        # Validate partner
        partner_config = get_partner_config(payload.partner_key)
        if not partner_config:
            raise HTTPException(status_code=401, detail="Invalid partner key")
        
        # Fetch ad details
        ad_response = supabase_request(
            "GET",
            "ads",
            params={"select": "*", "id": f"eq.{payload.ad_id}", "limit": "1"},
        )
        if not ad_response:
            raise HTTPException(status_code=404, detail="Ad not found")
        
        ad = ad_response[0]
        
        # Build constrained prompt for LLM
        system_prompt = f"""You are a helpful assistant answering questions about a product/service.
        
Product: {ad.get('title', '')}
Brand: {ad.get('brand', '')}
Category: {ad.get('category', '')}
Description: {ad.get('description', '')}
Details: {json.dumps(ad.get('metadata', {}))}

Answer the user's question based on the product information above. Keep responses concise (1-2 sentences).
If the question cannot be answered from the available information, say so politely."""
        
        # Call LLM
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": payload.question}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 150
                }
            )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
        
        # Log interaction event
        try:
            supabase_request("POST", "events", body={
                "partner_id": partner_config.get("id"),
                "session_id": payload.session_id,
                "event_type": "sponsored_ask",
                "ad_id": payload.ad_id,
                "properties": {
                    "question": payload.question,
                    "ip_address": normalize_ip(request) or "unknown"
                }
            })
        except Exception as e:
            logger.error(f"Error logging sponsored_ask event: {e}")
        
        return SponsoredAskResponse(answer=answer, ad_id=payload.ad_id)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /v1/sponsored/ask: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
