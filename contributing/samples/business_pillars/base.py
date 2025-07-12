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

"""Base classes for Business Pillar Agents."""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from pydantic import BaseModel, Field

# Import our existing infrastructure
if TYPE_CHECKING:
  from ..control_plane.control_plane_agent import ControlPlaneAgent
  from ..control_plane.treasury import Treasury
  from ..control_plane.policy_engine import PolicyEngine
  from ..data_mesh.event_bus import EventBus
  from ..data_mesh.lineage_service import LineageService

logger = logging.getLogger(__name__)


class AgentRole(Enum):
  """Agent roles within each business pillar."""
  PLANNER = "planner"      # Strategic planning and coordination
  WORKER = "worker"        # Execution and implementation
  CRITIC = "critic"        # Quality assurance and validation
  GUARD = "guard"         # Security and compliance monitoring


class PillarType(Enum):
  """Business pillar types."""
  MISSION_GOVERNANCE = "Mission & Governance"
  PRODUCT_EXPERIENCE = "Product & Experience"
  GROWTH_ENGINE = "Growth Engine"
  CUSTOMER_SUCCESS = "Customer Success"
  RESOURCE_SUPPLY = "Resource & Supply"
  PEOPLE_CULTURE = "People & Culture"
  INTELLIGENCE_IMPROVEMENT = "Intelligence & Improvement"
  PLATFORM_INFRASTRUCTURE = "Platform & Infra"


@dataclass
class WorkflowStep:
  """Individual step in a pillar workflow."""
  step_id: str
  agent_role: AgentRole
  action: str
  inputs: Dict[str, Any]
  outputs: Optional[Dict[str, Any]] = None
  status: str = "pending"  # pending, running, completed, failed
  start_time: Optional[datetime] = None
  end_time: Optional[datetime] = None
  error: Optional[str] = None
  
  def start(self):
    """Mark step as started."""
    self.status = "running"
    self.start_time = datetime.now()
  
  def complete(self, outputs: Dict[str, Any]):
    """Mark step as completed."""
    self.status = "completed"
    self.end_time = datetime.now()
    self.outputs = outputs
  
  def fail(self, error: str):
    """Mark step as failed."""
    self.status = "failed"
    self.end_time = datetime.now()
    self.error = error


@dataclass
class WorkflowResult:
  """Result of a pillar workflow execution."""
  workflow_id: str
  pillar: PillarType
  steps: List[WorkflowStep]
  status: str = "running"
  start_time: datetime = field(default_factory=datetime.now)
  end_time: Optional[datetime] = None
  final_output: Optional[Dict[str, Any]] = None
  trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
  
  def add_step(self, step: WorkflowStep):
    """Add a workflow step."""
    self.steps.append(step)
  
  def complete(self, final_output: Dict[str, Any]):
    """Mark workflow as completed."""
    self.status = "completed"
    self.end_time = datetime.now()
    self.final_output = final_output
  
  def fail(self, error: str):
    """Mark workflow as failed."""
    self.status = "failed"
    self.end_time = datetime.now()
    # Find the failed step
    for step in self.steps:
      if step.status == "failed":
        self.final_output = {"error": error, "failed_step": step.step_id}
        break


class BusinessPillarAgent(ABC):
  """Base class for all business pillar agents."""
  
  def __init__(
    self,
    agent_id: str,
    role: AgentRole,
    pillar: PillarType,
    control_plane_agent: Optional["ControlPlaneAgent"] = None,
    event_bus: Optional["EventBus"] = None,
    lineage_service: Optional["LineageService"] = None
  ):
    self.agent_id = agent_id
    self.role = role
    self.pillar = pillar
    self.control_plane_agent = control_plane_agent
    self.event_bus = event_bus
    self.lineage_service = lineage_service
    self._tools: Dict[str, Callable] = {}
    self._active_workflows: Dict[str, WorkflowResult] = {}
  
  @abstractmethod
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute a task for this agent."""
    pass
  
  @abstractmethod
  def get_capabilities(self) -> List[str]:
    """Get list of capabilities this agent provides."""
    pass
  
  def register_tool(self, name: str, tool_func: Callable, cost: float = 0.0):
    """Register a tool for this agent."""
    self._tools[name] = tool_func
    
    # Register with control plane if available
    if self.control_plane_agent:
      # Add cost metadata for budget tracking
      if hasattr(tool_func, '__annotations__'):
        tool_func.__cost__ = cost
  
  async def call_tool(
    self,
    tool_name: str,
    args: Dict[str, Any],
    trace_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Call a tool with policy enforcement."""
    if tool_name not in self._tools:
      raise ValueError(f"Tool {tool_name} not registered for agent {self.agent_id}")
    
    tool_func = self._tools[tool_name]
    
    # Use control plane if available for policy enforcement
    if self.control_plane_agent:
      try:
        # This will enforce policies, budgets, and AML restrictions
        result = await self.control_plane_agent._call_tool_with_enforcement(
          tool_name, args, trace_id
        )
        
        # Track lineage if available
        if self.lineage_service and trace_id:
          await self.lineage_service.track_tool_invocation(
            agent_id=self.agent_id,
            tool_name=tool_name,
            trace_id=trace_id,
            inputs=args,
            outputs=result,
            pillar=self.pillar.value
          )
        
        return result
        
      except Exception as e:
        logger.error(f"Tool call failed: {tool_name} - {e}")
        raise
    else:
      # Direct tool call without control plane
      try:
        if asyncio.iscoroutinefunction(tool_func):
          result = await tool_func(**args)
        else:
          result = tool_func(**args)
        
        return {"result": result, "success": True}
        
      except Exception as e:
        logger.error(f"Direct tool call failed: {tool_name} - {e}")
        return {"error": str(e), "success": False}
  
  async def publish_event(
    self,
    event_type: str,
    payload: Dict[str, Any],
    target_pillar: Optional[str] = None,
    trace_id: Optional[str] = None
  ):
    """Publish an event to the data mesh."""
    if not self.event_bus:
      logger.warning("No event bus configured - cannot publish event")
      return
    
    from ..data_mesh.event_bus import Event, EventMetadata, EventPriority, EventType
    
    # Create event
    event = Event(
      event_type=EventType.CUSTOM,
      metadata=EventMetadata(
        source_pillar=self.pillar.value,
        source_agent=self.agent_id,
        target_pillar=target_pillar,
        priority=EventPriority.NORMAL,
        trace_id=trace_id or str(uuid.uuid4()),
        tags={
          "agent_role": self.role.value,
          "event_type": event_type
        }
      ),
      payload=payload
    )
    
    # Determine topic
    if target_pillar:
      from ..data_mesh.event_bus import Topics
      topic = Topics.for_pillar(target_pillar)
    else:
      topic = f"pillar.{self.pillar.value.lower().replace(' ', '_')}"
    
    # Publish event
    success = await self.event_bus.publish(topic, event)
    if success:
      logger.info(f"Published event {event_type} from {self.agent_id}")
    else:
      logger.error(f"Failed to publish event {event_type}")
  
  async def start_workflow(
    self,
    workflow_id: str,
    description: str
  ) -> WorkflowResult:
    """Start a new workflow."""
    workflow = WorkflowResult(
      workflow_id=workflow_id,
      pillar=self.pillar
    )
    
    self._active_workflows[workflow_id] = workflow
    
    # Publish workflow started event
    await self.publish_event(
      "workflow.started",
      {
        "workflow_id": workflow_id,
        "description": description,
        "agent_id": self.agent_id,
        "role": self.role.value
      },
      trace_id=workflow.trace_id
    )
    
    return workflow
  
  async def complete_workflow(
    self,
    workflow_id: str,
    final_output: Dict[str, Any]
  ):
    """Complete a workflow."""
    if workflow_id not in self._active_workflows:
      raise ValueError(f"Unknown workflow: {workflow_id}")
    
    workflow = self._active_workflows[workflow_id]
    workflow.complete(final_output)
    
    # Publish workflow completed event
    await self.publish_event(
      "workflow.completed",
      {
        "workflow_id": workflow_id,
        "final_output": final_output,
        "duration_seconds": (
          workflow.end_time - workflow.start_time
        ).total_seconds(),
        "steps_count": len(workflow.steps)
      },
      trace_id=workflow.trace_id
    )
    
    # Remove from active workflows
    del self._active_workflows[workflow_id]
  
  def get_status(self) -> Dict[str, Any]:
    """Get agent status."""
    return {
      "agent_id": self.agent_id,
      "role": self.role.value,
      "pillar": self.pillar.value,
      "tools_registered": list(self._tools.keys()),
      "active_workflows": len(self._active_workflows),
      "capabilities": self.get_capabilities(),
      "has_control_plane": self.control_plane_agent is not None,
      "has_event_bus": self.event_bus is not None,
      "has_lineage": self.lineage_service is not None
    }


class BusinessPillar(ABC):
  """Base class for organizing agents within a business pillar."""
  
  def __init__(
    self,
    pillar_type: PillarType,
    event_bus: Optional["EventBus"] = None,
    lineage_service: Optional["LineageService"] = None,
    treasury: Optional["Treasury"] = None,
    policy_engine: Optional["PolicyEngine"] = None
  ):
    self.pillar_type = pillar_type
    self.event_bus = event_bus
    self.lineage_service = lineage_service
    self.treasury = treasury
    self.policy_engine = policy_engine
    self.agents: Dict[AgentRole, BusinessPillarAgent] = {}
    self._workflows: Dict[str, WorkflowResult] = {}
  
  def register_agent(self, agent: BusinessPillarAgent):
    """Register an agent with this pillar."""
    self.agents[agent.role] = agent
    logger.info(f"Registered {agent.role.value} agent for {self.pillar_type.value}")
  
  def get_agent(self, role: AgentRole) -> Optional[BusinessPillarAgent]:
    """Get an agent by role."""
    return self.agents.get(role)
  
  @abstractmethod
  async def execute_workflow(
    self,
    workflow_type: str,
    inputs: Dict[str, Any],
    requester: Optional[str] = None
  ) -> WorkflowResult:
    """Execute a pillar-specific workflow."""
    pass
  
  @abstractmethod
  def get_workflow_types(self) -> List[str]:
    """Get supported workflow types."""
    pass
  
  async def cross_pillar_request(
    self,
    target_pillar: str,
    request_type: str,
    payload: Dict[str, Any],
    trace_id: Optional[str] = None
  ):
    """Make a request to another pillar."""
    if not self.event_bus:
      raise ValueError("Event bus required for cross-pillar requests")
    
    from ..data_mesh.event_bus import Event, EventMetadata, EventPriority, EventType
    
    event = Event(
      event_type=EventType.CUSTOM,
      metadata=EventMetadata(
        source_pillar=self.pillar_type.value,
        source_agent=f"{self.pillar_type.value}_coordinator",
        target_pillar=target_pillar,
        priority=EventPriority.HIGH,
        trace_id=trace_id or str(uuid.uuid4()),
        tags={"request_type": request_type}
      ),
      payload=payload
    )
    
    from ..data_mesh.event_bus import Topics
    topic = Topics.for_pillar(target_pillar)
    
    success = await self.event_bus.publish(topic, event)
    if not success:
      raise RuntimeError(f"Failed to send request to {target_pillar}")
  
  def get_status(self) -> Dict[str, Any]:
    """Get pillar status."""
    return {
      "pillar_type": self.pillar_type.value,
      "agents": {
        role.value: agent.get_status()
        for role, agent in self.agents.items()
      },
      "active_workflows": len(self._workflows),
      "workflow_types": self.get_workflow_types()
    }


class PillarRegistry:
  """Registry for managing all business pillars."""
  
  def __init__(self):
    self.pillars: Dict[PillarType, BusinessPillar] = {}
    self._cross_pillar_handlers: Dict[str, Callable] = {}
  
  def register_pillar(self, pillar: BusinessPillar):
    """Register a business pillar."""
    self.pillars[pillar.pillar_type] = pillar
    logger.info(f"Registered {pillar.pillar_type.value} pillar")
  
  def get_pillar(self, pillar_type: PillarType) -> Optional[BusinessPillar]:
    """Get a pillar by type."""
    return self.pillars.get(pillar_type)
  
  def register_cross_pillar_handler(
    self,
    event_type: str,
    handler: Callable
  ):
    """Register a handler for cross-pillar events."""
    self._cross_pillar_handlers[event_type] = handler
  
  async def execute_cross_pillar_workflow(
    self,
    primary_pillar: PillarType,
    workflow_type: str,
    inputs: Dict[str, Any],
    involved_pillars: List[PillarType]
  ) -> Dict[str, Any]:
    """Execute a workflow involving multiple pillars."""
    trace_id = str(uuid.uuid4())
    results = {}
    
    # Start with primary pillar
    primary = self.get_pillar(primary_pillar)
    if not primary:
      raise ValueError(f"Primary pillar {primary_pillar.value} not registered")
    
    logger.info(f"Starting cross-pillar workflow {workflow_type} with trace {trace_id}")
    
    try:
      # Execute primary workflow
      primary_result = await primary.execute_workflow(
        workflow_type, inputs, f"cross_pillar_{trace_id}"
      )
      results[primary_pillar.value] = primary_result.final_output
      
      # Coordinate with other pillars
      for pillar_type in involved_pillars:
        if pillar_type == primary_pillar:
          continue
        
        pillar = self.get_pillar(pillar_type)
        if pillar:
          # Send coordination request
          await primary.cross_pillar_request(
            target_pillar=pillar_type.value,
            request_type=f"coordinate_{workflow_type}",
            payload={
              "primary_result": primary_result.final_output,
              "trace_id": trace_id
            },
            trace_id=trace_id
          )
      
      return {
        "success": True,
        "trace_id": trace_id,
        "results": results
      }
      
    except Exception as e:
      logger.error(f"Cross-pillar workflow failed: {e}")
      return {
        "success": False,
        "trace_id": trace_id,
        "error": str(e)
      }
  
  def get_system_status(self) -> Dict[str, Any]:
    """Get status of all pillars."""
    return {
      "pillars": {
        pillar_type.value: pillar.get_status()
        for pillar_type, pillar in self.pillars.items()
      },
      "total_pillars": len(self.pillars),
      "cross_pillar_handlers": list(self._cross_pillar_handlers.keys())
    }