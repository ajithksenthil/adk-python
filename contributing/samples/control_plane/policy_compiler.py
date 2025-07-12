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
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field

from .policy_engine import (
  AutonomyPolicyRule,
  BudgetPolicyRule,
  CompliancePolicyRule,
  PolicyRule,
  PolicyType,
)

logger = logging.getLogger(__name__)


class RuleLanguage(Enum):
  """Supported business rule languages."""
  NATURAL = "natural"  # Natural language rules
  YAML = "yaml"  # YAML-based rules
  JSON = "json"  # JSON-based rules
  REGO = "rego"  # OPA Rego language


@dataclass
class BusinessRule:
  """High-level business rule representation."""
  name: str
  description: str
  rule_text: str
  language: RuleLanguage
  pillar: Optional[str] = None
  priority: int = 0
  enabled: bool = True
  metadata: Dict[str, Any] = None


class CompiledPolicy(BaseModel):
  """Result of compiling a business rule."""
  policy_rule: PolicyRule
  opa_rego: Optional[str] = None  # OPA Rego code if applicable
  validation_errors: List[str] = Field(default_factory=list)
  warnings: List[str] = Field(default_factory=list)


class PolicyCompiler:
  """Compiles business rules into enforceable policies."""
  
  def __init__(self):
    self.natural_patterns = self._init_natural_patterns()
    self.rego_templates = self._init_rego_templates()
  
  def _init_natural_patterns(self) -> Dict[str, re.Pattern]:
    """Initialize patterns for natural language parsing."""
    return {
      # Budget patterns
      "max_cost": re.compile(
        r"(?:max|maximum|limit)\s+(?:cost|spend|budget)"
        r".*?(?:is|to|of)\s+\$?(\d+(?:\.\d+)?)",
        re.IGNORECASE
      ),
      "daily_limit": re.compile(
        r"(?:daily|per day)\s+(?:limit|budget|spend)"
        r".*?(?:is|to|of)\s+\$?(\d+(?:\.\d+)?)",
        re.IGNORECASE
      ),
      "approval_threshold": re.compile(
        r"(?:require|need)\s+approval.*?"
        r"(?:above|over|exceeding)\s+\$?(\d+(?:\.\d+)?)",
        re.IGNORECASE
      ),
      
      # Autonomy patterns
      "min_autonomy": re.compile(
        r"(?:minimum|min|at least)\s+(?:autonomy|AML)"
        r".*?(?:level|of)\s+(\d+)",
        re.IGNORECASE
      ),
      "tool_allow": re.compile(
        r"(?:allow|permit|can use)\s+tools?\s*:?\s*"
        r"([\w\s,]+)",
        re.IGNORECASE
      ),
      "tool_deny": re.compile(
        r"(?:deny|forbid|cannot use|prohibited)\s+tools?\s*:?\s*"
        r"([\w\s,]+)",
        re.IGNORECASE
      ),
      
      # Compliance patterns
      "required_tags": re.compile(
        r"(?:require|must have)\s+tags?\s*:?\s*"
        r"([\w\s,]+)",
        re.IGNORECASE
      ),
      "data_residency": re.compile(
        r"data\s+(?:must|should)\s+(?:stay|remain|reside)\s+in\s+"
        r"([\w\s,]+)",
        re.IGNORECASE
      ),
    }
  
  def _init_rego_templates(self) -> Dict[str, str]:
    """Initialize OPA Rego templates."""
    return {
      "budget": """
package adk.policies.budget

import future.keywords.contains
import future.keywords.if

# {description}
{rule_name} = result if {{
    input.cost_estimate > 0
    result := {{
        "allow": input.cost_estimate <= {max_cost},
        "reasons": reason
    }}
    reason := ["Cost exceeds limit of ${max_cost}"] if input.cost_estimate > {max_cost} else []
}}
""",
      "autonomy": """
package adk.policies.autonomy

import future.keywords.contains
import future.keywords.if

# {description}
{rule_name} = result if {{
    result := {{
        "allow": allow,
        "reasons": reasons
    }}
    
    allow := input.autonomy_level >= {min_level}
    reasons := ["Autonomy level too low"] if not allow else []
    
    # Tool restrictions
    {tool_checks}
}}
""",
      "compliance": """
package adk.policies.compliance

import future.keywords.contains
import future.keywords.if

# {description}
{rule_name} = result if {{
    result := {{
        "allow": allow,
        "reasons": reasons
    }}
    
    # Required tags check
    required_tags := {required_tags}
    missing_tags := [tag | tag := required_tags[_]; not contains(input.metadata.tags, tag)]
    
    allow := count(missing_tags) == 0
    reasons := [concat(" ", ["Missing required tags:", concat(", ", missing_tags)])] if not allow else []
}}
"""
    }
  
  def compile(self, rule: BusinessRule) -> CompiledPolicy:
    """Compile a business rule into an enforceable policy."""
    if rule.language == RuleLanguage.NATURAL:
      return self._compile_natural_language(rule)
    elif rule.language == RuleLanguage.YAML:
      return self._compile_yaml(rule)
    elif rule.language == RuleLanguage.JSON:
      return self._compile_json(rule)
    elif rule.language == RuleLanguage.REGO:
      return self._compile_rego(rule)
    else:
      return CompiledPolicy(
        policy_rule=PolicyRule(
          name=rule.name,
          description=rule.description,
          policy_type=PolicyType.COMPLIANCE,
          enabled=False
        ),
        validation_errors=[f"Unsupported language: {rule.language}"]
      )
  
  def _compile_natural_language(self, rule: BusinessRule) -> CompiledPolicy:
    """Compile natural language rules."""
    errors = []
    warnings = []
    policy_type = None
    policy_params = {}
    
    # Parse budget rules
    max_cost_match = self.natural_patterns["max_cost"].search(rule.rule_text)
    daily_limit_match = self.natural_patterns["daily_limit"].search(rule.rule_text)
    approval_match = self.natural_patterns["approval_threshold"].search(rule.rule_text)
    
    if max_cost_match or daily_limit_match or approval_match:
      policy_type = PolicyType.BUDGET
      if max_cost_match:
        policy_params["max_cost_per_action"] = float(max_cost_match.group(1))
      if daily_limit_match:
        policy_params["max_daily_cost"] = float(daily_limit_match.group(1))
      if approval_match:
        policy_params["require_approval_above"] = float(approval_match.group(1))
    
    # Parse autonomy rules
    min_autonomy_match = self.natural_patterns["min_autonomy"].search(rule.rule_text)
    tool_allow_match = self.natural_patterns["tool_allow"].search(rule.rule_text)
    tool_deny_match = self.natural_patterns["tool_deny"].search(rule.rule_text)
    
    if min_autonomy_match or tool_allow_match or tool_deny_match:
      if policy_type:
        warnings.append("Multiple policy types detected, using first match")
      else:
        policy_type = PolicyType.AUTONOMY
        if min_autonomy_match:
          policy_params["min_autonomy_level"] = int(min_autonomy_match.group(1))
          policy_params["max_autonomy_level"] = 5  # Default max
        if tool_allow_match:
          tools = [t.strip() for t in tool_allow_match.group(1).split(",")]
          policy_params["allowed_tools"] = tools
        if tool_deny_match:
          tools = [t.strip() for t in tool_deny_match.group(1).split(",")]
          policy_params["denied_tools"] = tools
    
    # Parse compliance rules
    required_tags_match = self.natural_patterns["required_tags"].search(rule.rule_text)
    residency_match = self.natural_patterns["data_residency"].search(rule.rule_text)
    
    if required_tags_match or residency_match:
      if policy_type:
        warnings.append("Multiple policy types detected, using first match")
      else:
        policy_type = PolicyType.COMPLIANCE
        if required_tags_match:
          tags = [t.strip() for t in required_tags_match.group(1).split(",")]
          policy_params["required_tags"] = tags
        if residency_match:
          regions = [r.strip() for r in residency_match.group(1).split(",")]
          policy_params["data_residency_requirements"] = regions
    
    # Create appropriate policy rule
    if not policy_type:
      errors.append("Could not determine policy type from rule text")
      policy_rule = PolicyRule(
        name=rule.name,
        description=rule.description,
        policy_type=PolicyType.COMPLIANCE,
        enabled=False
      )
    else:
      policy_rule = self._create_policy_rule(
        rule.name,
        rule.description,
        policy_type,
        policy_params,
        rule.priority,
        rule.enabled
      )
    
    # Generate OPA Rego if applicable
    opa_rego = None
    if policy_type and not errors:
      opa_rego = self._generate_rego(policy_type, rule, policy_params)
    
    return CompiledPolicy(
      policy_rule=policy_rule,
      opa_rego=opa_rego,
      validation_errors=errors,
      warnings=warnings
    )
  
  def _compile_yaml(self, rule: BusinessRule) -> CompiledPolicy:
    """Compile YAML-based rules."""
    try:
      rule_data = yaml.safe_load(rule.rule_text)
      
      # Validate structure
      if not isinstance(rule_data, dict):
        return CompiledPolicy(
          policy_rule=PolicyRule(
            name=rule.name,
            description=rule.description,
            policy_type=PolicyType.COMPLIANCE,
            enabled=False
          ),
          validation_errors=["Invalid YAML structure"]
        )
      
      # Extract policy type
      policy_type_str = rule_data.get("type", "").lower()
      policy_type_map = {
        "budget": PolicyType.BUDGET,
        "autonomy": PolicyType.AUTONOMY,
        "compliance": PolicyType.COMPLIANCE,
        "security": PolicyType.SECURITY,
        "data_access": PolicyType.DATA_ACCESS,
        "tool_access": PolicyType.TOOL_ACCESS,
      }
      
      policy_type = policy_type_map.get(policy_type_str)
      if not policy_type:
        return CompiledPolicy(
          policy_rule=PolicyRule(
            name=rule.name,
            description=rule.description,
            policy_type=PolicyType.COMPLIANCE,
            enabled=False
          ),
          validation_errors=[f"Unknown policy type: {policy_type_str}"]
        )
      
      # Extract parameters
      params = rule_data.get("parameters", {})
      
      # Create policy rule
      policy_rule = self._create_policy_rule(
        rule.name,
        rule.description,
        policy_type,
        params,
        rule.priority,
        rule.enabled
      )
      
      # Generate OPA Rego if requested
      opa_rego = None
      if rule_data.get("generate_rego", False):
        opa_rego = self._generate_rego(policy_type, rule, params)
      
      return CompiledPolicy(
        policy_rule=policy_rule,
        opa_rego=opa_rego
      )
      
    except yaml.YAMLError as e:
      return CompiledPolicy(
        policy_rule=PolicyRule(
          name=rule.name,
          description=rule.description,
          policy_type=PolicyType.COMPLIANCE,
          enabled=False
        ),
        validation_errors=[f"YAML parsing error: {str(e)}"]
      )
  
  def _compile_json(self, rule: BusinessRule) -> CompiledPolicy:
    """Compile JSON-based rules."""
    try:
      rule_data = json.loads(rule.rule_text)
      # Similar to YAML compilation
      return self._compile_yaml(BusinessRule(
        name=rule.name,
        description=rule.description,
        rule_text=json.dumps(rule_data),  # Convert back for YAML parser
        language=RuleLanguage.YAML,
        pillar=rule.pillar,
        priority=rule.priority,
        enabled=rule.enabled
      ))
    except json.JSONDecodeError as e:
      return CompiledPolicy(
        policy_rule=PolicyRule(
          name=rule.name,
          description=rule.description,
          policy_type=PolicyType.COMPLIANCE,
          enabled=False
        ),
        validation_errors=[f"JSON parsing error: {str(e)}"]
      )
  
  def _compile_rego(self, rule: BusinessRule) -> CompiledPolicy:
    """Compile OPA Rego rules directly."""
    # For direct Rego, we just validate and return
    # In production, would validate Rego syntax
    return CompiledPolicy(
      policy_rule=PolicyRule(
        name=rule.name,
        description=rule.description,
        policy_type=PolicyType.COMPLIANCE,
        priority=rule.priority,
        enabled=rule.enabled
      ),
      opa_rego=rule.rule_text
    )
  
  def _create_policy_rule(
    self,
    name: str,
    description: str,
    policy_type: PolicyType,
    params: Dict[str, Any],
    priority: int,
    enabled: bool
  ) -> PolicyRule:
    """Create appropriate policy rule based on type."""
    base_params = {
      "name": name,
      "description": description,
      "policy_type": policy_type,
      "priority": priority,
      "enabled": enabled
    }
    
    if policy_type == PolicyType.BUDGET:
      return BudgetPolicyRule(**base_params, **params)
    elif policy_type == PolicyType.AUTONOMY:
      return AutonomyPolicyRule(**base_params, **params)
    elif policy_type == PolicyType.COMPLIANCE:
      return CompliancePolicyRule(**base_params, **params)
    else:
      return PolicyRule(**base_params)
  
  def _generate_rego(
    self,
    policy_type: PolicyType,
    rule: BusinessRule,
    params: Dict[str, Any]
  ) -> Optional[str]:
    """Generate OPA Rego code for the policy."""
    template = self.rego_templates.get(policy_type.value)
    if not template:
      return None
    
    # Prepare template variables
    template_vars = {
      "rule_name": re.sub(r'[^a-zA-Z0-9_]', '_', rule.name.lower()),
      "description": rule.description,
    }
    
    if policy_type == PolicyType.BUDGET:
      template_vars["max_cost"] = params.get("max_cost_per_action", 1000000)
    
    elif policy_type == PolicyType.AUTONOMY:
      template_vars["min_level"] = params.get("min_autonomy_level", 0)
      
      # Generate tool checks
      tool_checks = []
      if params.get("allowed_tools"):
        allowed = json.dumps(params["allowed_tools"])
        tool_checks.append(
          f"tool_allowed := input.tool in {allowed}"
        )
      if params.get("denied_tools"):
        denied = json.dumps(params["denied_tools"])
        tool_checks.append(
          f"tool_denied := input.tool in {denied}\n"
          f"    allow := allow and not tool_denied"
        )
      template_vars["tool_checks"] = "\n    ".join(tool_checks)
    
    elif policy_type == PolicyType.COMPLIANCE:
      template_vars["required_tags"] = json.dumps(
        params.get("required_tags", [])
      )
    
    # Format template
    try:
      return template.format(**template_vars)
    except KeyError as e:
      logger.error(f"Missing template variable: {e}")
      return None


def compile_business_rules(
  rules: List[BusinessRule],
  output_format: str = "policies"
) -> Union[List[PolicyRule], Dict[str, Any]]:
  """Compile multiple business rules.
  
  Args:
    rules: List of business rules to compile
    output_format: "policies" for PolicyRule list, "full" for detailed results
  
  Returns:
    List of PolicyRule objects or full compilation results
  """
  compiler = PolicyCompiler()
  results = []
  
  for rule in rules:
    result = compiler.compile(rule)
    results.append(result)
  
  if output_format == "policies":
    return [r.policy_rule for r in results if not r.validation_errors]
  else:
    return {
      "compiled": len([r for r in results if not r.validation_errors]),
      "failed": len([r for r in results if r.validation_errors]),
      "results": [r.dict() for r in results]
    }