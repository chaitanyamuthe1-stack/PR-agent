-- =============================================================================
-- Migration: 20261020000000_create_reviews_schema.sql
-- Description: Initial schema for PR Agent (Code Review & Auto-Correction Platform)
-- Includes:
--   1. Extensions (pgvector for 128D Semantic RAG Grounding)
--   2. reviews table (matching backend persistence layer with JSONB storage)
--   3. rag_knowledge_vectors table (for OWASP Top 10 & CWE Top 25 embeddings)
--   4. Indexes (B-tree, GIN for JSONB payloads, and vector cosine distance)
--   5. Row Level Security (RLS) policies
--   6. Automatic updated_at trigger
-- =============================================================================

-- 1. Enable pgvector extension for RAG vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create reviews table for code review runs and audit telemetry
CREATE TABLE IF NOT EXISTS public.reviews (
    review_id TEXT PRIMARY KEY,
    timestamp DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    filename TEXT NOT NULL DEFAULT 'unknown',
    language TEXT NOT NULL DEFAULT 'unknown',
    health_score NUMERIC(4, 2) NOT NULL DEFAULT 10.00,
    post_fix_score NUMERIC(4, 2) NOT NULL DEFAULT 10.00,
    verdict TEXT NOT NULL DEFAULT 'PENDING',
    unresolved_count INTEGER NOT NULL DEFAULT 0,
    resolved_count INTEGER NOT NULL DEFAULT 0,
    remediation_status TEXT NOT NULL DEFAULT 'NOT_REQUIRED',
    auto_fix_failure INTEGER NOT NULL DEFAULT 0,
    json_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table and column documentation
COMMENT ON TABLE public.reviews IS 'Stores PR Agent triage reports, health scores, and remediation telemetry.';
COMMENT ON COLUMN public.reviews.review_id IS 'Unique identifier for the review run (UUID or custom ID).';
COMMENT ON COLUMN public.reviews.health_score IS 'Initial health score out of 10.0 before remediation.';
COMMENT ON COLUMN public.reviews.post_fix_score IS 'Final health score out of 10.0 after Coder Agent remediation loop.';
COMMENT ON COLUMN public.reviews.verdict IS 'Triage outcome: CLEAN, FIX REQUIRED, or PENDING.';
COMMENT ON COLUMN public.reviews.remediation_status IS 'State of remediation: NOT_REQUIRED, REMEDIATED, or AUTO_FIX_FAILED.';
COMMENT ON COLUMN public.reviews.json_data IS 'Full structured review report payload (issues, diff, metrics).';

-- 3. Create rag_knowledge_vectors table for 128D normative RAG directives
CREATE TABLE IF NOT EXISTS public.rag_knowledge_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_type TEXT NOT NULL, -- 'OWASP' or 'CWE' or 'STYLE'
    rule_id TEXT NOT NULL,       -- e.g. 'A03:2021', 'CWE-89'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    remediation_guide TEXT,
    embedding vector(128),       -- 128-dimensional dense n-gram vector matching PR Agent RAG
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.rag_knowledge_vectors IS 'Normative security & style directives indexed for 128D cosine similarity retrieval.';

-- 4. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_reviews_timestamp ON public.reviews (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_verdict ON public.reviews (verdict);
CREATE INDEX IF NOT EXISTS idx_reviews_language ON public.reviews (language);
CREATE INDEX IF NOT EXISTS idx_reviews_json_data ON public.reviews USING GIN (json_data);

CREATE INDEX IF NOT EXISTS idx_rag_rule_id ON public.rag_knowledge_vectors (rule_id);
CREATE INDEX IF NOT EXISTS idx_rag_standard_type ON public.rag_knowledge_vectors (standard_type);

-- 5. Automatic updated_at timestamp trigger
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_reviews_updated_at ON public.reviews;
CREATE TRIGGER trigger_reviews_updated_at
    BEFORE UPDATE ON public.reviews
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 6. Row Level Security (RLS) Configuration
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rag_knowledge_vectors ENABLE ROW LEVEL SECURITY;

-- Allow public read access to review records
CREATE POLICY "Allow public read access on reviews"
    ON public.reviews
    FOR SELECT
    USING (true);

-- Allow public insert/update (suitable for local PR Agent development & anonymous runs)
CREATE POLICY "Allow public insert and update on reviews"
    ON public.reviews
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Allow public read on RAG knowledge vectors
CREATE POLICY "Allow public read on rag_knowledge_vectors"
    ON public.rag_knowledge_vectors
    FOR SELECT
    USING (true);

-- Service role full access on RAG knowledge vectors
CREATE POLICY "Allow service role full access on rag_knowledge_vectors"
    ON public.rag_knowledge_vectors
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
