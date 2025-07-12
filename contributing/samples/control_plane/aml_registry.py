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
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AutonomyLevel(IntEnum):
  """Autonomy Maturity Levels (AML) as defined in the architecture."""
  AML_0 = 0  # No action; read-only insights (100% human involvement)
  AML_1 = 1  # Suggest actions (Approve every action)
  AML_2 = 2  # Batch execution (Approve batches)
  AML_3 = 3  # Real-time execution under hard caps (Approve exceptions)
  AML_4 = 4  # Self-correcting execution, soft caps (Quarterly audit)
  AML_5 = 5  # Uncapped w/ treasury limits + self-eval retract (Kill-switch only)


@dataclass
class AutonomyCapabilities:
  """Capabilities allowed at each autonomy level."""
  level: AutonomyLevel
  allowed_tools: List[str] = field(default_factory=list)
  denied_tools: List[str] = field(default_factory=list)
  max_transaction_value: Optional[float] = None
  max_daily_spend: Optional[float] = None
  requires_approval: bool = True
  approval_threshold: Optional[float] = None
  batch_size_limit: Optional[int] = None
  self_correction_allowed: bool = False
  treasury_limits: Dict[str, float] = field(default_factory=dict)
  
  def __post_init__(self):
    """Set defaults based on autonomy level."""
    if self.level == AutonomyLevel.AML_0:
      self.allowed_tools = ["read", "analyze", "report"]
      self.max_transaction_value = 0
      self.requires_approval = True
      self.self_correction_allowed = False
    elif self.level == AutonomyLevel.AML_1:
      self.requires_approval = True
      self.self_correction_allowed = False
    elif self.level == AutonomyLevel.AML_2:
      self.requires_approval = True
      self.batch_size_limit = self.batch_size_limit or 10
    elif self.level == AutonomyLevel.AML_3:
      self.requires_approval = False  # Only for exceptions
      self.approval_threshold = self.approval_threshold or 1000.0
    elif self.level == AutonomyLevel.AML_4:
      self.requires_approval = False
      self.self_correction_allowed = True
    elif self.level == AutonomyLevel.AML_5:
      self.requires_approval = False
      self.self_correction_allowed = True


class AgentAutonomyProfile(BaseModel):
  """Autonomy profile for an agent."""
  agent_name: str
  pillar: str  # Business pillar (Mission, Product, Growth, etc.)
  current_level: AutonomyLevel
  target_level: Optional[AutonomyLevel] = None
  capabilities: Optional[AutonomyCapabilities] = None
  performance_metrics: Dict[str, float] = Field(default_factory=dict)
  level_history: List[Dict[str, Any]] = Field(default_factory=list)
  last_evaluation: Optional[datetime] = None
  next_evaluation: Optional[datetime] = None
  drift_incidents: int = 0
  approval_rate: float = 1.0
  
  @validator('capabilities', always=True)
  def set_capabilities(cls, v, values):
    """Set capabilities based on current level if not provided."""
    if v is None and 'current_level' in values:
      return AutonomyCapabilities(level=values['current_level'])
    return v
  
  def can_execute(self, tool_name: str, cost: Optional[float] = None) -> bool:
    """Check if agent can execute a tool at current autonomy level."""
    if not self.capabilities:
      return False
    
    # Check tool allowlist/denylist
    if self.capabilities.denied_tools and tool_name in self.capabilities.denied_tools:
      return False
    if self.capabilities.allowed_tools and tool_name not in self.capabilities.allowed_tools:
      return False
    
    # Check cost limits
    if cost is not None and self.capabilities.max_transaction_value is not None:
      if cost > self.capabilities.max_transaction_value:
        return False
    
    return True
  
  def promote(self) -> bool:
    """Promote agent to next autonomy level."""
    if self.current_level < AutonomyLevel.AML_5:
      old_level = self.current_level
      self.current_level = AutonomyLevel(self.current_level + 1)
      self.capabilities = AutonomyCapabilities(level=self.current_level)
      self.level_history.append({
        "timestamp": datetime.now().isoformat(),
        "from_level": old_level,
        "to_level": self.current_level.value,
        "reason": "promotion",
        "metrics": self.performance_metrics.copy()
      })
      return True
    return False
  
  def demote(self, reason: str = "drift") -> bool:
    """Demote agent to lower autonomy level."""
    if self.current_level > AutonomyLevel.AML_0:
      old_level = self.current_level
      self.current_level = AutonomyLevel(self.current_level - 1)
      self.capabilities = AutonomyCapabilities(level=self.current_level)
      self.drift_incidents += 1
      self.level_history.append({
        "timestamp": datetime.now().isoformat(),
        "from_level": old_level,
        "to_level": self.current_level.value,
        "reason": f"demotion: {reason}",
        "metrics": self.performance_metrics.copy()
      })
      return True
    return False


class AMLRegistry:
  """Registry for managing agent autonomy levels."""
  
  def __init__(self, storage_path: Optional[str] = None):
    self.storage_path = storage_path
    self.profiles: Dict[str, AgentAutonomyProfile] = {}
    self.pillar_defaults: Dict[str, AutonomyLevel] = {
      "Mission & Governance": AutonomyLevel.AML_1,
      "Product & Experience": AutonomyLevel.AML_2,
      "Growth Engine": AutonomyLevel.AML_3,
      "Customer Success": AutonomyLevel.AML_3,
      "Resource & Supply": AutonomyLevel.AML_2,
      "People & Culture": AutonomyLevel.AML_1,
      "Intelligence & Improvement": AutonomyLevel.AML_3,
      "Platform & Infra": AutonomyLevel.AML_2,
    }
    self._load_profiles()
  
  def _load_profiles(self):
    """Load profiles from storage."""
    if self.storage_path:
      try:
        with open(self.storage_path, 'r') as f:
          data = json.load(f)
          for agent_name, profile_data in data.items():
            profile = AgentAutonomyProfile(**profile_data)
            self.profiles[agent_name] = profile
      except FileNotFoundError:
        logger.info("No existing AML registry found, starting fresh")
      except Exception as e:
        logger.error(f"Error loading AML registry: {e}")
  
  def _save_profiles(self):
    """Save profiles to storage."""
    if self.storage_path:
      try:
        data = {
          name: profile.dict() for name, profile in self.profiles.items()
        }
        with open(self.storage_path, 'w') as f:
          json.dump(data, f, indent=2, default=str)
      except Exception as e:
        logger.error(f"Error saving AML registry: {e}")
  
  def register_agent(
    self,
    agent_name: str,
    pillar: str,
    initial_level: Optional[AutonomyLevel] = None
  ) -> AgentAutonomyProfile:
    """Register a new agent with autonomy profile."""
    if agent_name in self.profiles:
      return self.profiles[agent_name]
    
    # Use pillar default or provided level
    if initial_level is None:
      initial_level = self.pillar_defaults.get(
        pillar,
        AutonomyLevel.AML_1
      )
    
    profile = AgentAutonomyProfile(
      agent_name=agent_name,
      pillar=pillar,
      current_level=initial_level
    )
    
    self.profiles[agent_name] = profile
    self._save_profiles()
    return profile
  
  def get_profile(self, agent_name: str) -> Optional[AgentAutonomyProfile]:
    """Get agent's autonomy profile."""
    return self.profiles.get(agent_name)
  
  def update_metrics(
    self,
    agent_name: str,
    metrics: Dict[str, float]
  ):
    """Update agent performance metrics."""
    profile = self.profiles.get(agent_name)
    if profile:
      profile.performance_metrics.update(metrics)
      profile.last_evaluation = datetime.now()
      self._save_profiles()
  
  def evaluate_promotion(
    self,
    agent_name: str,
    min_approval_rate: float = 0.95,
    min_success_rate: float = 0.98,
    max_drift_incidents: int = 2
  ) -> bool:
    """Evaluate if agent is ready for promotion."""
    profile = self.profiles.get(agent_name)
    if not profile:
      return False
    
    # Check performance criteria
    if profile.approval_rate < min_approval_rate:
      return False
    
    success_rate = profile.performance_metrics.get("success_rate", 0)
    if success_rate < min_success_rate:
      return False
    
    if profile.drift_incidents > max_drift_incidents:
      return False
    
    # Check time at current level (minimum 30 days)
    if profile.level_history:
      last_change = datetime.fromisoformat(
        profile.level_history[-1]["timestamp"]
      )
      days_at_level = (datetime.now() - last_change).days
      if days_at_level < 30:
        return False
    
    return True
  
  def handle_drift(self, agent_name: str, severity: str = "medium"):
    """Handle drift incident for an agent."""
    profile = self.profiles.get(agent_name)
    if not profile:
      return
    
    # Demote on severe drift or repeated incidents
    if severity == "high" or profile.drift_incidents >= 3:
      profile.demote(reason=f"drift-{severity}")
      logger.warning(
        f"Agent {agent_name} demoted to AML {profile.current_level} "
        f"due to {severity} drift"
      )
    else:
      profile.drift_incidents += 1
    
    self._save_profiles()
  
  def get_pillar_summary(self) -> Dict[str, Dict[str, Any]]:
    """Get summary of autonomy levels by pillar."""
    summary = {}
    for pillar in self.pillar_defaults:
      pillar_agents = [
        p for p in self.profiles.values() if p.pillar == pillar
      ]
      if pillar_agents:
        summary[pillar] = {
          "agent_count": len(pillar_agents),
          "average_level": sum(p.current_level for p in pillar_agents) / len(pillar_agents),
          "max_level": max(p.current_level for p in pillar_agents),
          "min_level": min(p.current_level for p in pillar_agents),
          "agents": {
            p.agent_name: p.current_level.name for p in pillar_agents
          }
        }
    return summary