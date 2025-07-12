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


class MarketingPillarAgent(BasePillarAgent):
  """Marketing pillar agent for managing marketing operations."""
  
  def __init__(self, **kwargs):
    """Initialize the Marketing pillar agent."""
    kwargs.setdefault("pillar_name", "Marketing")
    kwargs.setdefault(
        "pillar_description",
        "Managing brand, campaigns, customer acquisition, "
        "and market analysis for the organization",
    )
    kwargs.setdefault(
        "cross_pillar_dependencies", ["Finance", "Operations", "IT", "Sales"]
    )
    
    super().__init__(**kwargs)
    self._add_marketing_capabilities()
    self._initialize_marketing_metrics()
  
  def _add_domain_specific_tools(self):
    """Add marketing-specific tools."""
    marketing_tools = [
        FunctionTool(
            name="analyze_campaign_performance",
            description="Analyze marketing campaign performance",
            func=lambda campaign_id: {
                "campaign_id": campaign_id,
                "metrics": {
                    "impressions": 1000000,
                    "clicks": 50000,
                    "conversions": 2500,
                    "roi": 250.0,
                },
            },
        ),
        FunctionTool(
            name="segment_customers",
            description="Segment customers for targeted marketing",
            func=lambda criteria: {
                "segments": [
                    {"name": "high_value", "size": 1000, "avg_ltv": 5000},
                    {"name": "growth", "size": 5000, "avg_ltv": 1000},
                    {"name": "at_risk", "size": 2000, "avg_ltv": 800},
                ]
            },
        ),
        FunctionTool(
            name="analyze_market_trends",
            description="Analyze market trends and opportunities",
            func=lambda market: {
                "market": market,
                "trends": ["Digital transformation", "Sustainability focus"],
                "opportunities": ["New demographic emerging", "Competitor weakness"],
            },
        ),
    ]
    
    self.tools.extend(marketing_tools)
  
  def _add_marketing_capabilities(self):
    """Add marketing capabilities."""
    capabilities = [
        PillarCapability(
            name="campaign_management",
            description="Plan and execute marketing campaigns",
            required_tools=["analyze_campaign_performance"],
        ),
        PillarCapability(
            name="customer_analytics",
            description="Analyze customer behavior and segments",
            required_tools=["segment_customers"],
        ),
        PillarCapability(
            name="market_intelligence",
            description="Gather and analyze market intelligence",
            required_tools=["analyze_market_trends"],
        ),
    ]
    
    for cap in capabilities:
      self.add_capability(cap)
  
  def _initialize_marketing_metrics(self):
    """Initialize marketing metrics."""
    self.update_metric("customer_acquisition_cost", 150.0)
    self.update_metric("customer_lifetime_value", 1500.0)
    self.update_metric("brand_awareness", 65.0)  # %
    self.update_metric("campaign_roi", 250.0)  # %
    
    self.set_target("customer_acquisition_cost", 120.0)
    self.set_target("customer_lifetime_value", 2000.0)
    self.set_target("brand_awareness", 75.0)
    self.set_target("campaign_roi", 300.0)