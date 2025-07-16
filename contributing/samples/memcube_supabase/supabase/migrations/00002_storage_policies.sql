-- Row Level Security (RLS) Policies for MemCube
-- Implements project-based access control with governance rules

-- Enable RLS on all tables
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_payloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_task_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pack_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

-- Create helper functions for auth
CREATE OR REPLACE FUNCTION auth.user_project_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('request.jwt.claims', true)::json->>'project_id';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('request.jwt.claims', true)::json->>'role';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION auth.user_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('request.jwt.claims', true)::json->>'sub';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if user has required role for memory governance
CREATE OR REPLACE FUNCTION has_memory_read_access(memory_governance JSONB)
RETURNS BOOLEAN AS $$
DECLARE
    required_roles TEXT[];
    user_role TEXT;
BEGIN
    required_roles := ARRAY(SELECT jsonb_array_elements_text(memory_governance->'read_roles'));
    user_role := auth.user_role();
    
    RETURN user_role = ANY(required_roles) OR user_role = 'ADMIN';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION has_memory_write_access(memory_governance JSONB)
RETURNS BOOLEAN AS $$
DECLARE
    required_roles TEXT[];
    user_role TEXT;
BEGIN
    required_roles := ARRAY(SELECT jsonb_array_elements_text(memory_governance->'write_roles'));
    user_role := auth.user_role();
    
    RETURN user_role = ANY(required_roles) OR user_role = 'ADMIN';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Memories table policies
CREATE POLICY "Users can view memories in their project with read access"
    ON memories FOR SELECT
    USING (
        project_id = auth.user_project_id() 
        AND has_memory_read_access(governance)
    );

CREATE POLICY "Users can create memories in their project"
    ON memories FOR INSERT
    WITH CHECK (
        project_id = auth.user_project_id()
        AND created_by = auth.user_id()
    );

CREATE POLICY "Users can update memories with write access"
    ON memories FOR UPDATE
    USING (
        project_id = auth.user_project_id()
        AND has_memory_write_access(governance)
    );

CREATE POLICY "Users can delete memories they created or with admin role"
    ON memories FOR DELETE
    USING (
        project_id = auth.user_project_id()
        AND (created_by = auth.user_id() OR auth.user_role() = 'ADMIN')
    );

-- Memory payloads policies (inherit from memories table)
CREATE POLICY "Users can view payloads for accessible memories"
    ON memory_payloads FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_payloads.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_read_access(m.governance)
        )
    );

CREATE POLICY "Users can create payloads for their memories"
    ON memory_payloads FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_payloads.memory_id
            AND m.project_id = auth.user_project_id()
            AND m.created_by = auth.user_id()
        )
    );

CREATE POLICY "Users can update payloads with write access"
    ON memory_payloads FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_payloads.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_write_access(m.governance)
        )
    );

-- Memory versions policies
CREATE POLICY "Users can view versions of accessible memories"
    ON memory_versions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_versions.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_read_access(m.governance)
        )
    );

CREATE POLICY "Users can create versions with write access"
    ON memory_versions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_versions.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_write_access(m.governance)
        )
        AND created_by = auth.user_id()
    );

-- Memory events policies (audit trail is append-only)
CREATE POLICY "Users can view events for accessible memories"
    ON memory_events FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_events.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_read_access(m.governance)
        )
    );

CREATE POLICY "Users can create events for accessible memories"
    ON memory_events FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_events.memory_id
            AND m.project_id = auth.user_project_id()
        )
        AND actor = auth.user_id()
    );

-- Task links policies
CREATE POLICY "Users can view task links in their project"
    ON memory_task_links FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_task_links.memory_id
            AND m.project_id = auth.user_project_id()
        )
    );

CREATE POLICY "Users can create task links with write access"
    ON memory_task_links FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_task_links.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_write_access(m.governance)
        )
    );

CREATE POLICY "Users can delete task links with write access"
    ON memory_task_links FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM memories m
            WHERE m.id = memory_task_links.memory_id
            AND m.project_id = auth.user_project_id()
            AND has_memory_write_access(m.governance)
        )
    );

-- Memory packs policies (marketplace)
CREATE POLICY "Anyone can view published packs"
    ON memory_packs FOR SELECT
    USING (published = true OR author_id = auth.user_id());

CREATE POLICY "Users can create their own packs"
    ON memory_packs FOR INSERT
    WITH CHECK (author_id = auth.user_id());

CREATE POLICY "Users can update their own packs"
    ON memory_packs FOR UPDATE
    USING (author_id = auth.user_id());

CREATE POLICY "Users can delete their own unpublished packs"
    ON memory_packs FOR DELETE
    USING (author_id = auth.user_id() AND published = false);

-- Pack memories policies
CREATE POLICY "Users can view memories in accessible packs"
    ON pack_memories FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM memory_packs p
            WHERE p.id = pack_memories.pack_id
            AND (p.published = true OR p.author_id = auth.user_id())
        )
    );

CREATE POLICY "Pack authors can manage pack memories"
    ON pack_memories FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM memory_packs p
            WHERE p.id = pack_memories.pack_id
            AND p.author_id = auth.user_id()
        )
    );

-- Insights policies
CREATE POLICY "Users can view insights in their project"
    ON insights FOR SELECT
    USING (project_id = auth.user_project_id());

CREATE POLICY "Users can create insights in their project"
    ON insights FOR INSERT
    WITH CHECK (
        project_id = auth.user_project_id()
        AND created_by = auth.user_id()
    );

CREATE POLICY "Users can update their own insights"
    ON insights FOR UPDATE
    USING (
        project_id = auth.user_project_id()
        AND created_by = auth.user_id()
    );

-- Create storage bucket for large payloads
INSERT INTO storage.buckets (id, name, public)
VALUES ('memory-payloads', 'memory-payloads', false);

-- Storage policies for memory payloads bucket
CREATE POLICY "Users can upload memory payloads"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'memory-payloads'
        AND auth.role() = 'authenticated'
    );

CREATE POLICY "Users can view their memory payloads"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'memory-payloads'
        AND auth.role() = 'authenticated'
    );

CREATE POLICY "Users can delete their memory payloads"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'memory-payloads'
        AND auth.role() = 'authenticated'
        AND owner = auth.uid()
    );

-- Create indexes for RLS performance
CREATE INDEX idx_memories_project_governance ON memories(project_id, governance);
CREATE INDEX idx_memories_created_by ON memories(created_by);

-- Grant necessary permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;