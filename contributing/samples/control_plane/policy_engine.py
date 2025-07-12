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

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PolicyDecision(Enum):
  """Policy evaluation decision."""
  ALLOW = "allow"
  DENY = "deny"
  REQUIRE_APPROVAL = "require_approval"


class PolicyType(Enum):
  """Types of policies that can be enforced."""
  BUDGET = "budget"
  SECURITY = "security"
  COMPLIANCE = "compliance"
  DATA_ACCESS = "data_access"
  TOOL_ACCESS = "tool_access"
  AUTONOMY = "autonomy"


@dataclass
class PolicyContext:
  """Context for policy evaluation."""
  agent_name: str
  tool_name: Optional[str] = None
  action: Optional[str] = None
  parameters: Dict[str, Any] = field(default_factory=dict)
  user_id: Optional[str] = None
  session_id: Optional[str] = None
  autonomy_level: int = 0  # AML 0-5
  cost_estimate: Optional[float] = None
  timestamp: datetime = field(default_factory=datetime.now)
  metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyResult:
  """Result of policy evaluation."""
  decision: PolicyDecision
  reasons: List[str] = field(default_factory=list)
  policy_type: Optional[PolicyType] = None
  policy_name: Optional[str] = None
  suggestions: List[str] = field(default_factory=list)
  required_approvals: List[str] = field(default_factory=list)
  metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyRule(BaseModel):
  """Base class for policy rules."""
  name: str
  description: str
  policy_type: PolicyType
  enabled: bool = True
  priority: int = 0  # Higher priority rules are evaluated first


class BudgetPolicyRule(PolicyRule):
  """Budget-related policy rule."""
  max_cost_per_action: Optional[float] = None
  max_daily_cost: Optional[float] = None
  max_monthly_cost: Optional[float] = None
  require_approval_above: Optional[float] = None


class AutonomyPolicyRule(PolicyRule):
  """Autonomy level policy rule."""
  min_autonomy_level: int = Field(ge=0, le=5)
  max_autonomy_level: int = Field(ge=0, le=5)
  allowed_tools: List[str] = Field(default_factory=list)
  denied_tools: List[str] = Field(default_factory=list)


class CompliancePolicyRule(PolicyRule):
  """Compliance-related policy rule."""
  required_tags: List[str] = Field(default_factory=list)
  forbidden_patterns: List[str] = Field(default_factory=list)
  data_residency_requirements: List[str] = Field(default_factory=list)


class PolicyEngine(ABC):
  """Abstract base class for policy engines."""
  
  @abstractmethod
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate policies for the given context."""
    pass
  
  @abstractmethod
  async def add_policy(self, policy: PolicyRule) -> bool:
    """Add a new policy rule."""
    pass
  
  @abstractmethod
  async def remove_policy(self, policy_name: str) -> bool:
    """Remove a policy rule."""
    pass
  
  @abstractmethod
  async def list_policies(self) -> List[PolicyRule]:
    """List all policy rules."""
    pass


class OPAPolicyEngine(PolicyEngine):
  """Open Policy Agent (OPA) based policy engine."""
  
  def __init__(self, opa_url: str = "http://localhost:8181"):
    self.opa_url = opa_url
    self.client = httpx.AsyncClient(timeout=30.0)
    self.policies: Dict[str, PolicyRule] = {}
    
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate policies using OPA."""
    # First, check local rules
    local_result = await self._evaluate_local_rules(context)
    if local_result.decision == PolicyDecision.DENY:
      return local_result
    
    # Then, evaluate with OPA if available
    try:
      opa_result = await self._evaluate_opa(context)
      # Combine results
      if opa_result.decision == PolicyDecision.DENY:
        return opa_result
      elif opa_result.decision == PolicyDecision.REQUIRE_APPROVAL:
        local_result.decision = PolicyDecision.REQUIRE_APPROVAL
        local_result.required_approvals.extend(opa_result.required_approvals)
        local_result.reasons.extend(opa_result.reasons)
    except Exception as e:
      logger.warning(f"OPA evaluation failed, using local rules only: {e}")
    
    return local_result
  
  async def _evaluate_local_rules(self, context: PolicyContext) -> PolicyResult:
    """Evaluate local policy rules."""
    result = PolicyResult(decision=PolicyDecision.ALLOW)
    
    # Sort policies by priority
    sorted_policies = sorted(
      self.policies.values(),
      key=lambda p: p.priority,
      reverse=True
    )
    
    for policy in sorted_policies:
      if not policy.enabled:
        continue
        
      policy_result = await self._evaluate_single_policy(policy, context)
      
      # Update result based on policy evaluation
      if policy_result.decision == PolicyDecision.DENY:
        return policy_result  # Fail fast on deny
      elif policy_result.decision == PolicyDecision.REQUIRE_APPROVAL:
        result.decision = PolicyDecision.REQUIRE_APPROVAL
        result.required_approvals.extend(policy_result.required_approvals)
        result.reasons.extend(policy_result.reasons)
    
    return result
  
  async def _evaluate_single_policy(
    self,
    policy: PolicyRule,
    context: PolicyContext
  ) -> PolicyResult:
    """Evaluate a single policy rule."""
    result = PolicyResult(
      decision=PolicyDecision.ALLOW,
      policy_type=policy.policy_type,
      policy_name=policy.name
    )
    
    if isinstance(policy, BudgetPolicyRule):
      return await self._evaluate_budget_policy(policy, context)
    elif isinstance(policy, AutonomyPolicyRule):
      return await self._evaluate_autonomy_policy(policy, context)
    elif isinstance(policy, CompliancePolicyRule):
      return await self._evaluate_compliance_policy(policy, context)
    
    return result
  
  async def _evaluate_budget_policy(
    self,
    policy: BudgetPolicyRule,
    context: PolicyContext
  ) -> PolicyResult:
    """Evaluate budget policy."""
    result = PolicyResult(
      decision=PolicyDecision.ALLOW,
      policy_type=PolicyType.BUDGET,
      policy_name=policy.name
    )
    
    if context.cost_estimate is None:
      return result
    
    # Check cost limits
    if (policy.max_cost_per_action is not None and
        context.cost_estimate > policy.max_cost_per_action):
      result.decision = PolicyDecision.DENY
      result.reasons.append(
        f"Cost ${context.cost_estimate} exceeds per-action limit "
        f"${policy.max_cost_per_action}"
      )
      return result
    
    # Check if approval is required
    if (policy.require_approval_above is not None and
        context.cost_estimate > policy.require_approval_above):
      result.decision = PolicyDecision.REQUIRE_APPROVAL
      result.reasons.append(
        f"Cost ${context.cost_estimate} requires approval "
        f"(threshold: ${policy.require_approval_above})"
      )
      result.required_approvals.append("budget_approver")
    
    return result
  
  async def _evaluate_autonomy_policy(
    self,
    policy: AutonomyPolicyRule,
    context: PolicyContext
  ) -> PolicyResult:
    """Evaluate autonomy level policy."""
    result = PolicyResult(
      decision=PolicyDecision.ALLOW,
      policy_type=PolicyType.AUTONOMY,
      policy_name=policy.name
    )
    
    # Check autonomy level bounds
    if context.autonomy_level < policy.min_autonomy_level:
      result.decision = PolicyDecision.DENY
      result.reasons.append(
        f"Autonomy level {context.autonomy_level} below minimum "
        f"{policy.min_autonomy_level} for this action"
      )
      result.suggestions.append(
        f"Increase agent autonomy to level {policy.min_autonomy_level} or higher"
      )
      return result
    
    if context.autonomy_level > policy.max_autonomy_level:
      result.decision = PolicyDecision.REQUIRE_APPROVAL
      result.reasons.append(
        f"Autonomy level {context.autonomy_level} exceeds maximum "
        f"{policy.max_autonomy_level} for this action"
      )
      result.required_approvals.append("autonomy_override")
    
    # Check tool access
    if context.tool_name:
      if (policy.allowed_tools and
          context.tool_name not in policy.allowed_tools):
        result.decision = PolicyDecision.DENY
        result.reasons.append(
          f"Tool '{context.tool_name}' not in allowed list for "
          f"autonomy level {context.autonomy_level}"
        )
        return result
      
      if context.tool_name in policy.denied_tools:
        result.decision = PolicyDecision.DENY
        result.reasons.append(
          f"Tool '{context.tool_name}' is explicitly denied for "
          f"autonomy level {context.autonomy_level}"
        )
        return result
    
    return result
  
  async def _evaluate_compliance_policy(
    self,
    policy: CompliancePolicyRule,
    context: PolicyContext
  ) -> PolicyResult:
    """Evaluate compliance policy."""
    result = PolicyResult(
      decision=PolicyDecision.ALLOW,
      policy_type=PolicyType.COMPLIANCE,
      policy_name=policy.name
    )
    
    # Check required tags
    context_tags = context.metadata.get("tags", [])
    missing_tags = [
      tag for tag in policy.required_tags
      if tag not in context_tags
    ]
    
    if missing_tags:
      result.decision = PolicyDecision.DENY
      result.reasons.append(
        f"Missing required compliance tags: {', '.join(missing_tags)}"
      )
      result.suggestions.append(
        f"Add the following tags to the context: {', '.join(missing_tags)}"
      )
    
    return result
  
  async def _evaluate_opa(self, context: PolicyContext) -> PolicyResult:
    """Evaluate policies using OPA server."""
    try:
      # Prepare OPA input
      opa_input = {
        "input": {
          "agent": context.agent_name,
          "tool": context.tool_name,
          "action": context.action,
          "parameters": context.parameters,
          "user": context.user_id,
          "session": context.session_id,
          "autonomy_level": context.autonomy_level,
          "cost_estimate": context.cost_estimate,
          "timestamp": context.timestamp.isoformat(),
          "metadata": context.metadata
        }
      }
      
      # Query OPA
      response = await self.client.post(
        f"{self.opa_url}/v1/data/adk/authz",
        json=opa_input
      )
      
      if response.status_code != 200:
        logger.error(f"OPA returned status {response.status_code}")
        return PolicyResult(decision=PolicyDecision.ALLOW)
      
      # Parse OPA response
      opa_response = response.json()
      result_data = opa_response.get("result", {})
      
      # Convert OPA decision to PolicyDecision
      decision_str = result_data.get("allow", True)
      if not decision_str:
        decision = PolicyDecision.DENY
      elif result_data.get("require_approval", False):
        decision = PolicyDecision.REQUIRE_APPROVAL
      else:
        decision = PolicyDecision.ALLOW
      
      return PolicyResult(
        decision=decision,
        reasons=result_data.get("reasons", []),
        required_approvals=result_data.get("required_approvals", []),
        metadata=result_data.get("metadata", {})
      )
      
    except Exception as e:
      logger.error(f"Error querying OPA: {e}")
      # Default to allow on OPA errors (fail open)
      return PolicyResult(decision=PolicyDecision.ALLOW)
  
  async def add_policy(self, policy: PolicyRule) -> bool:
    """Add a new policy rule."""
    self.policies[policy.name] = policy
    return True
  
  async def remove_policy(self, policy_name: str) -> bool:
    """Remove a policy rule."""
    if policy_name in self.policies:
      del self.policies[policy_name]
      return True
    return False
  
  async def list_policies(self) -> List[PolicyRule]:
    """List all policy rules."""
    return list(self.policies.values())
  
  async def close(self):
    """Close the HTTP client."""
    await self.client.aclose()


class LocalPolicyEngine(PolicyEngine):
  """Local policy engine without external dependencies."""
  
  def __init__(self):
    self.policies: Dict[str, PolicyRule] = {}
    
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate policies locally."""
    return await OPAPolicyEngine._evaluate_local_rules(self, context)
  
  async def add_policy(self, policy: PolicyRule) -> bool:
    """Add a new policy rule."""
    self.policies[policy.name] = policy
    return True
  
  async def remove_policy(self, policy_name: str) -> bool:
    """Remove a policy rule."""
    if policy_name in self.policies:
      del self.policies[policy_name]
      return True
    return False
  
  async def list_policies(self) -> List[PolicyRule]:
    """List all policy rules."""
    return list(self.policies.values())
  
  # Reuse evaluation methods from OPAPolicyEngine
  _evaluate_local_rules = OPAPolicyEngine._evaluate_local_rules
  _evaluate_single_policy = OPAPolicyEngine._evaluate_single_policy
  _evaluate_budget_policy = OPAPolicyEngine._evaluate_budget_policy
  _evaluate_autonomy_policy = OPAPolicyEngine._evaluate_autonomy_policy
  _evaluate_compliance_policy = OPAPolicyEngine._evaluate_compliance_policy