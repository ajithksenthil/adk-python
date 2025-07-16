-- FSA (Finite State Automaton) State Memory Schema
-- Provides live state coordination for multi-agent systems

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Custom types for FSA
CREATE TYPE agent_status AS ENUM ('ONLINE', 'BUSY', 'OFFLINE', 'ERROR');
CREATE TYPE task_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'BLOCKED');
CREATE TYPE aml_level AS ENUM ('AML0', 'AML1', 'AML2', 'AML3', 'AML4');

-- Projects table (top-level container)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    tenant_id TEXT NOT NULL,
    
    -- Budget and resources
    budget_total DECIMAL(10,2) DEFAULT 0,
    budget_spent DECIMAL(10,2) DEFAULT 0,
    
    -- Metadata
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived BOOLEAN DEFAULT false,
    
    CONSTRAINT project_name_check CHECK (length(name) > 0)
);

-- FSA states table (versioned state storage)
CREATE TABLE fsa_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    fsa_id TEXT NOT NULL, -- Logical FSA identifier
    
    -- State versioning
    version INTEGER NOT NULL DEFAULT 1,
    parent_version INTEGER, -- For branching/merging
    
    -- State content (JSONB for flexibility)
    state JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    actor TEXT NOT NULL,
    lineage_id TEXT, -- Trace ID for causality
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    UNIQUE(project_id, fsa_id, version),
    CONSTRAINT version_check CHECK (version > 0)
);

-- FSA state deltas (incremental updates)
CREATE TABLE fsa_deltas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_id UUID NOT NULL REFERENCES fsa_states(id) ON DELETE CASCADE,
    
    -- Delta content
    operations JSONB NOT NULL, -- Array of operations
    
    -- Metadata
    actor TEXT NOT NULL,
    lineage_id TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- For conflict resolution
    conflict_resolved BOOLEAN DEFAULT false,
    resolution_strategy TEXT
);

-- State slices cache (for efficient queries)
CREATE TABLE fsa_slice_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_id UUID NOT NULL REFERENCES fsa_states(id) ON DELETE CASCADE,
    
    -- Slice specification
    pattern TEXT NOT NULL, -- e.g., "task:DESIGN_*"
    k_limit INTEGER, -- Top K results
    
    -- Cached data
    slice_data JSONB NOT NULL,
    summary TEXT,
    token_count INTEGER,
    
    -- Cache metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    access_count INTEGER DEFAULT 1,
    
    -- TTL
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '5 minutes'),
    
    UNIQUE(state_id, pattern, k_limit)
);

-- Tasks table (core work units)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL, -- Human-readable ID like "DESIGN_001"
    
    -- Task details
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status task_status NOT NULL DEFAULT 'PENDING',
    priority INTEGER DEFAULT 0, -- Higher = more important
    
    -- Assignment
    assigned_to TEXT, -- Agent ID
    assigned_at TIMESTAMPTZ,
    
    -- Dependencies
    depends_on TEXT[], -- Array of task_ids
    blocks TEXT[], -- Tasks this blocks
    
    -- Timing
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Metadata
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Comments/discussion thread
    comments JSONB DEFAULT '[]',
    
    UNIQUE(project_id, task_id),
    CONSTRAINT task_id_format CHECK (task_id ~ '^[A-Z]+_[0-9]+$')
);

-- Agents table (AI workers)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- e.g., 'designer', 'developer', 'qa'
    
    -- Capabilities and constraints
    capabilities TEXT[] DEFAULT '{}',
    aml_level aml_level DEFAULT 'AML1',
    max_tokens_per_task INTEGER DEFAULT 100000,
    
    -- Status tracking
    status agent_status DEFAULT 'OFFLINE',
    last_heartbeat TIMESTAMPTZ,
    current_task_id UUID REFERENCES tasks(id),
    
    -- Performance metrics
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_completion_time_hours DECIMAL(5,2),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent sessions (online tracking)
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Session info
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    
    -- Activity metrics
    tasks_worked INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0
);

-- Resource tracking
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Resource details
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'compute', 'storage', 'api_calls', etc.
    unit TEXT NOT NULL, -- 'hours', 'GB', 'requests'
    
    -- Quotas and usage
    quota_amount DECIMAL(10,2),
    used_amount DECIMAL(10,2) DEFAULT 0,
    cost_per_unit DECIMAL(10,4),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(project_id, name)
);

-- Metrics tracking
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Metric identification
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'counter', 'gauge', 'histogram'
    
    -- Value storage
    value DECIMAL(20,6) NOT NULL,
    labels JSONB DEFAULT '{}', -- Additional dimensions
    
    -- Timing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Indexing for time-series queries
    CONSTRAINT metrics_name_check CHECK (length(name) > 0)
);

-- Policy rules (governance)
CREATE TABLE policy_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Rule specification
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'budget', 'resource', 'aml', 'custom'
    
    -- Rule definition
    condition JSONB NOT NULL, -- Rule condition in JSON
    action JSONB NOT NULL, -- What to do when triggered
    
    -- State
    enabled BOOLEAN DEFAULT true,
    last_triggered TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(project_id, name)
);

-- Create indexes for performance
CREATE INDEX idx_fsa_states_project_fsa ON fsa_states(project_id, fsa_id);
CREATE INDEX idx_fsa_states_version ON fsa_states(project_id, fsa_id, version DESC);
CREATE INDEX idx_fsa_states_lineage ON fsa_states(lineage_id) WHERE lineage_id IS NOT NULL;

CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_tasks_dependencies ON tasks USING gin(depends_on);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agent_sessions_active ON agent_sessions(agent_id, project_id) 
    WHERE ended_at IS NULL;

CREATE INDEX idx_metrics_project_name ON metrics(project_id, name);
CREATE INDEX idx_metrics_timestamp ON metrics(project_id, timestamp DESC);

CREATE INDEX idx_slice_cache_pattern ON fsa_slice_cache(state_id, pattern);
CREATE INDEX idx_slice_cache_expires ON fsa_slice_cache(expires_at);

-- Functions for FSA operations

-- Get latest state version
CREATE OR REPLACE FUNCTION get_latest_state_version(
    p_project_id UUID,
    p_fsa_id TEXT
) RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(
        (SELECT MAX(version) 
         FROM fsa_states 
         WHERE project_id = p_project_id 
         AND fsa_id = p_fsa_id),
        0
    );
END;
$$ LANGUAGE plpgsql;

-- Apply delta operations to state
CREATE OR REPLACE FUNCTION apply_delta_operations(
    current_state JSONB,
    operations JSONB
) RETURNS JSONB AS $$
DECLARE
    op JSONB;
    path TEXT[];
    value JSONB;
    result JSONB := current_state;
BEGIN
    -- Process each operation
    FOR op IN SELECT * FROM jsonb_array_elements(operations)
    LOOP
        path := ARRAY(SELECT jsonb_array_elements_text(op->'path'));
        value := op->'value';
        
        CASE op->>'op'
            WHEN 'set' THEN
                result := jsonb_set(result, path, value, true);
            WHEN 'inc' THEN
                -- Increment numeric value
                result := jsonb_set(
                    result, 
                    path, 
                    to_jsonb((result #>> path)::numeric + (value)::numeric)
                );
            WHEN 'push' THEN
                -- Append to array
                result := jsonb_set(
                    result,
                    path,
                    COALESCE(result #> path, '[]'::jsonb) || value
                );
            WHEN 'unset' THEN
                -- Remove field
                result := result #- path;
        END CASE;
    END LOOP;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Extract state slice by pattern
CREATE OR REPLACE FUNCTION extract_state_slice(
    state JSONB,
    pattern TEXT,
    k_limit INTEGER DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    result JSONB := '{}';
    key TEXT;
    value JSONB;
    count INTEGER := 0;
    regex TEXT;
BEGIN
    -- Convert pattern to regex (e.g., "task:DESIGN_*" -> "^task:DESIGN_.*")
    regex := '^' || replace(replace(pattern, '*', '.*'), ':', '\:');
    
    -- Extract matching keys
    FOR key, value IN SELECT * FROM jsonb_each(state)
    LOOP
        IF key ~ regex THEN
            result := jsonb_set(result, ARRAY[key], value);
            count := count + 1;
            
            IF k_limit IS NOT NULL AND count >= k_limit THEN
                EXIT;
            END IF;
        END IF;
    END LOOP;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Generate slice summary
CREATE OR REPLACE FUNCTION generate_slice_summary(
    slice_data JSONB,
    pattern TEXT
) RETURNS TEXT AS $$
DECLARE
    summary TEXT;
    item_count INTEGER;
    sample_keys TEXT[];
BEGIN
    item_count := jsonb_object_keys(slice_data)::INTEGER;
    
    -- Get sample keys
    SELECT ARRAY_AGG(key) INTO sample_keys
    FROM (
        SELECT jsonb_object_keys(slice_data) AS key
        LIMIT 3
    ) t;
    
    -- Generate summary based on pattern
    IF pattern LIKE 'task:%' THEN
        summary := format('%s tasks found: %s', 
            item_count, 
            array_to_string(sample_keys, ', ')
        );
    ELSIF pattern LIKE 'agent:%' THEN
        summary := format('%s agents online', item_count);
    ELSIF pattern LIKE 'metric:%' THEN
        summary := format('%s metrics tracked', item_count);
    ELSE
        summary := format('%s items matching pattern "%s"', 
            item_count, 
            pattern
        );
    END IF;
    
    RETURN summary;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE fsa_states IS 'Versioned state storage for FSA coordination';
COMMENT ON TABLE fsa_deltas IS 'Incremental state updates using CRDT operations';
COMMENT ON TABLE fsa_slice_cache IS 'Cached state slices for efficient queries';
COMMENT ON TABLE tasks IS 'Work units distributed among agents';
COMMENT ON TABLE agents IS 'AI agents that execute tasks';
COMMENT ON COLUMN fsa_states.lineage_id IS 'Trace ID for causality tracking';