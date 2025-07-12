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
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from .policy_types import Policy, PolicyContext, PolicyResult, PolicyType

logger = logging.getLogger(__name__)


class PolicyDecision(BaseModel):
  """Final decision after evaluating all policies."""
  
  allowed: bool = Field(description="Whether the action is allowed")
  evaluated_policies: List[PolicyResult] = Field(
      description="Results from all evaluated policies"
  )
  blocking_policies: List[PolicyResult] = Field(
      description="Policies that blocked the action"
  )
  recommendations: List[str] = Field(
      description="Aggregated recommendations"
  )
  metadata: Dict[str, any] = Field(
      default_factory=dict, description="Additional decision metadata"
  )


class PolicyEngine:
  """Engine for managing and evaluating policies."""
  
  def __init__(self):
    """Initialize the policy engine."""
    self._policies: Dict[str, Policy] = {}
    self._policy_types: Dict[PolicyType, List[str]] = {}
    
  def register_policy(self, policy: Policy) -> None:
    """Register a policy with the engine.
    
    Args:
        policy: The policy to register
    """
    if policy.name in self._policies:
      logger.warning(f"Overwriting existing policy: {policy.name}")
    
    self._policies[policy.name] = policy
    
    # Index by type
    if policy.policy_type not in self._policy_types:
      self._policy_types[policy.policy_type] = []
    if policy.name not in self._policy_types[policy.policy_type]:
      self._policy_types[policy.policy_type].append(policy.name)
    
    logger.info(
        f"Registered policy: {policy.name} (type: {policy.policy_type})"
    )
  
  def unregister_policy(self, policy_name: str) -> bool:
    """Unregister a policy.
    
    Args:
        policy_name: Name of the policy to unregister
        
    Returns:
        True if policy was found and removed, False otherwise
    """
    if policy_name not in self._policies:
      return False
    
    policy = self._policies[policy_name]
    del self._policies[policy_name]
    
    # Remove from type index
    if policy.policy_type in self._policy_types:
      self._policy_types[policy.policy_type].remove(policy_name)
    
    logger.info(f"Unregistered policy: {policy_name}")
    return True
  
  def get_policy(self, policy_name: str) -> Optional[Policy]:
    """Get a policy by name.
    
    Args:
        policy_name: Name of the policy
        
    Returns:
        The policy if found, None otherwise
    """
    return self._policies.get(policy_name)
  
  def list_policies(
      self, policy_type: Optional[PolicyType] = None, enabled_only: bool = True
  ) -> List[Policy]:
    """List registered policies.
    
    Args:
        policy_type: Filter by policy type
        enabled_only: Only return enabled policies
        
    Returns:
        List of policies matching the criteria
    """
    policies = []
    
    if policy_type and policy_type in self._policy_types:
      policy_names = self._policy_types[policy_type]
      policies = [self._policies[name] for name in policy_names]
    else:
      policies = list(self._policies.values())
    
    if enabled_only:
      policies = [p for p in policies if p.enabled]
    
    # Sort by priority (descending)
    policies.sort(key=lambda p: p.priority, reverse=True)
    
    return policies
  
  async def evaluate(
      self,
      context: PolicyContext,
      policy_types: Optional[Set[PolicyType]] = None,
      fail_fast: bool = True,
  ) -> PolicyDecision:
    """Evaluate all applicable policies.
    
    Args:
        context: The context for policy evaluation
        policy_types: Specific policy types to evaluate (None = all)
        fail_fast: Stop on first denial (True) or evaluate all (False)
        
    Returns:
        PolicyDecision with the final verdict and details
    """
    evaluated_policies = []
    blocking_policies = []
    all_recommendations = []
    
    # Get policies to evaluate
    policies_to_evaluate = []
    if policy_types:
      for policy_type in policy_types:
        policies_to_evaluate.extend(
            self.list_policies(policy_type=policy_type, enabled_only=True)
        )
    else:
      policies_to_evaluate = self.list_policies(enabled_only=True)
    
    # Evaluate policies
    for policy in policies_to_evaluate:
      try:
        result = await policy.evaluate(context)
        evaluated_policies.append(result)
        
        if not result.allowed:
          blocking_policies.append(result)
          all_recommendations.extend(result.recommendations)
          
          if fail_fast:
            logger.info(
                f"Policy {policy.name} denied action (fail_fast=True)"
            )
            break
        
      except Exception as e:
        logger.error(f"Error evaluating policy {policy.name}: {e}")
        # Treat errors as denials for safety
        error_result = PolicyResult(
            allowed=False,
            policy_name=policy.name,
            policy_type=policy.policy_type,
            reason=f"Policy evaluation error: {str(e)}",
            recommendations=["Fix policy configuration"],
        )
        evaluated_policies.append(error_result)
        blocking_policies.append(error_result)
        
        if fail_fast:
          break
    
    # Determine final decision
    allowed = len(blocking_policies) == 0
    
    # Deduplicate recommendations
    unique_recommendations = list(dict.fromkeys(all_recommendations))
    
    decision = PolicyDecision(
        allowed=allowed,
        evaluated_policies=evaluated_policies,
        blocking_policies=blocking_policies,
        recommendations=unique_recommendations,
        metadata={
            "total_policies_evaluated": len(evaluated_policies),
            "total_policies_available": len(policies_to_evaluate),
            "fail_fast": fail_fast,
        },
    )
    
    logger.info(
        f"Policy decision: allowed={allowed}, "
        f"evaluated={len(evaluated_policies)}, "
        f"blocked={len(blocking_policies)}"
    )
    
    return decision
  
  async def evaluate_parallel(
      self,
      context: PolicyContext,
      policy_types: Optional[Set[PolicyType]] = None,
  ) -> PolicyDecision:
    """Evaluate policies in parallel for better performance.
    
    Args:
        context: The context for policy evaluation
        policy_types: Specific policy types to evaluate (None = all)
        
    Returns:
        PolicyDecision with the final verdict and details
    """
    # Get policies to evaluate
    policies_to_evaluate = []
    if policy_types:
      for policy_type in policy_types:
        policies_to_evaluate.extend(
            self.list_policies(policy_type=policy_type, enabled_only=True)
        )
    else:
      policies_to_evaluate = self.list_policies(enabled_only=True)
    
    # Create evaluation tasks
    tasks = []
    for policy in policies_to_evaluate:
      task = asyncio.create_task(self._evaluate_policy_safe(policy, context))
      tasks.append((policy, task))
    
    # Wait for all evaluations
    evaluated_policies = []
    blocking_policies = []
    all_recommendations = []
    
    for policy, task in tasks:
      result = await task
      evaluated_policies.append(result)
      
      if not result.allowed:
        blocking_policies.append(result)
        all_recommendations.extend(result.recommendations)
    
    # Determine final decision
    allowed = len(blocking_policies) == 0
    
    # Deduplicate recommendations
    unique_recommendations = list(dict.fromkeys(all_recommendations))
    
    decision = PolicyDecision(
        allowed=allowed,
        evaluated_policies=evaluated_policies,
        blocking_policies=blocking_policies,
        recommendations=unique_recommendations,
        metadata={
            "total_policies_evaluated": len(evaluated_policies),
            "total_policies_available": len(policies_to_evaluate),
            "parallel_evaluation": True,
        },
    )
    
    return decision
  
  async def _evaluate_policy_safe(
      self, policy: Policy, context: PolicyContext
  ) -> PolicyResult:
    """Safely evaluate a policy, catching exceptions.
    
    Args:
        policy: The policy to evaluate
        context: The evaluation context
        
    Returns:
        PolicyResult (error result if evaluation fails)
    """
    try:
      return await policy.evaluate(context)
    except Exception as e:
      logger.error(f"Error evaluating policy {policy.name}: {e}")
      return PolicyResult(
          allowed=False,
          policy_name=policy.name,
          policy_type=policy.policy_type,
          reason=f"Policy evaluation error: {str(e)}",
          recommendations=["Fix policy configuration"],
      )