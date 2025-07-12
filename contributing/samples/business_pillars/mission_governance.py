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

"""Mission & Governance Pillar - Set direction, allocate capital, stay compliant."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep

logger = logging.getLogger(__name__)


class BudgetGovernor(BusinessPillarAgent):
  """Agent responsible for budget allocation and capital deployment."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="budget_governor",
      role=AgentRole.WORKER,
      pillar=PillarType.MISSION_GOVERNANCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup budget governance tools."""
    self.register_tool("check_budget_allocation", self._check_budget_allocation, cost=0.1)
    self.register_tool("approve_expenditure", self._approve_expenditure, cost=0.5)
    self.register_tool("create_budget_proposal", self._create_budget_proposal, cost=1.0)
    self.register_tool("execute_multisig_transaction", self._execute_multisig_transaction, cost=2.0)
    self.register_tool("calculate_var_exposure", self._calculate_var_exposure, cost=0.3)
  
  async def _check_budget_allocation(
    self,
    pillar: str,
    period: str = "monthly"
  ) -> Dict[str, Any]:
    """Check budget allocation for a pillar."""
    # Mock implementation - would integrate with treasury/ERP
    allocations = {
      "Growth Engine": {"monthly": 50000, "daily": 2000},
      "Product & Experience": {"monthly": 80000, "daily": 3000},
      "Customer Success": {"monthly": 30000, "daily": 1200},
      "Resource & Supply": {"monthly": 100000, "daily": 4000},
      "People & Culture": {"monthly": 120000, "daily": 4500},
      "Intelligence & Improvement": {"monthly": 40000, "daily": 1500},
      "Platform & Infra": {"monthly": 60000, "daily": 2500}
    }
    
    return {
      "pillar": pillar,
      "period": period,
      "allocated": allocations.get(pillar, {}).get(period, 0),
      "spent": allocations.get(pillar, {}).get(period, 0) * 0.65,  # Mock 65% utilization
      "remaining": allocations.get(pillar, {}).get(period, 0) * 0.35,
      "utilization_rate": 0.65
    }
  
  async def _approve_expenditure(
    self,
    pillar: str,
    amount: float,
    purpose: str,
    urgency: str = "normal"
  ) -> Dict[str, Any]:
    """Approve or reject an expenditure request."""
    # Check against daily limits and policies
    budget_check = await self._check_budget_allocation(pillar, "daily")
    
    approval_thresholds = {
      "low": 500,
      "normal": 2000,
      "high": 10000
    }
    
    threshold = approval_thresholds.get(urgency, 2000)
    remaining = budget_check["remaining"]
    
    if amount <= threshold and amount <= remaining:
      status = "approved"
      reason = "Within budget and threshold limits"
    elif amount <= remaining:
      status = "requires_board_approval"
      reason = f"Exceeds {urgency} threshold of ${threshold}"
    else:
      status = "rejected"
      reason = f"Exceeds remaining budget of ${remaining}"
    
    return {
      "request_id": str(uuid.uuid4()),
      "pillar": pillar,
      "amount": amount,
      "purpose": purpose,
      "status": status,
      "reason": reason,
      "approved_amount": amount if status == "approved" else 0,
      "timestamp": datetime.now().isoformat()
    }
  
  async def _create_budget_proposal(
    self,
    pillar: str,
    period: str,
    requested_amount: float,
    justification: str
  ) -> Dict[str, Any]:
    """Create a budget proposal for board review."""
    proposal_id = str(uuid.uuid4())
    
    # Calculate variance from current allocation
    current = await self._check_budget_allocation(pillar, period)
    variance = requested_amount - current["allocated"]
    variance_percent = (variance / current["allocated"]) * 100 if current["allocated"] > 0 else 0
    
    return {
      "proposal_id": proposal_id,
      "pillar": pillar,
      "period": period,
      "current_allocation": current["allocated"],
      "requested_amount": requested_amount,
      "variance": variance,
      "variance_percent": variance_percent,
      "justification": justification,
      "status": "pending_review",
      "created_at": datetime.now().isoformat(),
      "requires_board_vote": abs(variance_percent) > 20  # >20% change needs board vote
    }
  
  async def _execute_multisig_transaction(
    self,
    transaction_type: str,
    amount: float,
    recipient: str,
    signers_required: int = 3
  ) -> Dict[str, Any]:
    """Execute a multisig transaction via Gnosis Safe or similar."""
    # Mock implementation - would integrate with actual blockchain
    tx_id = str(uuid.uuid4())
    
    return {
      "transaction_id": tx_id,
      "type": transaction_type,
      "amount": amount,
      "recipient": recipient,
      "signers_required": signers_required,
      "signers_collected": 0,
      "status": "pending_signatures",
      "safe_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
      "created_at": datetime.now().isoformat()
    }
  
  async def _calculate_var_exposure(
    self,
    portfolio: str = "treasury",
    confidence_level: float = 0.95,
    time_horizon_days: int = 1
  ) -> Dict[str, Any]:
    """Calculate Value at Risk for treasury exposure."""
    # Mock VaR calculation
    base_value = 1000000  # $1M treasury
    daily_volatility = 0.02  # 2% daily vol
    
    # Simple VaR calculation (would use proper risk models in production)
    z_score = 1.645 if confidence_level == 0.95 else 2.33  # 95% or 99%
    var_amount = base_value * daily_volatility * z_score * (time_horizon_days ** 0.5)
    
    return {
      "portfolio": portfolio,
      "portfolio_value": base_value,
      "confidence_level": confidence_level,
      "time_horizon_days": time_horizon_days,
      "var_amount": var_amount,
      "var_percentage": (var_amount / base_value) * 100,
      "risk_limit": base_value * 0.05,  # 5% risk limit
      "within_limit": var_amount <= (base_value * 0.05),
      "calculated_at": datetime.now().isoformat()
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute budget governance tasks."""
    if task == "review_budget_request":
      return await self._approve_expenditure(
        pillar=context["pillar"],
        amount=context["amount"],
        purpose=context["purpose"],
        urgency=context.get("urgency", "normal")
      )
    
    elif task == "monitor_var_limits":
      var_result = await self._calculate_var_exposure()
      if not var_result["within_limit"]:
        # Alert risk auditor
        await self.publish_event(
          "risk.var_limit_breach",
          {
            "var_amount": var_result["var_amount"],
            "risk_limit": var_result["risk_limit"],
            "portfolio": var_result["portfolio"]
          },
          trace_id=workflow_id
        )
      return var_result
    
    elif task == "allocate_quarterly_budget":
      proposals = []
      for pillar in ["Growth Engine", "Product & Experience", "Customer Success"]:
        proposal = await self._create_budget_proposal(
          pillar=pillar,
          period="quarterly",
          requested_amount=context.get(f"{pillar}_budget", 150000),
          justification=context.get(f"{pillar}_justification", "Standard allocation")
        )
        proposals.append(proposal)
      
      return {"proposals": proposals, "total_requested": sum(p["requested_amount"] for p in proposals)}
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get budget governor capabilities."""
    return [
      "budget_allocation_review",
      "expenditure_approval",
      "multisig_transaction_execution",
      "var_risk_monitoring",
      "treasury_management",
      "board_proposal_creation"
    ]


class RiskAuditor(BusinessPillarAgent):
  """Agent responsible for risk monitoring and compliance auditing."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="risk_auditor",
      role=AgentRole.CRITIC,
      pillar=PillarType.MISSION_GOVERNANCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup risk auditing tools."""
    self.register_tool("assess_operational_risk", self._assess_operational_risk, cost=0.5)
    self.register_tool("compliance_check", self._compliance_check, cost=0.3)
    self.register_tool("generate_risk_report", self._generate_risk_report, cost=1.0)
    self.register_tool("audit_policy_adherence", self._audit_policy_adherence, cost=0.8)
    self.register_tool("monitor_anomalies", self._monitor_anomalies, cost=0.4)
  
  async def _assess_operational_risk(
    self,
    pillar: str,
    time_period: str = "7d"
  ) -> Dict[str, Any]:
    """Assess operational risk for a pillar."""
    # Mock risk assessment - would integrate with actual monitoring systems
    risk_factors = {
      "Growth Engine": {"spend_variance": 0.15, "conversion_drop": 0.05, "market_volatility": 0.10},
      "Product & Experience": {"bug_rate": 0.08, "deployment_failures": 0.03, "user_complaints": 0.12},
      "Customer Success": {"churn_spike": 0.20, "response_time": 0.06, "satisfaction_drop": 0.15},
      "Platform & Infra": {"uptime_risk": 0.02, "security_events": 0.04, "capacity_strain": 0.08}
    }
    
    factors = risk_factors.get(pillar, {"unknown_pillar": 0.50})
    
    # Calculate composite risk score
    risk_score = sum(factors.values()) / len(factors)
    risk_level = "low" if risk_score < 0.1 else "medium" if risk_score < 0.2 else "high"
    
    return {
      "pillar": pillar,
      "time_period": time_period,
      "risk_factors": factors,
      "composite_risk_score": risk_score,
      "risk_level": risk_level,
      "recommendations": self._get_risk_recommendations(risk_level, factors),
      "assessed_at": datetime.now().isoformat()
    }
  
  def _get_risk_recommendations(self, risk_level: str, factors: Dict[str, float]) -> List[str]:
    """Get risk mitigation recommendations."""
    recommendations = []
    
    if risk_level == "high":
      recommendations.append("Implement enhanced monitoring and controls")
      recommendations.append("Consider reducing autonomy level until risk subsides")
    
    # Factor-specific recommendations
    for factor, score in factors.items():
      if score > 0.15:
        if "spend" in factor:
          recommendations.append("Review budget controls and approval thresholds")
        elif "security" in factor:
          recommendations.append("Conduct security audit and implement additional safeguards")
        elif "churn" in factor:
          recommendations.append("Activate customer retention protocols")
    
    return recommendations
  
  async def _compliance_check(
    self,
    regulation: str,
    scope: str = "company-wide"
  ) -> Dict[str, Any]:
    """Perform compliance check against regulations."""
    # Mock compliance check
    regulations = {
      "SOX": {"data_retention": 0.95, "financial_controls": 0.88, "audit_trail": 0.92},
      "GDPR": {"data_privacy": 0.96, "consent_management": 0.89, "breach_response": 0.94},
      "ISO27001": {"security_controls": 0.91, "incident_response": 0.87, "risk_management": 0.93}
    }
    
    scores = regulations.get(regulation, {"unknown": 0.50})
    overall_score = sum(scores.values()) / len(scores)
    compliant = overall_score >= 0.90
    
    return {
      "regulation": regulation,
      "scope": scope,
      "compliance_scores": scores,
      "overall_score": overall_score,
      "compliant": compliant,
      "non_compliant_areas": [area for area, score in scores.items() if score < 0.90],
      "checked_at": datetime.now().isoformat()
    }
  
  async def _generate_risk_report(
    self,
    report_type: str = "monthly",
    include_pillars: List[str] = None
  ) -> Dict[str, Any]:
    """Generate comprehensive risk report."""
    if include_pillars is None:
      include_pillars = [
        "Growth Engine", "Product & Experience", "Customer Success",
        "Resource & Supply", "People & Culture", "Platform & Infra"
      ]
    
    report = {
      "report_id": str(uuid.uuid4()),
      "report_type": report_type,
      "generated_at": datetime.now().isoformat(),
      "summary": {},
      "pillar_assessments": {},
      "compliance_status": {},
      "recommendations": []
    }
    
    # Assess each pillar
    total_risk = 0
    for pillar in include_pillars:
      assessment = await self._assess_operational_risk(pillar)
      report["pillar_assessments"][pillar] = assessment
      total_risk += assessment["composite_risk_score"]
    
    # Overall risk summary
    avg_risk = total_risk / len(include_pillars)
    report["summary"] = {
      "average_risk_score": avg_risk,
      "overall_risk_level": "low" if avg_risk < 0.1 else "medium" if avg_risk < 0.2 else "high",
      "pillars_high_risk": [
        pillar for pillar, data in report["pillar_assessments"].items()
        if data["risk_level"] == "high"
      ]
    }
    
    # Compliance checks
    for regulation in ["SOX", "GDPR", "ISO27001"]:
      compliance = await self._compliance_check(regulation)
      report["compliance_status"][regulation] = compliance
    
    return report
  
  async def _audit_policy_adherence(
    self,
    pillar: str,
    policies: List[str] = None
  ) -> Dict[str, Any]:
    """Audit adherence to policies."""
    if policies is None:
      policies = ["budget_control", "approval_workflow", "data_privacy", "security_baseline"]
    
    adherence_scores = {}
    for policy in policies:
      # Mock policy adherence check
      if policy == "budget_control":
        adherence_scores[policy] = 0.94  # 94% adherence
      elif policy == "approval_workflow":
        adherence_scores[policy] = 0.89
      elif policy == "data_privacy":
        adherence_scores[policy] = 0.96
      elif policy == "security_baseline":
        adherence_scores[policy] = 0.87
      else:
        adherence_scores[policy] = 0.85
    
    overall_adherence = sum(adherence_scores.values()) / len(adherence_scores)
    
    return {
      "pillar": pillar,
      "policies_audited": policies,
      "adherence_scores": adherence_scores,
      "overall_adherence": overall_adherence,
      "non_compliant_policies": [
        policy for policy, score in adherence_scores.items() if score < 0.90
      ],
      "audit_timestamp": datetime.now().isoformat()
    }
  
  async def _monitor_anomalies(
    self,
    metric_type: str,
    threshold: float = 2.0
  ) -> Dict[str, Any]:
    """Monitor for anomalous behavior."""
    # Mock anomaly detection
    anomalies = []
    
    if metric_type == "spending":
      anomalies.append({
        "pillar": "Growth Engine",
        "metric": "daily_spend",
        "current_value": 3500,
        "expected_value": 2000,
        "z_score": 2.3,
        "anomaly_type": "spike"
      })
    elif metric_type == "performance":
      anomalies.append({
        "pillar": "Platform & Infra",
        "metric": "response_time",
        "current_value": 850,
        "expected_value": 200,
        "z_score": 4.2,
        "anomaly_type": "degradation"
      })
    
    return {
      "metric_type": metric_type,
      "threshold": threshold,
      "anomalies_detected": len(anomalies),
      "anomalies": anomalies,
      "monitoring_timestamp": datetime.now().isoformat()
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute risk auditing tasks."""
    if task == "daily_risk_check":
      pillar = context.get("pillar", "all")
      if pillar == "all":
        # Check all pillars
        results = {}
        for p in ["Growth Engine", "Product & Experience", "Customer Success"]:
          results[p] = await self._assess_operational_risk(p)
        return {"pillar_risks": results}
      else:
        return await self._assess_operational_risk(pillar)
    
    elif task == "compliance_audit":
      regulation = context.get("regulation", "SOX")
      return await self._compliance_check(regulation)
    
    elif task == "anomaly_detection":
      metric_type = context.get("metric_type", "spending")
      anomalies = await self._monitor_anomalies(metric_type)
      
      # Alert if anomalies found
      if anomalies["anomalies_detected"] > 0:
        await self.publish_event(
          "risk.anomalies_detected",
          anomalies,
          trace_id=workflow_id
        )
      
      return anomalies
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get risk auditor capabilities."""
    return [
      "operational_risk_assessment",
      "compliance_monitoring",
      "policy_adherence_auditing",
      "anomaly_detection",
      "risk_reporting",
      "regulatory_compliance"
    ]


class PolicyCompiler(BusinessPillarAgent):
  """Agent responsible for translating business rules into executable policies."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="policy_compiler",
      role=AgentRole.PLANNER,
      pillar=PillarType.MISSION_GOVERNANCE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup policy compilation tools."""
    self.register_tool("compile_business_rule", self._compile_business_rule, cost=0.8)
    self.register_tool("validate_policy", self._validate_policy, cost=0.3)
    self.register_tool("deploy_policy", self._deploy_policy, cost=1.0)
    self.register_tool("update_policy", self._update_policy, cost=0.6)
    self.register_tool("generate_opa_rego", self._generate_opa_rego, cost=0.5)
  
  async def _compile_business_rule(
    self,
    rule_description: str,
    rule_type: str,
    target_pillar: str = "all"
  ) -> Dict[str, Any]:
    """Compile a business rule into a structured policy."""
    rule_id = str(uuid.uuid4())
    
    # Parse rule and generate policy structure
    policy = {
      "rule_id": rule_id,
      "description": rule_description,
      "type": rule_type,
      "target_pillar": target_pillar,
      "conditions": self._parse_rule_conditions(rule_description),
      "actions": self._parse_rule_actions(rule_description),
      "parameters": self._extract_parameters(rule_description),
      "compiled_at": datetime.now().isoformat()
    }
    
    return policy
  
  def _parse_rule_conditions(self, rule_description: str) -> List[Dict[str, Any]]:
    """Parse conditions from rule description."""
    conditions = []
    
    # Simple rule parsing (would use NLP in production)
    if "daily limit" in rule_description.lower():
      conditions.append({
        "type": "threshold",
        "field": "daily_spend",
        "operator": "<=",
        "value": self._extract_amount(rule_description)
      })
    
    if "approval required" in rule_description.lower():
      conditions.append({
        "type": "approval",
        "field": "amount",
        "operator": ">",
        "value": self._extract_approval_threshold(rule_description)
      })
    
    return conditions
  
  def _parse_rule_actions(self, rule_description: str) -> List[str]:
    """Parse actions from rule description."""
    actions = []
    
    if "require approval" in rule_description.lower():
      actions.append("require_approval")
    if "reject" in rule_description.lower():
      actions.append("reject_transaction")
    if "notify" in rule_description.lower():
      actions.append("send_notification")
    
    return actions
  
  def _extract_parameters(self, rule_description: str) -> Dict[str, Any]:
    """Extract parameters from rule description."""
    parameters = {}
    
    # Extract dollar amounts
    amount = self._extract_amount(rule_description)
    if amount:
      parameters["amount_limit"] = amount
    
    # Extract approval threshold
    approval_threshold = self._extract_approval_threshold(rule_description)
    if approval_threshold:
      parameters["approval_threshold"] = approval_threshold
    
    return parameters
  
  def _extract_amount(self, text: str) -> Optional[float]:
    """Extract dollar amount from text."""
    import re
    match = re.search(r'\$([0-9,]+)', text)
    if match:
      return float(match.group(1).replace(',', ''))
    return None
  
  def _extract_approval_threshold(self, text: str) -> Optional[float]:
    """Extract approval threshold from text."""
    # Look for "above $X" or "over $X"
    import re
    match = re.search(r'above \$([0-9,]+)', text)
    if not match:
      match = re.search(r'over \$([0-9,]+)', text)
    if match:
      return float(match.group(1).replace(',', ''))
    return None
  
  async def _validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a compiled policy."""
    validation_result = {
      "policy_id": policy.get("rule_id"),
      "valid": True,
      "errors": [],
      "warnings": []
    }
    
    # Validate required fields
    required_fields = ["rule_id", "description", "type", "conditions", "actions"]
    for field in required_fields:
      if field not in policy:
        validation_result["errors"].append(f"Missing required field: {field}")
        validation_result["valid"] = False
    
    # Validate conditions
    for condition in policy.get("conditions", []):
      if "type" not in condition or "field" not in condition:
        validation_result["errors"].append("Invalid condition structure")
        validation_result["valid"] = False
    
    # Check for potential conflicts
    if policy.get("type") == "budget" and not policy.get("parameters", {}).get("amount_limit"):
      validation_result["warnings"].append("Budget policy without amount limit")
    
    return validation_result
  
  async def _deploy_policy(
    self,
    policy: Dict[str, Any],
    target_environment: str = "production"
  ) -> Dict[str, Any]:
    """Deploy policy to target environment."""
    # Validate first
    validation = await self._validate_policy(policy)
    if not validation["valid"]:
      return {
        "deployed": False,
        "policy_id": policy.get("rule_id"),
        "errors": validation["errors"]
      }
    
    # Generate OPA Rego code
    rego_code = await self._generate_opa_rego(policy)
    
    deployment_result = {
      "deployed": True,
      "policy_id": policy.get("rule_id"),
      "environment": target_environment,
      "rego_code": rego_code,
      "deployed_at": datetime.now().isoformat(),
      "validation_warnings": validation.get("warnings", [])
    }
    
    return deployment_result
  
  async def _update_policy(
    self,
    policy_id: str,
    updates: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Update an existing policy."""
    # Mock policy update
    return {
      "policy_id": policy_id,
      "updated": True,
      "changes": list(updates.keys()),
      "updated_at": datetime.now().isoformat(),
      "version": "1.1"
    }
  
  async def _generate_opa_rego(self, policy: Dict[str, Any]) -> str:
    """Generate OPA Rego code from policy."""
    rule_id = policy.get("rule_id", "unknown")
    rule_type = policy.get("type", "generic")
    
    # Generate basic Rego template
    rego_template = f"""
package adk.{rule_type}

# Generated policy for rule: {rule_id}
# Description: {policy.get('description', 'No description')}

default allow = false

# Main policy rule
allow {{
"""
    
    # Add conditions
    for i, condition in enumerate(policy.get("conditions", [])):
      if condition["type"] == "threshold":
        rego_template += f"""  input.{condition['field']} {condition['operator']} {condition['value']}
"""
    
    rego_template += "}\n"
    
    # Add violation rule
    rego_template += """
# Violation details
violation[{"msg": msg}] {
  not allow
  msg := sprintf("Policy violation: %s", [input.operation])
}
"""
    
    return rego_template.strip()
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute policy compilation tasks."""
    if task == "compile_rule":
      rule_description = context["rule_description"]
      rule_type = context.get("rule_type", "business")
      target_pillar = context.get("target_pillar", "all")
      
      policy = await self._compile_business_rule(rule_description, rule_type, target_pillar)
      return policy
    
    elif task == "deploy_policies":
      policies = context["policies"]
      results = []
      
      for policy in policies:
        result = await self._deploy_policy(policy)
        results.append(result)
      
      return {"deployment_results": results}
    
    elif task == "update_policy_suite":
      updates = context["updates"]
      results = []
      
      for policy_id, update_data in updates.items():
        result = await self._update_policy(policy_id, update_data)
        results.append(result)
      
      return {"update_results": results}
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get policy compiler capabilities."""
    return [
      "business_rule_compilation",
      "policy_validation",
      "opa_rego_generation",
      "policy_deployment",
      "policy_versioning",
      "rule_conflict_detection"
    ]


class MissionGovernancePillar(BusinessPillar):
  """Mission & Governance pillar coordinating governance agents."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.MISSION_GOVERNANCE, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    # Budget Governor (Worker)
    budget_governor = BudgetGovernor(
      control_plane_agent=None,  # Will be set later
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(budget_governor)
    
    # Risk Auditor (Critic)
    risk_auditor = RiskAuditor(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(risk_auditor)
    
    # Policy Compiler (Planner)
    policy_compiler = PolicyCompiler(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(policy_compiler)
  
  async def execute_workflow(
    self,
    workflow_type: str,
    inputs: Dict[str, Any],
    requester: Optional[str] = None
  ) -> WorkflowResult:
    """Execute governance workflows."""
    workflow_id = f"governance_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "budget_allocation_review":
      return await self._execute_budget_allocation_workflow(workflow, inputs)
    
    elif workflow_type == "quarterly_risk_assessment":
      return await self._execute_risk_assessment_workflow(workflow, inputs)
    
    elif workflow_type == "policy_update_cycle":
      return await self._execute_policy_update_workflow(workflow, inputs)
    
    elif workflow_type == "emergency_response":
      return await self._execute_emergency_response_workflow(workflow, inputs)
    
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_budget_allocation_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute budget allocation review workflow."""
    budget_governor = self.get_agent(AgentRole.WORKER)
    risk_auditor = self.get_agent(AgentRole.CRITIC)
    
    try:
      # Step 1: Risk assessment
      step1 = WorkflowStep(
        step_id="risk_assessment",
        agent_role=AgentRole.CRITIC,
        action="assess_operational_risk",
        inputs={"pillar": "all"}
      )
      step1.start()
      workflow.add_step(step1)
      
      risk_result = await risk_auditor.execute_task(
        "daily_risk_check",
        {"pillar": "all"},
        workflow.workflow_id
      )
      step1.complete(risk_result)
      
      # Step 2: Budget allocation
      step2 = WorkflowStep(
        step_id="budget_allocation", 
        agent_role=AgentRole.WORKER,
        action="allocate_quarterly_budget",
        inputs=inputs
      )
      step2.start()
      workflow.add_step(step2)
      
      budget_result = await budget_governor.execute_task(
        "allocate_quarterly_budget",
        inputs,
        workflow.workflow_id
      )
      step2.complete(budget_result)
      
      # Combine results
      final_output = {
        "risk_assessment": risk_result,
        "budget_allocation": budget_result,
        "recommendations": self._generate_allocation_recommendations(risk_result, budget_result)
      }
      
      workflow.complete(final_output)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_risk_assessment_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute quarterly risk assessment workflow."""
    risk_auditor = self.get_agent(AgentRole.CRITIC)
    
    try:
      # Comprehensive risk report
      step1 = WorkflowStep(
        step_id="generate_risk_report",
        agent_role=AgentRole.CRITIC,
        action="generate_risk_report",
        inputs={"report_type": "quarterly"}
      )
      step1.start()
      workflow.add_step(step1)
      
      report = await risk_auditor._generate_risk_report("quarterly")
      step1.complete(report)
      
      workflow.complete({"risk_report": report})
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_policy_update_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute policy update workflow."""
    policy_compiler = self.get_agent(AgentRole.PLANNER)
    
    try:
      # Compile and deploy new policies
      step1 = WorkflowStep(
        step_id="compile_policies",
        agent_role=AgentRole.PLANNER,
        action="compile_rule",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      policy_result = await policy_compiler.execute_task(
        "compile_rule",
        inputs,
        workflow.workflow_id
      )
      step1.complete(policy_result)
      
      workflow.complete({"policy_updates": policy_result})
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_emergency_response_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute emergency response workflow."""
    try:
      # Immediate risk assessment and containment
      emergency_type = inputs.get("emergency_type", "unknown")
      affected_pillar = inputs.get("affected_pillar", "all")
      
      # Step 1: Assess impact
      step1 = WorkflowStep(
        step_id="assess_emergency_impact",
        agent_role=AgentRole.CRITIC,
        action="assess_operational_risk",
        inputs={"pillar": affected_pillar, "emergency": True}
      )
      step1.start()
      workflow.add_step(step1)
      
      # Immediate containment actions
      containment_actions = {
        "security_breach": ["pause_affected_agents", "enable_enhanced_monitoring"],
        "budget_breach": ["freeze_expenditures", "require_manual_approval"],
        "compliance_violation": ["stop_non_compliant_operations", "escalate_to_board"]
      }
      
      actions = containment_actions.get(emergency_type, ["escalate_to_human"])
      
      step1.complete({
        "emergency_type": emergency_type,
        "affected_pillar": affected_pillar,
        "containment_actions": actions,
        "status": "contained"
      })
      
      workflow.complete({
        "emergency_response": "activated",
        "containment_actions": actions
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def _generate_allocation_recommendations(
    self,
    risk_assessment: Dict[str, Any],
    budget_allocation: Dict[str, Any]
  ) -> List[str]:
    """Generate budget allocation recommendations based on risk."""
    recommendations = []
    
    # Check for high-risk pillars
    if "pillar_risks" in risk_assessment:
      for pillar, risk_data in risk_assessment["pillar_risks"].items():
        if risk_data["risk_level"] == "high":
          recommendations.append(f"Consider reducing budget for {pillar} due to elevated risk")
        elif risk_data["risk_level"] == "low":
          recommendations.append(f"Safe to maintain or increase budget for {pillar}")
    
    return recommendations
  
  def get_workflow_types(self) -> List[str]:
    """Get supported workflow types."""
    return [
      "budget_allocation_review",
      "quarterly_risk_assessment", 
      "policy_update_cycle",
      "emergency_response"
    ]