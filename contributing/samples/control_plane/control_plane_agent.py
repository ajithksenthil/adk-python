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
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
  from .blockchain_treasury import BlockchainTreasury

from google.adk.agents import Agent
from google.adk.exceptions import ToolExecutionError
from google.adk.prompts import SystemInstructionStaticContext
from google.adk.runners import BaseRunner, InMemoryRunner, RunConfig
from google.adk.toolbox import Toolbox

from .aml_registry_enhanced import EnhancedAMLRegistry, AutonomyLevel
from .policy_engine import (
  LocalPolicyEngine,
  OPAPolicyEngine,
  PolicyContext,
  PolicyDecision,
  PolicyEngine,
  PolicyResult,
)
from .treasury import Treasury, Transaction
from .blockchain_treasury import BlockchainTreasury, WalletType

logger = logging.getLogger(__name__)


class PolicyEnforcedToolbox(Toolbox):
  """Toolbox wrapper that enforces policies on tool execution."""
  
  def __init__(
    self,
    original_toolbox: Toolbox,
    policy_engine: PolicyEngine,
    aml_registry: EnhancedAMLRegistry,
    treasury: Union[Treasury, "BlockchainTreasury"],
    agent_name: str,
    pillar: str,
  ):
    self._original_toolbox = original_toolbox
    self._policy_engine = policy_engine
    self._aml_registry = aml_registry
    self._treasury = treasury
    self._agent_name = agent_name
    self._pillar = pillar
    self._audit_log: List[Dict[str, Any]] = []
    
    # Copy tool definitions from original toolbox
    super().__init__()
    self._tools = original_toolbox._tools.copy()
  
  async def execute_tool(
    self,
    tool_name: str,
    arguments: Dict[str, Any],
    context: Optional[Any] = None
  ) -> Any:
    """Execute tool with policy enforcement."""
    # Get agent's autonomy profile (use agent_group format for enhanced registry)
    agent_group = f"{self._agent_name}_group"
    profile = await self._aml_registry.get_agent_profile(agent_group)
    if not profile:
      raise ToolExecutionError(
        f"Agent {self._agent_name} not registered in AML registry"
      )
    
    # Estimate cost if tool has cost metadata
    cost_estimate = self._estimate_tool_cost(tool_name, arguments)
    
    # Create policy context
    policy_context = PolicyContext(
      agent_name=self._agent_name,
      tool_name=tool_name,
      action="execute_tool",
      parameters=arguments,
      autonomy_level=profile.aml_level,
      cost_estimate=cost_estimate,
      metadata={
        "pillar": self._pillar,
        "tool_metadata": self._tools.get(tool_name, {})
      }
    )
    
    # Evaluate policies
    policy_result = await self._policy_engine.evaluate(policy_context)
    
    # Log policy evaluation
    self._audit_log.append({
      "timestamp": policy_context.timestamp.isoformat(),
      "tool": tool_name,
      "decision": policy_result.decision.value,
      "reasons": policy_result.reasons,
      "autonomy_level": profile.aml_level
    })
    
    # Handle policy decision
    if policy_result.decision == PolicyDecision.DENY:
      raise ToolExecutionError(
        f"Policy denied execution of {tool_name}: "
        f"{', '.join(policy_result.reasons)}"
      )
    
    elif policy_result.decision == PolicyDecision.REQUIRE_APPROVAL:
      # Request treasury approval if needed
      if cost_estimate and cost_estimate > 0:
        transaction = self._treasury.request_transaction(
          agent_name=self._agent_name,
          pillar=self._pillar,
          amount=cost_estimate,
          description=f"Tool execution: {tool_name}",
          metadata={
            "tool_name": tool_name,
            "arguments": arguments,
            "policy_reasons": policy_result.reasons
          }
        )
        
        if transaction.status.value == "rejected":
          raise ToolExecutionError(
            f"Treasury rejected transaction: "
            f"{transaction.metadata.get('rejection_reason', 'Unknown')}"
          )
        
        # Handle blockchain transactions if treasury is blockchain-enabled
        if isinstance(self._treasury, BlockchainTreasury):
          # Create blockchain transaction
          blockchain_tx = asyncio.run(
            self._treasury.execute_transaction(
              treasury_tx_id=transaction.id,
              pillar=self._pillar,
              amount=cost_estimate
            )
          )
          
          if blockchain_tx.status == "pending" and blockchain_tx.required_signatures > 1:
            raise ToolExecutionError(
              f"Tool execution requires {blockchain_tx.required_signatures} blockchain signatures. "
              f"Blockchain TX ID: {blockchain_tx.id}"
            )
        
        # For pending approvals, we would normally wait or return a message
        # For this example, we'll raise an error
        if transaction.status.value == "pending":
          raise ToolExecutionError(
            f"Tool execution requires approval. Transaction ID: {transaction.id}"
          )
      else:
        # Non-financial approval required
        raise ToolExecutionError(
          f"Tool execution requires approval: {', '.join(policy_result.reasons)}"
        )
    
    # Execute the tool if allowed
    try:
      result = await self._original_toolbox.execute_tool(
        tool_name,
        arguments,
        context
      )
      
      # Record successful execution
      if cost_estimate and cost_estimate > 0:
        # Update treasury with actual cost if available
        pass  # In real implementation, would update transaction
      
      return result
      
    except Exception as e:
      # Log tool execution failure
      self._audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "error": str(e),
        "type": "execution_failure"
      })
      raise
  
  def _estimate_tool_cost(
    self,
    tool_name: str,
    arguments: Dict[str, Any]
  ) -> Optional[float]:
    """Estimate cost of tool execution."""
    # Static cost mapping for tools
    static_costs = {
      "analyze_data": 0.01,
      "generate_report": 0.05,
      "send_email": 0.001,
      "execute_trade": 0.10,
      "modify_database": 0.02,
      "create_cloud_resource": 0.10,
      "execute_large_trade": 5.00,
      "transfer_funds": 1.00,
      "approve_vendor_payment": 2.50,
    }
    
    # Check static cost mapping
    if tool_name in static_costs:
      base_cost = static_costs[tool_name]
      
      # Adjust cost based on arguments for certain tools
      if tool_name == "create_cloud_resource":
        quantity = arguments.get("quantity", 1)
        return base_cost * quantity
      elif tool_name == "execute_trade" or tool_name == "execute_large_trade":
        quantity = arguments.get("quantity", 1)
        # Scale cost by quantity for trades
        return base_cost * (1 + (quantity / 1000))
      
      return base_cost
    
    # Default to no cost if unknown tool
    return None
  
  def get_audit_log(self) -> List[Dict[str, Any]]:
    """Get audit log of policy decisions."""
    return self._audit_log.copy()


class ControlPlaneAgent(Agent):
  """Agent wrapper that enforces control plane policies."""
  
  def __init__(
    self,
    wrapped_agent: Agent,
    pillar: str,
    policy_engine: Optional[PolicyEngine] = None,
    aml_registry: Optional[EnhancedAMLRegistry] = None,
    treasury: Optional[Union[Treasury, "BlockchainTreasury"]] = None,
    initial_autonomy_level: AutonomyLevel = AutonomyLevel.AML_1,
    enable_blockchain: bool = False,
    **kwargs
  ):
    """Initialize control plane agent.
    
    Args:
      wrapped_agent: The agent to wrap with policy enforcement
      pillar: Business pillar this agent belongs to
      policy_engine: Policy engine for evaluation (creates local if None)
      aml_registry: AML registry for autonomy management
      treasury: Treasury for budget management
      initial_autonomy_level: Initial autonomy level for the agent
      **kwargs: Additional arguments passed to parent Agent
    """
    # Initialize control plane components
    self._wrapped_agent = wrapped_agent
    self._pillar = pillar
    self._policy_engine = policy_engine or LocalPolicyEngine()
    self._aml_registry = aml_registry or EnhancedAMLRegistry()
    
    # Initialize treasury (with optional blockchain)
    if treasury:
      self._treasury = treasury
    else:
      base_treasury = Treasury(total_budget=1000000.0)
      if enable_blockchain:
        self._treasury = BlockchainTreasury(
          treasury=base_treasury,
          default_wallet_type=WalletType.MOCK
        )
      else:
        self._treasury = base_treasury
    
    # Register agent in AML registry (enhanced registry is async)
    # Note: This needs to be called asynchronously after initialization
    self._agent_registration_pending = {
      "agent_group": f"{wrapped_agent.name}_group",
      "pillar": pillar,
      "initial_level": initial_autonomy_level
    }
    
    # Create policy-enforced toolbox
    if wrapped_agent.tools:
      enforced_toolbox = PolicyEnforcedToolbox(
        original_toolbox=wrapped_agent.tools,
        policy_engine=self._policy_engine,
        aml_registry=self._aml_registry,
        treasury=self._treasury,
        agent_name=wrapped_agent.name,
        pillar=pillar
      )
    else:
      enforced_toolbox = None
    
    # Add control plane instructions
    control_plane_instructions = f"""
You are operating under a control plane governance system with the following constraints:

1. Current Autonomy Level: {initial_autonomy_level.name} ({initial_autonomy_level.value})
   - Level 0: Read-only insights (no actions)
   - Level 1: Suggest actions (require approval)
   - Level 2: Batch execution (approve batches)
   - Level 3: Real-time execution under hard caps
   - Level 4: Self-correcting execution with soft caps
   - Level 5: Uncapped with treasury limits

2. Business Pillar: {pillar}
   - You are part of the {pillar} business unit
   - Budget and policy constraints apply based on your pillar

3. Policy Enforcement:
   - All tool executions are subject to policy checks
   - Budget constraints are enforced by the treasury
   - Compliance and security policies must be followed

4. When a tool execution is denied:
   - Explain the policy violation to the user
   - Suggest alternative approaches if possible
   - Request approval if the action requires it

Remember to operate within your assigned autonomy level and pillar constraints.
"""
    
    # Combine instructions
    combined_instruction = (
      f"{control_plane_instructions}\n\n"
      f"Original Instructions:\n{wrapped_agent.instruction}"
    )
    
    # Initialize parent with wrapped agent's properties
    super().__init__(
      name=f"controlled_{wrapped_agent.name}",
      model=wrapped_agent.model,
      instruction=combined_instruction,
      tools=enforced_toolbox,
      sub_agents=wrapped_agent.sub_agents,
      **kwargs
    )
    
    # Store reference to original agent
    self._wrapped_agent = wrapped_agent
  
  async def initialize(self):
    """Initialize the enhanced AML registry and register the agent."""
    if hasattr(self._aml_registry, 'initialize'):
      await self._aml_registry.initialize()
    
    # Register agent group if registration is pending
    if hasattr(self, '_agent_registration_pending'):
      reg_info = self._agent_registration_pending
      await self._aml_registry.register_agent_group(
        agent_group=reg_info["agent_group"],
        pillar=reg_info["pillar"],
        initial_level=reg_info["initial_level"]
      )
      delattr(self, '_agent_registration_pending')
  
  async def update_autonomy_level(self, new_level: AutonomyLevel):
    """Update agent's autonomy level."""
    agent_group = f"{self._wrapped_agent.name}_group"
    profile = await self._aml_registry.get_agent_profile(agent_group)
    if profile:
      if new_level > profile.aml_level:
        await self._aml_registry.promote_agent_group(
          agent_group, 
          changed_by="control_plane_agent",
          reason="Manual autonomy level update"
        )
      elif new_level < profile.aml_level:
        await self._aml_registry.demote_agent_group(
          agent_group,
          changed_by="control_plane_agent", 
          reason="Manual autonomy level update"
        )
      logger.info(
        f"Updated {self._wrapped_agent.name} to autonomy level {new_level.name}"
      )
  
  async def get_policy_summary(self) -> Dict[str, Any]:
    """Get summary of current policies and constraints."""
    agent_group = f"{self._wrapped_agent.name}_group"
    profile = await self._aml_registry.get_agent_profile(agent_group)
    budget_summary = self._treasury.get_budget_summary()
    policies = await self._policy_engine.list_policies()
    
    return {
      "agent": self._wrapped_agent.name,
      "pillar": self._pillar,
      "autonomy_level": profile.aml_level.name if profile else "Unknown",
      "policies": [
        {
          "name": p.name,
          "type": p.policy_type.value,
          "enabled": p.enabled
        }
        for p in policies
      ],
      "budget": budget_summary["pillars"].get(self._pillar, {}),
      "pending_approvals": len(
        self._treasury.get_pending_approvals(self._pillar)
      )
    }
  
  def get_audit_log(self) -> List[Dict[str, Any]]:
    """Get audit log from the policy-enforced toolbox."""
    if isinstance(self.tools, PolicyEnforcedToolbox):
      return self.tools.get_audit_log()
    return []


def create_controlled_agent(
  agent: Agent,
  pillar: str,
  opa_url: Optional[str] = None,
  **kwargs
) -> ControlPlaneAgent:
  """Factory function to create a control plane agent.
  
  Args:
    agent: The agent to wrap with control plane
    pillar: Business pillar for the agent
    opa_url: Optional OPA server URL
    **kwargs: Additional arguments for ControlPlaneAgent
  
  Returns:
    ControlPlaneAgent instance
  """
  # Create policy engine
  if opa_url:
    policy_engine = OPAPolicyEngine(opa_url)
  else:
    policy_engine = LocalPolicyEngine()
  
  # Create control plane agent
  return ControlPlaneAgent(
    wrapped_agent=agent,
    pillar=pillar,
    policy_engine=policy_engine,
    **kwargs
  )