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

import logging
from typing import Any, Dict, List, Optional, Set

from pydantic import Field

from ..agents.base_agent import BaseAgent
from ..agents.invocation_context import InvocationContext
from ..agents.llm_agent import LlmAgent
from ..events.event import Event
from ..models import types
from ..tools.base_tool import BaseTool
from ..tools.function_tool import FunctionTool
from .policy_engine import PolicyDecision, PolicyEngine
from .policy_types import Policy, PolicyContext, PolicyType

logger = logging.getLogger(__name__)


class ControlPlaneAgent(LlmAgent):
  """Control plane agent that manages other agents with policy enforcement.
  
  This agent acts as a governance layer, enforcing policies before
  delegating work to sub-agents. It provides centralized control over:
  - Resource access and usage
  - Security policies
  - Compliance requirements
  - Rate limiting
  - Cost controls
  """
  
  policy_engine: PolicyEngine = Field(
      default_factory=PolicyEngine,
      description="Policy engine for enforcing governance rules",
  )
  
  enforce_policies: bool = Field(
      default=True, description="Whether to enforce policies"
  )
  
  policy_types_to_check: Optional[Set[PolicyType]] = Field(
      default=None,
      description="Specific policy types to check (None = all)",
  )
  
  audit_all_actions: bool = Field(
      default=True, description="Whether to audit all actions"
  )
  
  def __init__(self, **kwargs):
    """Initialize the control plane agent."""
    # Set default instruction if not provided
    if "instruction" not in kwargs:
      kwargs["instruction"] = (
          "I am a control plane agent that manages and governs other agents. "
          "I enforce policies, ensure compliance, and coordinate work between "
          "specialized agents while maintaining security and resource controls."
      )
    
    # Initialize parent
    super().__init__(**kwargs)
    
    # Add control plane tools
    self._add_control_plane_tools()
  
  def _add_control_plane_tools(self):
    """Add tools for control plane operations."""
    control_tools = [
        FunctionTool(
            name="check_policies",
            description="Check if an action is allowed by policies",
            func=self._check_policies_tool,
        ),
        FunctionTool(
            name="list_active_policies",
            description="List all active policies",
            func=self._list_policies_tool,
        ),
        FunctionTool(
            name="get_policy_decision",
            description="Get detailed policy decision for an action",
            func=self._get_policy_decision_tool,
        ),
    ]
    
    # Add control tools to existing tools
    if self.tools:
      self.tools.extend(control_tools)
    else:
      self.tools = control_tools
  
  def register_policy(self, policy: Policy) -> None:
    """Register a policy with the control plane.
    
    Args:
        policy: The policy to register
    """
    self.policy_engine.register_policy(policy)
    logger.info(f"Registered policy: {policy.name}")
  
  def register_policies(self, policies: List[Policy]) -> None:
    """Register multiple policies.
    
    Args:
        policies: List of policies to register
    """
    for policy in policies:
      self.register_policy(policy)
  
  async def _run_async_impl(
      self, invocation_context: InvocationContext
  ) -> AsyncGenerator[Event, None]:
    """Run the control plane agent with policy enforcement.
    
    This method intercepts the normal agent flow to add policy checks
    before delegating to sub-agents or executing actions.
    """
    # Check policies before proceeding
    if self.enforce_policies:
      decision = await self._check_initial_policies(invocation_context)
      
      if not decision.allowed:
        # Generate policy denial event
        denial_message = self._format_policy_denial(decision)
        yield Event(
            invocation_id=invocation_context.invocation_id,
            author=self.name,
            content=types.Content(parts=[types.Part(text=denial_message)]),
        )
        return
    
    # Add policy enforcement to tool calls
    original_before_tool = self.before_tool_callback
    
    async def policy_enforced_before_tool(context):
      # Check tool usage policies
      tool_name = context.metadata.get("tool_name")
      if tool_name and self.enforce_policies:
        policy_context = PolicyContext(
            agent_name=self.name,
            user_id=invocation_context.session.user_id,
            session_id=invocation_context.session.id,
            action=f"tool_call:{tool_name}",
            metadata={"tool_name": tool_name},
        )
        
        decision = await self.policy_engine.evaluate(
            policy_context, self.policy_types_to_check
        )
        
        if not decision.allowed:
          # Modify context to prevent tool execution
          context.metadata["policy_blocked"] = True
          context.metadata["policy_reason"] = decision.blocking_policies[0].reason
      
      # Call original callback if exists
      if original_before_tool:
        return await original_before_tool(context)
    
    # Temporarily replace callback
    self.before_tool_callback = policy_enforced_before_tool
    
    try:
      # Delegate to parent implementation
      async for event in super()._run_async_impl(invocation_context):
        # Audit events if enabled
        if self.audit_all_actions:
          await self._audit_event(event, invocation_context)
        
        yield event
    finally:
      # Restore original callback
      self.before_tool_callback = original_before_tool
  
  async def _check_initial_policies(
      self, invocation_context: InvocationContext
  ) -> PolicyDecision:
    """Check initial policies when agent is invoked.
    
    Args:
        invocation_context: The invocation context
        
    Returns:
        PolicyDecision indicating if the invocation is allowed
    """
    policy_context = PolicyContext(
        agent_name=self.name,
        user_id=invocation_context.session.user_id,
        session_id=invocation_context.session.id,
        action="agent_invocation",
        metadata={
            "invocation_id": invocation_context.invocation_id,
            "authenticated": True,  # Assume authenticated if we got here
        },
    )
    
    decision = await self.policy_engine.evaluate(
        policy_context, self.policy_types_to_check
    )
    
    return decision
  
  def _format_policy_denial(self, decision: PolicyDecision) -> str:
    """Format a policy denial message.
    
    Args:
        decision: The policy decision
        
    Returns:
        Formatted denial message
    """
    messages = ["I cannot proceed with this request due to policy restrictions."]
    
    # Add specific policy reasons
    for policy_result in decision.blocking_policies:
      messages.append(f"\n- {policy_result.reason}")
    
    # Add recommendations
    if decision.recommendations:
      messages.append("\nRecommendations:")
      for rec in decision.recommendations:
        messages.append(f"- {rec}")
    
    return "\n".join(messages)
  
  async def _audit_event(
      self, event: Event, invocation_context: InvocationContext
  ) -> None:
    """Audit an event for compliance and monitoring.
    
    Args:
        event: The event to audit
        invocation_context: The invocation context
    """
    # Log event for audit trail
    logger.info(
        f"Audit: agent={self.name}, "
        f"user={invocation_context.session.user_id}, "
        f"session={invocation_context.session.id}, "
        f"author={event.author}, "
        f"type={event.type}"
    )
    
    # TODO: Implement persistent audit storage
  
  # Tool implementations
  async def _check_policies_tool(
      self, action: str, resource: Optional[str] = None, **kwargs
  ) -> Dict[str, Any]:
    """Tool to check if an action is allowed by policies."""
    # Get current context from somewhere (this is simplified)
    policy_context = PolicyContext(
        agent_name=self.name,
        user_id="current_user",  # Should get from context
        session_id="current_session",  # Should get from context
        action=action,
        resource=resource,
        metadata=kwargs,
    )
    
    decision = await self.policy_engine.evaluate(
        policy_context, self.policy_types_to_check
    )
    
    return {
        "allowed": decision.allowed,
        "reasons": [p.reason for p in decision.blocking_policies],
        "recommendations": decision.recommendations,
    }
  
  def _list_policies_tool(
      self, policy_type: Optional[str] = None
  ) -> List[Dict[str, Any]]:
    """Tool to list active policies."""
    policy_type_enum = PolicyType(policy_type) if policy_type else None
    policies = self.policy_engine.list_policies(
        policy_type=policy_type_enum, enabled_only=True
    )
    
    return [
        {
            "name": p.name,
            "type": p.policy_type,
            "priority": p.priority,
            "description": p.description,
        }
        for p in policies
    ]
  
  async def _get_policy_decision_tool(
      self, action: str, resource: Optional[str] = None, **kwargs
  ) -> Dict[str, Any]:
    """Tool to get detailed policy decision."""
    policy_context = PolicyContext(
        agent_name=self.name,
        user_id="current_user",  # Should get from context
        session_id="current_session",  # Should get from context
        action=action,
        resource=resource,
        metadata=kwargs,
    )
    
    decision = await self.policy_engine.evaluate(
        policy_context, self.policy_types_to_check, fail_fast=False
    )
    
    return {
        "allowed": decision.allowed,
        "evaluated_policies": [
            {
                "name": p.policy_name,
                "type": p.policy_type,
                "allowed": p.allowed,
                "reason": p.reason,
            }
            for p in decision.evaluated_policies
        ],
        "blocking_policies": [
            {
                "name": p.policy_name,
                "type": p.policy_type,
                "reason": p.reason,
            }
            for p in decision.blocking_policies
        ],
        "recommendations": decision.recommendations,
        "metadata": decision.metadata,
    }