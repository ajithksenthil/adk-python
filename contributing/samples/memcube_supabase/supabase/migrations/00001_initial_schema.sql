-- MemCube Initial Schema Migration
-- Creates core tables, types, and indexes for the memory system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- Create custom types
CREATE TYPE memory_type AS ENUM ('PLAINTEXT', 'ACTIVATION', 'PARAMETER');
CREATE TYPE memory_lifecycle AS ENUM ('NEW', 'ACTIVE', 'STALE', 'ARCHIVED', 'EXPIRED');
CREATE TYPE memory_priority AS ENUM ('HOT', 'WARM', 'COLD');
CREATE TYPE storage_mode AS ENUM ('INLINE', 'COMPRESSED', 'COLD');

-- Create memories table (core metadata)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    label TEXT NOT NULL,
    type memory_type NOT NULL DEFAULT 'PLAINTEXT',
    version INTEGER NOT NULL DEFAULT 1,
    origin TEXT,
    
    -- Governance
    governance JSONB NOT NULL DEFAULT jsonb_build_object(
        'read_roles', ARRAY['MEMBER', 'AGENT'],
        'write_roles', ARRAY['AGENT'],
        'ttl_days', 365,
        'shareable', true,
        'license', null,
        'pii_tagged', false
    ),
    
    -- Metadata
    usage_hits INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMPTZ,
    priority memory_priority NOT NULL DEFAULT 'WARM',
    lifecycle memory_lifecycle NOT NULL DEFAULT 'NEW',
    provenance_id UUID REFERENCES memories(id),
    kv_hint BOOLEAN DEFAULT false,
    watermark BOOLEAN DEFAULT false,
    
    -- Vector embedding for similarity search
    embedding vector(1536), -- OpenAI ada-002 dimensions
    
    -- Tracking
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT memories_label_check CHECK (length(label) > 0),
    CONSTRAINT memories_project_check CHECK (length(project_id) > 0)
);

-- Create memory payloads table (content storage)
CREATE TABLE memory_payloads (
    memory_id UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    content TEXT, -- For PLAINTEXT type
    content_binary BYTEA, -- For ACTIVATION/PARAMETER types
    content_url TEXT, -- For external storage
    storage_mode storage_mode NOT NULL,
    size_bytes INTEGER NOT NULL,
    token_count INTEGER,
    checksum TEXT, -- For integrity verification
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Ensure only one content type is used
    CONSTRAINT payload_content_check CHECK (
        (content IS NOT NULL AND content_binary IS NULL AND content_url IS NULL) OR
        (content IS NULL AND content_binary IS NOT NULL AND content_url IS NULL) OR
        (content IS NULL AND content_binary IS NULL AND content_url IS NOT NULL)
    ),
    
    -- Size validation based on type
    CONSTRAINT payload_size_check CHECK (
        CASE 
            WHEN storage_mode = 'INLINE' THEN size_bytes <= 4096
            WHEN storage_mode = 'COMPRESSED' THEN size_bytes <= 65536
            ELSE true
        END
    )
);

-- Create memory versions table (version history)
CREATE TABLE memory_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    changes JSONB, -- What changed in this version
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(memory_id, version)
);

-- Create memory events table (audit trail)
CREATE TABLE memory_events (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    event TEXT NOT NULL,
    actor TEXT NOT NULL,
    meta JSONB DEFAULT '{}',
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Index for efficient querying
    CONSTRAINT event_name_check CHECK (length(event) > 0)
);

-- Create task-memory links
CREATE TABLE memory_task_links (
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'READ',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    PRIMARY KEY (memory_id, task_id),
    CONSTRAINT role_check CHECK (role IN ('READ', 'WRITE'))
);

-- Create memory packs table (marketplace)
CREATE TABLE memory_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    cover_img TEXT,
    price_cents INTEGER NOT NULL DEFAULT 0,
    royalty_pct INTEGER NOT NULL DEFAULT 10,
    watermark BOOLEAN NOT NULL DEFAULT true,
    tags TEXT[] DEFAULT '{}',
    
    -- Stats
    download_count INTEGER NOT NULL DEFAULT 0,
    rating_sum INTEGER NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    
    -- Status
    published BOOLEAN NOT NULL DEFAULT false,
    approved BOOLEAN NOT NULL DEFAULT false,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT pack_royalty_check CHECK (royalty_pct >= 0 AND royalty_pct <= 100),
    CONSTRAINT pack_price_check CHECK (price_cents >= 0)
);

-- Create pack memories junction table
CREATE TABLE pack_memories (
    pack_id UUID REFERENCES memory_packs(id) ON DELETE CASCADE,
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    
    PRIMARY KEY (pack_id, memory_id)
);

-- Create insights table
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    insight TEXT NOT NULL,
    evidence_refs TEXT[] DEFAULT '{}',
    support_count INTEGER NOT NULL DEFAULT 0,
    sentiment REAL DEFAULT 0.0,
    priority memory_priority NOT NULL DEFAULT 'WARM',
    tags TEXT[] DEFAULT '{}',
    
    -- Converted memory reference
    memory_id UUID REFERENCES memories(id),
    
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT sentiment_range CHECK (sentiment >= -1.0 AND sentiment <= 1.0)
);

-- Create indexes for performance
CREATE INDEX idx_memories_project_id ON memories(project_id);
CREATE INDEX idx_memories_type ON memories(type);
CREATE INDEX idx_memories_priority ON memories(priority);
CREATE INDEX idx_memories_lifecycle ON memories(lifecycle);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_last_used ON memories(last_used DESC NULLS LAST);
CREATE INDEX idx_memories_label_trgm ON memories USING gin(label gin_trgm_ops);

-- Vector similarity search index
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100); -- Adjust based on data size

-- Events and task links
CREATE INDEX idx_memory_events_memory_id ON memory_events(memory_id);
CREATE INDEX idx_memory_events_ts ON memory_events(ts DESC);
CREATE INDEX idx_memory_task_links_task_id ON memory_task_links(task_id);

-- Marketplace indexes
CREATE INDEX idx_memory_packs_author ON memory_packs(author_id);
CREATE INDEX idx_memory_packs_published ON memory_packs(published) WHERE published = true;
CREATE INDEX idx_memory_packs_tags ON memory_packs USING gin(tags);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_packs_updated_at BEFORE UPDATE ON memory_packs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to increment usage hits
CREATE OR REPLACE FUNCTION increment_memory_usage(memory_uuid UUID)
RETURNS void AS $$
BEGIN
    UPDATE memories 
    SET usage_hits = usage_hits + 1,
        last_used = now()
    WHERE id = memory_uuid;
END;
$$ LANGUAGE plpgsql;

-- Create function to calculate pack rating
CREATE OR REPLACE FUNCTION get_pack_rating(pack_uuid UUID)
RETURNS REAL AS $$
DECLARE
    pack_record RECORD;
BEGIN
    SELECT rating_sum, rating_count INTO pack_record
    FROM memory_packs
    WHERE id = pack_uuid;
    
    IF pack_record.rating_count = 0 THEN
        RETURN 0.0;
    ELSE
        RETURN pack_record.rating_sum::REAL / pack_record.rating_count::REAL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function for memory lifecycle transitions
CREATE OR REPLACE FUNCTION update_memory_lifecycle()
RETURNS void AS $$
BEGIN
    -- Mark as STALE if not used for 30 days
    UPDATE memories
    SET lifecycle = 'STALE'
    WHERE lifecycle = 'ACTIVE'
    AND last_used < now() - interval '30 days';
    
    -- Mark as ACTIVE if recently used
    UPDATE memories
    SET lifecycle = 'ACTIVE'
    WHERE lifecycle IN ('NEW', 'STALE')
    AND last_used > now() - interval '7 days';
    
    -- Archive based on governance TTL
    UPDATE memories m
    SET lifecycle = 'ARCHIVED'
    WHERE lifecycle != 'EXPIRED'
    AND created_at < now() - ((m.governance->>'ttl_days')::integer || ' days')::interval;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE memories IS 'Core memory storage with metadata and governance';
COMMENT ON TABLE memory_payloads IS 'Memory content storage with support for different modes';
COMMENT ON TABLE memory_events IS 'Audit trail for all memory operations';
COMMENT ON TABLE memory_packs IS 'Marketplace memory packs for distribution';
COMMENT ON TABLE insights IS 'User-generated insights that can become memories';
COMMENT ON COLUMN memories.embedding IS 'Vector embedding for semantic similarity search';
COMMENT ON COLUMN memories.governance IS 'Access control and lifecycle policies';
COMMENT ON COLUMN memory_payloads.storage_mode IS 'INLINE (<4KB), COMPRESSED (<64KB), or COLD (external)';