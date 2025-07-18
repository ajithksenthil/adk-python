-- Collaborative Filtering: Recommend memories based on collective usage patterns

-- Extend memory_events table for tracking interactions
ALTER TABLE memory_events 
  ADD COLUMN IF NOT EXISTS agent_id UUID,
  ADD COLUMN IF NOT EXISTS interaction_type TEXT DEFAULT 'view',
  ADD COLUMN IF NOT EXISTS duration_ms INTEGER,
  ADD COLUMN IF NOT EXISTS quality_score FLOAT;

-- Add constraints for interaction types
ALTER TABLE memory_events
  ADD CONSTRAINT memory_events_interaction_type_check 
  CHECK (interaction_type IN ('view', 'use', 'copy', 'modify', 'upvote', 'downvote'));

-- Create table for memory similarity scores
CREATE TABLE IF NOT EXISTS memory_similarities (
  memory_id_1 UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  memory_id_2 UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  similarity_score FLOAT NOT NULL,
  similarity_type TEXT NOT NULL DEFAULT 'usage',
  calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  PRIMARY KEY (memory_id_1, memory_id_2, similarity_type),
  CONSTRAINT memory_similarities_check CHECK (memory_id_1 < memory_id_2),
  CONSTRAINT memory_similarities_score_check CHECK (similarity_score >= 0 AND similarity_score <= 1),
  CONSTRAINT memory_similarities_type_check CHECK (similarity_type IN ('usage', 'content', 'hybrid'))
);

-- Create table for project-level recommendations
CREATE TABLE IF NOT EXISTS memory_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  score FLOAT NOT NULL,
  reason TEXT,
  generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '7 days',
  
  CONSTRAINT memory_recommendations_unique UNIQUE (project_id, memory_id),
  CONSTRAINT memory_recommendations_score_check CHECK (score >= 0 AND score <= 1)
);

-- Create table for explicit feedback
CREATE TABLE IF NOT EXISTS memory_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),
  agent_id UUID,
  feedback_type TEXT NOT NULL,
  feedback_value INTEGER,
  comment TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT memory_feedback_type_check CHECK (feedback_type IN ('rating', 'relevance', 'quality')),
  CONSTRAINT memory_feedback_value_check CHECK (
    (feedback_type = 'rating' AND feedback_value >= 1 AND feedback_value <= 5) OR
    (feedback_type IN ('relevance', 'quality') AND feedback_value IN (-1, 0, 1))
  )
);

-- Indexes for performance
CREATE INDEX memory_events_agent_idx ON memory_events(agent_id, created_at);
CREATE INDEX memory_events_interaction_idx ON memory_events(interaction_type, created_at);
CREATE INDEX memory_similarities_memory1_idx ON memory_similarities(memory_id_1);
CREATE INDEX memory_similarities_memory2_idx ON memory_similarities(memory_id_2);
CREATE INDEX memory_recommendations_project_idx ON memory_recommendations(project_id, score DESC);
CREATE INDEX memory_recommendations_expires_idx ON memory_recommendations(expires_at);
CREATE INDEX memory_feedback_memory_idx ON memory_feedback(memory_id, feedback_type);

-- Function to calculate item-based collaborative filtering similarities
CREATE OR REPLACE FUNCTION calculate_memory_similarities(
  p_similarity_type TEXT DEFAULT 'usage',
  p_min_interactions INTEGER DEFAULT 5,
  p_time_window INTERVAL DEFAULT '30 days'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_count INTEGER := 0;
  v_memory_pair RECORD;
BEGIN
  -- Clear old similarities
  DELETE FROM memory_similarities 
  WHERE similarity_type = p_similarity_type 
    AND calculated_at < NOW() - INTERVAL '1 day';
  
  -- Calculate similarities based on co-usage patterns
  FOR v_memory_pair IN
    WITH memory_usage AS (
      SELECT 
        memory_id,
        project_id,
        COUNT(DISTINCT COALESCE(agent_id, user_id)) as user_count
      FROM memory_events
      WHERE 
        event_type IN ('retrieve', 'search') 
        AND interaction_type IN ('view', 'use', 'copy')
        AND created_at > NOW() - p_time_window
      GROUP BY memory_id, project_id
      HAVING COUNT(*) >= p_min_interactions
    ),
    cooccurrence AS (
      SELECT 
        m1.memory_id as memory_id_1,
        m2.memory_id as memory_id_2,
        COUNT(DISTINCT m1.project_id) as shared_projects,
        COUNT(DISTINCT COALESCE(e1.agent_id, e1.user_id)) as shared_users
      FROM memory_usage m1
      JOIN memory_usage m2 ON m1.project_id = m2.project_id 
        AND m1.memory_id < m2.memory_id
      JOIN memory_events e1 ON e1.memory_id = m1.memory_id 
        AND e1.project_id = m1.project_id
      JOIN memory_events e2 ON e2.memory_id = m2.memory_id 
        AND e2.project_id = m2.project_id
        AND COALESCE(e1.agent_id, e1.user_id) = COALESCE(e2.agent_id, e2.user_id)
      WHERE 
        e1.created_at > NOW() - p_time_window
        AND e2.created_at > NOW() - p_time_window
      GROUP BY m1.memory_id, m2.memory_id
    )
    SELECT 
      memory_id_1,
      memory_id_2,
      -- Jaccard similarity: intersection / union
      shared_users::FLOAT / (
        (SELECT COUNT(DISTINCT COALESCE(agent_id, user_id)) 
         FROM memory_events 
         WHERE memory_id IN (memory_id_1, memory_id_2)
           AND created_at > NOW() - p_time_window)
      ) as similarity
    FROM cooccurrence
    WHERE shared_users > 0
  LOOP
    INSERT INTO memory_similarities (
      memory_id_1, memory_id_2, similarity_score, similarity_type
    ) VALUES (
      v_memory_pair.memory_id_1, 
      v_memory_pair.memory_id_2, 
      v_memory_pair.similarity,
      p_similarity_type
    )
    ON CONFLICT (memory_id_1, memory_id_2, similarity_type) 
    DO UPDATE SET 
      similarity_score = EXCLUDED.similarity_score,
      calculated_at = NOW();
    
    v_count := v_count + 1;
  END LOOP;
  
  RETURN v_count;
END;
$$;

-- Function to generate recommendations for a project
CREATE OR REPLACE FUNCTION generate_project_recommendations(
  p_project_id UUID,
  p_top_k INTEGER DEFAULT 20,
  p_min_score FLOAT DEFAULT 0.3
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_count INTEGER := 0;
  v_recommendation RECORD;
BEGIN
  -- Clear old recommendations
  DELETE FROM memory_recommendations 
  WHERE project_id = p_project_id;
  
  -- Generate recommendations based on project's memory usage
  FOR v_recommendation IN
    WITH project_memories AS (
      -- Get memories used by this project
      SELECT DISTINCT memory_id
      FROM memory_events
      WHERE project_id = p_project_id
        AND event_type IN ('retrieve', 'search')
        AND created_at > NOW() - INTERVAL '30 days'
    ),
    similar_memories AS (
      -- Find similar memories based on collaborative filtering
      SELECT 
        CASE 
          WHEN s.memory_id_1 IN (SELECT memory_id FROM project_memories) 
          THEN s.memory_id_2 
          ELSE s.memory_id_1 
        END as recommended_memory_id,
        AVG(s.similarity_score) as avg_similarity,
        COUNT(*) as connection_count
      FROM memory_similarities s
      WHERE 
        (s.memory_id_1 IN (SELECT memory_id FROM project_memories) OR 
         s.memory_id_2 IN (SELECT memory_id FROM project_memories))
        AND s.similarity_type = 'usage'
      GROUP BY recommended_memory_id
    ),
    memory_quality AS (
      -- Calculate quality scores based on feedback
      SELECT 
        memory_id,
        AVG(CASE 
          WHEN feedback_type = 'rating' THEN feedback_value / 5.0
          WHEN feedback_type IN ('relevance', 'quality') THEN (feedback_value + 1) / 2.0
        END) as quality_score
      FROM memory_feedback
      GROUP BY memory_id
    )
    SELECT 
      sm.recommended_memory_id as memory_id,
      -- Combine similarity and quality scores
      (0.7 * sm.avg_similarity + 0.3 * COALESCE(mq.quality_score, 0.5)) as score,
      CASE 
        WHEN sm.connection_count > 5 THEN 'Frequently used together'
        WHEN sm.avg_similarity > 0.7 THEN 'Highly similar usage pattern'
        ELSE 'Related content'
      END as reason
    FROM similar_memories sm
    LEFT JOIN memory_quality mq ON sm.recommended_memory_id = mq.memory_id
    WHERE 
      -- Don't recommend memories already in the project
      sm.recommended_memory_id NOT IN (
        SELECT id FROM memories WHERE project_id = p_project_id
      )
      -- Don't recommend memories already used recently
      AND sm.recommended_memory_id NOT IN (
        SELECT memory_id FROM project_memories
      )
    ORDER BY score DESC
    LIMIT p_top_k
  LOOP
    IF v_recommendation.score >= p_min_score THEN
      INSERT INTO memory_recommendations (
        project_id, memory_id, score, reason
      ) VALUES (
        p_project_id, 
        v_recommendation.memory_id, 
        v_recommendation.score,
        v_recommendation.reason
      );
      
      v_count := v_count + 1;
    END IF;
  END LOOP;
  
  RETURN v_count;
END;
$$;

-- Function to record interaction and update recommendations
CREATE OR REPLACE FUNCTION record_memory_interaction(
  p_memory_id UUID,
  p_project_id UUID,
  p_interaction_type TEXT,
  p_agent_id UUID DEFAULT NULL,
  p_user_id UUID DEFAULT NULL,
  p_duration_ms INTEGER DEFAULT NULL,
  p_quality_score FLOAT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  v_event_id UUID;
BEGIN
  -- Insert interaction event
  INSERT INTO memory_events (
    event_type, memory_id, project_id, agent_id, user_id,
    interaction_type, duration_ms, quality_score
  ) VALUES (
    'retrieve', p_memory_id, p_project_id, p_agent_id, p_user_id,
    p_interaction_type, p_duration_ms, p_quality_score
  ) RETURNING id INTO v_event_id;
  
  -- Update memory heat for scheduling
  UPDATE memories 
  SET 
    heat = heat + CASE 
      WHEN p_interaction_type = 'use' THEN 2
      WHEN p_interaction_type = 'copy' THEN 3
      WHEN p_interaction_type = 'upvote' THEN 5
      WHEN p_interaction_type = 'downvote' THEN -2
      ELSE 1
    END,
    last_accessed = NOW()
  WHERE id = p_memory_id;
  
  -- Schedule recommendation update if enough interactions
  IF (SELECT COUNT(*) FROM memory_events 
      WHERE project_id = p_project_id 
        AND created_at > NOW() - INTERVAL '1 hour') > 10 THEN
    -- In production, this would trigger an async job
    -- For now, we'll just mark it
    INSERT INTO embedding_jobs (memory_id, status)
    VALUES (p_memory_id, 'pending')
    ON CONFLICT DO NOTHING;
  END IF;
  
  RETURN v_event_id;
END;
$$;

-- Function to get recommendations with explanations
CREATE OR REPLACE FUNCTION get_memory_recommendations(
  p_project_id UUID,
  p_limit INTEGER DEFAULT 10,
  p_include_content BOOLEAN DEFAULT false
)
RETURNS TABLE (
  memory_id UUID,
  label TEXT,
  type memory_type,
  score FLOAT,
  reason TEXT,
  content TEXT,
  tags TEXT[],
  creator_name TEXT,
  usage_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    m.id as memory_id,
    m.label,
    m.type,
    r.score,
    r.reason,
    CASE 
      WHEN p_include_content AND m.storage_mode = 'INLINE' 
      THEN p.content::TEXT
      ELSE NULL
    END as content,
    m.tags,
    u.raw_user_meta_data->>'full_name' as creator_name,
    (SELECT COUNT(*) FROM memory_events WHERE memory_id = m.id) as usage_count
  FROM memory_recommendations r
  JOIN memories m ON r.memory_id = m.id
  LEFT JOIN payloads p ON m.id = p.memory_id
  LEFT JOIN auth.users u ON m.created_by = u.id
  WHERE 
    r.project_id = p_project_id
    AND r.expires_at > NOW()
    AND m.archived_at IS NULL
  ORDER BY r.score DESC
  LIMIT p_limit;
END;
$$;

-- Scheduled job to update similarities (would run daily)
CREATE OR REPLACE FUNCTION update_collaborative_filtering()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_similarity_count INTEGER;
  v_recommendation_count INTEGER;
  v_project RECORD;
BEGIN
  -- Calculate usage-based similarities
  v_similarity_count := calculate_memory_similarities('usage', 5, '30 days');
  
  RAISE NOTICE 'Updated % memory similarities', v_similarity_count;
  
  -- Generate recommendations for active projects
  v_recommendation_count := 0;
  FOR v_project IN
    SELECT DISTINCT p.id
    FROM projects p
    JOIN memory_events e ON p.id = e.project_id
    WHERE e.created_at > NOW() - INTERVAL '7 days'
  LOOP
    v_recommendation_count := v_recommendation_count + 
      generate_project_recommendations(v_project.id, 20, 0.3);
  END LOOP;
  
  RAISE NOTICE 'Generated % recommendations', v_recommendation_count;
END;
$$;

-- RLS Policies
ALTER TABLE memory_similarities ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_feedback ENABLE ROW LEVEL SECURITY;

-- Similarities are read-only for users
CREATE POLICY "Users can view memory similarities"
  ON memory_similarities FOR SELECT
  USING (true);

-- Recommendations follow project access
CREATE POLICY "Users can view recommendations for their projects"
  ON memory_recommendations FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
  );

-- Feedback can be created by project members
CREATE POLICY "Users can provide feedback on memories"
  ON memory_feedback FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT project_id FROM project_members 
      WHERE user_id = auth.uid() AND role IN ('OWNER', 'ADMIN', 'MEMBER')
    )
  );

CREATE POLICY "Users can view feedback"
  ON memory_feedback FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
  );