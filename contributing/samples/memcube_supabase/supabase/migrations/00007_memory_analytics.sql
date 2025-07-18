-- Memory Analytics: Track and analyze memory usage patterns

-- Create analytics_metrics table for storing computed metrics
CREATE TABLE IF NOT EXISTS memory_analytics_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  metric_type TEXT NOT NULL,
  metric_value JSONB NOT NULL,
  computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  time_period_start TIMESTAMP WITH TIME ZONE,
  time_period_end TIMESTAMP WITH TIME ZONE,
  
  CONSTRAINT memory_analytics_metrics_type_check CHECK (
    metric_type IN ('usage', 'temporal', 'tag_popularity', 'lifecycle', 'performance')
  )
);

-- Create analytics_aggregates table for project-level analytics
CREATE TABLE IF NOT EXISTS memory_analytics_aggregates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  aggregate_type TEXT NOT NULL,
  aggregate_value JSONB NOT NULL,
  computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  time_period TEXT NOT NULL, -- 'hour', 'day', 'week', 'month'
  period_start TIMESTAMP WITH TIME ZONE NOT NULL,
  period_end TIMESTAMP WITH TIME ZONE NOT NULL,
  
  CONSTRAINT memory_analytics_aggregates_type_check CHECK (
    aggregate_type IN ('usage_summary', 'tag_distribution', 'type_distribution', 
                      'performance_stats', 'lifecycle_summary', 'heat_distribution')
  ),
  CONSTRAINT memory_analytics_aggregates_period_check CHECK (
    time_period IN ('hour', 'day', 'week', 'month')
  ),
  CONSTRAINT memory_analytics_aggregates_unique UNIQUE (
    project_id, aggregate_type, time_period, period_start
  )
);

-- Create analytics_schedules table for managing analytics jobs
CREATE TABLE IF NOT EXISTS memory_analytics_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name TEXT NOT NULL UNIQUE,
  job_type TEXT NOT NULL,
  schedule TEXT NOT NULL, -- cron expression
  last_run TIMESTAMP WITH TIME ZONE,
  next_run TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN DEFAULT true,
  config JSONB DEFAULT '{}',
  
  CONSTRAINT memory_analytics_schedules_type_check CHECK (
    job_type IN ('compute_metrics', 'aggregate_stats', 'cleanup_old', 'optimize_heat')
  )
);

-- Indexes for performance
CREATE INDEX memory_analytics_metrics_memory_idx ON memory_analytics_metrics(memory_id, computed_at DESC);
CREATE INDEX memory_analytics_metrics_project_idx ON memory_analytics_metrics(project_id, metric_type, computed_at DESC);
CREATE INDEX memory_analytics_aggregates_project_idx ON memory_analytics_aggregates(project_id, aggregate_type, period_start DESC);
CREATE INDEX memory_analytics_schedules_next_run_idx ON memory_analytics_schedules(next_run) WHERE is_active = true;

-- Function to compute memory usage metrics
CREATE OR REPLACE FUNCTION compute_memory_usage_metrics(
  p_memory_id UUID,
  p_time_window INTERVAL DEFAULT '30 days'
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  v_metrics JSONB;
BEGIN
  WITH usage_stats AS (
    SELECT 
      COUNT(*) as total_accesses,
      COUNT(DISTINCT project_id) as unique_projects,
      COUNT(DISTINCT COALESCE(agent_id, user_id)) as unique_users,
      COUNT(DISTINCT DATE(created_at)) as active_days,
      MAX(created_at) as last_access,
      MIN(created_at) as first_access,
      AVG(EXTRACT(EPOCH FROM (LEAD(created_at) OVER (ORDER BY created_at) - created_at))) as avg_time_between_accesses
    FROM memory_events
    WHERE 
      memory_id = p_memory_id 
      AND created_at > NOW() - p_time_window
      AND event_type IN ('retrieve', 'search')
  ),
  interaction_breakdown AS (
    SELECT 
      interaction_type,
      COUNT(*) as count
    FROM memory_events
    WHERE 
      memory_id = p_memory_id 
      AND created_at > NOW() - p_time_window
      AND interaction_type IS NOT NULL
    GROUP BY interaction_type
  ),
  quality_stats AS (
    SELECT 
      AVG(quality_score) as avg_quality_score,
      COUNT(*) as quality_ratings
    FROM memory_events
    WHERE 
      memory_id = p_memory_id 
      AND created_at > NOW() - p_time_window
      AND quality_score IS NOT NULL
  )
  SELECT jsonb_build_object(
    'total_accesses', COALESCE(u.total_accesses, 0),
    'unique_projects', COALESCE(u.unique_projects, 0),
    'unique_users', COALESCE(u.unique_users, 0),
    'active_days', COALESCE(u.active_days, 0),
    'last_access', u.last_access,
    'first_access', u.first_access,
    'avg_time_between_accesses_seconds', COALESCE(u.avg_time_between_accesses, 0),
    'interactions', COALESCE(
      (SELECT jsonb_object_agg(interaction_type, count) FROM interaction_breakdown),
      '{}'::jsonb
    ),
    'avg_quality_score', COALESCE(q.avg_quality_score, 0),
    'quality_ratings', COALESCE(q.quality_ratings, 0)
  ) INTO v_metrics
  FROM usage_stats u
  CROSS JOIN quality_stats q;
  
  RETURN v_metrics;
END;
$$;

-- Function to compute temporal patterns
CREATE OR REPLACE FUNCTION compute_temporal_patterns(
  p_memory_id UUID,
  p_time_window INTERVAL DEFAULT '30 days'
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  v_patterns JSONB;
BEGIN
  WITH hourly_pattern AS (
    SELECT 
      EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC') as hour,
      COUNT(*) as access_count
    FROM memory_events
    WHERE 
      memory_id = p_memory_id 
      AND created_at > NOW() - p_time_window
      AND event_type IN ('retrieve', 'search')
    GROUP BY hour
  ),
  daily_pattern AS (
    SELECT 
      EXTRACT(DOW FROM created_at AT TIME ZONE 'UTC') as day_of_week,
      COUNT(*) as access_count
    FROM memory_events
    WHERE 
      memory_id = p_memory_id 
      AND created_at > NOW() - p_time_window
      AND event_type IN ('retrieve', 'search')
    GROUP BY day_of_week
  ),
  trend AS (
    SELECT 
      DATE_TRUNC('day', created_at) as day,
      COUNT(*) as daily_count
    FROM memory_events
    WHERE 
      memory_id = p_memory_id 
      AND created_at > NOW() - p_time_window
      AND event_type IN ('retrieve', 'search')
    GROUP BY day
    ORDER BY day
  )
  SELECT jsonb_build_object(
    'hourly_distribution', COALESCE(
      (SELECT jsonb_object_agg(hour::text, access_count) FROM hourly_pattern),
      '{}'::jsonb
    ),
    'daily_distribution', COALESCE(
      (SELECT jsonb_object_agg(
        CASE day_of_week
          WHEN 0 THEN 'Sunday'
          WHEN 1 THEN 'Monday'
          WHEN 2 THEN 'Tuesday'
          WHEN 3 THEN 'Wednesday'
          WHEN 4 THEN 'Thursday'
          WHEN 5 THEN 'Friday'
          WHEN 6 THEN 'Saturday'
        END,
        access_count
      ) FROM daily_pattern),
      '{}'::jsonb
    ),
    'trend', COALESCE(
      (SELECT jsonb_agg(jsonb_build_object(
        'date', day,
        'count', daily_count
      ) ORDER BY day) FROM trend),
      '[]'::jsonb
    ),
    'peak_hour', (SELECT hour FROM hourly_pattern ORDER BY access_count DESC LIMIT 1),
    'peak_day', (SELECT 
      CASE day_of_week
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
      END
      FROM daily_pattern ORDER BY access_count DESC LIMIT 1
    )
  ) INTO v_patterns;
  
  RETURN v_patterns;
END;
$$;

-- Function to analyze tag popularity
CREATE OR REPLACE FUNCTION analyze_tag_popularity(
  p_project_id UUID DEFAULT NULL,
  p_time_window INTERVAL DEFAULT '30 days'
)
RETURNS TABLE (
  tag TEXT,
  memory_count INTEGER,
  total_accesses BIGINT,
  avg_quality_score FLOAT,
  popularity_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH tag_stats AS (
    SELECT 
      UNNEST(m.tags) as tag,
      m.id as memory_id,
      COUNT(e.id) as access_count,
      AVG(e.quality_score) as quality_score
    FROM memories m
    LEFT JOIN memory_events e ON m.id = e.memory_id 
      AND e.created_at > NOW() - p_time_window
      AND e.event_type IN ('retrieve', 'search')
    WHERE 
      (p_project_id IS NULL OR m.project_id = p_project_id)
      AND m.archived_at IS NULL
    GROUP BY tag, m.id
  )
  SELECT 
    ts.tag,
    COUNT(DISTINCT ts.memory_id)::INTEGER as memory_count,
    SUM(ts.access_count) as total_accesses,
    AVG(ts.quality_score) as avg_quality_score,
    -- Popularity score combines frequency and quality
    (0.6 * LOG(1 + SUM(ts.access_count)) + 
     0.4 * COALESCE(AVG(ts.quality_score), 0.5) * 10) as popularity_score
  FROM tag_stats ts
  GROUP BY ts.tag
  ORDER BY popularity_score DESC;
END;
$$;

-- Function to compute lifecycle metrics
CREATE OR REPLACE FUNCTION compute_lifecycle_metrics(
  p_project_id UUID,
  p_time_window INTERVAL DEFAULT '90 days'
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  v_metrics JSONB;
BEGIN
  WITH memory_lifecycle AS (
    SELECT 
      m.id,
      m.created_at,
      m.archived_at,
      m.heat,
      m.last_accessed,
      EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 86400 as age_days,
      EXTRACT(EPOCH FROM (NOW() - m.last_accessed)) / 86400 as days_since_access,
      COUNT(e.id) as total_accesses
    FROM memories m
    LEFT JOIN memory_events e ON m.id = e.memory_id
      AND e.event_type IN ('retrieve', 'search')
    WHERE 
      m.project_id = p_project_id
      AND m.created_at > NOW() - p_time_window
    GROUP BY m.id
  ),
  lifecycle_stages AS (
    SELECT 
      CASE 
        WHEN archived_at IS NOT NULL THEN 'archived'
        WHEN days_since_access > 30 THEN 'dormant'
        WHEN days_since_access > 7 THEN 'cooling'
        WHEN heat > 80 THEN 'hot'
        WHEN heat > 50 THEN 'warm'
        ELSE 'cold'
      END as stage,
      COUNT(*) as memory_count,
      AVG(total_accesses) as avg_accesses,
      AVG(age_days) as avg_age_days
    FROM memory_lifecycle
    GROUP BY stage
  ),
  retention_curve AS (
    SELECT 
      FLOOR(age_days / 7) as week_number,
      COUNT(*) FILTER (WHERE days_since_access <= 7) as active_memories,
      COUNT(*) as total_memories
    FROM memory_lifecycle
    WHERE age_days <= 84 -- 12 weeks
    GROUP BY week_number
  )
  SELECT jsonb_build_object(
    'lifecycle_distribution', COALESCE(
      (SELECT jsonb_object_agg(stage, jsonb_build_object(
        'count', memory_count,
        'avg_accesses', avg_accesses,
        'avg_age_days', avg_age_days
      )) FROM lifecycle_stages),
      '{}'::jsonb
    ),
    'retention_curve', COALESCE(
      (SELECT jsonb_agg(jsonb_build_object(
        'week', week_number,
        'retention_rate', CASE 
          WHEN total_memories > 0 
          THEN active_memories::FLOAT / total_memories 
          ELSE 0 
        END
      ) ORDER BY week_number) FROM retention_curve),
      '[]'::jsonb
    ),
    'avg_memory_lifespan_days', (
      SELECT AVG(CASE 
        WHEN archived_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (archived_at - created_at)) / 86400
        ELSE age_days
      END) FROM memory_lifecycle
    ),
    'churn_rate', (
      SELECT COUNT(*) FILTER (WHERE archived_at IS NOT NULL)::FLOAT / 
             NULLIF(COUNT(*), 0)
      FROM memory_lifecycle
    )
  ) INTO v_metrics;
  
  RETURN v_metrics;
END;
$$;

-- Function to aggregate project analytics
CREATE OR REPLACE FUNCTION aggregate_project_analytics(
  p_project_id UUID,
  p_period TEXT DEFAULT 'day',
  p_period_start TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
  v_period_start TIMESTAMP WITH TIME ZONE;
  v_period_end TIMESTAMP WITH TIME ZONE;
  v_usage_summary JSONB;
  v_tag_distribution JSONB;
  v_type_distribution JSONB;
  v_performance_stats JSONB;
  v_heat_distribution JSONB;
BEGIN
  -- Calculate period boundaries
  IF p_period_start IS NULL THEN
    v_period_start := DATE_TRUNC(p_period, NOW());
  ELSE
    v_period_start := DATE_TRUNC(p_period, p_period_start);
  END IF;
  
  v_period_end := v_period_start + ('1 ' || p_period)::INTERVAL;
  
  -- Usage summary
  SELECT jsonb_build_object(
    'total_memories', COUNT(DISTINCT m.id),
    'total_accesses', COUNT(e.id),
    'unique_users', COUNT(DISTINCT COALESCE(e.agent_id, e.user_id)),
    'avg_accesses_per_memory', AVG(access_count),
    'most_accessed_memory', (
      SELECT jsonb_build_object('id', memory_id, 'label', label, 'count', access_count)
      FROM (
        SELECT e2.memory_id, m2.label, COUNT(*) as access_count
        FROM memory_events e2
        JOIN memories m2 ON e2.memory_id = m2.id
        WHERE e2.project_id = p_project_id
          AND e2.created_at >= v_period_start
          AND e2.created_at < v_period_end
        GROUP BY e2.memory_id, m2.label
        ORDER BY access_count DESC
        LIMIT 1
      ) top_memory
    )
  ) INTO v_usage_summary
  FROM memories m
  LEFT JOIN LATERAL (
    SELECT COUNT(*) as access_count
    FROM memory_events e
    WHERE e.memory_id = m.id
      AND e.created_at >= v_period_start
      AND e.created_at < v_period_end
  ) e ON true
  WHERE m.project_id = p_project_id;
  
  -- Tag distribution
  WITH tag_counts AS (
    SELECT 
      UNNEST(tags) as tag,
      COUNT(*) as count
    FROM memories
    WHERE project_id = p_project_id
      AND created_at < v_period_end
      AND (archived_at IS NULL OR archived_at >= v_period_start)
    GROUP BY tag
  )
  SELECT jsonb_object_agg(tag, count) INTO v_tag_distribution
  FROM tag_counts
  WHERE tag IS NOT NULL;
  
  -- Type distribution
  SELECT jsonb_object_agg(type, count) INTO v_type_distribution
  FROM (
    SELECT type, COUNT(*) as count
    FROM memories
    WHERE project_id = p_project_id
      AND created_at < v_period_end
      AND (archived_at IS NULL OR archived_at >= v_period_start)
    GROUP BY type
  ) type_counts;
  
  -- Performance stats
  SELECT jsonb_build_object(
    'avg_response_time_ms', AVG(duration_ms),
    'p95_response_time_ms', PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms),
    'avg_quality_score', AVG(quality_score),
    'error_rate', COUNT(*) FILTER (WHERE event_type = 'error')::FLOAT / NULLIF(COUNT(*), 0)
  ) INTO v_performance_stats
  FROM memory_events
  WHERE project_id = p_project_id
    AND created_at >= v_period_start
    AND created_at < v_period_end;
  
  -- Heat distribution
  SELECT jsonb_build_object(
    'hot', COUNT(*) FILTER (WHERE heat > 80),
    'warm', COUNT(*) FILTER (WHERE heat > 50 AND heat <= 80),
    'cool', COUNT(*) FILTER (WHERE heat > 20 AND heat <= 50),
    'cold', COUNT(*) FILTER (WHERE heat <= 20)
  ) INTO v_heat_distribution
  FROM memories
  WHERE project_id = p_project_id
    AND (archived_at IS NULL OR archived_at >= v_period_start);
  
  -- Insert aggregated data
  INSERT INTO memory_analytics_aggregates (
    project_id, aggregate_type, aggregate_value, 
    time_period, period_start, period_end
  ) VALUES 
    (p_project_id, 'usage_summary', v_usage_summary, p_period, v_period_start, v_period_end),
    (p_project_id, 'tag_distribution', COALESCE(v_tag_distribution, '{}'::jsonb), p_period, v_period_start, v_period_end),
    (p_project_id, 'type_distribution', v_type_distribution, p_period, v_period_start, v_period_end),
    (p_project_id, 'performance_stats', v_performance_stats, p_period, v_period_start, v_period_end),
    (p_project_id, 'heat_distribution', v_heat_distribution, p_period, v_period_start, v_period_end)
  ON CONFLICT (project_id, aggregate_type, time_period, period_start) 
  DO UPDATE SET 
    aggregate_value = EXCLUDED.aggregate_value,
    computed_at = NOW();
END;
$$;

-- Function to optimize memory heat based on analytics
CREATE OR REPLACE FUNCTION optimize_memory_heat(
  p_project_id UUID DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_updated_count INTEGER := 0;
  v_memory RECORD;
BEGIN
  FOR v_memory IN
    SELECT 
      m.id,
      m.heat as current_heat,
      COUNT(e.id) as recent_accesses,
      AVG(e.quality_score) as avg_quality,
      MAX(e.created_at) as last_access,
      EXTRACT(EPOCH FROM (NOW() - m.last_accessed)) / 3600 as hours_since_access
    FROM memories m
    LEFT JOIN memory_events e ON m.id = e.memory_id
      AND e.created_at > NOW() - INTERVAL '7 days'
      AND e.event_type IN ('retrieve', 'search')
    WHERE 
      (p_project_id IS NULL OR m.project_id = p_project_id)
      AND m.archived_at IS NULL
    GROUP BY m.id
  LOOP
    DECLARE
      v_new_heat INTEGER;
      v_decay_rate FLOAT;
    BEGIN
      -- Calculate decay rate based on time
      v_decay_rate := CASE
        WHEN v_memory.hours_since_access < 1 THEN 0
        WHEN v_memory.hours_since_access < 24 THEN 0.02
        WHEN v_memory.hours_since_access < 168 THEN 0.05 -- 1 week
        ELSE 0.1
      END;
      
      -- Calculate new heat value
      v_new_heat := GREATEST(0, LEAST(100,
        v_memory.current_heat * (1 - v_decay_rate) +
        v_memory.recent_accesses * 2 +
        COALESCE(v_memory.avg_quality * 10, 0)
      ));
      
      -- Update if significantly different
      IF ABS(v_new_heat - v_memory.current_heat) > 5 THEN
        UPDATE memories 
        SET heat = v_new_heat
        WHERE id = v_memory.id;
        
        v_updated_count := v_updated_count + 1;
      END IF;
    END;
  END LOOP;
  
  RETURN v_updated_count;
END;
$$;

-- Function to get analytics dashboard data
CREATE OR REPLACE FUNCTION get_analytics_dashboard(
  p_project_id UUID,
  p_time_range TEXT DEFAULT '7d' -- 1h, 24h, 7d, 30d, 90d
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  v_time_window INTERVAL;
  v_dashboard JSONB;
BEGIN
  -- Parse time range
  v_time_window := CASE p_time_range
    WHEN '1h' THEN INTERVAL '1 hour'
    WHEN '24h' THEN INTERVAL '24 hours'
    WHEN '7d' THEN INTERVAL '7 days'
    WHEN '30d' THEN INTERVAL '30 days'
    WHEN '90d' THEN INTERVAL '90 days'
    ELSE INTERVAL '7 days'
  END;
  
  -- Build dashboard data
  SELECT jsonb_build_object(
    'summary', jsonb_build_object(
      'total_memories', (
        SELECT COUNT(*) FROM memories 
        WHERE project_id = p_project_id AND archived_at IS NULL
      ),
      'active_memories', (
        SELECT COUNT(DISTINCT memory_id) FROM memory_events
        WHERE project_id = p_project_id 
          AND created_at > NOW() - v_time_window
          AND event_type IN ('retrieve', 'search')
      ),
      'total_accesses', (
        SELECT COUNT(*) FROM memory_events
        WHERE project_id = p_project_id 
          AND created_at > NOW() - v_time_window
          AND event_type IN ('retrieve', 'search')
      ),
      'unique_users', (
        SELECT COUNT(DISTINCT COALESCE(agent_id, user_id)) 
        FROM memory_events
        WHERE project_id = p_project_id 
          AND created_at > NOW() - v_time_window
      )
    ),
    'top_memories', (
      SELECT jsonb_agg(memory_data ORDER BY access_count DESC)
      FROM (
        SELECT 
          m.id,
          m.label,
          m.type,
          m.heat,
          COUNT(e.id) as access_count,
          MAX(e.created_at) as last_accessed
        FROM memories m
        LEFT JOIN memory_events e ON m.id = e.memory_id
          AND e.created_at > NOW() - v_time_window
          AND e.event_type IN ('retrieve', 'search')
        WHERE m.project_id = p_project_id AND m.archived_at IS NULL
        GROUP BY m.id, m.label, m.type, m.heat
        ORDER BY access_count DESC
        LIMIT 10
      ) memory_data
    ),
    'tag_cloud', (
      SELECT jsonb_agg(tag_data ORDER BY popularity_score DESC)
      FROM (
        SELECT * FROM analyze_tag_popularity(p_project_id, v_time_window)
        LIMIT 20
      ) tag_data
    ),
    'usage_trend', (
      SELECT jsonb_agg(trend_data ORDER BY period)
      FROM (
        SELECT 
          DATE_TRUNC(
            CASE 
              WHEN v_time_window <= INTERVAL '1 day' THEN 'hour'
              WHEN v_time_window <= INTERVAL '7 days' THEN 'day'
              ELSE 'week'
            END,
            created_at
          ) as period,
          COUNT(*) as access_count,
          COUNT(DISTINCT memory_id) as unique_memories
        FROM memory_events
        WHERE project_id = p_project_id 
          AND created_at > NOW() - v_time_window
          AND event_type IN ('retrieve', 'search')
        GROUP BY period
      ) trend_data
    ),
    'heat_distribution', (
      SELECT jsonb_build_object(
        'hot', COUNT(*) FILTER (WHERE heat > 80),
        'warm', COUNT(*) FILTER (WHERE heat > 50 AND heat <= 80),
        'cool', COUNT(*) FILTER (WHERE heat > 20 AND heat <= 50),
        'cold', COUNT(*) FILTER (WHERE heat <= 20)
      )
      FROM memories
      WHERE project_id = p_project_id AND archived_at IS NULL
    ),
    'recent_activity', (
      SELECT jsonb_agg(activity ORDER BY created_at DESC)
      FROM (
        SELECT 
          e.id,
          e.event_type,
          e.interaction_type,
          e.created_at,
          m.label as memory_label,
          u.raw_user_meta_data->>'full_name' as user_name
        FROM memory_events e
        JOIN memories m ON e.memory_id = m.id
        LEFT JOIN auth.users u ON e.user_id = u.id
        WHERE e.project_id = p_project_id 
          AND e.created_at > NOW() - INTERVAL '1 hour'
        ORDER BY e.created_at DESC
        LIMIT 20
      ) activity
    )
  ) INTO v_dashboard;
  
  RETURN v_dashboard;
END;
$$;

-- Scheduled job functions
CREATE OR REPLACE FUNCTION run_analytics_jobs()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_job RECORD;
  v_project RECORD;
BEGIN
  -- Get jobs that need to run
  FOR v_job IN
    SELECT * FROM memory_analytics_schedules
    WHERE is_active = true
      AND (next_run IS NULL OR next_run <= NOW())
    ORDER BY last_run ASC NULLS FIRST
  LOOP
    BEGIN
      CASE v_job.job_type
        WHEN 'compute_metrics' THEN
          -- Compute metrics for memories that need updates
          FOR v_project IN
            SELECT DISTINCT m.id as memory_id, m.project_id
            FROM memories m
            JOIN memory_events e ON m.id = e.memory_id
            WHERE e.created_at > COALESCE(v_job.last_run, NOW() - INTERVAL '1 day')
            LIMIT 100
          LOOP
            INSERT INTO memory_analytics_metrics (
              memory_id, project_id, metric_type, metric_value
            ) VALUES 
              (v_project.memory_id, v_project.project_id, 'usage', 
               compute_memory_usage_metrics(v_project.memory_id)),
              (v_project.memory_id, v_project.project_id, 'temporal',
               compute_temporal_patterns(v_project.memory_id));
          END LOOP;
          
        WHEN 'aggregate_stats' THEN
          -- Aggregate stats for active projects
          FOR v_project IN
            SELECT DISTINCT project_id
            FROM memory_events
            WHERE created_at > NOW() - INTERVAL '1 day'
          LOOP
            PERFORM aggregate_project_analytics(v_project.project_id, 'hour');
            PERFORM aggregate_project_analytics(v_project.project_id, 'day');
            
            -- Weekly aggregates on Sundays
            IF EXTRACT(DOW FROM NOW()) = 0 THEN
              PERFORM aggregate_project_analytics(v_project.project_id, 'week');
            END IF;
            
            -- Monthly aggregates on the 1st
            IF EXTRACT(DAY FROM NOW()) = 1 THEN
              PERFORM aggregate_project_analytics(v_project.project_id, 'month');
            END IF;
          END LOOP;
          
        WHEN 'cleanup_old' THEN
          -- Clean up old analytics data
          DELETE FROM memory_analytics_metrics
          WHERE computed_at < NOW() - INTERVAL '90 days';
          
          DELETE FROM memory_analytics_aggregates
          WHERE computed_at < NOW() - INTERVAL '180 days';
          
        WHEN 'optimize_heat' THEN
          -- Optimize heat values
          PERFORM optimize_memory_heat();
      END CASE;
      
      -- Update job status
      UPDATE memory_analytics_schedules
      SET 
        last_run = NOW(),
        next_run = NOW() + (v_job.config->>'interval')::INTERVAL
      WHERE id = v_job.id;
      
    EXCEPTION WHEN OTHERS THEN
      -- Log error (in production, this would go to a proper logging system)
      RAISE NOTICE 'Analytics job % failed: %', v_job.job_name, SQLERRM;
    END;
  END LOOP;
END;
$$;

-- Initialize default analytics schedules
INSERT INTO memory_analytics_schedules (job_name, job_type, schedule, config) VALUES
  ('compute_memory_metrics', 'compute_metrics', '*/15 * * * *', '{"interval": "15 minutes"}'),
  ('aggregate_project_stats', 'aggregate_stats', '0 * * * *', '{"interval": "1 hour"}'),
  ('cleanup_old_analytics', 'cleanup_old', '0 2 * * *', '{"interval": "1 day"}'),
  ('optimize_memory_heat', 'optimize_heat', '*/30 * * * *', '{"interval": "30 minutes"}')
ON CONFLICT (job_name) DO NOTHING;

-- RLS Policies
ALTER TABLE memory_analytics_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_analytics_aggregates ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_analytics_schedules ENABLE ROW LEVEL SECURITY;

-- Analytics metrics follow project access
CREATE POLICY "Users can view analytics for their projects"
  ON memory_analytics_metrics FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can view aggregated analytics"
  ON memory_analytics_aggregates FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
  );

-- Only admins can manage schedules
CREATE POLICY "Only admins can view schedules"
  ON memory_analytics_schedules FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM project_members 
      WHERE user_id = auth.uid() AND role = 'OWNER'
    )
  );