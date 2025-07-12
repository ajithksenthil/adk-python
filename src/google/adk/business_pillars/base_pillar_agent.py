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

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..agents.llm_agent import LlmAgent
from ..tools.base_tool import BaseTool
from ..tools.function_tool import FunctionTool


class PillarMetrics(BaseModel):
  """Metrics tracked by a business pillar."""
  
  kpis: Dict[str, float] = Field(
      default_factory=dict, description="Key Performance Indicators"
  )
  targets: Dict[str, float] = Field(
      default_factory=dict, description="Target values for KPIs"
  )
  alerts: List[str] = Field(
      default_factory=list, description="Active alerts for this pillar"
  )


class PillarCapability(BaseModel):
  """A capability provided by a business pillar."""
  
  name: str = Field(description="Name of the capability")
  description: str = Field(description="Description of what this capability does")
  required_tools: List[str] = Field(
      default_factory=list, description="Tools required for this capability"
  )
  dependencies: List[str] = Field(
      default_factory=list, description="Other capabilities this depends on"
  )


class BasePillarAgent(LlmAgent):
  """Base class for business pillar agents.
  
  Each pillar agent represents a major business function (Finance, Operations,
  Marketing, HR, IT, etc.) and contains specialized knowledge and tools for
  that domain.
  """
  
  pillar_name: str = Field(description="Name of the business pillar")
  
  pillar_description: str = Field(
      description="Description of the pillar's responsibilities"
  )
  
  capabilities: List[PillarCapability] = Field(
      default_factory=list, description="Capabilities provided by this pillar"
  )
  
  metrics: PillarMetrics = Field(
      default_factory=PillarMetrics, description="Metrics tracked by this pillar"
  )
  
  cross_pillar_dependencies: List[str] = Field(
      default_factory=list,
      description="Other pillars this one frequently interacts with",
  )
  
  domain_knowledge: Dict[str, Any] = Field(
      default_factory=dict,
      description="Domain-specific knowledge and configurations",
  )
  
  def __init__(self, **kwargs):
    """Initialize the pillar agent."""
    # Add pillar-specific instruction if not provided
    if "instruction" not in kwargs and "pillar_name" in kwargs:
      kwargs["instruction"] = self._generate_pillar_instruction()
    
    super().__init__(**kwargs)
    
    # Add common pillar tools
    self._add_common_pillar_tools()
    
    # Add domain-specific tools
    self._add_domain_specific_tools()
  
  def _generate_pillar_instruction(self) -> str:
    """Generate default instruction based on pillar information."""
    return (
        f"I am the {self.pillar_name} pillar agent responsible for "
        f"{self.pillar_description}. I have specialized knowledge and tools "
        f"for managing {self.pillar_name.lower()} operations and can collaborate "
        f"with other business pillars to achieve organizational goals."
    )
  
  def _add_common_pillar_tools(self):
    """Add tools common to all pillar agents."""
    common_tools = [
        FunctionTool(
            name="get_pillar_metrics",
            description="Get current metrics for this pillar",
            func=self.get_metrics,
        ),
        FunctionTool(
            name="get_pillar_capabilities",
            description="List capabilities of this pillar",
            func=self.get_capabilities,
        ),
        FunctionTool(
            name="check_cross_pillar_dependency",
            description="Check dependencies with other pillars",
            func=self.check_cross_pillar_dependency,
        ),
        FunctionTool(
            name="report_pillar_status",
            description="Generate status report for this pillar",
            func=self.report_status,
        ),
    ]
    
    if self.tools:
      self.tools.extend(common_tools)
    else:
      self.tools = common_tools
  
  @abstractmethod
  def _add_domain_specific_tools(self):
    """Add tools specific to this pillar's domain.
    
    Must be implemented by each pillar agent.
    """
    pass
  
  def get_metrics(self) -> Dict[str, Any]:
    """Get current metrics for this pillar."""
    return {
        "pillar": self.pillar_name,
        "kpis": self.metrics.kpis,
        "targets": self.metrics.targets,
        "alerts": self.metrics.alerts,
        "health_score": self._calculate_health_score(),
    }
  
  def get_capabilities(self) -> List[Dict[str, Any]]:
    """List all capabilities of this pillar."""
    return [
        {
            "name": cap.name,
            "description": cap.description,
            "required_tools": cap.required_tools,
            "dependencies": cap.dependencies,
        }
        for cap in self.capabilities
    ]
  
  def check_cross_pillar_dependency(
      self, target_pillar: str, capability: str
  ) -> Dict[str, Any]:
    """Check if this pillar depends on another for a capability."""
    depends = target_pillar in self.cross_pillar_dependencies
    
    # Check specific capability dependencies
    capability_depends = False
    for cap in self.capabilities:
      if capability in cap.dependencies:
        capability_depends = True
        break
    
    return {
        "source_pillar": self.pillar_name,
        "target_pillar": target_pillar,
        "general_dependency": depends,
        "capability_dependency": capability_depends,
        "capability": capability,
    }
  
  def report_status(self) -> Dict[str, Any]:
    """Generate a status report for this pillar."""
    return {
        "pillar": self.pillar_name,
        "description": self.pillar_description,
        "health_score": self._calculate_health_score(),
        "active_alerts": len(self.metrics.alerts),
        "capabilities_count": len(self.capabilities),
        "cross_dependencies": self.cross_pillar_dependencies,
        "metrics_summary": {
            "tracked_kpis": len(self.metrics.kpis),
            "kpis_meeting_targets": self._count_kpis_meeting_targets(),
        },
    }
  
  def _calculate_health_score(self) -> float:
    """Calculate overall health score for this pillar (0-100)."""
    if not self.metrics.kpis or not self.metrics.targets:
      return 100.0  # No metrics to track, assume healthy
    
    scores = []
    for kpi_name, kpi_value in self.metrics.kpis.items():
      if kpi_name in self.metrics.targets:
        target = self.metrics.targets[kpi_name]
        # Simple percentage of target achieved (capped at 100%)
        score = min((kpi_value / target) * 100, 100.0) if target > 0 else 100.0
        scores.append(score)
    
    # Deduct points for alerts
    alert_penalty = len(self.metrics.alerts) * 5
    
    avg_score = sum(scores) / len(scores) if scores else 100.0
    final_score = max(avg_score - alert_penalty, 0.0)
    
    return round(final_score, 2)
  
  def _count_kpis_meeting_targets(self) -> int:
    """Count how many KPIs are meeting their targets."""
    count = 0
    for kpi_name, kpi_value in self.metrics.kpis.items():
      if kpi_name in self.metrics.targets:
        if kpi_value >= self.metrics.targets[kpi_name]:
          count += 1
    return count
  
  def add_capability(self, capability: PillarCapability):
    """Add a new capability to this pillar."""
    self.capabilities.append(capability)
  
  def update_metric(self, kpi_name: str, value: float):
    """Update a KPI value."""
    self.metrics.kpis[kpi_name] = value
  
  def set_target(self, kpi_name: str, target: float):
    """Set a target for a KPI."""
    self.metrics.targets[kpi_name] = target
  
  def add_alert(self, alert: str):
    """Add an alert for this pillar."""
    if alert not in self.metrics.alerts:
      self.metrics.alerts.append(alert)
  
  def clear_alert(self, alert: str):
    """Clear an alert."""
    if alert in self.metrics.alerts:
      self.metrics.alerts.remove(alert)