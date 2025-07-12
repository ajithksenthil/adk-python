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

from ..tools.function_tool import FunctionTool
from .base_pillar_agent import BasePillarAgent, PillarCapability


class ITPillarAgent(BasePillarAgent):
  """IT pillar agent for managing technology operations."""
  
  def __init__(self, **kwargs):
    """Initialize the IT pillar agent."""
    kwargs.setdefault("pillar_name", "Information Technology")
    kwargs.setdefault(
        "pillar_description",
        "Managing technology infrastructure, applications, security, "
        "and digital transformation initiatives",
    )
    kwargs.setdefault(
        "cross_pillar_dependencies", ["Finance", "Operations", "Security", "All"]
    )
    
    super().__init__(**kwargs)
    self._add_it_capabilities()
    self._initialize_it_metrics()
  
  def _add_domain_specific_tools(self):
    """Add IT-specific tools."""
    it_tools = [
        FunctionTool(
            name="monitor_system_health",
            description="Monitor IT system health and performance",
            func=lambda system=None: {
                "overall_health": 95.0,  # %
                "uptime": 99.9,  # %
                "response_time": 120,  # ms
                "active_incidents": 3,
                "systems_monitored": 150,
            },
        ),
        FunctionTool(
            name="assess_security_posture",
            description="Assess cybersecurity posture",
            func=lambda: {
                "security_score": 88.0,  # %
                "vulnerabilities": {"critical": 0, "high": 2, "medium": 15, "low": 45},
                "last_incident": "30 days ago",
                "compliance_status": "compliant",
            },
        ),
        FunctionTool(
            name="manage_it_projects",
            description="Manage IT projects and initiatives",
            func=lambda: {
                "active_projects": 25,
                "on_schedule": 20,
                "at_risk": 3,
                "delayed": 2,
                "total_budget": 5000000,
                "budget_utilization": 78.0,  # %
            },
        ),
    ]
    
    self.tools.extend(it_tools)
  
  def _add_it_capabilities(self):
    """Add IT capabilities."""
    capabilities = [
        PillarCapability(
            name="infrastructure_management",
            description="Manage IT infrastructure and operations",
            required_tools=["monitor_system_health"],
        ),
        PillarCapability(
            name="cybersecurity",
            description="Ensure cybersecurity and compliance",
            required_tools=["assess_security_posture"],
        ),
        PillarCapability(
            name="project_delivery",
            description="Deliver IT projects and initiatives",
            required_tools=["manage_it_projects"],
        ),
    ]
    
    for cap in capabilities:
      self.add_capability(cap)
  
  def _initialize_it_metrics(self):
    """Initialize IT metrics."""
    self.update_metric("system_uptime", 99.9)  # %
    self.update_metric("security_score", 88.0)  # %
    self.update_metric("project_success_rate", 80.0)  # %
    self.update_metric("it_cost_per_employee", 2500.0)  # $
    
    self.set_target("system_uptime", 99.95)
    self.set_target("security_score", 95.0)
    self.set_target("project_success_rate", 90.0)
    self.set_target("it_cost_per_employee", 2200.0)