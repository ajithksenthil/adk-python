-- Orchestrator Kernel Schema
-- Manages task execution, tool calling, and agent coordination

-- Tool registry
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL, -- 'code_execution', 'api_call', 'file_operation', etc.
    
    -- Tool specification
    description TEXT,
    parameters JSONB NOT NULL, -- JSON Schema for parameters
    
    -- Permissions
    required_aml_level aml_level DEFAULT 'AML1',
    requires_approval BOOLEAN DEFAULT false,
    
    -- Rate limiting
    rate_limit_per_minute INTEGER,
    rate_limit_per_hour INTEGER,
    
    -- Cost tracking
    cost_per_use DECIMAL(10,4) DEFAULT 0,
    
    -- Metadata
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tool executions log
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id),
    
    -- Execution context
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id),
    agent_id TEXT NOT NULL,
    
    -- Execution details
    parameters JSONB NOT NULL,
    result JSONB,
    error TEXT,
    
    -- Performance
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Resource usage
    tokens_used INTEGER,
    memory_mb INTEGER,
    
    -- Approval workflow
    requires_approval BOOLEAN DEFAULT false,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    
    -- Lineage
    lineage_id TEXT,
    parent_execution_id UUID REFERENCES tool_executions(id)
);

-- Execution requests queue
CREATE TABLE execution_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Request details
    agent_id TEXT NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    parameters JSONB NOT NULL,
    
    -- Queue management
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    
    -- Scheduling
    scheduled_for TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Result
    result JSONB,
    error TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Agent tool permissions
CREATE TABLE agent_tool_permissions (
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    
    -- Permission details
    granted BOOLEAN DEFAULT true,
    daily_limit INTEGER,
    monthly_limit INTEGER,
    
    -- Usage tracking
    daily_usage INTEGER DEFAULT 0,
    monthly_usage INTEGER DEFAULT 0,
    last_reset_daily TIMESTAMPTZ DEFAULT now(),
    last_reset_monthly TIMESTAMPTZ DEFAULT now(),
    
    PRIMARY KEY (agent_id, tool_id)
);

-- Workflow definitions
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Workflow details
    name TEXT NOT NULL,
    description TEXT,
    
    -- DAG definition
    steps JSONB NOT NULL, -- Array of workflow steps
    
    -- Triggers
    trigger_type TEXT, -- 'manual', 'schedule', 'event'
    trigger_config JSONB,
    
    -- State
    enabled BOOLEAN DEFAULT true,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    
    -- Metadata
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(project_id, name)
);

-- Workflow executions
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    
    -- Execution state
    status TEXT DEFAULT 'running', -- 'running', 'completed', 'failed', 'cancelled'
    current_step INTEGER DEFAULT 0,
    
    -- Step results
    step_results JSONB DEFAULT '[]',
    
    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    
    -- Context
    input_data JSONB,
    output_data JSONB,
    error TEXT,
    
    -- Lineage
    triggered_by TEXT,
    lineage_id TEXT
);

-- Event bus for async communication
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event identification
    type TEXT NOT NULL, -- 'task.created', 'tool.executed', etc.
    source TEXT NOT NULL, -- Source system/agent
    
    -- Event data
    data JSONB NOT NULL,
    
    -- Routing
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    target_agent TEXT, -- Specific agent or null for broadcast
    
    -- Processing
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    processed_by TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ DEFAULT (now() + interval '24 hours'),
    
    -- For ordering
    sequence_number BIGSERIAL
);

-- Agent capabilities registry
CREATE TABLE agent_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Capability details
    capability TEXT NOT NULL, -- 'code_review', 'ui_design', etc.
    proficiency_level INTEGER DEFAULT 1, -- 1-10 scale
    
    -- Examples and evidence
    examples JSONB DEFAULT '[]',
    
    -- Metadata
    verified BOOLEAN DEFAULT false,
    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    
    UNIQUE(agent_id, capability)
);

-- Task templates
CREATE TABLE task_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Template details
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    
    -- Template definition
    default_title TEXT,
    default_description TEXT,
    required_capabilities TEXT[],
    estimated_hours DECIMAL(5,2),
    
    -- Auto-assignment rules
    assignment_strategy TEXT, -- 'round_robin', 'least_busy', 'best_match'
    preferred_agents TEXT[],
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Performance tracking
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Context
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_id TEXT,
    task_id UUID REFERENCES tasks(id),
    
    -- Metric details
    metric_name TEXT NOT NULL,
    metric_value DECIMAL(20,6) NOT NULL,
    unit TEXT,
    
    -- Time window
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Aggregation
    aggregation_type TEXT DEFAULT 'sum', -- 'sum', 'avg', 'max', 'min'
    sample_count INTEGER DEFAULT 1,
    
    -- Metadata
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes
CREATE INDEX idx_tool_executions_project ON tool_executions(project_id);
CREATE INDEX idx_tool_executions_agent ON tool_executions(agent_id);
CREATE INDEX idx_tool_executions_lineage ON tool_executions(lineage_id) WHERE lineage_id IS NOT NULL;

CREATE INDEX idx_execution_requests_status ON execution_requests(status, priority DESC);
CREATE INDEX idx_execution_requests_agent ON execution_requests(agent_id);

CREATE INDEX idx_events_unprocessed ON events(project_id, processed) WHERE processed = false;
CREATE INDEX idx_events_sequence ON events(sequence_number);
CREATE INDEX idx_events_expires ON events(expires_at);

CREATE INDEX idx_workflow_executions_status ON workflow_executions(workflow_id, status);

CREATE INDEX idx_performance_metrics_lookup ON performance_metrics(project_id, agent_id, metric_name, period_start);

-- Functions for orchestration

-- Get next task for agent
CREATE OR REPLACE FUNCTION get_next_task_for_agent(
    p_agent_id TEXT
) RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
    v_agent_capabilities TEXT[];
BEGIN
    -- Get agent capabilities
    SELECT capabilities INTO v_agent_capabilities
    FROM agents
    WHERE agent_id = p_agent_id;
    
    -- Find suitable task
    SELECT t.id INTO v_task_id
    FROM tasks t
    JOIN projects p ON t.project_id = p.id
    LEFT JOIN agents a ON a.current_task_id = t.id
    WHERE t.status = 'PENDING'
    AND t.assigned_to IS NULL
    AND NOT p.archived
    AND (
        -- Task has no dependencies
        t.depends_on IS NULL 
        OR t.depends_on = '{}'
        OR NOT EXISTS (
            -- Or all dependencies are completed
            SELECT 1 FROM unnest(t.depends_on) AS dep_id
            WHERE EXISTS (
                SELECT 1 FROM tasks 
                WHERE task_id = dep_id 
                AND project_id = t.project_id
                AND status != 'COMPLETED'
            )
        )
    )
    ORDER BY t.priority DESC, t.created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;
    
    -- Assign task if found
    IF v_task_id IS NOT NULL THEN
        UPDATE tasks
        SET assigned_to = p_agent_id,
            assigned_at = now(),
            status = 'IN_PROGRESS'
        WHERE id = v_task_id;
        
        UPDATE agents
        SET current_task_id = v_task_id,
            status = 'BUSY'
        WHERE agent_id = p_agent_id;
    END IF;
    
    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql;

-- Check tool permission
CREATE OR REPLACE FUNCTION check_tool_permission(
    p_agent_id TEXT,
    p_tool_name TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_tool_id UUID;
    v_agent_aml aml_level;
    v_tool_aml aml_level;
    v_has_permission BOOLEAN;
    v_daily_usage INTEGER;
    v_daily_limit INTEGER;
BEGIN
    -- Get tool and agent info
    SELECT id, required_aml_level INTO v_tool_id, v_tool_aml
    FROM tools
    WHERE name = p_tool_name AND enabled = true;
    
    IF v_tool_id IS NULL THEN
        RETURN false;
    END IF;
    
    SELECT aml_level INTO v_agent_aml
    FROM agents
    WHERE agent_id = p_agent_id;
    
    -- Check AML level
    IF v_agent_aml < v_tool_aml THEN
        RETURN false;
    END IF;
    
    -- Check specific permissions
    SELECT granted, daily_usage, daily_limit 
    INTO v_has_permission, v_daily_usage, v_daily_limit
    FROM agent_tool_permissions
    WHERE agent_id = p_agent_id AND tool_id = v_tool_id;
    
    IF v_has_permission IS NULL THEN
        -- No specific permission set, allow by default
        RETURN true;
    END IF;
    
    IF NOT v_has_permission THEN
        RETURN false;
    END IF;
    
    -- Check daily limit
    IF v_daily_limit IS NOT NULL AND v_daily_usage >= v_daily_limit THEN
        RETURN false;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Record tool usage
CREATE OR REPLACE FUNCTION record_tool_usage(
    p_agent_id TEXT,
    p_tool_id UUID
) RETURNS void AS $$
BEGIN
    -- Update or insert permission record with usage
    INSERT INTO agent_tool_permissions (agent_id, tool_id, daily_usage, monthly_usage)
    VALUES (p_agent_id, p_tool_id, 1, 1)
    ON CONFLICT (agent_id, tool_id) DO UPDATE
    SET daily_usage = CASE 
            WHEN agent_tool_permissions.last_reset_daily::date < CURRENT_DATE 
            THEN 1 
            ELSE agent_tool_permissions.daily_usage + 1 
        END,
        monthly_usage = CASE 
            WHEN agent_tool_permissions.last_reset_monthly::date < date_trunc('month', CURRENT_DATE)
            THEN 1 
            ELSE agent_tool_permissions.monthly_usage + 1 
        END,
        last_reset_daily = CASE 
            WHEN agent_tool_permissions.last_reset_daily::date < CURRENT_DATE 
            THEN CURRENT_DATE 
            ELSE agent_tool_permissions.last_reset_daily 
        END,
        last_reset_monthly = CASE 
            WHEN agent_tool_permissions.last_reset_monthly::date < date_trunc('month', CURRENT_DATE)
            THEN date_trunc('month', CURRENT_DATE)
            ELSE agent_tool_permissions.last_reset_monthly 
        END;
END;
$$ LANGUAGE plpgsql;

-- Workflow step executor
CREATE OR REPLACE FUNCTION execute_workflow_step(
    p_execution_id UUID,
    p_step_index INTEGER
) RETURNS JSONB AS $$
DECLARE
    v_workflow_id UUID;
    v_steps JSONB;
    v_step JSONB;
    v_result JSONB;
BEGIN
    -- Get workflow info
    SELECT w.id, w.steps INTO v_workflow_id, v_steps
    FROM workflow_executions we
    JOIN workflows w ON we.workflow_id = w.id
    WHERE we.id = p_execution_id;
    
    -- Get specific step
    v_step := v_steps->p_step_index;
    
    IF v_step IS NULL THEN
        RETURN jsonb_build_object('error', 'Step not found');
    END IF;
    
    -- Execute based on step type
    CASE v_step->>'type'
        WHEN 'tool' THEN
            -- Queue tool execution
            INSERT INTO execution_requests (
                agent_id, 
                project_id,
                tool_name, 
                parameters,
                priority
            )
            SELECT 
                v_step->>'agent_id',
                w.project_id,
                v_step->>'tool_name',
                v_step->'parameters',
                100 -- High priority for workflow steps
            FROM workflows w
            WHERE w.id = v_workflow_id;
            
            v_result := jsonb_build_object('status', 'queued');
            
        WHEN 'condition' THEN
            -- Evaluate condition
            -- Simplified - in production would need proper evaluation
            v_result := jsonb_build_object(
                'status', 'completed',
                'next_step', CASE 
                    WHEN random() > 0.5 
                    THEN v_step->'true_branch'
                    ELSE v_step->'false_branch'
                END
            );
            
        ELSE
            v_result := jsonb_build_object('error', 'Unknown step type');
    END CASE;
    
    -- Update execution
    UPDATE workflow_executions
    SET step_results = step_results || jsonb_build_array(v_result),
        current_step = p_step_index + 1
    WHERE id = p_execution_id;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Default tools
INSERT INTO tools (name, type, description, parameters, required_aml_level) VALUES
('bash', 'code_execution', 'Execute bash commands', 
 '{"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}',
 'AML2'),
('python', 'code_execution', 'Execute Python code',
 '{"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}',
 'AML2'),
('http_request', 'api_call', 'Make HTTP requests',
 '{"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}}}',
 'AML1'),
('read_file', 'file_operation', 'Read file contents',
 '{"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}',
 'AML1'),
('write_file', 'file_operation', 'Write file contents',
 '{"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}',
 'AML2');

-- Comments
COMMENT ON TABLE tools IS 'Registry of available tools for agents';
COMMENT ON TABLE tool_executions IS 'Log of all tool executions with results';
COMMENT ON TABLE execution_requests IS 'Queue for pending tool executions';
COMMENT ON TABLE workflows IS 'Multi-step workflow definitions';
COMMENT ON TABLE events IS 'Event bus for async agent communication';