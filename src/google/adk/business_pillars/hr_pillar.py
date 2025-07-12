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


class HRPillarAgent(BasePillarAgent):
  """HR pillar agent for managing human resources."""
  
  def __init__(self, **kwargs):
    """Initialize the HR pillar agent."""
    kwargs.setdefault("pillar_name", "Human Resources")
    kwargs.setdefault(
        "pillar_description",
        "Managing talent acquisition, development, compensation, "
        "and employee experience across the organization",
    )
    kwargs.setdefault(
        "cross_pillar_dependencies", ["Finance", "IT", "Legal", "Operations"]
    )
    
    super().__init__(**kwargs)
    self._add_hr_capabilities()
    self._initialize_hr_metrics()
  
  def _add_domain_specific_tools(self):
    """Add HR-specific tools."""
    hr_tools = [
        FunctionTool(
            name="analyze_workforce",
            description="Analyze workforce composition and trends",
            func=lambda dept=None: {
                "total_employees": 5000,
                "departments": 12,
                "avg_tenure": 3.5,
                "diversity_index": 0.75,
                "trends": ["Remote work preference", "Skill gap in AI/ML"],
            },
        ),
        FunctionTool(
            name="manage_talent_pipeline",
            description="Manage recruitment and talent pipeline",
            func=lambda role: {
                "open_positions": 50,
                "candidates_in_pipeline": 250,
                "avg_time_to_hire": 35,  # days
                "offer_acceptance_rate": 85.0,  # %
            },
        ),
        FunctionTool(
            name="assess_employee_engagement",
            description="Assess employee engagement and satisfaction",
            func=lambda: {
                "engagement_score": 78.0,  # %
                "satisfaction_score": 82.0,  # %
                "retention_rate": 90.0,  # %
                "key_drivers": ["Career growth", "Work-life balance", "Compensation"],
            },
        ),
    ]
    
    self.tools.extend(hr_tools)
  
  def _add_hr_capabilities(self):
    """Add HR capabilities."""
    capabilities = [
        PillarCapability(
            name="talent_acquisition",
            description="Recruit and onboard talent",
            required_tools=["manage_talent_pipeline"],
        ),
        PillarCapability(
            name="employee_development",
            description="Develop and retain employees",
            required_tools=["analyze_workforce"],
        ),
        PillarCapability(
            name="engagement_management",
            description="Manage employee engagement and culture",
            required_tools=["assess_employee_engagement"],
        ),
    ]
    
    for cap in capabilities:
      self.add_capability(cap)
  
  def _initialize_hr_metrics(self):
    """Initialize HR metrics."""
    self.update_metric("employee_retention", 90.0)  # %
    self.update_metric("time_to_hire", 35.0)  # days
    self.update_metric("engagement_score", 78.0)  # %
    self.update_metric("training_roi", 180.0)  # %
    
    self.set_target("employee_retention", 92.0)
    self.set_target("time_to_hire", 30.0)
    self.set_target("engagement_score", 85.0)
    self.set_target("training_roi", 200.0)