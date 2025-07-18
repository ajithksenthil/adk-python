-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to memories table
ALTER TABLE memories 
  ADD COLUMN IF NOT EXISTS embedding vector(1536),
  ADD COLUMN IF NOT EXISTS embedding_model TEXT DEFAULT 'text-embedding-3-small',
  ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP WITH TIME ZONE;

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Function to search memories by semantic similarity
CREATE OR REPLACE FUNCTION search_memories_semantic(
  query_embedding vector,
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 10,
  filter_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  project_id UUID,
  label TEXT,
  type memory_type,
  content TEXT,
  similarity FLOAT,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    m.id,
    m.project_id,
    m.label,
    m.type,
    CASE 
      WHEN m.storage_mode = 'INLINE' THEN p.content::TEXT
      ELSE NULL
    END as content,
    1 - (m.embedding <=> query_embedding) as similarity,
    m.created_at
  FROM memories m
  LEFT JOIN payloads p ON m.id = p.memory_id
  WHERE 
    m.embedding IS NOT NULL
    AND (filter_project_id IS NULL OR m.project_id = filter_project_id)
    AND 1 - (m.embedding <=> query_embedding) > match_threshold
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function to blend semantic and tag-based search
CREATE OR REPLACE FUNCTION search_memories_hybrid(
  query_text TEXT,
  query_embedding vector DEFAULT NULL,
  semantic_weight FLOAT DEFAULT 0.5,
  tag_weight FLOAT DEFAULT 0.3,
  recency_weight FLOAT DEFAULT 0.2,
  match_count INT DEFAULT 20,
  filter_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  project_id UUID,
  label TEXT,
  type memory_type,
  score FLOAT,
  semantic_similarity FLOAT,
  tag_relevance FLOAT,
  recency_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH semantic_scores AS (
    SELECT 
      m.id,
      1 - (m.embedding <=> query_embedding) as similarity
    FROM memories m
    WHERE 
      query_embedding IS NOT NULL 
      AND m.embedding IS NOT NULL
      AND (filter_project_id IS NULL OR m.project_id = filter_project_id)
  ),
  tag_scores AS (
    SELECT 
      m.id,
      COUNT(DISTINCT tag) / GREATEST(array_length(string_to_array(query_text, ' '), 1), 1)::FLOAT as relevance
    FROM memories m, unnest(m.tags) as tag
    WHERE 
      tag = ANY(string_to_array(lower(query_text), ' '))
      AND (filter_project_id IS NULL OR m.project_id = filter_project_id)
    GROUP BY m.id
  ),
  recency_scores AS (
    SELECT 
      m.id,
      CASE 
        WHEN m.updated_at > NOW() - INTERVAL '1 day' THEN 1.0
        WHEN m.updated_at > NOW() - INTERVAL '7 days' THEN 0.8
        WHEN m.updated_at > NOW() - INTERVAL '30 days' THEN 0.5
        ELSE 0.2
      END as recency
    FROM memories m
    WHERE (filter_project_id IS NULL OR m.project_id = filter_project_id)
  )
  SELECT 
    m.id,
    m.project_id,
    m.label,
    m.type,
    COALESCE(ss.similarity * semantic_weight, 0) + 
    COALESCE(ts.relevance * tag_weight, 0) + 
    COALESCE(rs.recency * recency_weight, 0) as score,
    COALESCE(ss.similarity, 0) as semantic_similarity,
    COALESCE(ts.relevance, 0) as tag_relevance,
    COALESCE(rs.recency, 0) as recency_score
  FROM memories m
  LEFT JOIN semantic_scores ss ON m.id = ss.id
  LEFT JOIN tag_scores ts ON m.id = ts.id
  LEFT JOIN recency_scores rs ON m.id = rs.id
  WHERE 
    (filter_project_id IS NULL OR m.project_id = filter_project_id)
    AND (ss.similarity > 0 OR ts.relevance > 0 OR rs.recency > 0)
  ORDER BY score DESC
  LIMIT match_count;
END;
$$;

-- Trigger to mark when embeddings need regeneration
CREATE OR REPLACE FUNCTION mark_embedding_stale()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.content IS DISTINCT FROM OLD.content THEN
    NEW.embedding_generated_at = NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER memories_embedding_stale
BEFORE UPDATE ON memories
FOR EACH ROW
EXECUTE FUNCTION mark_embedding_stale();

-- Table to track embedding generation jobs
CREATE TABLE IF NOT EXISTS embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending',
  error TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT embedding_jobs_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX embedding_jobs_status_idx ON embedding_jobs(status, created_at);