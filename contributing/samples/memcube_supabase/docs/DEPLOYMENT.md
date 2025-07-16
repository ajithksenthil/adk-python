# MemCube Supabase Deployment Guide

## Prerequisites

- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- Node.js 18+ (for Edge Functions)
- A Supabase account at [app.supabase.com](https://app.supabase.com)

## Quick Deploy

### 1. Create Supabase Project

1. Go to [app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Fill in:
   - Project name: `memcube-prod`
   - Database password: (save this securely)
   - Region: Choose closest to your users

### 2. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd memcube_supabase

# Install Supabase CLI if not already installed
npm install -g supabase

# Login to Supabase
supabase login
```

### 3. Link to Project

```bash
# Get your project reference from Supabase dashboard
supabase link --project-ref your-project-ref

# Verify link
supabase status
```

### 4. Deploy Database Schema

```bash
# Push all migrations
supabase db push

# Verify tables created
supabase db dump --schema public
```

### 5. Configure Secrets

```bash
# Set required secrets
supabase secrets set OPENAI_API_KEY=sk-your-openai-key
supabase secrets set MARKETPLACE_WEBHOOK_URL=https://your-marketplace.com/webhook

# Optional: External storage
supabase secrets set S3_BUCKET=your-bucket-name
supabase secrets set S3_ACCESS_KEY=your-access-key
supabase secrets set S3_SECRET_KEY=your-secret-key
```

### 6. Deploy Edge Functions

```bash
# Deploy all functions
supabase functions deploy

# Or deploy individually
supabase functions deploy memories-crud
supabase functions deploy memories-schedule

# Verify deployment
supabase functions list
```

### 7. Configure Storage

```bash
# Create storage bucket (if not created by migration)
supabase storage create memory-payloads

# Set CORS policy
supabase storage update memory-payloads --public false --allowed-mime-types "text/*,application/json,application/octet-stream"
```

## Production Configuration

### Environment Variables

Create `.env.production`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# External Services
OPENAI_API_KEY=sk-xxx
MARKETPLACE_WEBHOOK_URL=https://api.marketplace.com/webhook

# Optional: External Storage
S3_BUCKET=memcube-payloads
S3_REGION=us-east-1
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx

# Application
NODE_ENV=production
LOG_LEVEL=info
```

### Database Indexes

Ensure optimal performance by creating additional indexes:

```sql
-- Performance indexes
CREATE INDEX idx_memories_project_type_priority 
ON memories(project_id, type, priority);

CREATE INDEX idx_memories_project_lifecycle 
ON memories(project_id, lifecycle) 
WHERE lifecycle NOT IN ('ARCHIVED', 'EXPIRED');

-- Text search index
CREATE INDEX idx_memories_label_fts 
ON memories USING gin(to_tsvector('english', label));

-- Partial indexes for hot queries
CREATE INDEX idx_memories_hot 
ON memories(project_id, last_used DESC) 
WHERE priority = 'HOT';
```

### Security Configuration

#### 1. API Rate Limiting

Configure in Supabase dashboard:
- API Settings → Rate Limiting
- Set limits per endpoint
- Enable DDoS protection

#### 2. Custom Domain

```bash
# Add custom domain
supabase domains add memcube.yourdomain.com

# Verify DNS
supabase domains verify memcube.yourdomain.com
```

#### 3. Backup Configuration

```sql
-- Enable point-in-time recovery
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET archive_mode = 'on';

-- Schedule regular backups via Supabase dashboard
```

## Monitoring Setup

### 1. Enable Logging

```sql
-- Enable statement logging
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_duration = 'on';
```

### 2. Metrics Collection

Create monitoring dashboard:

```sql
-- Create metrics view
CREATE OR REPLACE VIEW memory_metrics AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    project_id,
    type,
    COUNT(*) as memories_created,
    AVG(usage_hits) as avg_usage
FROM memories
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY 1, 2, 3;

-- Usage by project
CREATE OR REPLACE VIEW project_usage AS
SELECT 
    project_id,
    COUNT(DISTINCT m.id) as total_memories,
    COUNT(DISTINCT e.actor) as active_agents,
    SUM(p.size_bytes) as total_bytes
FROM memories m
LEFT JOIN memory_events e ON m.id = e.memory_id
LEFT JOIN memory_payloads p ON m.id = p.memory_id
GROUP BY project_id;
```

### 3. Alerts

Configure alerts in Supabase dashboard:
- Database size > 80%
- API errors > 1%
- Function execution time > 10s
- Storage usage > quota

## Scaling Considerations

### 1. Database Scaling

```sql
-- Partition large tables by project
CREATE TABLE memories_partitioned (
    LIKE memories INCLUDING ALL
) PARTITION BY HASH (project_id);

-- Create partitions
CREATE TABLE memories_p0 PARTITION OF memories_partitioned
FOR VALUES WITH (modulus 4, remainder 0);
-- Repeat for p1, p2, p3
```

### 2. Edge Function Scaling

Configure in `supabase/functions/[function-name]/config.toml`:

```toml
[function]
memory = 512  # MB
timeout = 30  # seconds
instances = 10  # max concurrent

[env]
NODE_OPTIONS = "--max-old-space-size=512"
```

### 3. Caching Strategy

```typescript
// Edge Function caching
const cache = new Map()
const CACHE_TTL = 300000 // 5 minutes

// In function handler
const cached = cache.get(cacheKey)
if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
  return cached.data
}
```

## Migration from Existing System

### 1. Data Migration Script

```python
# migrate_to_supabase.py
import asyncio
from supabase import create_client

async def migrate_memories(old_db, supabase_client):
    """Migrate memories from old system"""
    
    # Get memories from old system
    old_memories = await old_db.get_all_memories()
    
    # Batch insert to Supabase
    batch_size = 100
    for i in range(0, len(old_memories), batch_size):
        batch = old_memories[i:i+batch_size]
        
        # Transform to new schema
        transformed = [transform_memory(m) for m in batch]
        
        # Insert
        supabase_client.table('memories').insert(transformed).execute()
        
        print(f"Migrated {i+len(batch)} memories")

def transform_memory(old_memory):
    """Transform old schema to new"""
    return {
        'project_id': old_memory['tenant_id'],
        'label': old_memory['name'],
        'type': 'PLAINTEXT',
        'governance': {
            'read_roles': ['MEMBER', 'AGENT'],
            'write_roles': ['AGENT'],
            'ttl_days': 365
        },
        'created_by': old_memory['creator'],
        'created_at': old_memory['timestamp']
    }
```

### 2. Validation

```sql
-- Verify migration
SELECT 
    COUNT(*) as total,
    COUNT(DISTINCT project_id) as projects,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM memories;

-- Check for issues
SELECT * FROM memories 
WHERE governance IS NULL 
OR label IS NULL 
OR project_id IS NULL;
```

## Maintenance

### Daily Tasks

```bash
# Check function health
supabase functions list

# Monitor storage
supabase storage list
```

### Weekly Tasks

```sql
-- Update statistics
ANALYZE memories;
ANALYZE memory_payloads;

-- Check for stale memories
SELECT update_memory_lifecycle();

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY memory_stats;
```

### Monthly Tasks

```sql
-- Archive old memories
UPDATE memories 
SET lifecycle = 'ARCHIVED'
WHERE lifecycle = 'STALE' 
AND last_used < NOW() - INTERVAL '90 days';

-- Clean up expired
DELETE FROM memories 
WHERE lifecycle = 'EXPIRED' 
AND updated_at < NOW() - INTERVAL '30 days';

-- Vacuum tables
VACUUM ANALYZE memories;
```

## Troubleshooting

### Common Issues

1. **Function Timeout**
   ```bash
   # Increase timeout
   supabase functions deploy memories-schedule --timeout 60
   ```

2. **Storage Full**
   ```sql
   -- Check usage
   SELECT 
     schemaname,
     tablename,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

3. **Slow Queries**
   ```sql
   -- Enable query logging
   ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s
   
   -- Check missing indexes
   SELECT schemaname, tablename, attname, n_distinct, correlation
   FROM pg_stats
   WHERE schemaname = 'public'
   AND n_distinct > 100
   AND correlation < 0.1;
   ```

### Performance Tuning

```sql
-- Tune PostgreSQL settings
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Reload configuration
SELECT pg_reload_conf();
```

## Rollback Procedures

### Database Rollback

```bash
# List migrations
supabase migration list

# Create rollback migration
supabase migration new rollback_to_v1

# Edit and apply
supabase db push
```

### Function Rollback

```bash
# Deploy previous version
cd supabase/functions/memories-crud
git checkout tags/v1.0.0
supabase functions deploy memories-crud
```

## Security Checklist

- [ ] RLS enabled on all tables
- [ ] Service role key not exposed
- [ ] API rate limiting configured
- [ ] Backup policy active
- [ ] Monitoring alerts set
- [ ] Custom domain with SSL
- [ ] Secrets rotated quarterly
- [ ] Audit logs enabled
- [ ] DDoS protection active
- [ ] CORS properly configured