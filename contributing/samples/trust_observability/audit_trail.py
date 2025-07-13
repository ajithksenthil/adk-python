# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OpenTelemetry-based audit trail generation and storage."""

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncContextManager

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SpanType(Enum):
    """Types of AI spans for different operations."""
    AGENT_EXECUTION = "agent.execution"
    TOOL_CALL = "agent.tool_call"
    POLICY_CHECK = "policy.check"
    TREASURY_TRANSACTION = "treasury.transaction"
    WORKFLOW_STEP = "workflow.step"
    MODEL_INFERENCE = "model.inference"
    DATA_ACCESS = "data.access"
    CROSS_PILLAR_EVENT = "event.cross_pillar"


class SpanStatus(Enum):
    """Span execution status."""
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class SpanData:
    """Core data structure for an AI span."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    span_type: SpanType
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.OK
    
    # AI-specific attributes
    agent_id: Optional[str] = None
    pillar: Optional[str] = None
    aml_level: Optional[int] = None
    lineage_id: Optional[str] = None
    
    # Policy and governance
    policy_decision: Optional[str] = None
    policy_reasons: List[str] = field(default_factory=list)
    treasury_tx_hash: Optional[str] = None
    
    # Model and reasoning
    model_name: Optional[str] = None
    prompt_hash: Optional[str] = None
    response_hash: Optional[str] = None
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Tool execution details
    tool_name: Optional[str] = None
    tool_inputs: Dict[str, Any] = field(default_factory=dict)
    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    
    # Custom attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    def to_otel_dict(self) -> Dict[str, Any]:
        """Convert to OpenTelemetry-compatible dictionary."""
        otel_data = {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "operationName": self.operation_name,
            "startTime": int(self.start_time.timestamp() * 1000000),  # microseconds
            "duration": int(self.duration_ms() * 1000) if self.end_time else None,
            "tags": {
                "span.type": self.span_type.value,
                "span.status": self.status.value,
                "ai.agent.id": self.agent_id,
                "ai.agent.pillar": self.pillar,
                "ai.agent.aml_level": self.aml_level,
                "ai.lineage.id": self.lineage_id,
                "ai.policy.decision": self.policy_decision,
                "ai.policy.reasons": ",".join(self.policy_reasons) if self.policy_reasons else None,
                "ai.treasury.tx_hash": self.treasury_tx_hash,
                "ai.model.name": self.model_name,
                "ai.model.prompt_hash": self.prompt_hash,
                "ai.model.response_hash": self.response_hash,
                "ai.model.token_count": self.token_count,
                "ai.model.cost_usd": self.cost_usd,
                "ai.tool.name": self.tool_name,
                "ai.tool.inputs": json.dumps(self.tool_inputs) if self.tool_inputs else None,
                "ai.tool.outputs": json.dumps(self.tool_outputs) if self.tool_outputs else None,
                "error.type": self.error_type,
                "error.message": self.error_message,
                **self.attributes
            }
        }
        
        # Remove None values
        otel_data["tags"] = {k: v for k, v in otel_data["tags"].items() if v is not None}
        
        return otel_data


class AISpan:
    """Context manager for creating AI spans with automatic lifecycle management."""
    
    def __init__(
        self,
        audit_manager: "AuditTrailManager",
        span_data: SpanData
    ):
        self.audit_manager = audit_manager
        self.span_data = span_data
        self._active = False
    
    def __enter__(self):
        """Start the span."""
        self._active = True
        self.span_data.start_time = datetime.now()
        logger.debug(f"Started span {self.span_data.span_id}: {self.span_data.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the span and record it."""
        self._active = False
        self.span_data.end_time = datetime.now()
        
        if exc_type:
            self.span_data.status = SpanStatus.ERROR
            self.span_data.error_type = exc_type.__name__
            self.span_data.error_message = str(exc_val)
            if exc_tb:
                import traceback
                self.span_data.error_stack = "".join(traceback.format_tb(exc_tb))
        
        # Record the span
        self.audit_manager.record_span(self.span_data)
        logger.debug(f"Ended span {self.span_data.span_id} with status {self.span_data.status.value}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.__enter__()
        
        # Handle lineage tracking if configured
        if hasattr(self, '_lineage_service') and self._lineage_service:
            try:
                await self._lineage_service.track_agent_execution(
                    agent_id=self._lineage_agent_id,
                    operation=self._lineage_operation,
                    trace_id=self._lineage_trace_id,
                    pillar=self._lineage_pillar
                )
            except Exception as e:
                logger.warning(f"Failed to track lineage: {e}")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Handle trajectory evaluation if configured
        if hasattr(self, '_trajectory_evaluator') and self._trajectory_evaluator:
            try:
                await self._trajectory_evaluator.evaluate_span_realtime(self.span_data)
            except Exception as e:
                logger.warning(f"Failed to evaluate trajectory: {e}")
        
        return self.__exit__(exc_type, exc_val, exc_tb)
    
    def add_attribute(self, key: str, value: Any):
        """Add custom attribute to the span."""
        self.span_data.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to the span."""
        event = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {}
        }
        
        if "events" not in self.span_data.attributes:
            self.span_data.attributes["events"] = []
        self.span_data.attributes["events"].append(event)
    
    def set_status(self, status: SpanStatus, description: Optional[str] = None):
        """Set span status."""
        self.span_data.status = status
        if description:
            self.span_data.attributes["status.description"] = description


class SpanStorage:
    """Abstract interface for storing spans."""
    
    async def store_span(self, span_data: SpanData) -> bool:
        """Store a span. Returns True if successful."""
        raise NotImplementedError
    
    async def get_spans(
        self,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SpanData]:
        """Retrieve spans based on filters."""
        raise NotImplementedError


class InMemorySpanStorage(SpanStorage):
    """In-memory span storage for development and testing."""
    
    def __init__(self):
        self.spans: List[SpanData] = []
    
    async def store_span(self, span_data: SpanData) -> bool:
        """Store span in memory."""
        self.spans.append(span_data)
        return True
    
    async def get_spans(
        self,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SpanData]:
        """Retrieve spans with filtering."""
        filtered_spans = self.spans
        
        if trace_id:
            filtered_spans = [s for s in filtered_spans if s.trace_id == trace_id]
        
        if agent_id:
            filtered_spans = [s for s in filtered_spans if s.agent_id == agent_id]
        
        if start_time:
            filtered_spans = [s for s in filtered_spans if s.start_time >= start_time]
        
        if end_time:
            filtered_spans = [s for s in filtered_spans if s.start_time <= end_time]
        
        # Sort by start time (newest first) and limit
        filtered_spans.sort(key=lambda x: x.start_time, reverse=True)
        return filtered_spans[:limit]


class CloudSpanStorage(SpanStorage):
    """Cloud-based span storage (mock implementation for WORM + hot query store)."""
    
    def __init__(
        self,
        worm_bucket: str,
        hot_store_endpoint: str,
        project_id: Optional[str] = None
    ):
        self.worm_bucket = worm_bucket
        self.hot_store_endpoint = hot_store_endpoint
        self.project_id = project_id
        logger.info(f"Initialized cloud span storage: WORM={worm_bucket}, Hot={hot_store_endpoint}")
    
    async def store_span(self, span_data: SpanData) -> bool:
        """Store span to both WORM and hot store."""
        try:
            # Mock: Store to WORM bucket (write-once, immutable)
            worm_path = f"spans/{span_data.start_time.strftime('%Y/%m/%d')}/{span_data.span_id}.json"
            logger.debug(f"Would store to WORM: {self.worm_bucket}/{worm_path}")
            
            # Mock: Store to hot query store (ClickHouse/Loki)
            otel_data = span_data.to_otel_dict()
            logger.debug(f"Would store to hot store: {self.hot_store_endpoint}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store span {span_data.span_id}: {e}")
            return False
    
    async def get_spans(
        self,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SpanData]:
        """Mock query from hot store."""
        logger.info(f"Would query hot store with filters: trace_id={trace_id}, agent_id={agent_id}")
        return []  # Mock implementation


class AuditTrailManager:
    """Central manager for audit trail generation and storage."""
    
    def __init__(
        self,
        storage: Optional[SpanStorage] = None,
        enable_sampling: bool = True,
        sampling_rate: float = 1.0
    ):
        self.storage = storage or InMemorySpanStorage()
        self.enable_sampling = enable_sampling
        self.sampling_rate = sampling_rate
        self._active_traces: Dict[str, List[str]] = {}  # trace_id -> span_ids
    
    def create_span(
        self,
        operation_name: str,
        span_type: SpanType,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        **attributes
    ) -> AISpan:
        """Create a new AI span."""
        # Generate IDs
        span_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        
        # Apply sampling
        if self.enable_sampling and self.sampling_rate < 1.0:
            import random
            if random.random() > self.sampling_rate:
                # Return a no-op span
                return NoOpSpan()
        
        # Create span data
        span_data = SpanData(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=span_type,
            operation_name=operation_name,
            start_time=datetime.now(),
            **attributes
        )
        
        # Track active trace
        if trace_id not in self._active_traces:
            self._active_traces[trace_id] = []
        self._active_traces[trace_id].append(span_id)
        
        return AISpan(self, span_data)
    
    def record_span(self, span_data: SpanData):
        """Record a completed span."""
        # Store the span asynchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self.storage.store_span(span_data))
        except RuntimeError:
            # No event loop running, store synchronously for testing
            asyncio.run(self.storage.store_span(span_data))
        
        # Clean up trace tracking
        if span_data.trace_id in self._active_traces:
            if span_data.span_id in self._active_traces[span_data.trace_id]:
                self._active_traces[span_data.trace_id].remove(span_data.span_id)
            
            if not self._active_traces[span_data.trace_id]:
                del self._active_traces[span_data.trace_id]
    
    async def get_trace(self, trace_id: str) -> List[SpanData]:
        """Get all spans for a trace."""
        return await self.storage.get_spans(trace_id=trace_id)
    
    async def get_agent_spans(
        self,
        agent_id: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[SpanData]:
        """Get recent spans for an agent."""
        start_time = datetime.now() - timedelta(hours=hours)
        return await self.storage.get_spans(
            agent_id=agent_id,
            start_time=start_time,
            limit=limit
        )
    
    def get_active_traces(self) -> Dict[str, int]:
        """Get count of active spans per trace."""
        return {trace_id: len(span_ids) for trace_id, span_ids in self._active_traces.items()}


class NoOpSpan:
    """No-operation span for when sampling is disabled."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_attribute(self, key: str, value: Any):
        pass
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        pass
    
    def set_status(self, status: SpanStatus, description: Optional[str] = None):
        pass


# Convenience functions for common span types
def agent_execution_span(
    audit_manager: AuditTrailManager,
    agent_id: str,
    pillar: str,
    operation: str,
    aml_level: int,
    trace_id: Optional[str] = None
) -> AISpan:
    """Create span for agent execution."""
    return audit_manager.create_span(
        operation_name=f"agent.{operation}",
        span_type=SpanType.AGENT_EXECUTION,
        trace_id=trace_id,
        agent_id=agent_id,
        pillar=pillar,
        aml_level=aml_level
    )


def tool_call_span(
    audit_manager: AuditTrailManager,
    agent_id: str,
    tool_name: str,
    tool_inputs: Dict[str, Any],
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None
) -> AISpan:
    """Create span for tool call."""
    return audit_manager.create_span(
        operation_name=f"tool.{tool_name}",
        span_type=SpanType.TOOL_CALL,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        agent_id=agent_id,
        tool_name=tool_name,
        tool_inputs=tool_inputs
    )


def policy_check_span(
    audit_manager: AuditTrailManager,
    agent_id: str,
    policy_decision: str,
    policy_reasons: List[str],
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None
) -> AISpan:
    """Create span for policy check."""
    return audit_manager.create_span(
        operation_name="policy.check",
        span_type=SpanType.POLICY_CHECK,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        agent_id=agent_id,
        policy_decision=policy_decision,
        policy_reasons=policy_reasons
    )


# Global audit manager instance
_global_audit_manager: Optional[AuditTrailManager] = None


def get_audit_manager() -> AuditTrailManager:
    """Get the global audit manager."""
    global _global_audit_manager
    if _global_audit_manager is None:
        _global_audit_manager = AuditTrailManager()
    return _global_audit_manager


def set_audit_manager(audit_manager: AuditTrailManager):
    """Set the global audit manager."""
    global _global_audit_manager
    _global_audit_manager = audit_manager