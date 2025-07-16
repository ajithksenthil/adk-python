"""State Memory Service implementation."""

from typing import Dict, Any, Optional
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import redis
from redis.exceptions import RedisError
import asyncio
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import threading

from .models import StateVersion, StateDelta, StateUpdateResponse
from .conflict_resolver import ConflictResolver
from .policy_validator import StatePolicyValidator, ValidationResult

logger = logging.getLogger(__name__)


class StateMemoryService:
    """Core service for managing FSA state memory."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 kafka_bootstrap_servers: str = "localhost:9092"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.kafka_servers = kafka_bootstrap_servers
        self.conflict_resolver = ConflictResolver()
        self.policy_validator = StatePolicyValidator()
        self.kafka_consumer = None
        self.consumer_thread = None
        self.running = False
        
    def start_kafka_consumer(self):
        """Start Kafka consumer for state.delta topic."""
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_state_deltas)
        self.consumer_thread.start()
        
    def stop_kafka_consumer(self):
        """Stop Kafka consumer gracefully."""
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join()
            
    def _consume_state_deltas(self):
        """Background thread to consume state delta events."""
        try:
            self.kafka_consumer = KafkaConsumer(
                'tenant.state.delta',
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='sms-consumer-group',
                auto_offset_reset='latest'
            )
            
            logger.info("Started Kafka consumer for state.delta topic")
            
            while self.running:
                messages = self.kafka_consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            self._process_state_delta(record.value)
                        except Exception as e:
                            logger.error(f"Error processing state delta: {e}")
                            
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")
        finally:
            if self.kafka_consumer:
                self.kafka_consumer.close()
                
    def _process_state_delta(self, delta_event: Dict[str, Any]):
        """Process a state delta event from Kafka."""
        delta = StateDelta(**delta_event)
        logger.info(f"Processing state delta for {delta.tenant}:{delta.fsa_id}")
        
        # Extract context for validation
        context = {
            "tenant_id": delta.tenant,
            "pillar": delta_event.get("pillar", ""),
            "aml_level": delta_event.get("aml_level", 0),
            "agent_type": delta_event.get("agent_type", ""),
            "lineage_id": delta.lineage_id
        }
        
        # Apply the delta with validation
        result = self.apply_delta(delta.tenant, delta.fsa_id, delta.delta, 
                                 delta.actor, delta.lineage_id, context)
        
        if result.success:
            logger.info(f"Applied delta successfully, new version: {result.version}")
        else:
            logger.warning(f"Failed to apply delta: {result.message}")
    
    def _get_state_key(self, tenant_id: str, fsa_id: str) -> str:
        """Generate Redis key for state storage."""
        return f"state:{tenant_id}:{fsa_id}"
    
    def _get_version_key(self, tenant_id: str, fsa_id: str) -> str:
        """Generate Redis key for version tracking."""
        return f"version:{tenant_id}:{fsa_id}"
    
    def get_state(self, tenant_id: str, fsa_id: str) -> Optional[StateVersion]:
        """Retrieve the latest state for a given FSA."""
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
                
            state = json.loads(state_json)
            version = int(version) if version else 1
            
            return StateVersion(
                tenant_id=tenant_id,
                fsa_id=fsa_id,
                version=version,
                state=state,
                lineage_id=state.get('_metadata', {}).get('lineage_id'),
                created_at=datetime.fromisoformat(
                    state.get('_metadata', {}).get('created_at', datetime.utcnow().isoformat())
                ),
                created_by=state.get('_metadata', {}).get('created_by')
            )
            
        except RedisError as e:
            logger.error(f"Redis error getting state: {e}")
            raise HTTPException(status_code=500, detail="State retrieval failed")
    
    def set_state(self, tenant_id: str, fsa_id: str, state: Dict[str, Any], 
                  actor: Optional[str] = None, lineage_id: Optional[str] = None) -> StateUpdateResponse:
        """Set the complete state (overwrite)."""
        try:
            state_key = self._get_state_key(tenant_id, fsa_id)
            version_key = self._get_version_key(tenant_id, fsa_id)
            
            # Add metadata
            state['_metadata'] = {
                'created_at': datetime.utcnow().isoformat(),
                'created_by': actor,
                'lineage_id': lineage_id
            }
            
            # Atomic update with version increment
            pipe = self.redis.pipeline()
            pipe.incr(version_key)
            pipe.set(state_key, json.dumps(state))
            version, _ = pipe.execute()
            
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
        """Apply a delta to the current state."""
        try:
            # Get current state
            current = self.get_state(tenant_id, fsa_id)
            current_state = current.state if current else {}
            
            # Validate delta against policies if context provided
            if context:
                validation_result = self.policy_validator.validate_delta(
                    current_state, delta, context
                )
                
                if not validation_result.allowed:
                    logger.warning(f"Policy validation failed: {validation_result.violations}")
                    return StateUpdateResponse(
                        success=False,
                        version=current.version if current else 0,
                        message=f"Policy violation: {'; '.join(validation_result.violations)}",
                        conflicts={"violations": validation_result.violations}
                    )
            
            # Apply the delta
            if current:
                new_state = self.conflict_resolver.merge_delta(current.state, delta)
            else:
                new_state = delta
                
            # Set the merged state
            return self.set_state(tenant_id, fsa_id, new_state, actor, lineage_id)
            
        except Exception as e:
            logger.error(f"Error applying delta: {e}")
            return StateUpdateResponse(
                success=False,
                version=0,
                message=f"Delta application failed: {str(e)}"
            )


# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    # Startup
    logger.info("Starting State Memory Service...")
    app.state.sms = StateMemoryService()
    app.state.sms.start_kafka_consumer()
    yield
    # Shutdown
    logger.info("Shutting down State Memory Service...")
    app.state.sms.stop_kafka_consumer()


app = FastAPI(title="State Memory Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "state-memory-service"}


@app.get("/state/{tenant_id}/{fsa_id}")
async def get_state(tenant_id: str, fsa_id: str):
    """Get the latest state for an FSA."""
    state = app.state.sms.get_state(tenant_id, fsa_id)
    if state:
        return state.dict()
    return {"state": {}, "version": 0}


@app.post("/state/{tenant_id}/{fsa_id}")
async def update_state(tenant_id: str, fsa_id: str, state: Dict[str, Any], 
                      actor: Optional[str] = None, lineage_id: Optional[str] = None):
    """Update the complete state."""
    result = app.state.sms.set_state(tenant_id, fsa_id, state, actor, lineage_id)
    return result.dict()


@app.post("/state/{tenant_id}/{fsa_id}/delta")
async def apply_delta(tenant_id: str, fsa_id: str, delta: Dict[str, Any],
                     actor: Optional[str] = None, lineage_id: Optional[str] = None,
                     pillar: Optional[str] = None, aml_level: Optional[int] = 0):
    """Apply a delta to the current state."""
    # Build context for validation
    context = {
        "tenant_id": tenant_id,
        "pillar": pillar or "",
        "aml_level": aml_level,
        "lineage_id": lineage_id or ""
    }
    
    result = app.state.sms.apply_delta(tenant_id, fsa_id, delta, actor, lineage_id, context)
    return result.dict()


@app.post("/validate/delta")
async def validate_delta(tenant_id: str, fsa_id: str, delta: Dict[str, Any],
                        pillar: str = "", aml_level: int = 0):
    """Validate a delta without applying it."""
    # Get current state
    current = app.state.sms.get_state(tenant_id, fsa_id)
    current_state = current.state if current else {}
    
    # Build context
    context = {
        "tenant_id": tenant_id,
        "pillar": pillar,
        "aml_level": aml_level
    }
    
    # Validate
    validation_result = app.state.sms.policy_validator.validate_delta(
        current_state, delta, context
    )
    
    return {
        "allowed": validation_result.allowed,
        "violations": validation_result.violations,
        "warnings": validation_result.warnings
    }