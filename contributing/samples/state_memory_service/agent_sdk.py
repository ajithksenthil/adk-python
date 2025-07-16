"""Agent SDK extensions for State Memory Service integration."""

import json
import logging
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class StateDeltaProducer:
    """Helper for agents to propose state deltas."""
    
    def __init__(self, kafka_bootstrap_servers: str = "localhost:9092"):
        self.kafka_servers = kafka_bootstrap_servers
        self._producer = None
        
    def initialize(self):
        """Initialize Kafka producer."""
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            logger.info("Initialized state delta producer")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
            
    def close(self):
        """Close the producer."""
        if self._producer:
            self._producer.close()
            
    def propose_state_delta(self, tenant_id: str, fsa_id: str, agent_name: str,
                          delta: Dict[str, Any], lineage_id: str) -> bool:
        """
        Propose a state delta to be applied.
        
        Args:
            tenant_id: Tenant identifier
            fsa_id: FSA identifier  
            agent_name: Name of the agent proposing the delta
            delta: The state changes to apply
            lineage_id: Trace ID for lineage tracking
            
        Returns:
            True if successfully published
        """
        if not self._producer:
            logger.error("Producer not initialized")
            return False
            
        event = {
            "tenant": tenant_id,
            "fsa_id": fsa_id,
            "actor": agent_name,
            "delta": delta,
            "lineage_id": lineage_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        key = f"{tenant_id}:{fsa_id}"
        
        try:
            future = self._producer.send(
                'tenant.state.delta',
                key=key,
                value=event
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            logger.info(f"Published state delta to {record_metadata.topic}:{record_metadata.partition}:{record_metadata.offset}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish state delta: {e}")
            return False


class AgentStateHelper:
    """Helper class for agents to work with state."""
    
    def __init__(self, state_producer: Optional[StateDeltaProducer] = None):
        self.state_producer = state_producer or StateDeltaProducer()
        self._initialized = False
        
    def initialize(self):
        """Initialize the helper."""
        if not self._initialized:
            self.state_producer.initialize()
            self._initialized = True
            
    def close(self):
        """Clean up resources."""
        if self._initialized:
            self.state_producer.close()
            self._initialized = False
            
    def __enter__(self):
        self.initialize()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def propose_state_update(self, context: Dict[str, Any], delta: Dict[str, Any]) -> bool:
        """
        Propose a state update based on agent context.
        
        Args:
            context: Agent execution context containing tenant_id, fsa_id, etc.
            delta: State changes to propose
            
        Returns:
            True if successfully proposed
        """
        if not self._initialized:
            self.initialize()
            
        tenant_id = context.get("tenant_id")
        fsa_id = context.get("fsa_id")
        agent_name = context.get("agent_name", "unknown")
        lineage_id = context.get("lineage_id", "")
        
        if not all([tenant_id, fsa_id]):
            logger.error("Missing required context fields: tenant_id, fsa_id")
            return False
            
        return self.state_producer.propose_state_delta(
            tenant_id=tenant_id,
            fsa_id=fsa_id,
            agent_name=agent_name,
            delta=delta,
            lineage_id=lineage_id
        )
        
    def create_task_update(self, task_id: str, status: str, **kwargs) -> Dict[str, Any]:
        """Helper to create a task status update delta."""
        delta = {
            "task_status": {
                task_id: status
            }
        }
        
        # Add any additional fields
        for key, value in kwargs.items():
            delta[key] = value
            
        return delta
        
    def create_inventory_update(self, item: str, change: int) -> Dict[str, Any]:
        """Helper to create an inventory update delta."""
        return {
            "inventory": {
                item: {"$inc": change}
            }
        }
        
    def create_budget_update(self, amount: float) -> Dict[str, Any]:
        """Helper to create a budget update delta."""
        return {
            "budget_remaining": {"$inc": amount}
        }