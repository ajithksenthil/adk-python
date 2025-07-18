-- Memory Chains: Enable linking multiple memories into ordered sequences

-- Create memory_chains table
CREATE TABLE IF NOT EXISTS memory_chains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  
  -- Chain configuration
  max_length INTEGER DEFAULT 100,
  auto_summarize BOOLEAN DEFAULT true,
  summary_threshold INTEGER DEFAULT 10000, -- tokens
  
  CONSTRAINT memory_chains_title_length CHECK (char_length(title) <= 255)
);

-- Create memory_chain_links table for ordered memory sequences
CREATE TABLE IF NOT EXISTS memory_chain_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chain_id UUID NOT NULL REFERENCES memory_chains(id) ON DELETE CASCADE,
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  order_index INTEGER NOT NULL,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  added_by UUID REFERENCES auth.users(id),
  
  -- Optional narrative context
  transition_text TEXT,
  
  CONSTRAINT memory_chain_links_unique UNIQUE (chain_id, memory_id),
  CONSTRAINT memory_chain_links_order_unique UNIQUE (chain_id, order_index),
  CONSTRAINT memory_chain_links_order_positive CHECK (order_index >= 0)
);

-- Create chain summaries table
CREATE TABLE IF NOT EXISTS memory_chain_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chain_id UUID NOT NULL REFERENCES memory_chains(id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  token_count INTEGER,
  generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  model_used TEXT,
  
  CONSTRAINT memory_chain_summaries_chain_unique UNIQUE (chain_id)
);

-- Indexes for performance
CREATE INDEX memory_chains_project_idx ON memory_chains(project_id);
CREATE INDEX memory_chain_links_chain_idx ON memory_chain_links(chain_id, order_index);
CREATE INDEX memory_chain_links_memory_idx ON memory_chain_links(memory_id);

-- Function to add memory to chain
CREATE OR REPLACE FUNCTION add_memory_to_chain(
  p_chain_id UUID,
  p_memory_id UUID,
  p_position INTEGER DEFAULT NULL,
  p_transition_text TEXT DEFAULT NULL,
  p_user_id UUID DEFAULT NULL
)
RETURNS memory_chain_links
LANGUAGE plpgsql
AS $$
DECLARE
  v_max_index INTEGER;
  v_new_link memory_chain_links;
  v_chain memory_chains;
BEGIN
  -- Get chain info
  SELECT * INTO v_chain FROM memory_chains WHERE id = p_chain_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Chain not found';
  END IF;
  
  -- Check if memory is already in chain
  IF EXISTS (SELECT 1 FROM memory_chain_links WHERE chain_id = p_chain_id AND memory_id = p_memory_id) THEN
    RAISE EXCEPTION 'Memory already exists in chain';
  END IF;
  
  -- Get current max index
  SELECT COALESCE(MAX(order_index), -1) INTO v_max_index 
  FROM memory_chain_links 
  WHERE chain_id = p_chain_id;
  
  -- Check chain length limit
  IF v_max_index + 1 >= v_chain.max_length THEN
    RAISE EXCEPTION 'Chain has reached maximum length of % memories', v_chain.max_length;
  END IF;
  
  -- If position not specified, append to end
  IF p_position IS NULL THEN
    p_position := v_max_index + 1;
  END IF;
  
  -- Shift existing links if inserting in middle
  IF p_position <= v_max_index THEN
    UPDATE memory_chain_links
    SET order_index = order_index + 1
    WHERE chain_id = p_chain_id AND order_index >= p_position;
  END IF;
  
  -- Insert new link
  INSERT INTO memory_chain_links (
    chain_id, memory_id, order_index, transition_text, added_by
  ) VALUES (
    p_chain_id, p_memory_id, p_position, p_transition_text, p_user_id
  ) RETURNING * INTO v_new_link;
  
  -- Update chain timestamp
  UPDATE memory_chains SET updated_at = NOW() WHERE id = p_chain_id;
  
  -- Invalidate summary if exists
  DELETE FROM memory_chain_summaries WHERE chain_id = p_chain_id;
  
  RETURN v_new_link;
END;
$$;

-- Function to remove memory from chain
CREATE OR REPLACE FUNCTION remove_memory_from_chain(
  p_chain_id UUID,
  p_memory_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
  v_order_index INTEGER;
BEGIN
  -- Get the order index of the memory to remove
  SELECT order_index INTO v_order_index
  FROM memory_chain_links
  WHERE chain_id = p_chain_id AND memory_id = p_memory_id;
  
  IF NOT FOUND THEN
    RETURN FALSE;
  END IF;
  
  -- Delete the link
  DELETE FROM memory_chain_links
  WHERE chain_id = p_chain_id AND memory_id = p_memory_id;
  
  -- Shift remaining links
  UPDATE memory_chain_links
  SET order_index = order_index - 1
  WHERE chain_id = p_chain_id AND order_index > v_order_index;
  
  -- Update chain timestamp
  UPDATE memory_chains SET updated_at = NOW() WHERE id = p_chain_id;
  
  -- Invalidate summary
  DELETE FROM memory_chain_summaries WHERE chain_id = p_chain_id;
  
  RETURN TRUE;
END;
$$;

-- Function to get chain with memories in order
CREATE OR REPLACE FUNCTION get_memory_chain(
  p_chain_id UUID,
  p_include_content BOOLEAN DEFAULT true
)
RETURNS TABLE (
  chain_id UUID,
  chain_title TEXT,
  chain_description TEXT,
  memory_id UUID,
  memory_label TEXT,
  memory_type memory_type,
  order_index INTEGER,
  transition_text TEXT,
  content TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id as chain_id,
    c.title as chain_title,
    c.description as chain_description,
    m.id as memory_id,
    m.label as memory_label,
    m.type as memory_type,
    l.order_index,
    l.transition_text,
    CASE 
      WHEN p_include_content AND m.storage_mode = 'INLINE' THEN p.content::TEXT
      ELSE NULL
    END as content
  FROM memory_chains c
  JOIN memory_chain_links l ON c.id = l.chain_id
  JOIN memories m ON l.memory_id = m.id
  LEFT JOIN payloads p ON m.id = p.memory_id
  WHERE c.id = p_chain_id
  ORDER BY l.order_index;
END;
$$;

-- Function to calculate chain token count
CREATE OR REPLACE FUNCTION calculate_chain_tokens(
  p_chain_id UUID
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_total_tokens INTEGER := 0;
  v_memory RECORD;
BEGIN
  FOR v_memory IN
    SELECT m.label, p.content
    FROM memory_chain_links l
    JOIN memories m ON l.memory_id = m.id
    LEFT JOIN payloads p ON m.id = p.memory_id
    WHERE l.chain_id = p_chain_id
    ORDER BY l.order_index
  LOOP
    -- Simple token estimation: ~4 chars per token
    v_total_tokens := v_total_tokens + 
      COALESCE(char_length(v_memory.label) / 4, 0) +
      COALESCE(char_length(v_memory.content) / 4, 0);
  END LOOP;
  
  RETURN v_total_tokens;
END;
$$;

-- RLS Policies
ALTER TABLE memory_chains ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_chain_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_chain_summaries ENABLE ROW LEVEL SECURITY;

-- Chains follow project access
CREATE POLICY "Users can view chains in their projects"
  ON memory_chains FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members 
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create chains in their projects"
  ON memory_chains FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT project_id FROM project_members 
      WHERE user_id = auth.uid() AND role IN ('OWNER', 'ADMIN', 'MEMBER')
    )
  );

CREATE POLICY "Users can update chains in their projects"
  ON memory_chains FOR UPDATE
  USING (
    project_id IN (
      SELECT project_id FROM project_members 
      WHERE user_id = auth.uid() AND role IN ('OWNER', 'ADMIN', 'MEMBER')
    )
  );

-- Similar policies for chain links and summaries
CREATE POLICY "Users can view chain links"
  ON memory_chain_links FOR SELECT
  USING (
    chain_id IN (
      SELECT id FROM memory_chains WHERE project_id IN (
        SELECT project_id FROM project_members WHERE user_id = auth.uid()
      )
    )
  );

CREATE POLICY "Users can manage chain links"
  ON memory_chain_links FOR ALL
  USING (
    chain_id IN (
      SELECT id FROM memory_chains WHERE project_id IN (
        SELECT project_id FROM project_members 
        WHERE user_id = auth.uid() AND role IN ('OWNER', 'ADMIN', 'MEMBER')
      )
    )
  );