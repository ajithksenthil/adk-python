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

"""Enhanced AML Registry with full specification compliance for AI-native enterprise."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum, Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AutonomyLevel(IntEnum):
  """Autonomy Maturity Levels (AML) as defined in the architecture."""
  AML_0 = 0  # Observe: Read-only analytics, no tool calls
  AML_1 = 1  # Recommend: Draft actions, requires human OK
  AML_2 = 2  # Batch Execute: Execute scheduled or batched actions under fixed caps
  AML_3 = 3  # Real-time Execute: Execute continuously under hard caps
  AML_4 = 4  # Self-Correct: Same as AML 3 plus roll-back when metrics drift
  AML_5 = 5  # Delegate: Unlimited under treasury caps; can tune its own caps


class KPIOperator(str, Enum):
  """Operators for KPI conditions."""
  GREATER_THAN = ">"
  GREATER_EQUAL = ">="
  LESS_THAN = "<"
  LESS_EQUAL = "<="
  EQUAL = "=="
  NOT_EQUAL = "!="


class ChangeType(str, Enum):
  """Types of AML changes."""
  PROMOTION = "promotion"
  DEMOTION = "demotion"
  MANUAL_OVERRIDE = "manual_override"
  EMERGENCY_PAUSE = "emergency_pause"
  DRIFT_RESPONSE = "drift_response"


@dataclass
class KPICondition:
  """Individual KPI condition for promotion/demotion."""
  metric_name: str
  operator: KPIOperator
  threshold: float
  time_window_days: int = 7
  description: str = ""
  
  def evaluate(self, metrics: Dict[str, float]) -> bool:
    """Evaluate this condition against metrics."""
    if self.metric_name not in metrics:
      return False
    
    value = metrics[self.metric_name]
    
    if self.operator == KPIOperator.GREATER_THAN:
      return value > self.threshold
    elif self.operator == KPIOperator.GREATER_EQUAL:
      return value >= self.threshold
    elif self.operator == KPIOperator.LESS_THAN:
      return value < self.threshold
    elif self.operator == KPIOperator.LESS_EQUAL:
      return value <= self.threshold
    elif self.operator == KPIOperator.EQUAL:
      return abs(value - self.threshold) < 0.001  # Float comparison
    elif self.operator == KPIOperator.NOT_EQUAL:
      return abs(value - self.threshold) >= 0.001
    
    return False


@dataclass
class AMLChangeRecord:
  """Immutable record of AML level changes."""
  change_id: str
  agent_group: str
  pillar: str
  from_level: AutonomyLevel
  to_level: AutonomyLevel
  change_type: ChangeType
  changed_by: str  # User ID or system component
  timestamp: datetime
  reason: str
  kpi_snapshot: Dict[str, float] = field(default_factory=dict)
  policy_refs: List[str] = field(default_factory=list)
  metadata: Dict[str, Any] = field(default_factory=dict)
  
  def to_audit_log(self) -> Dict[str, Any]:
    """Convert to immutable audit log entry."""
    return {
      "change_id": self.change_id,
      "agent_group": self.agent_group,
      "pillar": self.pillar,
      "from_level": self.from_level.value,
      "to_level": self.to_level.value,
      "change_type": self.change_type.value,
      "changed_by": self.changed_by,
      "timestamp": self.timestamp.isoformat(),
      "reason": self.reason,
      "kpi_snapshot": self.kpi_snapshot,
      "policy_refs": self.policy_refs,
      "metadata": self.metadata
    }


class AMLAgentProfile(BaseModel):
  """Complete AML profile matching the specification."""
  # Core fields from specification
  pillar: str
  agent_group: str
  aml_level: AutonomyLevel
  policy_refs: List[str] = Field(default_factory=list)
  promote_conditions: List[KPICondition] = Field(default_factory=list)
  demote_conditions: List[KPICondition] = Field(default_factory=list)
  last_change_by: str = "system"
  ts_last_change: datetime = Field(default_factory=datetime.now)
  
  # Extended tracking fields
  agent_names: List[str] = Field(default_factory=list)  # Agents in this group
  current_metrics: Dict[str, float] = Field(default_factory=dict)
  metric_history: List[Dict[str, Any]] = Field(default_factory=list)
  drift_incidents: int = 0
  emergency_paused: bool = False
  kill_switch_active: bool = False
  last_evaluation: Optional[datetime] = None
  next_evaluation: Optional[datetime] = None
  
  class Config:
    arbitrary_types_allowed = True
    json_encoders = {
      datetime: lambda v: v.isoformat(),
      AutonomyLevel: lambda v: v.value,
      KPIOperator: lambda v: v.value
    }
  
  @validator('promote_conditions', 'demote_conditions', pre=True)
  def parse_conditions(cls, v):
    """Parse conditions from dict if needed."""
    if isinstance(v, list) and v and isinstance(v[0], dict):
      return [KPICondition(**cond) for cond in v]
    return v
  
  def can_execute_tool(
    self,
    tool_name: str,
    cost: Optional[float] = None,
    transaction_value: Optional[float] = None
  ) -> Dict[str, Any]:
    """Check if agent group can execute tool at current AML level."""
    result = {
      "allowed": True,
      "reason": "",
      "requires_approval": False,
      "approval_threshold": None
    }
    
    # Emergency checks
    if self.emergency_paused or self.kill_switch_active:
      result["allowed"] = False
      result["reason"] = "Emergency pause or kill switch active"
      return result
    
    # AML level restrictions
    if self.aml_level == AutonomyLevel.AML_0:
      # Read-only mode
      read_only_tools = ["read", "analyze", "report", "query", "fetch"]
      if not any(ro_tool in tool_name.lower() for ro_tool in read_only_tools):
        result["allowed"] = False
        result["reason"] = "AML 0: Read-only mode, tool not permitted"
        return result
    
    elif self.aml_level == AutonomyLevel.AML_1:
      # All actions require approval
      result["requires_approval"] = True
      result["reason"] = "AML 1: All actions require human approval"
    
    elif self.aml_level == AutonomyLevel.AML_2:
      # Batch execution with caps
      if cost and cost > 1000:  # Example cap
        result["requires_approval"] = True
        result["approval_threshold"] = 1000
        result["reason"] = "AML 2: Cost exceeds batch execution limit"
    
    elif self.aml_level == AutonomyLevel.AML_3:
      # Real-time execution under hard caps
      if transaction_value and transaction_value > 5000:  # Example cap
        result["requires_approval"] = True
        result["approval_threshold"] = 5000
        result["reason"] = "AML 3: Transaction exceeds hard cap"
    
    # AML 4 and 5 have fewer restrictions
    
    return result
  
  def should_promote(self) -> bool:
    """Check if all promotion conditions are met."""
    if not self.promote_conditions:
      return False
    
    return all(
      condition.evaluate(self.current_metrics)
      for condition in self.promote_conditions
    )
  
  def should_demote(self) -> bool:
    """Check if any demotion conditions are met."""
    if not self.demote_conditions:
      return False
    
    return any(
      condition.evaluate(self.current_metrics)
      for condition in self.demote_conditions
    )


class AMLStorage(ABC):
  """Abstract storage interface for AML registry."""
  
  @abstractmethod
  async def get_profile(self, agent_group: str) -> Optional[AMLAgentProfile]:
    """Get agent profile by group."""
    pass
  
  @abstractmethod
  async def save_profile(self, profile: AMLAgentProfile) -> bool:
    """Save agent profile."""
    pass
  
  @abstractmethod
  async def list_profiles(self) -> List[AMLAgentProfile]:
    """List all profiles."""
    pass
  
  @abstractmethod
  async def save_change_record(self, record: AMLChangeRecord) -> bool:
    """Save immutable change record."""
    pass
  
  @abstractmethod
  async def get_change_history(
    self,
    agent_group: Optional[str] = None,
    limit: int = 100
  ) -> List[AMLChangeRecord]:
    """Get change history."""
    pass


class InMemoryAMLStorage(AMLStorage):
  """In-memory storage for development and testing."""
  
  def __init__(self):
    self.profiles: Dict[str, AMLAgentProfile] = {}
    self.change_records: List[AMLChangeRecord] = []
  
  async def get_profile(self, agent_group: str) -> Optional[AMLAgentProfile]:
    return self.profiles.get(agent_group)
  
  async def save_profile(self, profile: AMLAgentProfile) -> bool:
    self.profiles[profile.agent_group] = profile
    return True
  
  async def list_profiles(self) -> List[AMLAgentProfile]:
    return list(self.profiles.values())
  
  async def save_change_record(self, record: AMLChangeRecord) -> bool:
    self.change_records.append(record)
    return True
  
  async def get_change_history(
    self,
    agent_group: Optional[str] = None,
    limit: int = 100
  ) -> List[AMLChangeRecord]:
    records = self.change_records
    if agent_group:
      records = [r for r in records if r.agent_group == agent_group]
    return sorted(records, key=lambda x: x.timestamp, reverse=True)[:limit]


class CloudSpannerAMLStorage(AMLStorage):
  """Cloud Spanner storage for production (mock implementation)."""
  
  def __init__(self, project_id: str, instance_id: str, database_id: str):
    self.project_id = project_id
    self.instance_id = instance_id
    self.database_id = database_id
    # In production, would initialize Spanner client
    logger.info(f"Initialized Spanner AML storage: {project_id}/{instance_id}/{database_id}")
  
  async def get_profile(self, agent_group: str) -> Optional[AMLAgentProfile]:
    # Mock implementation - would query Spanner
    logger.info(f"Would query Spanner for agent group: {agent_group}")
    return None
  
  async def save_profile(self, profile: AMLAgentProfile) -> bool:
    # Mock implementation - would insert/update in Spanner
    logger.info(f"Would save profile to Spanner: {profile.agent_group}")
    return True
  
  async def list_profiles(self) -> List[AMLAgentProfile]:
    # Mock implementation
    return []
  
  async def save_change_record(self, record: AMLChangeRecord) -> bool:
    # Mock implementation - would insert immutable record
    logger.info(f"Would save change record to Spanner: {record.change_id}")
    return True
  
  async def get_change_history(
    self,
    agent_group: Optional[str] = None,
    limit: int = 100
  ) -> List[AMLChangeRecord]:
    # Mock implementation
    return []


class AMLEvaluationJob:
  """Evaluation job for dynamic autonomy adjustment."""
  
  def __init__(self, registry: 'EnhancedAMLRegistry'):
    self.registry = registry
    self.running = False
    self.evaluation_interval = timedelta(hours=1)  # Run every hour
    self.task: Optional[asyncio.Task] = None
  
  async def start(self):
    """Start the evaluation job."""
    if self.running:
      return
    
    self.running = True
    self.task = asyncio.create_task(self._evaluation_loop())
    logger.info("AML Evaluation Job started")
  
  async def stop(self):
    """Stop the evaluation job."""
    self.running = False
    if self.task:
      self.task.cancel()
      try:
        await self.task
      except asyncio.CancelledError:
        pass
    logger.info("AML Evaluation Job stopped")
  
  async def _evaluation_loop(self):
    """Main evaluation loop."""
    while self.running:
      try:
        await self._run_evaluation()
        await asyncio.sleep(self.evaluation_interval.total_seconds())
      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error(f"Error in AML evaluation loop: {e}")
        await asyncio.sleep(60)  # Wait 1 minute on error
  
  async def _run_evaluation(self):
    """Run evaluation for all agent groups."""
    profiles = await self.registry.storage.list_profiles()
    
    for profile in profiles:
      try:
        # Check for promotion
        if profile.should_promote() and profile.aml_level < AutonomyLevel.AML_5:
          await self.registry.promote_agent_group(
            profile.agent_group,
            changed_by="eval_job",
            reason="KPI conditions met for promotion"
          )
        
        # Check for demotion
        elif profile.should_demote() and profile.aml_level > AutonomyLevel.AML_0:
          await self.registry.demote_agent_group(
            profile.agent_group,
            changed_by="eval_job",
            reason="KPI conditions met for demotion"
          )
        
        # Update next evaluation time
        profile.last_evaluation = datetime.now()
        profile.next_evaluation = datetime.now() + self.evaluation_interval
        await self.registry.storage.save_profile(profile)
        
      except Exception as e:
        logger.error(f"Error evaluating agent group {profile.agent_group}: {e}")


class EnhancedAMLRegistry:
  """Enhanced AML Registry with full specification compliance."""
  
  def __init__(
    self,
    storage: Optional[AMLStorage] = None,
    enable_evaluation_job: bool = True
  ):
    self.storage = storage or InMemoryAMLStorage()
    self.evaluation_job = AMLEvaluationJob(self) if enable_evaluation_job else None
    self._initialized = False
  
  async def initialize(self):
    """Initialize the registry."""
    if self._initialized:
      return
    
    # Create default pillar profiles if they don't exist
    await self._create_default_profiles()
    
    # Start evaluation job if enabled
    if self.evaluation_job:
      await self.evaluation_job.start()
    
    self._initialized = True
    logger.info("Enhanced AML Registry initialized")
  
  async def shutdown(self):
    """Shutdown the registry."""
    if self.evaluation_job:
      await self.evaluation_job.stop()
    self._initialized = False
    logger.info("Enhanced AML Registry shutdown")
  
  async def _create_default_profiles(self):
    """Create default profiles for each pillar."""
    default_configs = {
      "Mission & Governance": {
        "aml_level": AutonomyLevel.AML_1,
        "promote_conditions": [
          KPICondition("policy_compliance_rate", KPIOperator.GREATER_EQUAL, 0.99, 30),
          KPICondition("risk_accuracy", KPIOperator.GREATER_EQUAL, 0.95, 14),
          KPICondition("audit_score", KPIOperator.GREATER_EQUAL, 0.98, 30)
        ],
        "demote_conditions": [
          KPICondition("policy_violations", KPIOperator.GREATER_THAN, 0, 1),
          KPICondition("risk_prediction_error", KPIOperator.GREATER_THAN, 0.1, 7)
        ]
      },
      "Growth Engine": {
        "aml_level": AutonomyLevel.AML_3,
        "promote_conditions": [
          KPICondition("roas", KPIOperator.GREATER_EQUAL, 3.0, 14),
          KPICondition("conversion_rate", KPIOperator.GREATER_EQUAL, 0.15, 7),
          KPICondition("cost_efficiency", KPIOperator.GREATER_EQUAL, 0.85, 14)
        ],
        "demote_conditions": [
          KPICondition("roas", KPIOperator.LESS_THAN, 2.0, 3),
          KPICondition("budget_variance", KPIOperator.GREATER_THAN, 0.2, 1)
        ]
      },
      "Customer Success": {
        "aml_level": AutonomyLevel.AML_3,
        "promote_conditions": [
          KPICondition("nps_score", KPIOperator.GREATER_EQUAL, 4.2, 30),
          KPICondition("refund_error_rate", KPIOperator.LESS_EQUAL, 0.005, 14),
          KPICondition("resolution_time", KPIOperator.LESS_EQUAL, 24.0, 7)
        ],
        "demote_conditions": [
          KPICondition("nps_score", KPIOperator.LESS_THAN, 3.5, 7),
          KPICondition("chargeback_rate", KPIOperator.GREATER_THAN, 0.008, 7)
        ]
      }
    }
    
    for pillar, config in default_configs.items():
      agent_group = f"{pillar.lower().replace(' ', '_')}_agents"
      existing = await self.storage.get_profile(agent_group)
      
      if not existing:
        profile = AMLAgentProfile(
          pillar=pillar,
          agent_group=agent_group,
          aml_level=config["aml_level"],
          promote_conditions=config["promote_conditions"],
          demote_conditions=config["demote_conditions"],
          policy_refs=[f"POL-{pillar.upper().replace(' ', '-')}-DEFAULT"]
        )
        await self.storage.save_profile(profile)
        logger.info(f"Created default AML profile for {pillar}")
  
  async def register_agent_group(
    self,
    agent_group: str,
    pillar: str,
    initial_level: AutonomyLevel = AutonomyLevel.AML_1,
    policy_refs: Optional[List[str]] = None
  ) -> AMLAgentProfile:
    """Register a new agent group."""
    existing = await self.storage.get_profile(agent_group)
    if existing:
      return existing
    
    profile = AMLAgentProfile(
      pillar=pillar,
      agent_group=agent_group,
      aml_level=initial_level,
      policy_refs=policy_refs or [],
      last_change_by="system"
    )
    
    await self.storage.save_profile(profile)
    
    # Create change record
    change_record = AMLChangeRecord(
      change_id=str(uuid.uuid4()),
      agent_group=agent_group,
      pillar=pillar,
      from_level=AutonomyLevel.AML_0,
      to_level=initial_level,
      change_type=ChangeType.PROMOTION,
      changed_by="system",
      timestamp=datetime.now(),
      reason="Initial registration"
    )
    await self.storage.save_change_record(change_record)
    
    logger.info(f"Registered agent group {agent_group} at {initial_level.name}")
    return profile
  
  async def get_agent_profile(self, agent_group: str) -> Optional[AMLAgentProfile]:
    """Get agent group profile."""
    return await self.storage.get_profile(agent_group)
  
  async def update_metrics(
    self,
    agent_group: str,
    metrics: Dict[str, float],
    timestamp: Optional[datetime] = None
  ):
    """Update metrics for an agent group."""
    profile = await self.storage.get_profile(agent_group)
    if not profile:
      logger.warning(f"Agent group {agent_group} not found for metrics update")
      return
    
    timestamp = timestamp or datetime.now()
    
    # Update current metrics
    profile.current_metrics.update(metrics)
    
    # Add to history
    profile.metric_history.append({
      "timestamp": timestamp.isoformat(),
      "metrics": metrics.copy()
    })
    
    # Keep only last 100 entries
    if len(profile.metric_history) > 100:
      profile.metric_history = profile.metric_history[-100:]
    
    await self.storage.save_profile(profile)
  
  async def promote_agent_group(
    self,
    agent_group: str,
    changed_by: str,
    reason: str = "Manual promotion"
  ) -> bool:
    """Promote agent group to next autonomy level."""
    profile = await self.storage.get_profile(agent_group)
    if not profile or profile.aml_level >= AutonomyLevel.AML_5:
      return False
    
    old_level = profile.aml_level
    new_level = AutonomyLevel(profile.aml_level + 1)
    
    # Update profile
    profile.aml_level = new_level
    profile.last_change_by = changed_by
    profile.ts_last_change = datetime.now()
    
    await self.storage.save_profile(profile)
    
    # Create change record
    change_record = AMLChangeRecord(
      change_id=str(uuid.uuid4()),
      agent_group=agent_group,
      pillar=profile.pillar,
      from_level=old_level,
      to_level=new_level,
      change_type=ChangeType.PROMOTION,
      changed_by=changed_by,
      timestamp=datetime.now(),
      reason=reason,
      kpi_snapshot=profile.current_metrics.copy()
    )
    await self.storage.save_change_record(change_record)
    
    logger.info(f"Promoted {agent_group} from {old_level.name} to {new_level.name}")
    return True
  
  async def demote_agent_group(
    self,
    agent_group: str,
    changed_by: str,
    reason: str = "Performance degradation"
  ) -> bool:
    """Demote agent group to lower autonomy level."""
    profile = await self.storage.get_profile(agent_group)
    if not profile or profile.aml_level <= AutonomyLevel.AML_0:
      return False
    
    old_level = profile.aml_level
    new_level = AutonomyLevel(profile.aml_level - 1)
    
    # Update profile
    profile.aml_level = new_level
    profile.last_change_by = changed_by
    profile.ts_last_change = datetime.now()
    profile.drift_incidents += 1
    
    await self.storage.save_profile(profile)
    
    # Create change record
    change_record = AMLChangeRecord(
      change_id=str(uuid.uuid4()),
      agent_group=agent_group,
      pillar=profile.pillar,
      from_level=old_level,
      to_level=new_level,
      change_type=ChangeType.DEMOTION,
      changed_by=changed_by,
      timestamp=datetime.now(),
      reason=reason,
      kpi_snapshot=profile.current_metrics.copy()
    )
    await self.storage.save_change_record(change_record)
    
    logger.warning(f"Demoted {agent_group} from {old_level.name} to {new_level.name}: {reason}")
    return True
  
  async def emergency_pause(
    self,
    agent_group: str,
    changed_by: str,
    reason: str = "Emergency pause"
  ) -> bool:
    """Emergency pause an agent group."""
    profile = await self.storage.get_profile(agent_group)
    if not profile:
      return False
    
    old_paused = profile.emergency_paused
    profile.emergency_paused = True
    profile.last_change_by = changed_by
    profile.ts_last_change = datetime.now()
    
    await self.storage.save_profile(profile)
    
    # Create change record
    change_record = AMLChangeRecord(
      change_id=str(uuid.uuid4()),
      agent_group=agent_group,
      pillar=profile.pillar,
      from_level=profile.aml_level,
      to_level=profile.aml_level,
      change_type=ChangeType.EMERGENCY_PAUSE,
      changed_by=changed_by,
      timestamp=datetime.now(),
      reason=reason
    )
    await self.storage.save_change_record(change_record)
    
    logger.critical(f"Emergency pause activated for {agent_group}: {reason}")
    return True
  
  async def activate_kill_switch(
    self,
    agent_group: str,
    changed_by: str,
    reason: str = "Kill switch activated"
  ) -> bool:
    """Activate kill switch for agent group."""
    profile = await self.storage.get_profile(agent_group)
    if not profile:
      return False
    
    profile.kill_switch_active = True
    profile.emergency_paused = True
    profile.last_change_by = changed_by
    profile.ts_last_change = datetime.now()
    
    await self.storage.save_profile(profile)
    
    # Create change record
    change_record = AMLChangeRecord(
      change_id=str(uuid.uuid4()),
      agent_group=agent_group,
      pillar=profile.pillar,
      from_level=profile.aml_level,
      to_level=AutonomyLevel.AML_0,  # Effectively AML 0
      change_type=ChangeType.EMERGENCY_PAUSE,
      changed_by=changed_by,
      timestamp=datetime.now(),
      reason=f"KILL SWITCH: {reason}"
    )
    await self.storage.save_change_record(change_record)
    
    logger.critical(f"KILL SWITCH ACTIVATED for {agent_group}: {reason}")
    return True
  
  async def check_agent_permission(
    self,
    agent_group: str,
    tool_name: str,
    cost: Optional[float] = None,
    transaction_value: Optional[float] = None
  ) -> Dict[str, Any]:
    """Check if agent group can execute a tool - called by Policy Engine."""
    profile = await self.storage.get_profile(agent_group)
    if not profile:
      return {
        "allowed": False,
        "reason": f"Agent group {agent_group} not registered",
        "aml_level": 0
      }
    
    result = profile.can_execute_tool(tool_name, cost, transaction_value)
    result["aml_level"] = profile.aml_level.value
    result["agent_group"] = agent_group
    result["pillar"] = profile.pillar
    
    return result
  
  async def get_pillar_summary(self) -> Dict[str, Any]:
    """Get AML summary by pillar."""
    profiles = await self.storage.list_profiles()
    pillar_summary = {}
    
    for profile in profiles:
      if profile.pillar not in pillar_summary:
        pillar_summary[profile.pillar] = {
          "agent_groups": [],
          "average_level": 0,
          "max_level": 0,
          "min_level": 5,
          "emergency_paused": 0,
          "kill_switches": 0
        }
      
      summary = pillar_summary[profile.pillar]
      summary["agent_groups"].append({
        "group": profile.agent_group,
        "level": profile.aml_level.value,
        "emergency_paused": profile.emergency_paused,
        "kill_switch": profile.kill_switch_active
      })
      
      summary["max_level"] = max(summary["max_level"], profile.aml_level.value)
      summary["min_level"] = min(summary["min_level"], profile.aml_level.value)
      
      if profile.emergency_paused:
        summary["emergency_paused"] += 1
      if profile.kill_switch_active:
        summary["kill_switches"] += 1
    
    # Calculate averages
    for pillar, summary in pillar_summary.items():
      if summary["agent_groups"]:
        levels = [ag["level"] for ag in summary["agent_groups"]]
        summary["average_level"] = sum(levels) / len(levels)
    
    return pillar_summary
  
  async def get_audit_trail(
    self,
    agent_group: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
  ) -> List[Dict[str, Any]]:
    """Get audit trail of AML changes."""
    records = await self.storage.get_change_history(agent_group, limit)
    
    # Filter by date range if specified
    if start_date or end_date:
      filtered_records = []
      for record in records:
        if start_date and record.timestamp < start_date:
          continue
        if end_date and record.timestamp > end_date:
          continue
        filtered_records.append(record)
      records = filtered_records
    
    return [record.to_audit_log() for record in records]


# Factory function for easy setup
def create_aml_registry(
  storage_type: str = "memory",
  **storage_kwargs
) -> EnhancedAMLRegistry:
  """Factory function to create AML registry with specified storage."""
  if storage_type == "memory":
    storage = InMemoryAMLStorage()
  elif storage_type == "spanner":
    storage = CloudSpannerAMLStorage(**storage_kwargs)
  else:
    raise ValueError(f"Unknown storage type: {storage_type}")
  
  return EnhancedAMLRegistry(storage=storage)