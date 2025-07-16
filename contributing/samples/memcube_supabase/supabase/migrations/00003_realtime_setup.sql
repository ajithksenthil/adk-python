-- Enable Realtime for memory system tables
-- Allows clients to subscribe to changes

-- Enable realtime for memories table
ALTER PUBLICATION supabase_realtime ADD TABLE memories;

-- Enable realtime for memory events (audit trail)
ALTER PUBLICATION supabase_realtime ADD TABLE memory_events;

-- Enable realtime for task links
ALTER PUBLICATION supabase_realtime ADD TABLE memory_task_links;

-- Enable realtime for insights
ALTER PUBLICATION supabase_realtime ADD TABLE insights;

-- Create notification function for memory changes
CREATE OR REPLACE FUNCTION notify_memory_change()
RETURNS TRIGGER AS $$
DECLARE
    payload JSONB;
BEGIN
    payload := jsonb_build_object(
        'operation', TG_OP,
        'memory_id', COALESCE(NEW.id, OLD.id),
        'project_id', COALESCE(NEW.project_id, OLD.project_id),
        'type', COALESCE(NEW.type, OLD.type),
        'priority', COALESCE(NEW.priority, OLD.priority),
        'actor', CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.created_by
            ELSE NEW.created_by
        END,
        'timestamp', now()
    );
    
    PERFORM pg_notify('memory_changes', payload::text);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create triggers for memory change notifications
CREATE TRIGGER notify_memory_insert
    AFTER INSERT ON memories
    FOR EACH ROW EXECUTE FUNCTION notify_memory_change();

CREATE TRIGGER notify_memory_update
    AFTER UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION notify_memory_change();

CREATE TRIGGER notify_memory_delete
    AFTER DELETE ON memories
    FOR EACH ROW EXECUTE FUNCTION notify_memory_change();

-- Create function for task coordination notifications
CREATE OR REPLACE FUNCTION notify_task_memory_link()
RETURNS TRIGGER AS $$
DECLARE
    payload JSONB;
    memory_data JSONB;
BEGIN
    -- Get memory details
    SELECT jsonb_build_object(
        'id', m.id,
        'label', m.label,
        'type', m.type,
        'priority', m.priority
    ) INTO memory_data
    FROM memories m
    WHERE m.id = COALESCE(NEW.memory_id, OLD.memory_id);
    
    payload := jsonb_build_object(
        'operation', TG_OP,
        'task_id', COALESCE(NEW.task_id, OLD.task_id),
        'memory_id', COALESCE(NEW.memory_id, OLD.memory_id),
        'memory', memory_data,
        'role', COALESCE(NEW.role, OLD.role),
        'timestamp', now()
    );
    
    PERFORM pg_notify('task_memory_updates', payload::text);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create triggers for task-memory link notifications
CREATE TRIGGER notify_task_memory_link_change
    AFTER INSERT OR UPDATE OR DELETE ON memory_task_links
    FOR EACH ROW EXECUTE FUNCTION notify_task_memory_link();

-- Create materialized view for memory statistics (refreshed hourly)
CREATE MATERIALIZED VIEW memory_stats AS
SELECT 
    project_id,
    type,
    priority,
    lifecycle,
    COUNT(*) as count,
    AVG(usage_hits) as avg_usage,
    MAX(usage_hits) as max_usage,
    SUM(CASE WHEN last_used > now() - interval '7 days' THEN 1 ELSE 0 END) as active_week,
    SUM(CASE WHEN last_used > now() - interval '30 days' THEN 1 ELSE 0 END) as active_month,
    AVG(EXTRACT(EPOCH FROM (now() - created_at))/86400)::INTEGER as avg_age_days
FROM memories
GROUP BY project_id, type, priority, lifecycle;

CREATE INDEX idx_memory_stats_project ON memory_stats(project_id);

-- Create function to refresh stats
CREATE OR REPLACE FUNCTION refresh_memory_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_stats;
END;
$$ LANGUAGE plpgsql;

-- Create view for hot memories (most frequently accessed)
CREATE OR REPLACE VIEW hot_memories AS
SELECT 
    m.*,
    p.content,
    p.token_count,
    RANK() OVER (PARTITION BY m.project_id ORDER BY m.usage_hits DESC, m.last_used DESC) as hot_rank
FROM memories m
LEFT JOIN memory_payloads p ON m.id = p.memory_id
WHERE m.lifecycle IN ('NEW', 'ACTIVE')
AND m.priority = 'HOT';

-- Create view for memory pack analytics
CREATE OR REPLACE VIEW pack_analytics AS
SELECT 
    mp.*,
    get_pack_rating(mp.id) as rating,
    COUNT(DISTINCT pm.memory_id) as memory_count,
    COALESCE(SUM(m.usage_hits), 0) as total_memory_usage
FROM memory_packs mp
LEFT JOIN pack_memories pm ON mp.id = pm.pack_id
LEFT JOIN memories m ON pm.memory_id = m.id
GROUP BY mp.id;

-- Create function for memory similarity search
CREATE OR REPLACE FUNCTION search_similar_memories(
    query_embedding vector(1536),
    project_id_param TEXT,
    similarity_threshold FLOAT DEFAULT 0.78,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    label TEXT,
    type memory_type,
    priority memory_priority,
    similarity FLOAT,
    content TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.label,
        m.type,
        m.priority,
        1 - (m.embedding <=> query_embedding) as similarity,
        p.content
    FROM memories m
    LEFT JOIN memory_payloads p ON m.id = p.memory_id
    WHERE m.project_id = project_id_param
    AND m.embedding IS NOT NULL
    AND 1 - (m.embedding <=> query_embedding) > similarity_threshold
    AND m.lifecycle NOT IN ('ARCHIVED', 'EXPIRED')
    ORDER BY m.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Create function for memory scheduling (used by Edge Functions)
CREATE OR REPLACE FUNCTION schedule_memories_for_agent(
    agent_id_param TEXT,
    task_id_param TEXT,
    project_id_param TEXT,
    need_tags TEXT[],
    token_budget INTEGER,
    prefer_hot BOOLEAN DEFAULT true
)
RETURNS TABLE (
    memory_id UUID,
    label TEXT,
    type memory_type,
    priority memory_priority,
    content TEXT,
    token_count INTEGER,
    relevance_score FLOAT
) AS $$
DECLARE
    total_tokens INTEGER := 0;
    tag_match_weight FLOAT := 0.4;
    recency_weight FLOAT := 0.2;
    frequency_weight FLOAT := 0.2;
    priority_weight FLOAT := 0.1;
    task_weight FLOAT := 0.1;
BEGIN
    RETURN QUERY
    WITH scored_memories AS (
        SELECT 
            m.id,
            m.label,
            m.type,
            m.priority,
            p.content,
            COALESCE(p.token_count, 100) as token_count,
            -- Calculate relevance score
            (
                -- Tag matching score
                CASE 
                    WHEN need_tags IS NULL OR array_length(need_tags, 1) IS NULL THEN 0.5
                    ELSE (
                        SELECT COUNT(*)::FLOAT / GREATEST(array_length(need_tags, 1), 1)
                        FROM unnest(need_tags) AS tag
                        WHERE LOWER(m.label) LIKE '%' || LOWER(tag) || '%'
                    )
                END * tag_match_weight +
                
                -- Recency score
                CASE 
                    WHEN m.last_used IS NULL THEN 0.1
                    ELSE GREATEST(0, 1 - EXTRACT(EPOCH FROM (now() - m.last_used))/604800)
                END * recency_weight +
                
                -- Frequency score
                LEAST(1.0, m.usage_hits::FLOAT / 50) * frequency_weight +
                
                -- Priority score
                CASE m.priority
                    WHEN 'HOT' THEN 1.0
                    WHEN 'WARM' THEN 0.5
                    ELSE 0.1
                END * priority_weight +
                
                -- Task relevance score
                CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM memory_task_links mtl
                        WHERE mtl.memory_id = m.id AND mtl.task_id = task_id_param
                    ) THEN 1.0
                    ELSE 0.0
                END * task_weight
            ) as relevance_score
        FROM memories m
        LEFT JOIN memory_payloads p ON m.id = p.memory_id
        WHERE m.project_id = project_id_param
        AND m.lifecycle NOT IN ('ARCHIVED', 'EXPIRED')
        AND has_memory_read_access(m.governance)
        AND (NOT prefer_hot OR m.priority IN ('HOT', 'WARM'))
    ),
    selected_memories AS (
        SELECT *,
            SUM(token_count) OVER (ORDER BY relevance_score DESC, priority DESC ROWS UNBOUNDED PRECEDING) as running_total
        FROM scored_memories
    )
    SELECT 
        memory_id,
        label,
        type,
        priority,
        content,
        token_count,
        relevance_score
    FROM selected_memories
    WHERE running_total - token_count < token_budget
    ORDER BY relevance_score DESC;
END;
$$ LANGUAGE plpgsql;

-- Create cron job entries for lifecycle management (requires pg_cron extension)
-- These will be scheduled by Edge Functions instead if pg_cron is not available
CREATE TABLE IF NOT EXISTS cron_jobs (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    schedule TEXT NOT NULL,
    command TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ
);

INSERT INTO cron_jobs (name, schedule, command) VALUES
    ('update_memory_lifecycle', '0 * * * *', 'SELECT update_memory_lifecycle()'),
    ('refresh_memory_stats', '0 * * * *', 'SELECT refresh_memory_stats()'),
    ('cleanup_expired_memories', '0 2 * * *', 'DELETE FROM memories WHERE lifecycle = ''EXPIRED'' AND updated_at < now() - interval ''7 days''')
ON CONFLICT (name) DO NOTHING;