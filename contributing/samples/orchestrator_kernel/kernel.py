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

"""Orchestrator Kernel - The runtime OS for all agents."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
import uuid

# Internal imports
from .execution_graph import (
    GraphNode, NodeType, ExecutionGraph, GraphCompiler,
    GraphScheduler, GraphRegistry
)
from .react_loop import (
    ReactLoop, LoopConfig, PolicyHook, AMLPolicyHook,
    OPAPolicyHook, ReactState
)
from .request_router import (
    Request, RequestRouter, RouteConfig, WorkerNode,
    RequestPriority
)

# External integrations
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from control_plane.policy_engine import PolicyEngine, PolicyDecision
    from data_mesh.event_bus import EventBus, Event, EventMetadata, EventType, Topics
    from data_mesh.lineage_service import LineageService
    from trust.observability import ObservabilityProvider, Span
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Some dependencies not available, running in standalone mode")
    # Define stub classes for standalone mode
    PolicyEngine = None
    EventBus = None
    LineageService = None
    ObservabilityProvider = None

logger = logging.getLogger(__name__)


class KernelStatus(Enum):
    """Status of the orchestrator kernel."""
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class KernelConfig:
    """Configuration for orchestrator kernel."""
    enable_observability: bool = True
    enable_policy_checks: bool = True
    enable_event_bus: bool = True
    enable_lineage_tracking: bool = True
    graph_cache_size: int = 100
    worker_pool_size: int = 10
    request_queue_size: int = 1000
    health_check_interval: int = 10  # seconds
    metrics_export_interval: int = 30  # seconds
    route_config: RouteConfig = field(default_factory=RouteConfig)
    loop_config: LoopConfig = field(default_factory=LoopConfig)


@dataclass
class ExecutionContext:
    """Context for graph execution."""
    request_id: str
    tenant_id: str
    pillar: str
    agent_type: str
    aml_level: int
    lineage_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "pillar": self.pillar,
            "agent_type": self.agent_type,
            "aml_level": self.aml_level,
            "lineage_id": self.lineage_id,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat()
        }


class OrchestratorKernel:
    """Main orchestrator kernel coordinating all components."""
    
    def __init__(self, config: KernelConfig):
        self.config = config
        self.status = KernelStatus.STOPPED
        
        # Core components
        self._graph_registry = GraphRegistry()
        self._graph_compiler = GraphCompiler()
        self._graph_scheduler = GraphScheduler()
        self._request_router = RequestRouter(config.route_config)
        
        # Integration components
        self._policy_engine: Optional[Any] = None
        self._event_bus: Optional[Any] = None
        self._lineage_service: Optional[Any] = None
        self._observability: Optional[Any] = None
        
        # Execution state
        self._active_executions: Dict[str, ExecutionContext] = {}
        self._execution_history: List[Dict[str, Any]] = []
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        
        # Metrics
        self._metrics = {
            "requests_received": 0,
            "requests_completed": 0,
            "requests_failed": 0,
            "graphs_executed": 0,
            "policy_denials": 0,
            "average_latency_ms": 0.0
        }
    
    async def initialize(
        self,
        policy_engine: Optional[Any] = None,
        event_bus: Optional[Any] = None,
        lineage_service: Optional[Any] = None,
        observability: Optional[Any] = None
    ):
        """Initialize the kernel with external components."""
        logger.info("Initializing Orchestrator Kernel")
        self.status = KernelStatus.STARTING
        
        # Set up integrations
        if self.config.enable_policy_checks and policy_engine:
            self._policy_engine = policy_engine
            logger.info("Policy engine integration enabled")
        
        if self.config.enable_event_bus and event_bus:
            self._event_bus = event_bus
            await self._setup_event_handlers()
            logger.info("Event bus integration enabled")
        
        if self.config.enable_lineage_tracking and lineage_service:
            self._lineage_service = lineage_service
            logger.info("Lineage tracking enabled")
        
        if self.config.enable_observability and observability:
            self._observability = observability
            logger.info("Observability integration enabled")
        
        # Register node executors
        self._register_node_executors()
        
        # Start background tasks
        await self._start_background_tasks()
        
        self.status = KernelStatus.RUNNING
        logger.info("Orchestrator Kernel initialized successfully")
    
    async def shutdown(self):
        """Shutdown the kernel."""
        logger.info("Shutting down Orchestrator Kernel")
        self.status = KernelStatus.STOPPING
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self.status = KernelStatus.STOPPED
        logger.info("Orchestrator Kernel shutdown complete")
    
    def _register_node_executors(self):
        """Register executors for different node types."""
        self._graph_scheduler.register_executor(
            NodeType.LLM_CALL,
            self._execute_llm_node
        )
        self._graph_scheduler.register_executor(
            NodeType.TOOL_INVOCATION,
            self._execute_tool_node
        )
        self._graph_scheduler.register_executor(
            NodeType.CONDITIONAL_BRANCH,
            self._execute_conditional_node
        )
        self._graph_scheduler.register_executor(
            NodeType.PARALLEL_BRANCH,
            self._execute_parallel_node
        )
    
    async def _setup_event_handlers(self):
        """Set up event bus handlers."""
        if not self._event_bus:
            return
        
        # Subscribe to orchestration requests
        async def handle_orchestration_request(event: Event):
            await self._handle_event_request(event)
        
        # Would subscribe to appropriate topics
        # await self._event_bus.subscribe(Topics.ORCHESTRATION, handle_orchestration_request)
    
    async def _start_background_tasks(self):
        """Start background tasks."""
        # Health check task
        self._background_tasks.append(
            asyncio.create_task(self._health_check_loop())
        )
        
        # Metrics export task
        self._background_tasks.append(
            asyncio.create_task(self._metrics_export_loop())
        )
        
        # Queue processing task
        self._background_tasks.append(
            asyncio.create_task(self._queue_processing_loop())
        )
    
    async def register_graph(
        self,
        graph_definition: Union[str, Dict[str, Any]],
        format: str = "yaml"
    ) -> str:
        """Register a new graph definition."""
        # Compile graph
        if format == "yaml":
            graph = self._graph_compiler.compile_yaml(graph_definition)
        else:
            graph = self._graph_compiler.compile_python(graph_definition)
        
        # Register in registry
        version = self._graph_registry.register_graph(graph)
        
        logger.info(f"Registered graph: {graph.name} version {version}")
        return version
    
    async def handle_request(self, request: Request) -> Dict[str, Any]:
        """Handle incoming request."""
        self._metrics["requests_received"] += 1
        
        # Create span for observability
        span = None
        if self._observability:
            span = await self._observability.start_span(
                name="orchestrator.handle_request",
                trace_id=request.lineage_id or str(uuid.uuid4()),
                attributes={
                    "request_id": request.id,
                    "tenant_id": request.tenant_id,
                    "pillar": request.pillar,
                    "agent_type": request.agent_type,
                    "aml_level": request.aml_level
                }
            )
        
        try:
            # Create execution context
            context = ExecutionContext(
                request_id=request.id,
                tenant_id=request.tenant_id,
                pillar=request.pillar,
                agent_type=request.agent_type,
                aml_level=request.aml_level,
                lineage_id=request.lineage_id or str(uuid.uuid4()),
                metadata=request.metadata
            )
            
            # Track active execution
            self._active_executions[context.request_id] = context
            
            # Route request to worker
            worker = await self._request_router.route_request(request)
            
            if not worker:
                raise Exception("No available worker for request")
            
            # Execute on worker
            result = await self._execute_on_worker(worker, request, context)
            
            self._metrics["requests_completed"] += 1
            
            # Record execution history
            self._execution_history.append({
                "request_id": context.request_id,
                "status": "completed",
                "worker": worker.name,
                "duration_ms": (datetime.now() - context.start_time).total_seconds() * 1000,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            self._metrics["requests_failed"] += 1
            logger.error(f"Request handling failed: {e}")
            
            if span:
                await self._observability.record_error(span, e)
            
            # Record failure
            self._execution_history.append({
                "request_id": request.id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            raise
        
        finally:
            # Clean up
            if context.request_id in self._active_executions:
                del self._active_executions[context.request_id]
            
            if span:
                await self._observability.end_span(span)
    
    async def _execute_on_worker(
        self,
        worker: WorkerNode,
        request: Request,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute request on worker."""
        # Get graph for execution
        graph_name = f"{request.pillar}_{request.agent_type}"
        graph = self._graph_registry.get_graph(graph_name)
        
        if not graph:
            # Use default graph or create simple one
            graph = await self._create_default_graph(request)
        
        # Create ReAct loop with policy hooks
        policy_hooks = []
        
        # Add AML policy hook
        aml_hook = AMLPolicyHook(
            aml_level=context.aml_level,
            caps=self._get_aml_caps(context.pillar, context.aml_level)
        )
        policy_hooks.append(aml_hook)
        
        # Add OPA policy hook if available
        if self._policy_engine:
            # Would integrate with actual policy engine
            opa_hook = OPAPolicyHook()
            policy_hooks.append(opa_hook)
        
        # Configure ReAct loop
        loop_config = LoopConfig(
            policy_hooks=policy_hooks,
            available_tools=self._get_available_tools(context.pillar)
        )
        
        react_loop = ReactLoop(loop_config)
        
        # Set LLM handler
        react_loop.set_llm_handler(self._create_llm_handler(worker))
        
        # Execute graph with ReAct loop
        execution_context = {
            "request": request.to_dict(),
            "context": context.to_dict(),
            "react_loop": react_loop
        }
        
        result = await self._graph_scheduler.execute_graph(
            graph=graph,
            context=execution_context
        )
        
        self._metrics["graphs_executed"] += 1
        
        return result
    
    async def _create_default_graph(self, request: Request) -> ExecutionGraph:
        """Create default graph for request."""
        # Simple think-act-observe graph
        graph_def = {
            "name": f"default_{request.pillar}_{request.agent_type}",
            "version": "1.0.0",
            "nodes": [
                {
                    "id": "think",
                    "name": "Think",
                    "type": "llm_call",
                    "config": {"prompt": "Analyze the request and plan actions"}
                },
                {
                    "id": "act",
                    "name": "Act",
                    "type": "tool_invocation",
                    "config": {"tool": "execute_action"}
                },
                {
                    "id": "observe",
                    "name": "Observe",
                    "type": "llm_call",
                    "config": {"prompt": "Analyze results and determine next steps"}
                }
            ],
            "edges": [
                {"from": "think", "to": "act"},
                {"from": "act", "to": "observe"}
            ],
            "entry_node": "think"
        }
        
        return self._graph_compiler.compile_python(graph_def)
    
    def _get_aml_caps(self, pillar: str, aml_level: int) -> Dict[str, Any]:
        """Get AML capability caps for pillar."""
        # Example caps - would be configured per deployment
        caps = {
            "customer_success": {
                "create_refund": {"max_amount": 100 if aml_level <= 3 else 500},
                "send_email": {"max_per_hour": 10 if aml_level <= 2 else 100}
            },
            "growth_engine": {
                "adjust_pricing": {"max_discount": 0.1 if aml_level <= 3 else 0.2},
                "create_campaign": {"max_budget": 1000 if aml_level <= 3 else 10000}
            }
        }
        
        return caps.get(pillar, {})
    
    def _get_available_tools(self, pillar: str) -> Dict[str, Callable]:
        """Get available tools for pillar."""
        # Mock tools for demo
        async def mock_tool(**kwargs):
            return {"status": "success", "result": "Tool executed"}
        
        # Would return actual tool implementations
        return {
            "create_refund": mock_tool,
            "send_email": mock_tool,
            "query_database": mock_tool,
            "call_api": mock_tool
        }
    
    def _create_llm_handler(self, worker: WorkerNode) -> Callable:
        """Create LLM handler for worker."""
        async def llm_handler(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
            # Mock LLM response
            # In production, would call actual LLM service on worker
            return {
                "thought": "I need to analyze the customer's request",
                "reasoning": "The customer is asking for a refund",
                "action": "create_refund",
                "parameters": {"amount": 50, "reason": "Service issue"},
                "confidence": 0.9
            }
        
        return llm_handler
    
    async def _execute_llm_node(
        self,
        node: GraphNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute LLM node."""
        react_loop = context.get("react_loop")
        if not react_loop:
            raise ValueError("No ReAct loop in context")
        
        # Execute through ReAct loop
        prompt = node.config.get("prompt", "")
        result = await react_loop.run(prompt, context)
        
        return {"react_state": result.to_dict()}
    
    async def _execute_tool_node(
        self,
        node: GraphNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool invocation node."""
        tool_name = node.config.get("tool", "")
        tool_params = inputs.get("parameters", {})
        
        # Get tool handler
        tools = self._get_available_tools(context.get("context", {}).get("pillar", ""))
        tool_handler = tools.get(tool_name)
        
        if not tool_handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Execute tool
        result = await tool_handler(**tool_params, context=context)
        
        return {"tool_result": result}
    
    async def _execute_conditional_node(
        self,
        node: GraphNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute conditional branch node."""
        condition = node.config.get("condition", "")
        
        # Evaluate condition
        # Simplified for demo - would use actual expression evaluator
        if condition == "success":
            branch = inputs.get("status") == "success"
        else:
            branch = True
        
        return {"branch_taken": branch}
    
    async def _execute_parallel_node(
        self,
        node: GraphNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute parallel branch node."""
        # Parallel execution handled by graph scheduler
        return {"parallel_started": True}
    
    async def _handle_event_request(self, event: Event):
        """Handle request from event bus."""
        # Convert event to request
        request = Request(
            tenant_id=event.metadata.tags.get("tenant_id", ""),
            pillar=event.metadata.tags.get("pillar", ""),
            agent_type=event.metadata.tags.get("agent_type", ""),
            aml_level=int(event.metadata.tags.get("aml_level", 0)),
            payload=event.payload,
            lineage_id=event.metadata.trace_id
        )
        
        # Handle request
        try:
            result = await self.handle_request(request)
            
            # Publish result event
            if self._event_bus:
                result_event = Event(
                    event_type=EventType.TASK_COMPLETE,
                    metadata=EventMetadata(
                        source_pillar="orchestrator_kernel",
                        trace_id=request.lineage_id
                    ),
                    payload=result
                )
                await self._event_bus.publish(Topics.AUDIT, result_event)
        
        except Exception as e:
            logger.error(f"Failed to handle event request: {e}")
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while self.status == KernelStatus.RUNNING:
            try:
                await self._request_router.health_check()
                
                # Check kernel health
                pool_stats = self._request_router.get_routing_stats()
                if pool_stats["pool_stats"]["total_workers"] == 0:
                    self.status = KernelStatus.DEGRADED
                else:
                    self.status = KernelStatus.RUNNING
                
                await asyncio.sleep(self.config.health_check_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _metrics_export_loop(self):
        """Background metrics export loop."""
        while self.status == KernelStatus.RUNNING:
            try:
                # Export metrics
                if self._observability:
                    await self._observability.record_metrics(self._metrics)
                
                # Log summary
                logger.info(f"Kernel metrics: {self._metrics}")
                
                await asyncio.sleep(self.config.metrics_export_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics export error: {e}")
    
    async def _queue_processing_loop(self):
        """Background queue processing loop."""
        while self.status == KernelStatus.RUNNING:
            try:
                await self._request_router.process_queued_requests()
                await asyncio.sleep(1)  # Check every second
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
    
    def get_kernel_status(self) -> Dict[str, Any]:
        """Get comprehensive kernel status."""
        routing_stats = self._request_router.get_routing_stats()
        
        return {
            "status": self.status.value,
            "metrics": self._metrics,
            "active_executions": len(self._active_executions),
            "registered_graphs": len(self._graph_registry._graphs),
            "routing_stats": routing_stats,
            "integrations": {
                "policy_engine": self._policy_engine is not None,
                "event_bus": self._event_bus is not None,
                "lineage_service": self._lineage_service is not None,
                "observability": self._observability is not None
            },
            "timestamp": datetime.now().isoformat()
        }