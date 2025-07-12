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

from typing import Any, Dict, List, Optional

from pydantic import Field

from ..agents.llm_agent import LlmAgent
from ..tools.function_tool import FunctionTool
from .base_pillar_agent import BasePillarAgent


class PillarOrchestrator(LlmAgent):
  """Orchestrator for coordinating multiple business pillar agents.
  
  This agent manages cross-pillar initiatives, resolves dependencies,
  and ensures aligned execution across all business functions.
  """
  
  pillar_agents: Dict[str, BasePillarAgent] = Field(
      default_factory=dict,
      description="Map of pillar names to their agents",
  )
  
  def __init__(self, **kwargs):
    """Initialize the pillar orchestrator."""
    # Set default instruction
    if "instruction" not in kwargs:
      kwargs["instruction"] = (
          "I am the Business Pillar Orchestrator responsible for coordinating "
          "across all business functions (Finance, Operations, Marketing, HR, IT). "
          "I ensure aligned execution, resolve cross-functional dependencies, "
          "and optimize overall business performance through integrated planning "
          "and execution."
      )
    
    # Extract pillar agents if provided in sub_agents
    if "sub_agents" in kwargs:
      pillar_agents = {}
      for agent in kwargs["sub_agents"]:
        if isinstance(agent, BasePillarAgent):
          pillar_agents[agent.pillar_name] = agent
      kwargs["pillar_agents"] = pillar_agents
    
    super().__init__(**kwargs)
    
    # Add orchestrator tools
    self._add_orchestrator_tools()
  
  def _add_orchestrator_tools(self):
    """Add orchestrator-specific tools."""
    orchestrator_tools = [
        FunctionTool(
            name="get_enterprise_health",
            description="Get overall enterprise health across all pillars",
            func=self._get_enterprise_health,
        ),
        FunctionTool(
            name="coordinate_cross_pillar_initiative",
            description="Coordinate initiative across multiple pillars",
            func=self._coordinate_initiative,
        ),
        FunctionTool(
            name="resolve_pillar_conflict",
            description="Resolve conflicts between pillar objectives",
            func=self._resolve_conflict,
        ),
        FunctionTool(
            name="optimize_resource_allocation",
            description="Optimize resource allocation across pillars",
            func=self._optimize_resources,
        ),
        FunctionTool(
            name="generate_executive_dashboard",
            description="Generate executive dashboard with key metrics",
            func=self._generate_dashboard,
        ),
        FunctionTool(
            name="analyze_pillar_dependencies",
            description="Analyze dependencies between pillars",
            func=self._analyze_dependencies,
        ),
    ]
    
    if self.tools:
      self.tools.extend(orchestrator_tools)
    else:
      self.tools = orchestrator_tools
  
  def register_pillar(self, pillar_agent: BasePillarAgent):
    """Register a pillar agent with the orchestrator.
    
    Args:
        pillar_agent: The pillar agent to register
    """
    self.pillar_agents[pillar_agent.pillar_name] = pillar_agent
    
    # Add as sub-agent if not already present
    if pillar_agent not in self.sub_agents:
      self.sub_agents.append(pillar_agent)
  
  def _get_enterprise_health(self) -> Dict[str, Any]:
    """Get overall enterprise health metrics."""
    pillar_health = {}
    overall_scores = []
    all_alerts = []
    
    for pillar_name, pillar_agent in self.pillar_agents.items():
      metrics = pillar_agent.get_metrics()
      pillar_health[pillar_name] = {
          "health_score": metrics["health_score"],
          "alerts": len(metrics["alerts"]),
          "kpi_summary": metrics["kpis"],
      }
      overall_scores.append(metrics["health_score"])
      all_alerts.extend(
          [f"{pillar_name}: {alert}" for alert in metrics["alerts"]]
      )
    
    # Calculate enterprise health score
    enterprise_score = (
        sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
    )
    
    return {
        "enterprise_health_score": round(enterprise_score, 2),
        "pillar_health": pillar_health,
        "total_alerts": len(all_alerts),
        "critical_alerts": all_alerts[:5],  # Top 5 alerts
        "pillars_below_target": [
            name
            for name, health in pillar_health.items()
            if health["health_score"] < 85.0
        ],
    }
  
  def _coordinate_initiative(
      self,
      initiative_name: str,
      required_pillars: List[str],
      objectives: Dict[str, str],
  ) -> Dict[str, Any]:
    """Coordinate a cross-pillar initiative."""
    coordination_plan = {
        "initiative": initiative_name,
        "status": "planning",
        "pillar_assignments": {},
        "dependencies": [],
        "timeline": {},
        "risks": [],
    }
    
    # Check pillar availability and capabilities
    for pillar_name in required_pillars:
      if pillar_name in self.pillar_agents:
        pillar = self.pillar_agents[pillar_name]
        pillar_objective = objectives.get(pillar_name, "Support initiative")
        
        coordination_plan["pillar_assignments"][pillar_name] = {
            "objective": pillar_objective,
            "status": "assigned",
            "capabilities": [cap.name for cap in pillar.capabilities[:3]],
        }
        
        # Check dependencies
        for dep in pillar.cross_pillar_dependencies:
          if dep in required_pillars and dep != pillar_name:
            coordination_plan["dependencies"].append(
                f"{pillar_name} depends on {dep}"
            )
    
    # Generate timeline
    coordination_plan["timeline"] = {
        "planning": "Week 1-2",
        "execution": "Week 3-8",
        "monitoring": "Week 9-12",
        "review": "Week 13",
    }
    
    # Identify risks
    if len(required_pillars) > 3:
      coordination_plan["risks"].append("High coordination complexity")
    if "IT" in required_pillars:
      coordination_plan["risks"].append("Technical implementation dependencies")
    
    return coordination_plan
  
  def _resolve_conflict(
      self,
      pillar1: str,
      pillar2: str,
      conflict_type: str,
      details: Optional[str] = None,
  ) -> Dict[str, Any]:
    """Resolve conflicts between pillars."""
    resolution = {
        "conflict": {
            "between": [pillar1, pillar2],
            "type": conflict_type,
            "details": details,
        },
        "analysis": {},
        "resolution_options": [],
        "recommendation": "",
    }
    
    # Analyze conflict based on type
    if conflict_type == "resource":
      resolution["analysis"] = {
          "resource_demand": "Both pillars competing for same resources",
          "impact": "Potential delays in both pillar objectives",
      }
      resolution["resolution_options"] = [
          "Prioritize based on strategic importance",
          "Find alternative resources",
          "Phase implementation to avoid overlap",
      ]
      resolution["recommendation"] = "Phase implementation with Finance first"
      
    elif conflict_type == "priority":
      resolution["analysis"] = {
          "priority_conflict": "Conflicting strategic priorities",
          "impact": "Misaligned execution",
      }
      resolution["resolution_options"] = [
          "Align with overall strategy",
          "Create integrated approach",
          "Escalate to executive team",
      ]
      resolution["recommendation"] = "Create integrated approach"
    
    return resolution
  
  def _optimize_resources(
      self, optimization_goal: str = "efficiency"
  ) -> Dict[str, Any]:
    """Optimize resource allocation across pillars."""
    current_allocation = {}
    optimized_allocation = {}
    
    # Simulate current allocation
    total_resources = 10000000  # $10M budget
    pillar_weights = {
        "Operations": 0.30,
        "IT": 0.25,
        "Marketing": 0.20,
        "Finance": 0.15,
        "HR": 0.10,
    }
    
    for pillar, weight in pillar_weights.items():
      current_allocation[pillar] = total_resources * weight
    
    # Optimize based on goal
    if optimization_goal == "efficiency":
      # Reallocate based on health scores
      for pillar_name, pillar_agent in self.pillar_agents.items():
        if pillar_name in current_allocation:
          health = pillar_agent.metrics.kpis.get("efficiency", 80.0)
          adjustment = (100 - health) / 100 * 0.1  # Up to 10% adjustment
          optimized_allocation[pillar_name] = current_allocation[pillar_name] * (
              1 + adjustment
          )
    else:
      optimized_allocation = current_allocation
    
    return {
        "optimization_goal": optimization_goal,
        "current_allocation": current_allocation,
        "optimized_allocation": optimized_allocation,
        "total_budget": total_resources,
        "expected_improvement": "8-12% efficiency gain",
        "implementation_steps": [
            "Review and approve reallocation",
            "Communicate changes to pillar leads",
            "Implement phased transition",
            "Monitor impact metrics",
        ],
    }
  
  def _generate_dashboard(self) -> Dict[str, Any]:
    """Generate executive dashboard."""
    health_data = self._get_enterprise_health()
    
    dashboard = {
        "executive_summary": {
            "enterprise_health": health_data["enterprise_health_score"],
            "trend": "improving" if health_data["enterprise_health_score"] > 85 else "declining",
            "alerts": health_data["total_alerts"],
        },
        "pillar_performance": {},
        "key_initiatives": [
            {"name": "Digital Transformation", "status": "on_track", "completion": 65},
            {"name": "Cost Optimization", "status": "ahead", "completion": 78},
            {"name": "Market Expansion", "status": "at_risk", "completion": 45},
        ],
        "financial_highlights": {
            "revenue_ytd": "$50M",
            "expenses_ytd": "$42M",
            "profit_margin": "16%",
            "cash_position": "Strong",
        },
        "recommendations": [],
    }
    
    # Add pillar performance
    for pillar_name, health in health_data["pillar_health"].items():
      dashboard["pillar_performance"][pillar_name] = {
          "health": health["health_score"],
          "status": "healthy" if health["health_score"] > 85 else "needs_attention",
      }
    
    # Generate recommendations
    if health_data["pillars_below_target"]:
      dashboard["recommendations"].append(
          f"Focus on improving: {', '.join(health_data['pillars_below_target'])}"
      )
    
    return dashboard
  
  def _analyze_dependencies(self) -> Dict[str, Any]:
    """Analyze dependencies between pillars."""
    dependency_matrix = {}
    critical_paths = []
    
    # Build dependency matrix
    for pillar_name, pillar_agent in self.pillar_agents.items():
      dependency_matrix[pillar_name] = {
          "depends_on": pillar_agent.cross_pillar_dependencies,
          "depended_by": [],
      }
    
    # Find reverse dependencies
    for pillar_name, deps in dependency_matrix.items():
      for dep in deps["depends_on"]:
        if dep in dependency_matrix:
          dependency_matrix[dep]["depended_by"].append(pillar_name)
    
    # Identify critical paths
    for pillar_name, deps in dependency_matrix.items():
      if len(deps["depended_by"]) >= 3:
        critical_paths.append({
            "pillar": pillar_name,
            "impact": f"Critical for {len(deps['depended_by'])} other pillars",
            "risk": "Single point of failure",
        })
    
    return {
        "dependency_matrix": dependency_matrix,
        "critical_paths": critical_paths,
        "recommendations": [
            "Ensure redundancy for critical path pillars",
            "Regular cross-pillar sync meetings",
            "Establish clear SLAs between dependent pillars",
        ],
    }