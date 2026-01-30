# CAIP v1 Development TODO

## Phase 1: Database & Backend Setup
- [x] Supabase pgvector schema (partners, policy_profiles, ads, coupons, events tables)
- [x] Database migrations and seed data system
- [x] FastAPI project structure with async endpoints

## Phase 2: Core Backend Endpoints
- [x] POST /v1/chat endpoint with LLM proxy and sponsored unit logic
- [x] POST /v1/events endpoint for impression/click/feedback logging
- [x] POST /v1/sponsored/ask endpoint for interactive Q&A

## Phase 3: Decisioning Engine
- [x] Policy filter implementation (blocked categories, explicit intent)
- [x] Frequency caps (max per session, min turns between)
- [x] Semantic matching with pgvector cosine similarity
- [x] User ID hashing (SHA256 with partner salt)
- [x] <200ms decisioning performance validation

## Phase 4: Premium Demo UI
- [x] Chat interface with message history
- [x] Placement mode toggles (Subtle/Direct/Interactive)
- [x] Sponsored card component with disclosure labels
- [x] User controls (Hide/Less like this/Turn off)
- [x] Interactive "Ask about this" CTA
- [x] "Why you're seeing this" expandable section
- [x] Permission pattern for non-explicit requests

## Phase 5: Testing & Seed Data
- [x] 20 safe-category example ads seed data
- [x] Unit tests for policy filtering
- [x] Unit tests for frequency caps
- [x] Integration tests for /v1/chat endpoint
- [x] Event logging verification

## Phase 6: Polish & Deployment
- [x] Swagger API documentation
- [x] Error handling and validation
- [x] Structured JSON logging
- [x] Rate limiting per partner_key
- [x] Caching for embeddings and search results
- [x] Final UI polish and visual refinement
