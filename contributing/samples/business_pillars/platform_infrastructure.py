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

"""Platform & Infrastructure Pillar - Keep the machine running."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep


class OrchestratorKernel(BusinessPillarAgent):
  """Agent for orchestrating and managing the platform."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="orchestrator_kernel",
      role=AgentRole.PLANNER,
      pillar=PillarType.PLATFORM_INFRASTRUCTURE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("orchestrate_workflow", self._orchestrate_workflow, cost=1.0)
    self.register_tool("manage_resources", self._manage_resources, cost=0.8)
    self.register_tool("coordinate_pillars", self._coordinate_pillars, cost=1.5)
  
  async def _orchestrate_workflow(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
    workflow_id = f"ORCH-{uuid.uuid4().hex[:8]}"
    return {
      "workflow_id": workflow_id,
      "status": "orchestrating",
      "involved_pillars": workflow_spec.get("pillars", []),
      "estimated_completion": "30 minutes",
      "started_at": datetime.now().isoformat()
    }
  
  async def _manage_resources(self, resource_type: str, action: str) -> Dict[str, Any]:
    return {
      "resource_type": resource_type,
      "action": action,
      "current_allocation": "75%",
      "target_allocation": "80%",
      "scaling_decision": "scale_up" if action == "scale" else "maintain"
    }
  
  async def _coordinate_pillars(self, coordination_request: Dict[str, Any]) -> Dict[str, Any]:
    return {
      "coordination_id": f"COORD-{uuid.uuid4().hex[:8]}",
      "pillars_involved": coordination_request.get("pillars", []),
      "coordination_type": coordination_request.get("type", "sync"),
      "status": "coordinating"
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "platform_orchestration":
      orchestration = await self._orchestrate_workflow(context.get("workflow_spec", {}))
      resource_mgmt = await self._manage_resources(
        context.get("resource_type", "compute"),
        context.get("action", "monitor")
      )
      coordination = await self._coordinate_pillars(context.get("coordination_request", {}))
      
      return {
        "orchestration": orchestration,
        "resource_management": resource_mgmt,
        "pillar_coordination": coordination
      }
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["workflow_orchestration", "resource_management", "cross_pillar_coordination"]


class SecuritySentinel(BusinessPillarAgent):
  """Agent for security monitoring and incident response."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="security_sentinel",
      role=AgentRole.CRITIC,
      pillar=PillarType.PLATFORM_INFRASTRUCTURE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("monitor_security_events", self._monitor_security_events, cost=0.5)
    self.register_tool("analyze_threats", self._analyze_threats, cost=1.0)
    self.register_tool("respond_to_incident", self._respond_to_incident, cost=2.0)
    self.register_tool("enforce_mtls", self._enforce_mtls, cost=0.3)
  
  async def _monitor_security_events(self, time_window: str = "1h") -> Dict[str, Any]:
    # Mock security monitoring
    events = [
      {"type": "failed_login", "count": 5, "severity": "low"},
      {"type": "privilege_escalation", "count": 1, "severity": "high"},
      {"type": "unusual_network_traffic", "count": 3, "severity": "medium"}
    ]
    
    return {
      "time_window": time_window,
      "events_detected": len(events),
      "events": events,
      "overall_threat_level": "medium"
    }
  
  async def _analyze_threats(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    high_severity_count = sum(1 for event in events if event.get("severity") == "high")
    
    return {
      "threat_analysis": {
        "critical_threats": high_severity_count,
        "attack_patterns": ["brute_force", "lateral_movement"],
        "risk_score": 0.7 if high_severity_count > 0 else 0.3
      },
      "recommended_actions": [
        "Block suspicious IPs",
        "Increase monitoring on affected systems"
      ] if high_severity_count > 0 else ["Continue monitoring"]
    }
  
  async def _respond_to_incident(self, incident_type: str, severity: str) -> Dict[str, Any]:
    incident_id = f"INC-{uuid.uuid4().hex[:8]}"
    
    if severity == "high":
      response_actions = [
        "Isolate affected systems",
        "Notify security team",
        "Begin forensic analysis"
      ]
    else:
      response_actions = [
        "Log incident",
        "Monitor for escalation"
      ]
    
    return {
      "incident_id": incident_id,
      "incident_type": incident_type,
      "severity": severity,
      "response_actions": response_actions,
      "status": "responding",
      "created_at": datetime.now().isoformat()
    }
  
  async def _enforce_mtls(self, service_mesh: str = "istio") -> Dict[str, Any]:
    # Mock mTLS enforcement check
    return {
      "service_mesh": service_mesh,
      "mtls_status": "enforced",
      "compliant_services": 45,
      "non_compliant_services": 2,
      "enforcement_percentage": 95.7
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "security_monitoring":
      events = await self._monitor_security_events()
      threat_analysis = await self._analyze_threats(events["events"])
      mtls_status = await self._enforce_mtls()
      
      # Respond to high-severity incidents
      high_severity_events = [e for e in events["events"] if e["severity"] == "high"]
      incident_responses = []
      
      for event in high_severity_events:
        response = await self._respond_to_incident(event["type"], event["severity"])
        incident_responses.append(response)
      
      return {
        "security_events": events,
        "threat_analysis": threat_analysis,
        "mtls_enforcement": mtls_status,
        "incident_responses": incident_responses
      }
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["security_monitoring", "threat_analysis", "incident_response", "mtls_enforcement"]


class CostOptimizer(BusinessPillarAgent):
  """Agent for cost optimization and resource efficiency."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="cost_optimizer",
      role=AgentRole.WORKER,
      pillar=PillarType.PLATFORM_INFRASTRUCTURE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("analyze_cost_trends", self._analyze_cost_trends, cost=0.8)
    self.register_tool("identify_optimization_opportunities", self._identify_optimization_opportunities, cost=1.0)
    self.register_tool("implement_cost_savings", self._implement_cost_savings, cost=1.5)
    self.register_tool("monitor_cost_alerts", self._monitor_cost_alerts, cost=0.3)
  
  async def _analyze_cost_trends(self, time_period: str = "30d") -> Dict[str, Any]:
    # Mock cost analysis
    return {
      "time_period": time_period,
      "total_cost": 45000,
      "cost_breakdown": {
        "compute": 25000,
        "storage": 8000,
        "networking": 5000,
        "other": 7000
      },
      "trend": "increasing",
      "month_over_month_change": 0.15,  # 15% increase
      "cost_per_user": 12.50
    }
  
  async def _identify_optimization_opportunities(self, cost_data: Dict[str, Any]) -> Dict[str, Any]:
    opportunities = [
      {
        "type": "right_sizing",
        "description": "Downsize over-provisioned instances",
        "potential_savings": 8500,
        "effort": "low"
      },
      {
        "type": "reserved_instances",
        "description": "Convert on-demand to reserved instances",
        "potential_savings": 12000,
        "effort": "medium"
      },
      {
        "type": "unused_resources",
        "description": "Remove unused storage volumes",
        "potential_savings": 3500,
        "effort": "low"
      }
    ]
    
    return {
      "opportunities": opportunities,
      "total_potential_savings": sum(op["potential_savings"] for op in opportunities),
      "priority_recommendations": [op for op in opportunities if op["effort"] == "low"]
    }
  
  async def _implement_cost_savings(self, optimization_plan: Dict[str, Any]) -> Dict[str, Any]:
    implementation_id = f"COST-OPT-{uuid.uuid4().hex[:8]}"
    
    return {
      "implementation_id": implementation_id,
      "optimizations_applied": optimization_plan.get("selected_optimizations", []),
      "estimated_monthly_savings": optimization_plan.get("target_savings", 5000),
      "implementation_status": "in_progress",
      "completion_eta": "3 business days"
    }
  
  async def _monitor_cost_alerts(self, alert_thresholds: Dict[str, float]) -> Dict[str, Any]:
    # Mock cost alert monitoring
    current_monthly_spend = 47500
    monthly_budget = 45000
    
    alerts = []
    if current_monthly_spend > monthly_budget:
      alerts.append({
        "type": "budget_exceeded",
        "severity": "high",
        "message": f"Monthly spend ${current_monthly_spend} exceeds budget ${monthly_budget}",
        "variance": ((current_monthly_spend - monthly_budget) / monthly_budget) * 100
      })
    
    return {
      "alerts": alerts,
      "current_spend": current_monthly_spend,
      "budget": monthly_budget,
      "alert_triggered": len(alerts) > 0
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "cost_optimization":
      cost_analysis = await self._analyze_cost_trends()
      opportunities = await self._identify_optimization_opportunities(cost_analysis)
      alerts = await self._monitor_cost_alerts(context.get("alert_thresholds", {}))
      
      # Implement high-priority optimizations if alerts triggered
      if alerts["alert_triggered"]:
        optimization_plan = {
          "selected_optimizations": opportunities["priority_recommendations"],
          "target_savings": sum(op["potential_savings"] for op in opportunities["priority_recommendations"])
        }
        implementation = await self._implement_cost_savings(optimization_plan)
        
        return {
          "cost_analysis": cost_analysis,
          "optimization_opportunities": opportunities,
          "cost_alerts": alerts,
          "implementation": implementation
        }
      else:
        return {
          "cost_analysis": cost_analysis,
          "optimization_opportunities": opportunities,
          "cost_alerts": alerts
        }
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["cost_analysis", "optimization_identification", "automated_cost_savings", "budget_monitoring"]


class PlatformInfrastructurePillar(BusinessPillar):
  """Platform & Infrastructure pillar coordinating platform operations."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.PLATFORM_INFRASTRUCTURE, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    self.register_agent(OrchestratorKernel(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(SecuritySentinel(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(CostOptimizer(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
  
  async def execute_workflow(self, workflow_type: str, inputs: Dict[str, Any], requester: Optional[str] = None) -> WorkflowResult:
    """Execute platform workflows."""
    workflow_id = f"platform_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "platform_health_check":
      return await self._execute_platform_health_check(workflow, inputs)
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_platform_health_check(self, workflow: WorkflowResult, inputs: Dict[str, Any]) -> WorkflowResult:
    """Execute comprehensive platform health check."""
    try:
      # Step 1: Security monitoring
      security_sentinel = self.get_agent(AgentRole.CRITIC)
      step1 = WorkflowStep(
        step_id="security_check",
        agent_role=AgentRole.CRITIC,
        action="security_monitoring",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      security_results = await security_sentinel.execute_task("security_monitoring", inputs, workflow.workflow_id)
      step1.complete(security_results)
      
      # Step 2: Cost optimization
      cost_optimizer = self.get_agent(AgentRole.WORKER)
      step2 = WorkflowStep(
        step_id="cost_optimization",
        agent_role=AgentRole.WORKER,
        action="cost_optimization",
        inputs=inputs
      )
      step2.start()
      workflow.add_step(step2)
      
      cost_results = await cost_optimizer.execute_task("cost_optimization", inputs, workflow.workflow_id)
      step2.complete(cost_results)
      
      # Step 3: Platform orchestration
      orchestrator = self.get_agent(AgentRole.PLANNER)
      step3 = WorkflowStep(
        step_id="orchestration_check",
        agent_role=AgentRole.PLANNER,
        action="platform_orchestration",
        inputs=inputs
      )
      step3.start()
      workflow.add_step(step3)
      
      orchestration_results = await orchestrator.execute_task("platform_orchestration", inputs, workflow.workflow_id)
      step3.complete(orchestration_results)
      
      workflow.complete({
        "security_check": security_results,
        "cost_optimization": cost_results,
        "orchestration": orchestration_results
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    return ["platform_health_check"]