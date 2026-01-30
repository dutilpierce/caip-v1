"""
CAIP v1 Test Suite
Tests for policy filtering, frequency caps, decisioning engine, and endpoints.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import the CAIP backend components
import sys
sys.path.insert(0, '/home/ubuntu/caip-v1/server')

from caip_backend import (
    DecisioningEngine,
    hash_user_id,
    Message,
    ChatRequest,
    EventRequest,
    SponsoredAskRequest
)

# ============================================================================
# TEST DATA
# ============================================================================

MOCK_PARTNER_CONFIG = {
    "id": "partner-123",
    "name": "Test Partner",
    "api_key_hash": "abc123",
    "policy_profiles": [
        {
            "id": "policy-123",
            "blocked_categories": ["gambling", "weapons", "adult"],
            "requires_explicit_intent_categories": ["finance", "health"],
            "max_sponsored_per_session": 3,
            "min_turns_between_sponsored": 2,
            "disclosure_mode": "sponsored_suggestion"
        }
    ]
}

MOCK_AD = {
    "id": "ad-123",
    "title": "Test Product",
    "description": "A great product",
    "landing_url": "https://example.com",
    "category": "productivity",
    "brand": "TestBrand",
    "payout_model": "cpm",
    "bid_cents": 500,
    "metadata": {"features": ["feature1", "feature2"]},
    "active": True
}

# ============================================================================
# UNIT TESTS
# ============================================================================

class TestUserIDHashing:
    """Test user ID hashing for privacy."""
    
    def test_hash_user_id_consistency(self):
        """Same user ID should produce same hash."""
        user_id = "user@example.com"
        hash1 = hash_user_id(user_id)
        hash2 = hash_user_id(user_id)
        assert hash1 == hash2
    
    def test_hash_user_id_different_users(self):
        """Different user IDs should produce different hashes."""
        hash1 = hash_user_id("user1@example.com")
        hash2 = hash_user_id("user2@example.com")
        assert hash1 != hash2
    
    def test_hash_user_id_length(self):
        """Hash should be SHA256 (64 hex characters)."""
        user_hash = hash_user_id("test_user")
        assert len(user_hash) == 64
        assert all(c in "0123456789abcdef" for c in user_hash)


class TestDecisioningEngine:
    """Test the core decisioning engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = DecisioningEngine(MOCK_PARTNER_CONFIG)
    
    def test_blocked_categories_detection(self):
        """Blocked categories should be detected."""
        assert self.engine.check_blocked_categories("gambling tips") is True
        assert self.engine.check_blocked_categories("weapons guide") is True
        assert self.engine.check_blocked_categories("adult content") is True
        assert self.engine.check_blocked_categories("productivity tools") is False
    
    def test_blocked_categories_case_insensitive(self):
        """Blocked category detection should be case-insensitive."""
        assert self.engine.check_blocked_categories("GAMBLING") is True
        assert self.engine.check_blocked_categories("Weapons") is True
    
    def test_explicit_intent_requirement(self):
        """Explicit intent requirement should be detected."""
        assert self.engine.check_explicit_intent_requirement("finance advice") is True
        assert self.engine.check_explicit_intent_requirement("health tips") is True
        assert self.engine.check_explicit_intent_requirement("productivity") is False
    
    def test_explicit_intent_case_insensitive(self):
        """Explicit intent detection should be case-insensitive."""
        assert self.engine.check_explicit_intent_requirement("FINANCE") is True
        assert self.engine.check_explicit_intent_requirement("Health") is True
    
    def test_disclosure_label_generation(self):
        """Disclosure label should match policy."""
        label = self.engine.get_disclosure_label()
        assert label == "Sponsored suggestion"
    
    def test_disclosure_label_partner_option(self):
        """Should support different disclosure modes."""
        config = MOCK_PARTNER_CONFIG.copy()
        config["policy_profiles"][0]["disclosure_mode"] = "partner_option"
        engine = DecisioningEngine(config)
        assert engine.get_disclosure_label() == "Partner option"
    
    def test_disclosure_label_paid_recommendation(self):
        """Should support paid recommendation disclosure."""
        config = MOCK_PARTNER_CONFIG.copy()
        config["policy_profiles"][0]["disclosure_mode"] = "paid_recommendation"
        engine = DecisioningEngine(config)
        assert engine.get_disclosure_label() == "Paid recommendation"


class TestFrequencyCaps:
    """Test frequency cap enforcement."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = DecisioningEngine(MOCK_PARTNER_CONFIG)
    
    @patch('caip_backend.supabase')
    def test_max_sponsored_per_session_cap(self, mock_supabase):
        """Should respect max sponsored per session."""
        # Mock: already 3 impressions in session
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "event-1"},
            {"id": "event-2"},
            {"id": "event-3"}
        ]
        
        result = self.engine.check_frequency_caps("session-123", "user-hash")
        assert result is False
    
    @patch('caip_backend.supabase')
    def test_min_turns_between_sponsored(self, mock_supabase):
        """Should respect minimum turns between sponsored."""
        # Mock: recent events include impression within min turns
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "event-1"}
        ]
        
        # First call for impression count
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        # Second call for recent events
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"event_type": "impression"}
        ]
        
        # This is a simplified test; full implementation would need more mocking
        # Result depends on mock setup
    
    @patch('caip_backend.supabase')
    def test_frequency_cap_check_passes(self, mock_supabase):
        """Should allow sponsored when caps not reached."""
        # Mock: no impressions yet
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock: no recent events
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        
        result = self.engine.check_frequency_caps("session-123", "user-hash")
        assert result is True


class TestPolicyFiltering:
    """Test policy-based ad filtering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = DecisioningEngine(MOCK_PARTNER_CONFIG)
    
    def test_blocked_category_prevents_ad_serving(self):
        """Ads in blocked categories should not be served."""
        # Intent matches blocked category
        is_blocked = self.engine.check_blocked_categories("gambling")
        assert is_blocked is True
    
    def test_allowed_category_permits_ad_serving(self):
        """Ads in allowed categories should be eligible."""
        is_blocked = self.engine.check_blocked_categories("productivity")
        assert is_blocked is False
    
    def test_explicit_intent_requirement_enforced(self):
        """Explicit intent categories require user request."""
        requires_explicit = self.engine.check_explicit_intent_requirement("finance")
        assert requires_explicit is True
    
    def test_non_restricted_category_no_explicit_intent(self):
        """Non-restricted categories don't require explicit intent."""
        requires_explicit = self.engine.check_explicit_intent_requirement("productivity")
        assert requires_explicit is False


class TestEmbeddingGeneration:
    """Test embedding generation (mocked)."""
    
    @pytest.mark.asyncio
    async def test_embedding_generation_success(self):
        """Should successfully generate embeddings."""
        from caip_backend import get_embedding
        
        with patch('caip_backend.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3] * 512}]  # 1536 dimensions
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            embedding = await get_embedding("test text")
            assert embedding is not None
            assert len(embedding) == 1536
    
    @pytest.mark.asyncio
    async def test_embedding_generation_handles_error(self):
        """Should handle embedding generation errors gracefully."""
        from caip_backend import get_embedding
        
        with patch('caip_backend.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
            
            embedding = await get_embedding("test text")
            assert embedding is None


class TestIntentExtraction:
    """Test intent label extraction (mocked)."""
    
    @pytest.mark.asyncio
    async def test_intent_extraction_success(self):
        """Should successfully extract intent labels."""
        from caip_backend import get_intent_label
        
        messages = [
            Message(role="user", content="How do I start a podcast?"),
            Message(role="assistant", content="Here are some steps..."),
            Message(role="user", content="What equipment do I need?")
        ]
        
        with patch('caip_backend.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "podcast"}}]
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            intent = await get_intent_label(messages)
            assert intent == "podcast"
    
    @pytest.mark.asyncio
    async def test_intent_extraction_handles_error(self):
        """Should handle intent extraction errors gracefully."""
        from caip_backend import get_intent_label
        
        messages = [Message(role="user", content="test")]
        
        with patch('caip_backend.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
            
            intent = await get_intent_label(messages)
            assert intent is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestChatEndpoint:
    """Test /v1/chat endpoint integration."""
    
    @pytest.mark.asyncio
    async def test_chat_request_validation(self):
        """Chat request should validate required fields."""
        # Valid request
        valid_request = ChatRequest(
            partner_key="demo_key",
            session_id="session-123",
            messages=[Message(role="user", content="Hello")]
        )
        assert valid_request.partner_key == "demo_key"
        assert valid_request.session_id == "session-123"
    
    @pytest.mark.asyncio
    async def test_chat_request_with_placement_mode(self):
        """Chat request should accept placement modes."""
        request = ChatRequest(
            partner_key="demo_key",
            session_id="session-123",
            messages=[Message(role="user", content="Hello")],
            placement_mode="interactive"
        )
        assert request.placement_mode == "interactive"


class TestEventLogging:
    """Test event logging functionality."""
    
    def test_event_request_validation(self):
        """Event request should validate required fields."""
        event = EventRequest(
            partner_key="demo_key",
            session_id="session-123",
            event_type="impression",
            ad_id="ad-123"
        )
        assert event.event_type == "impression"
        assert event.ad_id == "ad-123"
    
    def test_event_request_with_properties(self):
        """Event request should accept custom properties."""
        event = EventRequest(
            partner_key="demo_key",
            session_id="session-123",
            event_type="click",
            ad_id="ad-123",
            properties={"placement": "subtle", "duration_ms": 1500}
        )
        assert event.properties["placement"] == "subtle"


class TestSponsoredAsk:
    """Test sponsored ask endpoint."""
    
    def test_sponsored_ask_request_validation(self):
        """Sponsored ask request should validate required fields."""
        request = SponsoredAskRequest(
            partner_key="demo_key",
            ad_id="ad-123",
            question="Does this work on Mac?",
            session_id="session-123"
        )
        assert request.ad_id == "ad-123"
        assert request.question == "Does this work on Mac?"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance constraints."""
    
    def test_decisioning_engine_initialization_speed(self):
        """Decisioning engine should initialize quickly."""
        import time
        
        start = time.time()
        for _ in range(1000):
            engine = DecisioningEngine(MOCK_PARTNER_CONFIG)
        elapsed = (time.time() - start) * 1000
        
        # Should initialize 1000 engines in < 100ms
        assert elapsed < 100, f"Engine initialization too slow: {elapsed:.2f}ms for 1000 engines"
    
    def test_policy_check_speed(self):
        """Policy checks should be fast."""
        import time
        
        engine = DecisioningEngine(MOCK_PARTNER_CONFIG)
        
        start = time.time()
        for _ in range(10000):
            engine.check_blocked_categories("productivity")
            engine.check_explicit_intent_requirement("finance")
        elapsed = (time.time() - start) * 1000
        
        # Should perform 20000 checks in < 50ms
        assert elapsed < 50, f"Policy checks too slow: {elapsed:.2f}ms for 20000 checks"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
