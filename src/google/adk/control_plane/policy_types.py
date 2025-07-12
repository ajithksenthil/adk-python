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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyType(str, Enum):
  """Types of policies that can be enforced."""
  
  RESOURCE = "resource"
  SECURITY = "security"
  COMPLIANCE = "compliance"
  RATE_LIMIT = "rate_limit"
  DATA_GOVERNANCE = "data_governance"
  COST_CONTROL = "cost_control"


class PolicyResult(BaseModel):
  """Result of a policy evaluation."""
  
  allowed: bool = Field(description="Whether the action is allowed")
  policy_name: str = Field(description="Name of the policy that was evaluated")
  policy_type: PolicyType = Field(description="Type of policy")
  reason: Optional[str] = Field(
      default=None, description="Reason for the decision"
  )
  metadata: Dict[str, Any] = Field(
      default_factory=dict, description="Additional metadata about the decision"
  )
  recommendations: List[str] = Field(
      default_factory=list, description="Recommendations for policy compliance"
  )


class PolicyContext(BaseModel):
  """Context information for policy evaluation."""
  
  agent_name: str = Field(description="Name of the agent making the request")
  user_id: str = Field(description="ID of the user")
  session_id: str = Field(description="ID of the session")
  action: str = Field(description="Action being requested")
  resource: Optional[str] = Field(
      default=None, description="Resource being accessed"
  )
  metadata: Dict[str, Any] = Field(
      default_factory=dict, description="Additional context metadata"
  )


class Policy(ABC, BaseModel):
  """Base class for all policies."""
  
  name: str = Field(description="Name of the policy")
  policy_type: PolicyType = Field(description="Type of policy")
  enabled: bool = Field(default=True, description="Whether policy is enabled")
  priority: int = Field(
      default=0, description="Priority (higher = evaluated first)"
  )
  description: Optional[str] = Field(
      default=None, description="Policy description"
  )
  
  @abstractmethod
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate the policy against the given context.
    
    Args:
        context: The context for policy evaluation
        
    Returns:
        PolicyResult indicating whether the action is allowed
    """
    pass
  
  class Config:
    arbitrary_types_allowed = True


class ResourcePolicy(Policy):
  """Policy for controlling access to resources."""
  
  policy_type: PolicyType = Field(default=PolicyType.RESOURCE)
  allowed_resources: List[str] = Field(
      default_factory=list, description="List of allowed resource patterns"
  )
  denied_resources: List[str] = Field(
      default_factory=list, description="List of denied resource patterns"
  )
  max_resources_per_session: Optional[int] = Field(
      default=None, description="Maximum resources per session"
  )
  
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate resource access policy."""
    if not context.resource:
      return PolicyResult(
          allowed=True,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason="No resource specified",
      )
    
    # Check denied resources first
    for pattern in self.denied_resources:
      if self._matches_pattern(context.resource, pattern):
        return PolicyResult(
            allowed=False,
            policy_name=self.name,
            policy_type=self.policy_type,
            reason=f"Resource {context.resource} matches denied pattern {pattern}",
            recommendations=[
                "Request access to a different resource",
                "Contact administrator for exceptions",
            ],
        )
    
    # Check allowed resources
    if self.allowed_resources:
      for pattern in self.allowed_resources:
        if self._matches_pattern(context.resource, pattern):
          return PolicyResult(
              allowed=True,
              policy_name=self.name,
              policy_type=self.policy_type,
              reason=f"Resource {context.resource} matches allowed pattern {pattern}",
          )
      
      # If allowed list exists but no match, deny
      return PolicyResult(
          allowed=False,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason=f"Resource {context.resource} not in allowed list",
          recommendations=["Request access to this specific resource"],
      )
    
    # Default allow if no restrictions
    return PolicyResult(
        allowed=True,
        policy_name=self.name,
        policy_type=self.policy_type,
        reason="No resource restrictions configured",
    )
  
  def _matches_pattern(self, resource: str, pattern: str) -> bool:
    """Check if resource matches pattern (supports wildcards)."""
    import fnmatch
    return fnmatch.fnmatch(resource, pattern)


class SecurityPolicy(Policy):
  """Policy for security controls."""
  
  policy_type: PolicyType = Field(default=PolicyType.SECURITY)
  require_authentication: bool = Field(
      default=True, description="Require user authentication"
  )
  allowed_actions: List[str] = Field(
      default_factory=list, description="List of allowed actions"
  )
  denied_actions: List[str] = Field(
      default_factory=list, description="List of denied actions"
  )
  require_encryption: bool = Field(
      default=False, description="Require encrypted communication"
  )
  
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate security policy."""
    # Check authentication
    if self.require_authentication and not context.metadata.get("authenticated"):
      return PolicyResult(
          allowed=False,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason="Authentication required",
          recommendations=["Authenticate before proceeding"],
      )
    
    # Check denied actions first
    if context.action in self.denied_actions:
      return PolicyResult(
          allowed=False,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason=f"Action {context.action} is explicitly denied",
          recommendations=["Use an alternative action"],
      )
    
    # Check allowed actions
    if self.allowed_actions and context.action not in self.allowed_actions:
      return PolicyResult(
          allowed=False,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason=f"Action {context.action} not in allowed list",
          recommendations=[
              f"Use one of the allowed actions: {', '.join(self.allowed_actions)}"
          ],
      )
    
    # Check encryption
    if self.require_encryption and not context.metadata.get("encrypted"):
      return PolicyResult(
          allowed=False,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason="Encrypted communication required",
          recommendations=["Enable encryption for this session"],
      )
    
    return PolicyResult(
        allowed=True,
        policy_name=self.name,
        policy_type=self.policy_type,
        reason="Security checks passed",
    )


class CompliancePolicy(Policy):
  """Policy for regulatory compliance."""
  
  policy_type: PolicyType = Field(default=PolicyType.COMPLIANCE)
  data_retention_days: Optional[int] = Field(
      default=None, description="Data retention period in days"
  )
  require_audit_trail: bool = Field(
      default=True, description="Require audit trail for actions"
  )
  pii_handling: Dict[str, str] = Field(
      default_factory=dict, description="PII handling requirements"
  )
  geographic_restrictions: List[str] = Field(
      default_factory=list, description="Allowed geographic regions"
  )
  
  async def evaluate(self, context: PolicyContext) -> PolicyResult:
    """Evaluate compliance policy."""
    # Check audit trail
    if self.require_audit_trail and not context.metadata.get("audit_enabled"):
      return PolicyResult(
          allowed=False,
          policy_name=self.name,
          policy_type=self.policy_type,
          reason="Audit trail required for compliance",
          recommendations=["Enable audit logging for this session"],
      )
    
    # Check geographic restrictions
    if self.geographic_restrictions:
      user_region = context.metadata.get("region", "unknown")
      if user_region not in self.geographic_restrictions:
        return PolicyResult(
            allowed=False,
            policy_name=self.name,
            policy_type=self.policy_type,
            reason=f"Region {user_region} not in allowed list",
            recommendations=[
                f"Access from allowed regions: {', '.join(self.geographic_restrictions)}"
            ],
        )
    
    # Check PII handling
    if context.metadata.get("contains_pii"):
      pii_type = context.metadata.get("pii_type", "unknown")
      if pii_type in self.pii_handling:
        handling_requirement = self.pii_handling[pii_type]
        if not context.metadata.get(handling_requirement):
          return PolicyResult(
              allowed=False,
              policy_name=self.name,
              policy_type=self.policy_type,
              reason=f"PII type {pii_type} requires {handling_requirement}",
              recommendations=[f"Enable {handling_requirement} for PII handling"],
          )
    
    return PolicyResult(
        allowed=True,
        policy_name=self.name,
        policy_type=self.policy_type,
        reason="Compliance checks passed",
        metadata={
            "data_retention_days": self.data_retention_days,
            "audit_enabled": self.require_audit_trail,
        },
    )