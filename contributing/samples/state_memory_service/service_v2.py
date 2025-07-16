"""Enhanced State Memory Service with comprehensive project state."""

from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from contextlib import asynccontextmanager
import redis
from redis.exceptions import RedisError
import asyncio
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import threading

from .models_v2 import (
    ProjectState, Task, TaskStatus, Comment, CommentEvent,
    StateTransition
)
from .models import StateVersion, StateDelta, StateUpdateResponse
from .conflict_resolver import ConflictResolver
from .policy_validator import StatePolicyValidator, ValidationResult
from .slice_reader import StateSliceReader, SliceCache

logger = logging.getLogger(__name__)


class EnhancedStateMemoryService:
    """Enhanced SMS with comprehensive project state management."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 kafka_bootstrap_servers: str = "localhost:9092"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.kafka_servers = kafka_bootstrap_servers
        self.conflict_resolver = ConflictResolver()
        self.policy_validator = StatePolicyValidator()
        self.slice_reader = StateSliceReader()
        self.summary_cache = SliceCache(ttl_seconds=300)  # 5 min cache
        self.kafka_consumer = None
        self.consumer_thread = None
        self.running = False
        
        # Comments stored separately for efficiency
        self._comments_key_prefix = "comments:"
        
    def _get_state_key(self, tenant_id: str, fsa_id: str) -> str:
        """Generate Redis key for state storage."""
        return f"state:v2:{tenant_id}:{fsa_id}"
    
    def _get_version_key(self, tenant_id: str, fsa_id: str) -> str:
        """Generate Redis key for version tracking."""
        return f"version:v2:{tenant_id}:{fsa_id}"
    
    def _get_comments_key(self, tenant_id: str, fsa_id: str, task_id: str) -> str:
        """Generate Redis key for task comments."""
        return f"{self._comments_key_prefix}{tenant_id}:{fsa_id}:{task_id}"
    
    def get_state(self, tenant_id: str, fsa_id: str) -> Optional[ProjectState]:
        """Retrieve the current project state."""
        try:
            state_key = self._get_state_key(tenant_id, fsa_id)
            version_key = self._get_version_key(tenant_id, fsa_id)
            
            # Get state and version atomically
            pipe = self.redis.pipeline()
            pipe.get(state_key)
            pipe.get(version_key)
            state_json, version = pipe.execute()
            
            if not state_json:
                return None
                
            state_dict = json.loads(state_json)
            state = ProjectState(**state_dict)
            state.lineage_version = int(version) if version else 1
            
            return state
            
        except RedisError as e:
            logger.error(f"Redis error getting state: {e}")
            raise HTTPException(status_code=500, detail="State retrieval failed")

    def get_state_slice(self, tenant_id: str, fsa_id: str, slice_pattern: str, 
                       k: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve a slice of state for efficiency.
        
        Args:
            tenant_id: Tenant identifier
            fsa_id: FSA identifier
            slice_pattern: Pattern like "task:DESIGN_*" or "resources.inventory"
            k: Limit number of results
            
        Returns:
            Dict with slice data, summary, and version
        """
        try:
            # First check if we have a cached summary for this exact query
            state = self.get_state(tenant_id, fsa_id)
            if not state:
                return {"slice": {}, "summary": "", "version": 0}
            
            version = state.lineage_version
            
            # Check cache
            cached_summary = self.summary_cache.get_cached_summary(
                tenant_id, fsa_id, version, slice_pattern
            )
            
            # Extract the slice
            state_dict = state.dict()
            sliced_data = self.slice_reader.extract_slice(state_dict, slice_pattern, k)
            
            # Generate or use cached summary
            if cached_summary:
                summary = cached_summary
            else:
                summary = self.slice_reader.create_slice_summary(
                    sliced_data, 
                    context=f"{tenant_id}/{fsa_id} v{version}"
                )
                # Cache it
                self.summary_cache.cache_summary(
                    tenant_id, fsa_id, version, slice_pattern, summary
                )
            
            return {
                "slice": sliced_data,
                "summary": summary,
                "version": version
            }
            
        except Exception as e:
            logger.error(f"Error getting state slice: {e}")
            return {"slice": {}, "summary": "Error retrieving state", "version": 0}
    
    def set_state(self, tenant_id: str, fsa_id: str, state: ProjectState, 
                  actor: Optional[str] = None, lineage_id: Optional[str] = None) -> StateUpdateResponse:
        """Set the complete project state."""
        try:
            state_key = self._get_state_key(tenant_id, fsa_id)
            version_key = self._get_version_key(tenant_id, fsa_id)
            
            # Add metadata
            state._metadata = {
                'updated_at': datetime.utcnow().isoformat(),
                'updated_by': actor,
                'lineage_id': lineage_id
            }
            
            # Atomic update with version increment
            pipe = self.redis.pipeline()
            pipe.incr(version_key)
            pipe.set(state_key, json.dumps(state.dict()))
            version, _ = pipe.execute()
            
            state.lineage_version = version
            
            # Publish state update event
            self._publish_state_update(tenant_id, fsa_id, version, actor, lineage_id)
            
            return StateUpdateResponse(
                success=True,
                version=version,
                message="State updated successfully"
            )
            
        except RedisError as e:
            logger.error(f"Redis error setting state: {e}")
            return StateUpdateResponse(
                success=False,
                version=0,
                message=f"State update failed: {str(e)}"
            )
    
    def apply_delta(self, tenant_id: str, fsa_id: str, delta: Dict[str, Any], 
                    actor: Optional[str] = None, lineage_id: Optional[str] = None,
                    context: Optional[Dict[str, Any]] = None) -> StateUpdateResponse:
        """Apply a delta to the current state with validation."""
        try:
            # Get current state
            current = self.get_state(tenant_id, fsa_id)
            if not current:
                # Initialize with default state
                current = ProjectState()
                
            current_dict = current.dict()
            
            # Validate delta against policies if context provided
            if context:
                validation_result = self.policy_validator.validate_delta(
                    current_dict, delta, context
                )
                
                if not validation_result.allowed:
                    logger.warning(f"Policy validation failed: {validation_result.violations}")
                    
                    # Record failed transition
                    self._record_transition(
                        tenant_id, fsa_id, 
                        current.lineage_version, current.lineage_version,
                        delta, actor, lineage_id, False, validation_result.violations
                    )
                    
                    return StateUpdateResponse(
                        success=False,
                        version=current.lineage_version,
                        message=f"Policy violation: {'; '.join(validation_result.violations)}",
                        conflicts={"violations": validation_result.violations}
                    )
            
            # Apply the delta using JSONPath-like notation
            new_dict = self._apply_structured_delta(current_dict, delta)
            
            # Create new state
            new_state = ProjectState(**new_dict)
            
            # Set the merged state
            result = self.set_state(tenant_id, fsa_id, new_state, actor, lineage_id)
            
            if result.success:
                # Record successful transition
                self._record_transition(
                    tenant_id, fsa_id,
                    current.lineage_version, result.version,
                    delta, actor, lineage_id, True, None
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying delta: {e}")
            return StateUpdateResponse(
                success=False,
                version=0,
                message=f"Delta application failed: {str(e)}"
            )
    
    def _apply_structured_delta(self, state: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a structured delta using dot notation paths."""
        import copy
        new_state = copy.deepcopy(state)
        
        for path, value in delta.items():
            # Handle dot notation paths like "tasks.TASK-001.status"
            parts = path.split('.')
            current = new_state
            
            # Navigate to the parent
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Apply the change
            last_key = parts[-1]
            
            if isinstance(value, dict) and len(value) == 1:
                # Check for special operations
                op, op_value = next(iter(value.items()))
                
                if op == "$inc" and last_key in current:
                    current[last_key] = current.get(last_key, 0) + op_value
                elif op == "$push" and last_key in current:
                    if not isinstance(current[last_key], list):
                        current[last_key] = []
                    current[last_key].append(op_value)
                elif op == "$unset":
                    if last_key in current:
                        del current[last_key]
                else:
                    current[last_key] = value
            else:
                # Direct assignment
                current[last_key] = value
                
        return new_state
    
    def add_comment(self, tenant_id: str, fsa_id: str, task_id: str, 
                   comment: Comment) -> bool:
        """Add a comment to a task."""
        try:
            # Get current state to verify task exists
            state = self.get_state(tenant_id, fsa_id)
            if not state or task_id not in state.tasks:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Store comment
            comments_key = self._get_comments_key(tenant_id, fsa_id, task_id)
            comment_json = json.dumps(comment.dict())
            
            # Add to Redis list
            self.redis.rpush(comments_key, comment_json)
            
            # Publish comment event
            event = CommentEvent(
                task_id=task_id,
                comment=comment
            )
            self._publish_comment_event(tenant_id, fsa_id, event)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return False
    
    def get_task_comments(self, tenant_id: str, fsa_id: str, task_id: str,
                         limit: int = 10, since_ts: Optional[datetime] = None) -> List[Comment]:
        """Get comments for a task."""
        try:
            comments_key = self._get_comments_key(tenant_id, fsa_id, task_id)
            
            # Get all comments (could optimize with range for large threads)
            comment_jsons = self.redis.lrange(comments_key, 0, -1)
            
            comments = []
            for cj in comment_jsons:
                comment = Comment(**json.loads(cj))
                
                # Filter by timestamp if requested
                if since_ts and comment.ts < since_ts:
                    continue
                    
                comments.append(comment)
            
            # Sort by timestamp and limit
            comments.sort(key=lambda c: c.ts, reverse=True)
            return comments[:limit]
            
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []
    
    def update_agent_heartbeat(self, tenant_id: str, fsa_id: str, 
                             agent_name: str) -> bool:
        """Update agent heartbeat timestamp."""
        delta = {
            f"agents_online.{agent_name}": datetime.utcnow()
        }
        
        result = self.apply_delta(
            tenant_id, fsa_id, delta,
            actor=agent_name, 
            lineage_id=f"heartbeat-{agent_name}"
        )
        
        return result.success
    
    def _publish_state_update(self, tenant_id: str, fsa_id: str, version: int,
                            actor: str, lineage_id: str):
        """Publish state update event to Kafka."""
        try:
            if not hasattr(self, '_kafka_producer'):
                self._kafka_producer = KafkaProducer(
                    bootstrap_servers=self.kafka_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
            
            event = {
                "tenant_id": tenant_id,
                "fsa_id": fsa_id,
                "version": version,
                "actor": actor,
                "lineage_id": lineage_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._kafka_producer.send('tenant.state.updated', value=event)
            
        except Exception as e:
            logger.error(f"Failed to publish state update: {e}")
    
    def _publish_comment_event(self, tenant_id: str, fsa_id: str, event: CommentEvent):
        """Publish comment event to Kafka."""
        try:
            if not hasattr(self, '_kafka_producer'):
                self._kafka_producer = KafkaProducer(
                    bootstrap_servers=self.kafka_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
            
            event_data = event.dict()
            event_data['tenant_id'] = tenant_id
            event_data['fsa_id'] = fsa_id
            
            self._kafka_producer.send('tenant.comment.append', value=event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish comment event: {e}")
    
    def _record_transition(self, tenant_id: str, fsa_id: str,
                          from_version: int, to_version: int,
                          delta: Dict[str, Any], actor: str, lineage_id: str,
                          passed: bool, violations: Optional[List[str]]):
        """Record state transition for audit trail."""
        transition = StateTransition(
            from_version=from_version,
            to_version=to_version,
            delta=delta,
            actor=actor,
            lineage_id=lineage_id,
            policy_check_passed=passed,
            violations=violations
        )
        
        # Store in Redis with TTL (30 days)
        key = f"transition:{tenant_id}:{fsa_id}:{from_version}-{to_version}"
        self.redis.setex(key, 30 * 24 * 3600, json.dumps(transition.dict()))


# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    # Startup
    logger.info("Starting Enhanced State Memory Service...")
    app.state.sms = EnhancedStateMemoryService()
    yield
    # Shutdown
    logger.info("Shutting down Enhanced State Memory Service...")


app = FastAPI(title="Enhanced State Memory Service", version="2.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "enhanced-state-memory-service", "version": "2.0"}


@app.get("/state/{tenant_id}/{fsa_id}")
async def get_state(tenant_id: str, fsa_id: str, summary: bool = False):
    """Get the current project state."""
    state = app.state.sms.get_state(tenant_id, fsa_id)
    if state:
        if summary:
            return {
                "version": state.lineage_version,
                "summary": state.to_summary()
            }
        return state.dict()
    return {"state": {}, "version": 0}


@app.get("/state/{tenant_id}/{fsa_id}/slice")
async def get_state_slice(
    tenant_id: str, 
    fsa_id: str,
    slice: str = Query(..., description="Slice pattern like 'task:DESIGN_*' or 'resources.inventory'"),
    k: Optional[int] = Query(None, ge=1, le=100, description="Limit number of results")
):
    """
    Get a slice of state for efficient reading.
    
    Examples:
    - ?slice=task:DESIGN_* - Get all design tasks
    - ?slice=task:*&k=5 - Get first 5 tasks
    - ?slice=resources.inventory - Get just inventory
    - ?slice=metrics.ctr* - Get CTR-related metrics
    - ?slice=agent:*bot - Get all bot agents
    """
    result = app.state.sms.get_state_slice(tenant_id, fsa_id, slice, k)
    return result


@app.post("/state/{tenant_id}/{fsa_id}")
async def update_state(tenant_id: str, fsa_id: str, state_dict: Dict[str, Any], 
                      actor: Optional[str] = None, lineage_id: Optional[str] = None):
    """Update the complete state."""
    state = ProjectState(**state_dict)
    result = app.state.sms.set_state(tenant_id, fsa_id, state, actor, lineage_id)
    return result.dict()


@app.post("/state/{tenant_id}/{fsa_id}/delta")
async def apply_delta(tenant_id: str, fsa_id: str, delta: Dict[str, Any],
                     actor: Optional[str] = None, lineage_id: Optional[str] = None,
                     pillar: Optional[str] = None, aml_level: Optional[int] = 0):
    """Apply a delta to the current state."""
    context = {
        "tenant_id": tenant_id,
        "pillar": pillar or "",
        "aml_level": aml_level,
        "lineage_id": lineage_id or ""
    }
    
    result = app.state.sms.apply_delta(tenant_id, fsa_id, delta, actor, lineage_id, context)
    return result.dict()


@app.post("/tasks/{tenant_id}/{fsa_id}/{task_id}/comment")
async def add_comment(tenant_id: str, fsa_id: str, task_id: str,
                     author: str, body: str, lineage_id: str,
                     is_blocker: bool = False):
    """Add a comment to a task."""
    # Get current state version
    state = app.state.sms.get_state(tenant_id, fsa_id)
    state_ver = state.lineage_version if state else 0
    
    comment = Comment(
        comment_id=f"c-{datetime.utcnow().timestamp()}",
        author=author,
        lineage_id=lineage_id,
        state_ver=state_ver,
        body_md=body,
        is_blocker=is_blocker
    )
    
    success = app.state.sms.add_comment(tenant_id, fsa_id, task_id, comment)
    return {"success": success, "comment_id": comment.comment_id}


@app.get("/tasks/{tenant_id}/{fsa_id}/{task_id}/comments")
async def get_comments(tenant_id: str, fsa_id: str, task_id: str,
                      limit: int = Query(10, ge=1, le=100)):
    """Get comments for a task."""
    comments = app.state.sms.get_task_comments(tenant_id, fsa_id, task_id, limit)
    return {"task_id": task_id, "comments": [c.dict() for c in comments]}


@app.post("/agents/{tenant_id}/{fsa_id}/{agent_name}/heartbeat")
async def update_heartbeat(tenant_id: str, fsa_id: str, agent_name: str):
    """Update agent heartbeat."""
    success = app.state.sms.update_agent_heartbeat(tenant_id, fsa_id, agent_name)
    return {"success": success, "agent": agent_name, "timestamp": datetime.utcnow()}