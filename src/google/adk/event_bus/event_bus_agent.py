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

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from pydantic import Field

from ..agents.invocation_context import InvocationContext
from ..agents.llm_agent import LlmAgent
from ..events.event import Event
from ..models import types
from ..tools.function_tool import FunctionTool
from .base_event_bus import BaseEventBus, EventMessage, EventPriority

logger = logging.getLogger(__name__)


class EventBusAgent(LlmAgent):
  """Agent that communicates via an event bus.
  
  This agent can:
  - Publish events to notify other agents
  - Subscribe to events from other agents
  - Coordinate multi-agent workflows via events
  - Implement request-reply patterns
  """
  
  event_bus: BaseEventBus = Field(
      description="Event bus for inter-agent communication"
  )
  
  agent_topics: List[str] = Field(
      default_factory=list,
      description="Topics this agent subscribes to",
  )
  
  publish_topics: List[str] = Field(
      default_factory=list,
      description="Topics this agent can publish to",
  )
  
  event_handlers: Dict[str, Any] = Field(
      default_factory=dict,
      description="Custom event handlers by event type",
      exclude=True,
  )
  
  auto_subscribe: bool = Field(
      default=True,
      description="Automatically subscribe on initialization",
  )
  
  _subscriptions: List[Any] = []
  
  def __init__(self, **kwargs):
    """Initialize the event bus agent."""
    super().__init__(**kwargs)
    
    # Add event bus tools
    self._add_event_bus_tools()
    
    # Set up event handlers
    self._setup_default_handlers()
    
    # Auto-subscribe if enabled
    if self.auto_subscribe:
      asyncio.create_task(self._auto_subscribe())
  
  def _add_event_bus_tools(self):
    """Add tools for event bus operations."""
    event_tools = [
        FunctionTool(
            name="publish_event",
            description="Publish an event to other agents",
            func=self._publish_event_tool,
        ),
        FunctionTool(
            name="broadcast_status",
            description="Broadcast agent status update",
            func=self._broadcast_status_tool,
        ),
        FunctionTool(
            name="request_from_agent",
            description="Send request to another agent and wait for response",
            func=self._request_from_agent_tool,
        ),
        FunctionTool(
            name="get_event_history",
            description="Get historical events from the bus",
            func=self._get_event_history_tool,
        ),
        FunctionTool(
            name="coordinate_task",
            description="Coordinate a task across multiple agents",
            func=self._coordinate_task_tool,
        ),
    ]
    
    if self.tools:
      self.tools.extend(event_tools)
    else:
      self.tools = event_tools
  
  def _setup_default_handlers(self):
    """Set up default event handlers."""
    # Default handlers
    self.event_handlers.update({
        "agent.request": self._handle_agent_request,
        "agent.status_request": self._handle_status_request,
        "coordination.task": self._handle_coordination_task,
    })
  
  async def _auto_subscribe(self):
    """Automatically subscribe to configured topics."""
    if not self.agent_topics:
      # Default topics based on agent name
      self.agent_topics = [
          f"agent.{self.name}",
          "agent.broadcast",
          "coordination.all",
      ]
    
    for topic in self.agent_topics:
      subscription = await self.event_bus.subscribe(
          subscriber_id=self.name,
          topics=[topic],
          handler=self._handle_event,
      )
      self._subscriptions.append(subscription)
    
    logger.info(f"Agent {self.name} subscribed to: {', '.join(self.agent_topics)}")
  
  async def _handle_event(self, event: EventMessage):
    """Handle incoming events."""
    logger.debug(
        f"Agent {self.name} received event: {event.event_type} "
        f"from {event.source}"
    )
    
    # Look for custom handler
    handler = self.event_handlers.get(event.event_type)
    
    if handler:
      try:
        if asyncio.iscoroutinefunction(handler):
          await handler(event)
        else:
          handler(event)
      except Exception as e:
        logger.error(f"Error handling event {event.id}: {e}")
    else:
      # Default handling - log it
      logger.info(
          f"No handler for event type {event.event_type}, "
          f"payload: {event.payload}"
      )
  
  async def _handle_agent_request(self, event: EventMessage):
    """Handle request from another agent."""
    if not event.reply_to:
      logger.warning("Request event missing reply_to topic")
      return
    
    # Process request
    request_type = event.payload.get("request_type")
    request_data = event.payload.get("data", {})
    
    # Generate response based on request type
    response_data = {
        "request_id": event.id,
        "status": "success",
        "data": f"Processed {request_type} request",
    }
    
    # Send reply
    await self.event_bus.publish(
        topic=event.reply_to,
        event_type="agent.response",
        source=self.name,
        payload=response_data,
        correlation_id=event.correlation_id,
    )
  
  async def _handle_status_request(self, event: EventMessage):
    """Handle status request."""
    status = {
        "agent_name": self.name,
        "status": "active",
        "subscribed_topics": self.agent_topics,
        "capabilities": [tool.name for tool in self.tools[:5]],  # First 5 tools
        "metadata": {
            "model": getattr(self, "model", "unknown"),
            "sub_agents": len(self.sub_agents) if self.sub_agents else 0,
        },
    }
    
    # Publish status
    await self.event_bus.publish(
        topic="agent.status",
        event_type="agent.status_update",
        source=self.name,
        payload=status,
        correlation_id=event.correlation_id,
    )
  
  async def _handle_coordination_task(self, event: EventMessage):
    """Handle coordination task."""
    task = event.payload.get("task")
    assigned_agents = event.payload.get("assigned_agents", [])
    
    if self.name in assigned_agents:
      # This agent is assigned to the task
      logger.info(f"Agent {self.name} assigned to task: {task['name']}")
      
      # Simulate task processing
      await asyncio.sleep(1)
      
      # Report completion
      await self.event_bus.publish(
          topic="coordination.status",
          event_type="task.completed",
          source=self.name,
          payload={
              "task_id": task.get("id"),
              "task_name": task.get("name"),
              "agent": self.name,
              "result": "Task completed successfully",
          },
          correlation_id=event.correlation_id,
      )
  
  async def _run_async_impl(
      self, invocation_context: InvocationContext
  ) -> AsyncGenerator[Event, None]:
    """Run with event bus integration."""
    # Publish agent activation event
    await self.event_bus.publish(
        topic="agent.lifecycle",
        event_type="agent.activated",
        source=self.name,
        payload={
            "session_id": invocation_context.session.id,
            "user_id": invocation_context.session.user_id,
        },
    )
    
    try:
      # Normal agent execution
      async for event in super()._run_async_impl(invocation_context):
        yield event
    finally:
      # Publish deactivation event
      await self.event_bus.publish(
          topic="agent.lifecycle",
          event_type="agent.deactivated",
          source=self.name,
          payload={
              "session_id": invocation_context.session.id,
          },
      )
  
  # Tool implementations
  
  async def _publish_event_tool(
      self,
      topic: str,
      event_type: str,
      payload: Dict[str, Any],
      priority: str = "normal",
  ) -> Dict[str, Any]:
    """Tool to publish an event."""
    if topic not in self.publish_topics and not topic.startswith(f"agent.{self.name}"):
      return {
          "success": False,
          "error": f"Not authorized to publish to topic: {topic}",
      }
    
    event = await self.event_bus.publish(
        topic=topic,
        event_type=event_type,
        source=self.name,
        payload=payload,
        priority=EventPriority(priority),
    )
    
    return {
        "success": True,
        "event_id": event.id,
        "topic": topic,
        "event_type": event_type,
    }
  
  async def _broadcast_status_tool(self, status: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to broadcast status update."""
    event = await self.event_bus.publish(
        topic="agent.broadcast",
        event_type="agent.status_update",
        source=self.name,
        payload={
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        },
    )
    
    return {
        "success": True,
        "event_id": event.id,
        "broadcasted_to": "all agents",
    }
  
  async def _request_from_agent_tool(
      self,
      target_agent: str,
      request_type: str,
      data: Dict[str, Any],
      timeout: float = 10.0,
  ) -> Dict[str, Any]:
    """Tool to send request to another agent."""
    # Send request
    response = await self.event_bus.request_reply(
        topic=f"agent.{target_agent}",
        event_type="agent.request",
        source=self.name,
        payload={
            "request_type": request_type,
            "data": data,
        },
        reply_timeout=timeout,
    )
    
    if response:
      return {
          "success": True,
          "response": response.payload,
          "from_agent": response.source,
      }
    else:
      return {
          "success": False,
          "error": f"No response from {target_agent} within {timeout}s",
      }
  
  async def _get_event_history_tool(
      self,
      topic: Optional[str] = None,
      event_type: Optional[str] = None,
      limit: int = 10,
  ) -> List[Dict[str, Any]]:
    """Tool to get event history."""
    events = await self.event_bus.get_event_history(
        topic=topic,
        event_type=event_type,
        limit=limit,
    )
    
    return [
        {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "topic": event.topic,
            "event_type": event.event_type,
            "source": event.source,
            "payload": event.payload,
        }
        for event in events
    ]
  
  async def _coordinate_task_tool(
      self,
      task_name: str,
      assigned_agents: List[str],
      task_data: Dict[str, Any],
  ) -> Dict[str, Any]:
    """Tool to coordinate a task across multiple agents."""
    task_id = str(uuid4())
    
    # Publish coordination event
    event = await self.event_bus.publish(
        topic="coordination.all",
        event_type="coordination.task",
        source=self.name,
        payload={
            "task": {
                "id": task_id,
                "name": task_name,
                "data": task_data,
            },
            "assigned_agents": assigned_agents,
            "coordinator": self.name,
        },
        priority=EventPriority.HIGH,
    )
    
    # Wait for completion events
    completed_agents = []
    start_time = asyncio.get_event_loop().time()
    timeout = 30.0  # 30 second timeout
    
    while len(completed_agents) < len(assigned_agents):
      if asyncio.get_event_loop().time() - start_time > timeout:
        break
      
      # Wait for completion event
      completion = await self.event_bus.wait_for_event(
          topic="coordination.status",
          event_type="task.completed",
          correlation_id=event.correlation_id,
          timeout=5.0,
      )
      
      if completion and completion.payload.get("task_id") == task_id:
        completed_agents.append(completion.source)
    
    return {
        "task_id": task_id,
        "task_name": task_name,
        "assigned_agents": assigned_agents,
        "completed_agents": completed_agents,
        "success": len(completed_agents) == len(assigned_agents),
        "completion_rate": f"{len(completed_agents)}/{len(assigned_agents)}",
    }
  
  async def cleanup(self):
    """Clean up event bus subscriptions."""
    for subscription in self._subscriptions:
      await self.event_bus.unsubscribe(subscription.id)
    self._subscriptions.clear()