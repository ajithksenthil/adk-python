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

from typing import Dict, List, Optional

from ..tools.function_tool import FunctionTool
from .base_pillar_agent import BasePillarAgent, PillarCapability


class OperationsPillarAgent(BasePillarAgent):
  """Operations pillar agent for managing operational excellence."""
  
  def __init__(self, **kwargs):
    """Initialize the Operations pillar agent."""
    kwargs.setdefault("pillar_name", "Operations")
    kwargs.setdefault(
        "pillar_description",
        "Managing supply chain, production, quality, logistics, "
        "and operational efficiency across the organization",
    )
    kwargs.setdefault(
        "cross_pillar_dependencies", ["Finance", "IT", "HR", "Marketing"]
    )
    
    super().__init__(**kwargs)
    
    # Add operations-specific capabilities
    self._add_operations_capabilities()
    
    # Set up initial metrics
    self._initialize_operations_metrics()
  
  def _add_domain_specific_tools(self):
    """Add operations-specific tools."""
    operations_tools = [
        FunctionTool(
            name="optimize_supply_chain",
            description="Optimize supply chain operations",
            func=self._optimize_supply_chain,
        ),
        FunctionTool(
            name="analyze_production_efficiency",
            description="Analyze production line efficiency",
            func=self._analyze_production_efficiency,
        ),
        FunctionTool(
            name="manage_inventory",
            description="Manage inventory levels and optimization",
            func=self._manage_inventory,
        ),
        FunctionTool(
            name="track_quality_metrics",
            description="Track and analyze quality metrics",
            func=self._track_quality_metrics,
        ),
        FunctionTool(
            name="optimize_logistics",
            description="Optimize logistics and distribution",
            func=self._optimize_logistics,
        ),
        FunctionTool(
            name="forecast_demand",
            description="Forecast product/service demand",
            func=self._forecast_demand,
        ),
        FunctionTool(
            name="analyze_operational_costs",
            description="Analyze and optimize operational costs",
            func=self._analyze_operational_costs,
        ),
    ]
    
    self.tools.extend(operations_tools)
  
  def _add_operations_capabilities(self):
    """Add operations-specific capabilities."""
    capabilities = [
        PillarCapability(
            name="supply_chain_management",
            description="Manage end-to-end supply chain operations",
            required_tools=["optimize_supply_chain", "manage_inventory"],
        ),
        PillarCapability(
            name="production_optimization",
            description="Optimize production processes and efficiency",
            required_tools=["analyze_production_efficiency"],
            dependencies=["supply_chain_management"],
        ),
        PillarCapability(
            name="quality_assurance",
            description="Ensure product/service quality standards",
            required_tools=["track_quality_metrics"],
        ),
        PillarCapability(
            name="logistics_management",
            description="Manage logistics and distribution networks",
            required_tools=["optimize_logistics"],
            dependencies=["supply_chain_management"],
        ),
        PillarCapability(
            name="demand_planning",
            description="Forecast and plan for demand",
            required_tools=["forecast_demand"],
        ),
    ]
    
    for cap in capabilities:
      self.add_capability(cap)
  
  def _initialize_operations_metrics(self):
    """Initialize operations-specific metrics."""
    # Set initial KPIs
    self.update_metric("overall_equipment_effectiveness", 85.0)  # % OEE
    self.update_metric("on_time_delivery", 94.5)  # %
    self.update_metric("inventory_turnover", 12.0)  # times per year
    self.update_metric("defect_rate", 0.5)  # %
    self.update_metric("supply_chain_efficiency", 88.0)  # %
    
    # Set targets
    self.set_target("overall_equipment_effectiveness", 90.0)
    self.set_target("on_time_delivery", 98.0)
    self.set_target("inventory_turnover", 15.0)
    self.set_target("defect_rate", 0.3)
    self.set_target("supply_chain_efficiency", 92.0)
  
  # Operations-specific tool implementations
  
  def _optimize_supply_chain(
      self, optimization_target: str = "cost"
  ) -> Dict[str, any]:
    """Optimize supply chain operations."""
    return {
        "optimization_target": optimization_target,
        "current_state": {
            "suppliers": 25,
            "lead_time_days": 14,
            "cost_per_unit": 100,
            "reliability_score": 88.0,
        },
        "optimized_state": {
            "suppliers": 20,
            "lead_time_days": 10,
            "cost_per_unit": 92,
            "reliability_score": 92.0,
        },
        "recommendations": [
            "Consolidate suppliers for better negotiation power",
            "Implement JIT delivery for critical components",
            "Establish backup suppliers for critical items",
        ],
        "expected_savings": 80000,
    }
  
  def _analyze_production_efficiency(
      self, production_line: Optional[str] = None
  ) -> Dict[str, any]:
    """Analyze production efficiency."""
    return {
        "production_line": production_line or "all",
        "metrics": {
            "oee": 85.0,  # Overall Equipment Effectiveness
            "availability": 90.0,
            "performance": 95.0,
            "quality": 99.5,
            "throughput": 1000,  # units per hour
        },
        "bottlenecks": [
            {"area": "packaging", "impact": "15% throughput reduction"},
            {"area": "quality_inspection", "impact": "5% delay"},
        ],
        "improvement_opportunities": [
            "Automate packaging process",
            "Implement predictive maintenance",
            "Optimize changeover procedures",
        ],
    }
  
  def _manage_inventory(
      self, action: str = "optimize"
  ) -> Dict[str, any]:
    """Manage inventory levels."""
    return {
        "action": action,
        "current_inventory": {
            "total_value": 2500000,
            "turnover_ratio": 12.0,
            "stockout_rate": 2.0,  # %
            "carrying_cost": 150000,  # annual
        },
        "recommendations": {
            "optimal_levels": {
                "raw_materials": 500000,
                "work_in_progress": 300000,
                "finished_goods": 700000,
            },
            "reorder_points": {
                "critical_items": "2 weeks supply",
                "standard_items": "1 week supply",
            },
            "actions": [
                "Implement ABC analysis for inventory classification",
                "Set up automatic reorder points",
                "Reduce slow-moving inventory by 20%",
            ],
        },
    }
  
  def _track_quality_metrics(self) -> Dict[str, any]:
    """Track quality metrics."""
    return {
        "quality_metrics": {
            "defect_rate": 0.5,  # %
            "first_pass_yield": 98.5,  # %
            "customer_complaints": 12,  # per month
            "rework_rate": 1.5,  # %
            "inspection_pass_rate": 99.0,  # %
        },
        "trends": {
            "defect_rate": "improving",
            "customer_satisfaction": "stable",
            "rework_costs": "decreasing",
        },
        "quality_initiatives": [
            "Six Sigma implementation in progress",
            "ISO 9001 certification maintained",
            "Continuous improvement program active",
        ],
    }
  
  def _optimize_logistics(
      self, optimization_focus: str = "cost"
  ) -> Dict[str, any]:
    """Optimize logistics operations."""
    return {
        "optimization_focus": optimization_focus,
        "current_performance": {
            "delivery_cost_per_unit": 5.50,
            "average_delivery_time": 2.5,  # days
            "route_efficiency": 78.0,  # %
            "vehicle_utilization": 82.0,  # %
        },
        "optimization_results": {
            "new_routes": 15,
            "estimated_cost_savings": 120000,  # annual
            "delivery_time_reduction": 0.5,  # days
            "efficiency_improvement": 8.0,  # %
        },
        "implementation_plan": [
            "Deploy route optimization software",
            "Consolidate shipments where possible",
            "Implement real-time tracking",
        ],
    }
  
  def _forecast_demand(
      self, product: str, horizon_months: int = 3
  ) -> Dict[str, any]:
    """Forecast demand for products/services."""
    return {
        "product": product,
        "horizon_months": horizon_months,
        "forecast": {
            "month_1": 10000,
            "month_2": 12000,
            "month_3": 11000,
            "confidence_interval": 0.85,
        },
        "factors_considered": [
            "Historical sales data",
            "Seasonal patterns",
            "Market trends",
            "Economic indicators",
        ],
        "recommendations": [
            "Increase production capacity by 10% for month 2",
            "Secure additional raw materials",
            "Plan for temporary workforce if needed",
        ],
    }
  
  def _analyze_operational_costs(self) -> Dict[str, any]:
    """Analyze operational costs."""
    return {
        "total_operational_cost": 5000000,
        "cost_breakdown": {
            "labor": 0.40,  # 40%
            "materials": 0.35,  # 35%
            "overhead": 0.15,  # 15%
            "logistics": 0.10,  # 10%
        },
        "cost_trends": {
            "labor": "increasing",
            "materials": "stable",
            "overhead": "decreasing",
            "logistics": "increasing",
        },
        "cost_reduction_opportunities": [
            {"area": "automation", "potential_savings": 200000},
            {"area": "energy_efficiency", "potential_savings": 50000},
            {"area": "waste_reduction", "potential_savings": 75000},
        ],
        "recommended_actions": [
            "Implement automation in high-labor areas",
            "Negotiate better rates with suppliers",
            "Optimize energy consumption patterns",
        ],
    }