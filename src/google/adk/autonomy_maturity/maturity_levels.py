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

from enum import IntEnum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AutonomyLevel(IntEnum):
  """Levels of agent autonomy based on maturity."""
  
  LEVEL_0_MANUAL = 0  # No automation - human performs all tasks
  LEVEL_1_ASSISTED = 1  # Agent assists human with suggestions
  LEVEL_2_PARTIAL = 2  # Agent performs some tasks with human approval
  LEVEL_3_CONDITIONAL = 3  # Agent performs tasks, human monitors
  LEVEL_4_HIGH = 4  # Agent performs most tasks independently
  LEVEL_5_FULL = 5  # Fully autonomous agent operation
  
  @property
  def description(self) -> str:
    """Get description of the autonomy level."""
    descriptions = {
        self.LEVEL_0_MANUAL: "Manual operation - Human performs all tasks",
        self.LEVEL_1_ASSISTED: "AI-assisted - Agent provides suggestions and insights",
        self.LEVEL_2_PARTIAL: "Partial automation - Agent executes with approval",
        self.LEVEL_3_CONDITIONAL: "Conditional automation - Human monitors agent",
        self.LEVEL_4_HIGH: "High automation - Agent operates independently",
        self.LEVEL_5_FULL: "Full automation - Complete autonomous operation",
    }
    return descriptions.get(self, "Unknown level")
  
  @property
  def human_involvement(self) -> str:
    """Get the level of human involvement required."""
    involvement = {
        self.LEVEL_0_MANUAL: "Complete control",
        self.LEVEL_1_ASSISTED: "Makes all decisions",
        self.LEVEL_2_PARTIAL: "Approves actions",
        self.LEVEL_3_CONDITIONAL: "Monitors and intervenes",
        self.LEVEL_4_HIGH: "Sets objectives only",
        self.LEVEL_5_FULL: "Strategic oversight",
    }
    return involvement.get(self, "Unknown")


class MaturityDimension(BaseModel):
  """A dimension of maturity assessment."""
  
  name: str = Field(description="Name of the dimension")
  current_level: AutonomyLevel = Field(
      description="Current maturity level in this dimension"
  )
  target_level: AutonomyLevel = Field(
      description="Target maturity level for this dimension"
  )
  score: float = Field(
      description="Score from 0-100 representing maturity", ge=0, le=100
  )
  capabilities: List[str] = Field(
      default_factory=list, description="Capabilities in this dimension"
  )
  gaps: List[str] = Field(
      default_factory=list, description="Gaps to reach next level"
  )
  recommendations: List[str] = Field(
      default_factory=list, description="Recommendations for improvement"
  )


class MaturityAssessment(BaseModel):
  """Complete maturity assessment for an agent or system."""
  
  agent_name: str = Field(description="Name of the assessed agent")
  overall_level: AutonomyLevel = Field(description="Overall autonomy level")
  overall_score: float = Field(
      description="Overall maturity score", ge=0, le=100
  )
  dimensions: Dict[str, MaturityDimension] = Field(
      default_factory=dict, description="Individual dimension assessments"
  )
  strengths: List[str] = Field(
      default_factory=list, description="Key strengths identified"
  )
  improvement_areas: List[str] = Field(
      default_factory=list, description="Areas needing improvement"
  )
  roadmap: List[Dict[str, any]] = Field(
      default_factory=list, description="Roadmap to higher maturity"
  )
  assessment_date: str = Field(description="Date of assessment")
  next_review_date: str = Field(description="Recommended next review date")


class MaturityFramework(BaseModel):
  """Framework for assessing and tracking maturity."""
  
  name: str = Field(
      default="ADK Autonomy Maturity Framework",
      description="Name of the framework",
  )
  version: str = Field(default="1.0", description="Framework version")
  dimensions: List[str] = Field(
      default_factory=lambda: [
          "decision_making",
          "learning_capability",
          "error_handling",
          "interaction_complexity",
          "domain_expertise",
          "adaptability",
      ],
      description="Dimensions assessed in the framework",
  )
  
  def create_dimension_criteria(self) -> Dict[str, Dict[AutonomyLevel, str]]:
    """Create criteria for each dimension at each level."""
    return {
        "decision_making": {
            AutonomyLevel.LEVEL_0_MANUAL: "No automated decisions",
            AutonomyLevel.LEVEL_1_ASSISTED: "Provides decision recommendations",
            AutonomyLevel.LEVEL_2_PARTIAL: "Makes simple decisions with approval",
            AutonomyLevel.LEVEL_3_CONDITIONAL: "Makes routine decisions independently",
            AutonomyLevel.LEVEL_4_HIGH: "Makes complex decisions with exceptions",
            AutonomyLevel.LEVEL_5_FULL: "Full decision autonomy with learning",
        },
        "learning_capability": {
            AutonomyLevel.LEVEL_0_MANUAL: "No learning capability",
            AutonomyLevel.LEVEL_1_ASSISTED: "Basic pattern recognition",
            AutonomyLevel.LEVEL_2_PARTIAL: "Learns from explicit feedback",
            AutonomyLevel.LEVEL_3_CONDITIONAL: "Learns from outcomes",
            AutonomyLevel.LEVEL_4_HIGH: "Self-directed learning",
            AutonomyLevel.LEVEL_5_FULL: "Continuous adaptive learning",
        },
        "error_handling": {
            AutonomyLevel.LEVEL_0_MANUAL: "Human handles all errors",
            AutonomyLevel.LEVEL_1_ASSISTED: "Detects and reports errors",
            AutonomyLevel.LEVEL_2_PARTIAL: "Handles known error types",
            AutonomyLevel.LEVEL_3_CONDITIONAL: "Recovers from most errors",
            AutonomyLevel.LEVEL_4_HIGH: "Prevents and mitigates errors",
            AutonomyLevel.LEVEL_5_FULL: "Self-healing with learning",
        },
        "interaction_complexity": {
            AutonomyLevel.LEVEL_0_MANUAL: "No automated interaction",
            AutonomyLevel.LEVEL_1_ASSISTED: "Simple Q&A interactions",
            AutonomyLevel.LEVEL_2_PARTIAL: "Structured conversations",
            AutonomyLevel.LEVEL_3_CONDITIONAL: "Context-aware dialogue",
            AutonomyLevel.LEVEL_4_HIGH: "Multi-party negotiations",
            AutonomyLevel.LEVEL_5_FULL: "Human-like interaction",
        },
        "domain_expertise": {
            AutonomyLevel.LEVEL_0_MANUAL: "No domain knowledge",
            AutonomyLevel.LEVEL_1_ASSISTED: "Basic domain awareness",
            AutonomyLevel.LEVEL_2_PARTIAL: "Follows domain rules",
            AutonomyLevel.LEVEL_3_CONDITIONAL: "Applies domain expertise",
            AutonomyLevel.LEVEL_4_HIGH: "Expert-level knowledge",
            AutonomyLevel.LEVEL_5_FULL: "Innovates in domain",
        },
        "adaptability": {
            AutonomyLevel.LEVEL_0_MANUAL: "No adaptability",
            AutonomyLevel.LEVEL_1_ASSISTED: "Adapts to user preferences",
            AutonomyLevel.LEVEL_2_PARTIAL: "Adapts to new scenarios",
            AutonomyLevel.LEVEL_3_CONDITIONAL: "Adapts strategies",
            AutonomyLevel.LEVEL_4_HIGH: "Adapts to environment changes",
            AutonomyLevel.LEVEL_5_FULL: "Evolves capabilities",
        },
    }
  
  def calculate_overall_level(
      self, dimension_scores: Dict[str, float]
  ) -> AutonomyLevel:
    """Calculate overall autonomy level from dimension scores.
    
    Args:
        dimension_scores: Dict mapping dimension names to scores (0-100)
        
    Returns:
        Overall AutonomyLevel
    """
    if not dimension_scores:
      return AutonomyLevel.LEVEL_0_MANUAL
    
    avg_score = sum(dimension_scores.values()) / len(dimension_scores)
    
    # Map average score to level
    if avg_score >= 90:
      return AutonomyLevel.LEVEL_5_FULL
    elif avg_score >= 75:
      return AutonomyLevel.LEVEL_4_HIGH
    elif avg_score >= 60:
      return AutonomyLevel.LEVEL_3_CONDITIONAL
    elif avg_score >= 40:
      return AutonomyLevel.LEVEL_2_PARTIAL
    elif avg_score >= 20:
      return AutonomyLevel.LEVEL_1_ASSISTED
    else:
      return AutonomyLevel.LEVEL_0_MANUAL
  
  def get_capabilities_for_level(
      self, dimension: str, level: AutonomyLevel
  ) -> List[str]:
    """Get required capabilities for a dimension at a specific level.
    
    Args:
        dimension: The dimension name
        level: The autonomy level
        
    Returns:
        List of required capabilities
    """
    capabilities_map = {
        "decision_making": {
            AutonomyLevel.LEVEL_1_ASSISTED: [
                "Generate recommendations",
                "Explain reasoning",
            ],
            AutonomyLevel.LEVEL_2_PARTIAL: [
                "Execute approved decisions",
                "Track decision outcomes",
            ],
            AutonomyLevel.LEVEL_3_CONDITIONAL: [
                "Make routine decisions",
                "Escalate exceptions",
            ],
            AutonomyLevel.LEVEL_4_HIGH: [
                "Handle complex scenarios",
                "Optimize decision strategies",
            ],
            AutonomyLevel.LEVEL_5_FULL: [
                "Innovate solutions",
                "Self-governance",
            ],
        },
        "learning_capability": {
            AutonomyLevel.LEVEL_1_ASSISTED: [
                "Pattern recognition",
                "Basic memory",
            ],
            AutonomyLevel.LEVEL_2_PARTIAL: [
                "Learn from feedback",
                "Update knowledge base",
            ],
            AutonomyLevel.LEVEL_3_CONDITIONAL: [
                "Learn from outcomes",
                "Generalize learning",
            ],
            AutonomyLevel.LEVEL_4_HIGH: [
                "Self-directed learning",
                "Transfer learning",
            ],
            AutonomyLevel.LEVEL_5_FULL: [
                "Meta-learning",
                "Create new knowledge",
            ],
        },
    }
    
    return capabilities_map.get(dimension, {}).get(level, [])
  
  def get_maturity_roadmap(
      self, current_assessment: MaturityAssessment, target_level: AutonomyLevel
  ) -> List[Dict[str, any]]:
    """Generate roadmap to reach target maturity level.
    
    Args:
        current_assessment: Current maturity assessment
        target_level: Target autonomy level
        
    Returns:
        List of roadmap steps
    """
    roadmap = []
    current_level = current_assessment.overall_level
    
    if current_level >= target_level:
      return [{
          "phase": "Maintenance",
          "description": "Maintain current maturity level",
          "duration": "Ongoing",
          "actions": ["Regular assessments", "Continuous improvement"],
      }]
    
    # Generate phases for each level transition
    for level in range(current_level + 1, target_level + 1):
      phase = {
          "phase": f"Level {level} Achievement",
          "target_level": AutonomyLevel(level),
          "description": AutonomyLevel(level).description,
          "duration": f"{3 * (level - current_level)} months",
          "key_milestones": [],
          "required_capabilities": [],
          "success_metrics": [],
      }
      
      # Add dimension-specific milestones
      for dim_name, dimension in current_assessment.dimensions.items():
        if dimension.current_level < level:
          phase["key_milestones"].append(
              f"Upgrade {dim_name} to Level {level}"
          )
          phase["required_capabilities"].extend(
              self.get_capabilities_for_level(dim_name, AutonomyLevel(level))
          )
      
      # Add success metrics
      phase["success_metrics"] = [
          f"Overall maturity score > {20 * level}%",
          f"All critical dimensions at Level {level}",
          "Successful pilot in production",
      ]
      
      roadmap.append(phase)
    
    return roadmap