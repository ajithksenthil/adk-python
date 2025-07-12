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

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import Field

from ..agents.invocation_context import InvocationContext
from ..agents.llm_agent import LlmAgent
from ..events.event import Event
from ..models import types
from ..tools.function_tool import FunctionTool
from .maturity_evaluator import MaturityEvaluator
from .maturity_levels import AutonomyLevel, MaturityAssessment

logger = logging.getLogger(__name__)


class AdaptiveAutonomyAgent(LlmAgent):
  """Agent that adapts its autonomy level based on maturity assessment.
  
  This agent can operate at different autonomy levels and automatically
  adjusts its behavior based on:
  - Current maturity assessment
  - Performance metrics
  - User preferences
  - Context requirements
  """
  
  current_autonomy_level: AutonomyLevel = Field(
      default=AutonomyLevel.LEVEL_1_ASSISTED,
      description="Current operating autonomy level",
  )
  
  target_autonomy_level: AutonomyLevel = Field(
      default=AutonomyLevel.LEVEL_3_CONDITIONAL,
      description="Target autonomy level to achieve",
  )
  
  allow_dynamic_adjustment: bool = Field(
      default=True,
      description="Allow dynamic adjustment of autonomy level",
  )
  
  performance_metrics: Dict[str, Dict[str, float]] = Field(
      default_factory=dict,
      description="Performance metrics for maturity evaluation",
  )
  
  maturity_evaluator: MaturityEvaluator = Field(
      default_factory=MaturityEvaluator,
      description="Evaluator for assessing maturity",
  )
  
  last_assessment: Optional[MaturityAssessment] = Field(
      default=None, description="Last maturity assessment"
  )
  
  approval_required_actions: List[str] = Field(
      default_factory=list,
      description="Actions that require approval at current level",
  )
  
  def __init__(self, **kwargs):
    """Initialize the adaptive autonomy agent."""
    # Set instruction based on autonomy level
    if "instruction" not in kwargs:
      kwargs["instruction"] = self._generate_level_instruction()
    
    super().__init__(**kwargs)
    
    # Add maturity tools
    self._add_maturity_tools()
    
    # Configure based on current level
    self._configure_for_level()
  
  def _generate_level_instruction(self) -> str:
    """Generate instruction based on current autonomy level."""
    level_instructions = {
        AutonomyLevel.LEVEL_0_MANUAL: (
            "I am operating in manual mode. I will only provide information "
            "and suggestions. All actions must be performed by you."
        ),
        AutonomyLevel.LEVEL_1_ASSISTED: (
            "I am operating in assisted mode. I will provide recommendations "
            "and insights to help you make decisions, but you maintain control."
        ),
        AutonomyLevel.LEVEL_2_PARTIAL: (
            "I am operating in partial automation mode. I can execute certain "
            "actions with your approval. I will always ask before taking action."
        ),
        AutonomyLevel.LEVEL_3_CONDITIONAL: (
            "I am operating in conditional automation mode. I can handle routine "
            "tasks independently but will seek your input for complex decisions."
        ),
        AutonomyLevel.LEVEL_4_HIGH: (
            "I am operating in high automation mode. I work independently on "
            "most tasks and only involve you for strategic decisions."
        ),
        AutonomyLevel.LEVEL_5_FULL: (
            "I am operating in full automation mode. I handle all tasks "
            "autonomously while keeping you informed of important outcomes."
        ),
    }
    
    base_instruction = level_instructions.get(
        self.current_autonomy_level,
        "I am an adaptive agent operating at a custom autonomy level.",
    )
    
    return f"{base_instruction} My current autonomy level is {self.current_autonomy_level.name}."
  
  def _add_maturity_tools(self):
    """Add tools for maturity management."""
    maturity_tools = [
        FunctionTool(
            name="assess_maturity",
            description="Assess current maturity level",
            func=self._assess_maturity_tool,
        ),
        FunctionTool(
            name="adjust_autonomy_level",
            description="Adjust autonomy level based on context",
            func=self._adjust_autonomy_tool,
        ),
        FunctionTool(
            name="get_autonomy_status",
            description="Get current autonomy status and capabilities",
            func=self._get_autonomy_status_tool,
        ),
        FunctionTool(
            name="request_level_change",
            description="Request change in autonomy level",
            func=self._request_level_change_tool,
        ),
    ]
    
    if self.tools:
      self.tools.extend(maturity_tools)
    else:
      self.tools = maturity_tools
  
  def _configure_for_level(self):
    """Configure agent behavior based on current autonomy level."""
    # Clear previous configuration
    self.approval_required_actions.clear()
    
    # Configure based on level
    if self.current_autonomy_level <= AutonomyLevel.LEVEL_1_ASSISTED:
      # No automated actions
      self.approval_required_actions.extend([
          "execute_*",
          "modify_*",
          "delete_*",
          "create_*",
      ])
    elif self.current_autonomy_level == AutonomyLevel.LEVEL_2_PARTIAL:
      # Require approval for modifications
      self.approval_required_actions.extend([
          "modify_*",
          "delete_*",
      ])
    elif self.current_autonomy_level == AutonomyLevel.LEVEL_3_CONDITIONAL:
      # Require approval for destructive actions
      self.approval_required_actions.extend([
          "delete_*",
          "reset_*",
      ])
    # Levels 4 and 5 have minimal restrictions
    
    logger.info(
        f"Configured for {self.current_autonomy_level.name} with "
        f"{len(self.approval_required_actions)} restricted actions"
    )
  
  async def _run_async_impl(
      self, invocation_context: InvocationContext
  ) -> AsyncGenerator[Event, None]:
    """Run with autonomy level adaptation."""
    # Check if we should assess maturity
    if self.allow_dynamic_adjustment and not self.last_assessment:
      self._perform_self_assessment()
    
    # Adapt behavior based on level
    if self.current_autonomy_level <= AutonomyLevel.LEVEL_1_ASSISTED:
      # Add explanation to all responses
      async for event in super()._run_async_impl(invocation_context):
        if event.content and not event.partial:
          event.content.parts.append(
              types.Part(
                  text=f"\n\n[Operating at {self.current_autonomy_level.description}]"
              )
          )
        yield event
    else:
      # Normal operation with level-appropriate checks
      async for event in super()._run_async_impl(invocation_context):
        yield event
  
  def _perform_self_assessment(self):
    """Perform self-assessment of maturity."""
    assessment = self.maturity_evaluator.evaluate_agent(
        self,
        self.performance_metrics,
        self.target_autonomy_level,
    )
    
    self.last_assessment = assessment
    
    # Adjust level if appropriate
    if self.allow_dynamic_adjustment:
      if assessment.overall_level > self.current_autonomy_level:
        logger.info(
            f"Maturity assessment suggests advancing from "
            f"{self.current_autonomy_level.name} to {assessment.overall_level.name}"
        )
        # In practice, this might require user approval
  
  def set_autonomy_level(
      self, new_level: AutonomyLevel, reason: Optional[str] = None
  ):
    """Set a new autonomy level.
    
    Args:
        new_level: The new autonomy level
        reason: Optional reason for the change
    """
    old_level = self.current_autonomy_level
    self.current_autonomy_level = new_level
    
    # Reconfigure for new level
    self._configure_for_level()
    
    # Update instruction
    self.instruction = self._generate_level_instruction()
    
    logger.info(
        f"Autonomy level changed from {old_level.name} to {new_level.name}"
        f"{f' - Reason: {reason}' if reason else ''}"
    )
  
  def update_performance_metrics(
      self, dimension: str, metrics: Dict[str, float]
  ):
    """Update performance metrics for a dimension.
    
    Args:
        dimension: The dimension to update
        metrics: New metrics for the dimension
    """
    if dimension not in self.performance_metrics:
      self.performance_metrics[dimension] = {}
    
    self.performance_metrics[dimension].update(metrics)
    
    # Trigger reassessment if significant change
    if self.allow_dynamic_adjustment:
      # Simple heuristic: reassess if metrics change significantly
      if any(abs(metrics.get(k, 0) - self.performance_metrics[dimension].get(k, 0)) > 10 
             for k in metrics):
        self._perform_self_assessment()
  
  # Tool implementations
  
  def _assess_maturity_tool(self) -> Dict[str, Any]:
    """Tool to assess current maturity."""
    assessment = self.maturity_evaluator.evaluate_agent(
        self,
        self.performance_metrics,
        self.target_autonomy_level,
    )
    
    self.last_assessment = assessment
    
    return {
        "current_level": assessment.overall_level.name,
        "overall_score": assessment.overall_score,
        "strengths": assessment.strengths,
        "improvement_areas": assessment.improvement_areas,
        "dimension_scores": {
            dim.name: dim.score for dim in assessment.dimensions.values()
        },
    }
  
  def _adjust_autonomy_tool(
      self, context: str, risk_level: str = "medium"
  ) -> Dict[str, Any]:
    """Tool to adjust autonomy based on context."""
    # Simplified logic - in practice would be more sophisticated
    risk_adjustments = {
        "low": 1,  # Can operate one level higher
        "medium": 0,  # Operate at current level
        "high": -1,  # Drop one level for safety
    }
    
    adjustment = risk_adjustments.get(risk_level, 0)
    suggested_level = max(
        AutonomyLevel.LEVEL_0_MANUAL,
        min(
            AutonomyLevel.LEVEL_5_FULL,
            AutonomyLevel(self.current_autonomy_level + adjustment),
        ),
    )
    
    result = {
        "current_level": self.current_autonomy_level.name,
        "suggested_level": suggested_level.name,
        "risk_level": risk_level,
        "context": context,
        "adjustment_made": False,
    }
    
    if self.allow_dynamic_adjustment and suggested_level != self.current_autonomy_level:
      self.set_autonomy_level(
          suggested_level, f"Context adjustment for {risk_level} risk"
      )
      result["adjustment_made"] = True
    
    return result
  
  def _get_autonomy_status_tool(self) -> Dict[str, Any]:
    """Tool to get current autonomy status."""
    return {
        "current_level": {
            "name": self.current_autonomy_level.name,
            "value": self.current_autonomy_level.value,
            "description": self.current_autonomy_level.description,
            "human_involvement": self.current_autonomy_level.human_involvement,
        },
        "target_level": self.target_autonomy_level.name,
        "dynamic_adjustment": self.allow_dynamic_adjustment,
        "approval_required": self.approval_required_actions,
        "last_assessment": {
            "date": self.last_assessment.assessment_date,
            "score": self.last_assessment.overall_score,
        }
        if self.last_assessment
        else None,
    }
  
  def _request_level_change_tool(
      self, requested_level: str, justification: str
  ) -> Dict[str, Any]:
    """Tool to request autonomy level change."""
    try:
      new_level = AutonomyLevel[requested_level]
    except KeyError:
      return {
          "success": False,
          "error": f"Invalid level: {requested_level}",
          "valid_levels": [level.name for level in AutonomyLevel],
      }
    
    # Check if change is reasonable
    level_diff = abs(new_level - self.current_autonomy_level)
    
    if level_diff > 2:
      return {
          "success": False,
          "error": "Cannot jump more than 2 levels at once",
          "current_level": self.current_autonomy_level.name,
          "requested_level": new_level.name,
      }
    
    # In practice, this might require user approval
    approval_required = level_diff > 1 or new_level > AutonomyLevel.LEVEL_3_CONDITIONAL
    
    result = {
        "success": not approval_required,
        "current_level": self.current_autonomy_level.name,
        "requested_level": new_level.name,
        "justification": justification,
        "approval_required": approval_required,
    }
    
    if not approval_required:
      self.set_autonomy_level(new_level, justification)
      result["message"] = f"Level changed to {new_level.name}"
    else:
      result["message"] = "User approval required for this level change"
    
    return result