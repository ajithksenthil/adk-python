-- Privacy and Licensing Controls: Secure memory sharing with licensing

-- Create memory_licenses table
CREATE TABLE IF NOT EXISTS memory_licenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  license_type TEXT NOT NULL,
  permissions JSONB NOT NULL DEFAULT '{}',
  restrictions JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT memory_licenses_type_check CHECK (
    license_type IN ('OPEN', 'RESTRICTED', 'COMMERCIAL', 'PROPRIETARY', 'CUSTOM')
  ),
  CONSTRAINT memory_licenses_name_unique UNIQUE (name)
);

-- Create memory_privacy_settings table
CREATE TABLE IF NOT EXISTS memory_privacy_settings (
  memory_id UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
  visibility TEXT NOT NULL DEFAULT 'PRIVATE',
  license_id UUID REFERENCES memory_licenses(id),
  requires_attribution BOOLEAN DEFAULT false,
  allow_derivatives BOOLEAN DEFAULT true,
  allow_commercial_use BOOLEAN DEFAULT true,
  encryption_enabled BOOLEAN DEFAULT false,
  encryption_key_id TEXT,
  pii_detected BOOLEAN DEFAULT false,
  pii_scan_date TIMESTAMP WITH TIME ZONE,
  custom_terms TEXT,
  expires_at TIMESTAMP WITH TIME ZONE,
  
  CONSTRAINT memory_privacy_visibility_check CHECK (
    visibility IN ('PRIVATE', 'PROJECT', 'ORGANIZATION', 'PUBLIC')
  )
);

-- Create memory_access_logs table for audit trail
CREATE TABLE IF NOT EXISTS memory_access_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  accessed_by UUID REFERENCES auth.users(id),
  accessed_by_agent UUID,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  access_type TEXT NOT NULL,
  access_granted BOOLEAN NOT NULL,
  denial_reason TEXT,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT memory_access_logs_type_check CHECK (
    access_type IN ('READ', 'WRITE', 'SHARE', 'EXPORT', 'DELETE')
  )
);

-- Create memory_sharing_tokens table
CREATE TABLE IF NOT EXISTS memory_sharing_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),
  created_by UUID REFERENCES auth.users(id),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW() + INTERVAL '7 days',
  max_uses INTEGER DEFAULT 1,
  current_uses INTEGER DEFAULT 0,
  allowed_operations TEXT[] DEFAULT ARRAY['READ'],
  recipient_email TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT memory_sharing_tokens_uses_check CHECK (current_uses <= max_uses)
);

-- Create pii_detection_rules table
CREATE TABLE IF NOT EXISTS pii_detection_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name TEXT NOT NULL,
  pattern TEXT NOT NULL, -- Regex pattern
  pii_type TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'MEDIUM',
  is_active BOOLEAN DEFAULT true,
  
  CONSTRAINT pii_detection_rules_type_check CHECK (
    pii_type IN ('EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'IP_ADDRESS', 
                 'PHYSICAL_ADDRESS', 'NAME', 'DATE_OF_BIRTH', 'CUSTOM')
  ),
  CONSTRAINT pii_detection_rules_severity_check CHECK (
    severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
  )
);

-- Indexes
CREATE INDEX memory_privacy_settings_visibility_idx ON memory_privacy_settings(visibility);
CREATE INDEX memory_privacy_settings_license_idx ON memory_privacy_settings(license_id);
CREATE INDEX memory_access_logs_memory_idx ON memory_access_logs(memory_id, created_at DESC);
CREATE INDEX memory_access_logs_user_idx ON memory_access_logs(accessed_by, created_at DESC);
CREATE INDEX memory_sharing_tokens_token_idx ON memory_sharing_tokens(token) WHERE expires_at > NOW();

-- Function to check memory access permissions
CREATE OR REPLACE FUNCTION check_memory_access(
  p_memory_id UUID,
  p_user_id UUID,
  p_access_type TEXT DEFAULT 'READ',
  p_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
  allowed BOOLEAN,
  reason TEXT,
  requires_attribution BOOLEAN,
  license_info JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_memory memories%ROWTYPE;
  v_privacy memory_privacy_settings%ROWTYPE;
  v_license memory_licenses%ROWTYPE;
  v_is_owner BOOLEAN;
  v_is_project_member BOOLEAN;
  v_allowed BOOLEAN := false;
  v_reason TEXT;
BEGIN
  -- Get memory details
  SELECT * INTO v_memory FROM memories WHERE id = p_memory_id;
  IF NOT FOUND THEN
    RETURN QUERY SELECT false, 'Memory not found', false, NULL::JSONB;
    RETURN;
  END IF;
  
  -- Get privacy settings
  SELECT * INTO v_privacy FROM memory_privacy_settings WHERE memory_id = p_memory_id;
  
  -- Get license if exists
  IF v_privacy.license_id IS NOT NULL THEN
    SELECT * INTO v_license FROM memory_licenses WHERE id = v_privacy.license_id;
  END IF;
  
  -- Check if user is owner
  v_is_owner := (v_memory.created_by = p_user_id);
  
  -- Check if user is project member
  IF p_project_id IS NOT NULL THEN
    SELECT EXISTS (
      SELECT 1 FROM project_members 
      WHERE project_id = p_project_id AND user_id = p_user_id
    ) INTO v_is_project_member;
  ELSE
    SELECT EXISTS (
      SELECT 1 FROM project_members 
      WHERE project_id = v_memory.project_id AND user_id = p_user_id
    ) INTO v_is_project_member;
  END IF;
  
  -- Determine access based on visibility
  CASE v_privacy.visibility
    WHEN 'PRIVATE' THEN
      v_allowed := v_is_owner;
      v_reason := CASE WHEN v_allowed THEN 'Owner access' ELSE 'Private memory' END;
      
    WHEN 'PROJECT' THEN
      v_allowed := v_is_owner OR v_is_project_member;
      v_reason := CASE 
        WHEN v_is_owner THEN 'Owner access'
        WHEN v_allowed THEN 'Project member access'
        ELSE 'Not a project member'
      END;
      
    WHEN 'ORGANIZATION' THEN
      -- For now, organization = any project member in same org
      v_allowed := v_is_owner OR EXISTS (
        SELECT 1 FROM project_members pm1
        JOIN project_members pm2 ON pm1.project_id = pm2.project_id
        WHERE pm1.user_id = p_user_id AND pm2.user_id = v_memory.created_by
      );
      v_reason := CASE 
        WHEN v_is_owner THEN 'Owner access'
        WHEN v_allowed THEN 'Organization member access'
        ELSE 'Not in same organization'
      END;
      
    WHEN 'PUBLIC' THEN
      v_allowed := true;
      v_reason := 'Public memory';
      
    ELSE
      v_allowed := false;
      v_reason := 'Unknown visibility setting';
  END CASE;
  
  -- Check if memory has expired
  IF v_privacy.expires_at IS NOT NULL AND v_privacy.expires_at < NOW() THEN
    v_allowed := false;
    v_reason := 'Memory has expired';
  END IF;
  
  -- Log access attempt
  INSERT INTO memory_access_logs (
    memory_id, accessed_by, project_id, access_type, 
    access_granted, denial_reason
  ) VALUES (
    p_memory_id, p_user_id, p_project_id, p_access_type,
    v_allowed, CASE WHEN v_allowed THEN NULL ELSE v_reason END
  );
  
  -- Return result
  RETURN QUERY SELECT 
    v_allowed,
    v_reason,
    COALESCE(v_privacy.requires_attribution, false),
    CASE 
      WHEN v_license.id IS NOT NULL THEN
        jsonb_build_object(
          'id', v_license.id,
          'name', v_license.name,
          'type', v_license.license_type,
          'permissions', v_license.permissions,
          'restrictions', v_license.restrictions
        )
      ELSE NULL
    END;
END;
$$;

-- Function to detect PII in content
CREATE OR REPLACE FUNCTION detect_pii(
  p_content TEXT
)
RETURNS TABLE (
  has_pii BOOLEAN,
  pii_types TEXT[],
  severity TEXT,
  details JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_rule RECORD;
  v_pii_found BOOLEAN := false;
  v_pii_types TEXT[] := '{}';
  v_max_severity TEXT := 'LOW';
  v_matches JSONB := '[]'::JSONB;
  v_severity_order INTEGER;
BEGIN
  -- Check each active PII detection rule
  FOR v_rule IN
    SELECT * FROM pii_detection_rules WHERE is_active = true
  LOOP
    IF p_content ~* v_rule.pattern THEN
      v_pii_found := true;
      v_pii_types := array_append(v_pii_types, v_rule.pii_type);
      
      -- Update max severity
      v_severity_order := CASE v_rule.severity
        WHEN 'LOW' THEN 1
        WHEN 'MEDIUM' THEN 2
        WHEN 'HIGH' THEN 3
        WHEN 'CRITICAL' THEN 4
      END;
      
      IF v_severity_order > CASE v_max_severity
        WHEN 'LOW' THEN 1
        WHEN 'MEDIUM' THEN 2
        WHEN 'HIGH' THEN 3
        WHEN 'CRITICAL' THEN 4
      END THEN
        v_max_severity := v_rule.severity;
      END IF;
      
      -- Add match details
      v_matches := v_matches || jsonb_build_object(
        'type', v_rule.pii_type,
        'rule', v_rule.rule_name,
        'severity', v_rule.severity
      );
    END IF;
  END LOOP;
  
  RETURN QUERY SELECT 
    v_pii_found,
    v_pii_types,
    v_max_severity,
    jsonb_build_object(
      'matches', v_matches,
      'scan_date', NOW()
    );
END;
$$;

-- Function to encrypt sensitive memory content
CREATE OR REPLACE FUNCTION encrypt_memory_content(
  p_memory_id UUID,
  p_key_id TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
  v_payload_exists BOOLEAN;
BEGIN
  -- Check if payload exists
  SELECT EXISTS (
    SELECT 1 FROM payloads WHERE memory_id = p_memory_id
  ) INTO v_payload_exists;
  
  IF NOT v_payload_exists THEN
    RETURN false;
  END IF;
  
  -- In production, this would call an external encryption service
  -- For now, we just mark it as encrypted
  UPDATE memory_privacy_settings
  SET 
    encryption_enabled = true,
    encryption_key_id = p_key_id
  WHERE memory_id = p_memory_id;
  
  -- Add encryption metadata to payload
  UPDATE payloads
  SET metadata = COALESCE(metadata, '{}'::JSONB) || 
    jsonb_build_object(
      'encrypted', true,
      'encryption_key_id', p_key_id,
      'encrypted_at', NOW()
    )
  WHERE memory_id = p_memory_id;
  
  RETURN true;
END;
$$;

-- Function to create sharing token
CREATE OR REPLACE FUNCTION create_sharing_token(
  p_memory_id UUID,
  p_user_id UUID,
  p_expires_in INTERVAL DEFAULT '7 days',
  p_max_uses INTEGER DEFAULT 1,
  p_allowed_operations TEXT[] DEFAULT ARRAY['READ'],
  p_recipient_email TEXT DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
  v_token TEXT;
  v_access_check RECORD;
BEGIN
  -- Check if user has share permission
  SELECT * FROM check_memory_access(p_memory_id, p_user_id, 'SHARE')
  INTO v_access_check;
  
  IF NOT v_access_check.allowed THEN
    RAISE EXCEPTION 'No permission to share this memory: %', v_access_check.reason;
  END IF;
  
  -- Create token
  INSERT INTO memory_sharing_tokens (
    memory_id, created_by, expires_at, max_uses, 
    allowed_operations, recipient_email
  ) VALUES (
    p_memory_id, p_user_id, NOW() + p_expires_in, p_max_uses,
    p_allowed_operations, p_recipient_email
  ) RETURNING token INTO v_token;
  
  RETURN v_token;
END;
$$;

-- Function to redeem sharing token
CREATE OR REPLACE FUNCTION redeem_sharing_token(
  p_token TEXT,
  p_operation TEXT DEFAULT 'READ'
)
RETURNS TABLE (
  success BOOLEAN,
  memory_id UUID,
  reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_token_record memory_sharing_tokens%ROWTYPE;
BEGIN
  -- Get token details
  SELECT * INTO v_token_record
  FROM memory_sharing_tokens
  WHERE token = p_token
    AND expires_at > NOW()
    AND current_uses < max_uses
  FOR UPDATE;
  
  IF NOT FOUND THEN
    RETURN QUERY SELECT false, NULL::UUID, 'Invalid or expired token';
    RETURN;
  END IF;
  
  -- Check if operation is allowed
  IF NOT (p_operation = ANY(v_token_record.allowed_operations)) THEN
    RETURN QUERY SELECT false, v_token_record.memory_id, 'Operation not allowed';
    RETURN;
  END IF;
  
  -- Update usage count
  UPDATE memory_sharing_tokens
  SET current_uses = current_uses + 1
  WHERE id = v_token_record.id;
  
  -- Log access
  INSERT INTO memory_access_logs (
    memory_id, access_type, access_granted, denial_reason
  ) VALUES (
    v_token_record.memory_id, p_operation, true, 'Token access'
  );
  
  RETURN QUERY SELECT true, v_token_record.memory_id, 'Access granted';
END;
$$;

-- Initialize default licenses
INSERT INTO memory_licenses (name, license_type, permissions, restrictions) VALUES
  ('Open Access', 'OPEN', 
   '{"read": true, "modify": true, "share": true, "commercial": true}',
   '{}'),
  ('Attribution Required', 'RESTRICTED',
   '{"read": true, "modify": true, "share": true, "commercial": true}',
   '{"attribution": "required"}'),
  ('Non-Commercial', 'RESTRICTED',
   '{"read": true, "modify": true, "share": true, "commercial": false}',
   '{"commercial_use": "prohibited"}'),
  ('Read Only', 'RESTRICTED',
   '{"read": true, "modify": false, "share": false, "commercial": false}',
   '{"modifications": "prohibited", "redistribution": "prohibited"}'),
  ('Proprietary', 'PROPRIETARY',
   '{"read": false, "modify": false, "share": false, "commercial": false}',
   '{"all_rights": "reserved"}')
ON CONFLICT (name) DO NOTHING;

-- Initialize PII detection rules
INSERT INTO pii_detection_rules (rule_name, pattern, pii_type, severity) VALUES
  ('Email Address', '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL', 'MEDIUM'),
  ('Phone Number', '\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', 'PHONE', 'MEDIUM'),
  ('SSN', '\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b', 'SSN', 'CRITICAL'),
  ('Credit Card', '\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b', 'CREDIT_CARD', 'CRITICAL'),
  ('IP Address', '\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', 'IP_ADDRESS', 'LOW')
ON CONFLICT DO NOTHING;

-- Function to apply privacy settings to new memories
CREATE OR REPLACE FUNCTION apply_default_privacy_settings()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_pii_result RECORD;
BEGIN
  -- Create default privacy settings
  INSERT INTO memory_privacy_settings (
    memory_id, 
    visibility,
    requires_attribution,
    allow_derivatives,
    allow_commercial_use
  ) VALUES (
    NEW.id,
    'PROJECT', -- Default to project visibility
    false,
    true,
    true
  );
  
  -- Check for PII if content exists
  IF EXISTS (SELECT 1 FROM payloads WHERE memory_id = NEW.id) THEN
    SELECT * FROM detect_pii(
      (SELECT content::TEXT FROM payloads WHERE memory_id = NEW.id LIMIT 1)
    ) INTO v_pii_result;
    
    IF v_pii_result.has_pii THEN
      -- Update privacy settings if PII detected
      UPDATE memory_privacy_settings
      SET 
        pii_detected = true,
        pii_scan_date = NOW(),
        visibility = 'PRIVATE', -- Restrict visibility
        encryption_enabled = CASE 
          WHEN v_pii_result.severity IN ('HIGH', 'CRITICAL') THEN true
          ELSE false
        END
      WHERE memory_id = NEW.id;
      
      -- Log PII detection
      INSERT INTO memory_events (
        event_type, memory_id, project_id, metadata
      ) VALUES (
        'pii_detected', NEW.id, NEW.project_id, 
        jsonb_build_object(
          'pii_types', v_pii_result.pii_types,
          'severity', v_pii_result.severity,
          'auto_encrypted', v_pii_result.severity IN ('HIGH', 'CRITICAL')
        )
      );
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$;

-- Create trigger for new memories
CREATE TRIGGER apply_privacy_on_memory_create
  AFTER INSERT ON memories
  FOR EACH ROW
  EXECUTE FUNCTION apply_default_privacy_settings();

-- RLS Policies
ALTER TABLE memory_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_privacy_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_sharing_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE pii_detection_rules ENABLE ROW LEVEL SECURITY;

-- Everyone can view licenses
CREATE POLICY "Anyone can view licenses"
  ON memory_licenses FOR SELECT
  USING (true);

-- Privacy settings follow memory access
CREATE POLICY "Users can view privacy settings for accessible memories"
  ON memory_privacy_settings FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM check_memory_access(memory_id, auth.uid(), 'READ')
      WHERE allowed = true
    )
  );

CREATE POLICY "Memory owners can update privacy settings"
  ON memory_privacy_settings FOR UPDATE
  USING (
    memory_id IN (
      SELECT id FROM memories WHERE created_by = auth.uid()
    )
  );

-- Access logs visible to memory owners and project admins
CREATE POLICY "Users can view access logs for their memories"
  ON memory_access_logs FOR SELECT
  USING (
    memory_id IN (
      SELECT id FROM memories WHERE created_by = auth.uid()
    ) OR
    project_id IN (
      SELECT project_id FROM project_members 
      WHERE user_id = auth.uid() AND role IN ('OWNER', 'ADMIN')
    )
  );

-- Sharing tokens managed by creators
CREATE POLICY "Users can manage their sharing tokens"
  ON memory_sharing_tokens FOR ALL
  USING (created_by = auth.uid());

-- Only admins can manage PII rules
CREATE POLICY "Only admins can view PII rules"
  ON pii_detection_rules FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM project_members 
      WHERE user_id = auth.uid() AND role = 'OWNER'
    )
  );