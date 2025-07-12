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
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..agents.base_agent import BaseAgent
from ..tools.base_tool import BaseTool
from .maturity_levels import (
    AutonomyLevel,
    MaturityAssessment,
    MaturityDimension,
    MaturityFramework,
)

logger = logging.getLogger(__name__)


class EvaluationCriteria(BaseModel):
  """Criteria for evaluating a specific aspect of maturity."""
  
  dimension: str = Field(description="Dimension being evaluated")
  metric_name: str = Field(description="Name of the metric")
  weight: float = Field(
      default=1.0, description="Weight of this metric", ge=0, le=1
  )
  threshold_values: Dict[AutonomyLevel, float] = Field(
      description="Threshold values for each level"
  )
  
  def evaluate(self, value: float) -> AutonomyLevel:
    """Evaluate which level a value achieves.
    
    Args:
        value: The metric value to evaluate
        
    Returns:
        The achieved AutonomyLevel
    """
    achieved_level = AutonomyLevel.LEVEL_0_MANUAL
    
    for level in sorted(self.threshold_values.keys()):
      if value >= self.threshold_values[level]:
        achieved_level = level
      else:
        break
    
    return achieved_level


class MaturityEvaluator:
  """Evaluates agent maturity across multiple dimensions."""
  
  def __init__(self, framework: Optional[MaturityFramework] = None):
    """Initialize the maturity evaluator.
    
    Args:
        framework: The maturity framework to use
    """
    self.framework = framework or MaturityFramework()
    self.criteria = self._initialize_criteria()
  
  def _initialize_criteria(self) -> Dict[str, List[EvaluationCriteria]]:
    """Initialize evaluation criteria for each dimension."""
    criteria = {
        "decision_making": [
            EvaluationCriteria(
                dimension="decision_making",
                metric_name="decision_accuracy",
                weight=0.4,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 60.0,
                    AutonomyLevel.LEVEL_2_PARTIAL: 70.0,
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 80.0,
                    AutonomyLevel.LEVEL_4_HIGH: 90.0,
                    AutonomyLevel.LEVEL_5_FULL: 95.0,
                },
            ),
            EvaluationCriteria(
                dimension="decision_making",
                metric_name="decision_complexity",
                weight=0.3,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 1.0,  # Simple decisions
                    AutonomyLevel.LEVEL_2_PARTIAL: 2.0,  # Moderate complexity
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 3.0,  # Complex decisions
                    AutonomyLevel.LEVEL_4_HIGH: 4.0,  # Very complex
                    AutonomyLevel.LEVEL_5_FULL: 5.0,  # Unprecedented situations
                },
            ),
            EvaluationCriteria(
                dimension="decision_making",
                metric_name="autonomy_percentage",
                weight=0.3,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 0.0,
                    AutonomyLevel.LEVEL_2_PARTIAL: 20.0,
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 50.0,
                    AutonomyLevel.LEVEL_4_HIGH: 80.0,
                    AutonomyLevel.LEVEL_5_FULL: 95.0,
                },
            ),
        ],
        "learning_capability": [
            EvaluationCriteria(
                dimension="learning_capability",
                metric_name="learning_rate",
                weight=0.5,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 0.1,
                    AutonomyLevel.LEVEL_2_PARTIAL: 0.3,
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 0.5,
                    AutonomyLevel.LEVEL_4_HIGH: 0.7,
                    AutonomyLevel.LEVEL_5_FULL: 0.9,
                },
            ),
            EvaluationCriteria(
                dimension="learning_capability",
                metric_name="knowledge_retention",
                weight=0.5,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 50.0,
                    AutonomyLevel.LEVEL_2_PARTIAL: 70.0,
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 85.0,
                    AutonomyLevel.LEVEL_4_HIGH: 95.0,
                    AutonomyLevel.LEVEL_5_FULL: 99.0,
                },
            ),
        ],
        "error_handling": [
            EvaluationCriteria(
                dimension="error_handling",
                metric_name="error_recovery_rate",
                weight=0.6,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 0.0,
                    AutonomyLevel.LEVEL_2_PARTIAL: 30.0,
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 60.0,
                    AutonomyLevel.LEVEL_4_HIGH: 85.0,
                    AutonomyLevel.LEVEL_5_FULL: 95.0,
                },
            ),
            EvaluationCriteria(
                dimension="error_handling",
                metric_name="mean_time_to_recovery",
                weight=0.4,
                threshold_values={
                    AutonomyLevel.LEVEL_1_ASSISTED: 3600.0,  # 1 hour
                    AutonomyLevel.LEVEL_2_PARTIAL: 1800.0,  # 30 min
                    AutonomyLevel.LEVEL_3_CONDITIONAL: 600.0,  # 10 min
                    AutonomyLevel.LEVEL_4_HIGH: 120.0,  # 2 min
                    AutonomyLevel.LEVEL_5_FULL: 30.0,  # 30 sec
                },
            ),
        ],
    }
    
    return criteria
  
  def evaluate_agent(
      self,
      agent: BaseAgent,
      performance_metrics: Dict[str, Dict[str, float]],
      target_level: Optional[AutonomyLevel] = None,
  ) -> MaturityAssessment:
    """Evaluate an agent's maturity level.
    
    Args:
        agent: The agent to evaluate
        performance_metrics: Performance metrics by dimension
        target_level: Target maturity level (optional)
        
    Returns:
        MaturityAssessment with detailed results
    """
    dimensions = {}
    dimension_scores = {}
    
    # Evaluate each dimension
    for dimension in self.framework.dimensions:
      if dimension in performance_metrics:
        dim_assessment = self._evaluate_dimension(
            dimension,
            performance_metrics[dimension],
            target_level,
        )
        dimensions[dimension] = dim_assessment
        dimension_scores[dimension] = dim_assessment.score
      else:
        # Default assessment if no metrics provided
        dimensions[dimension] = MaturityDimension(
            name=dimension,
            current_level=AutonomyLevel.LEVEL_0_MANUAL,
            target_level=target_level or AutonomyLevel.LEVEL_3_CONDITIONAL,
            score=0.0,
            gaps=["No performance data available"],
            recommendations=["Start collecting metrics for this dimension"],
        )
        dimension_scores[dimension] = 0.0
    
    # Calculate overall level and score
    overall_level = self.framework.calculate_overall_level(dimension_scores)
    overall_score = (
        sum(dimension_scores.values()) / len(dimension_scores)
        if dimension_scores
        else 0.0
    )
    
    # Identify strengths and improvement areas
    strengths = []
    improvement_areas = []
    
    for dim_name, dim in dimensions.items():
      if dim.score >= 75:
        strengths.append(f"Strong {dim_name} capabilities (score: {dim.score})")
      elif dim.score < 50:
        improvement_areas.append(
            f"{dim_name} needs improvement (score: {dim.score})"
        )
    
    # Create assessment
    assessment = MaturityAssessment(
        agent_name=agent.name,
        overall_level=overall_level,
        overall_score=overall_score,
        dimensions=dimensions,
        strengths=strengths,
        improvement_areas=improvement_areas,
        assessment_date=datetime.now().isoformat(),
        next_review_date=(datetime.now() + timedelta(days=90)).isoformat(),
    )
    
    # Generate roadmap if target level specified
    if target_level and target_level > overall_level:
      assessment.roadmap = self.framework.get_maturity_roadmap(
          assessment, target_level
      )
    
    return assessment
  
  def _evaluate_dimension(
      self,
      dimension: str,
      metrics: Dict[str, float],
      target_level: Optional[AutonomyLevel],
  ) -> MaturityDimension:
    """Evaluate a single dimension.
    
    Args:
        dimension: The dimension to evaluate
        metrics: Performance metrics for this dimension
        target_level: Target maturity level
        
    Returns:
        MaturityDimension assessment
    """
    if dimension not in self.criteria:
      # Return basic assessment if no criteria defined
      return MaturityDimension(
          name=dimension,
          current_level=AutonomyLevel.LEVEL_1_ASSISTED,
          target_level=target_level or AutonomyLevel.LEVEL_3_CONDITIONAL,
          score=50.0,
          capabilities=["Basic functionality"],
          gaps=["Criteria not defined"],
          recommendations=["Define evaluation criteria"],
      )
    
    # Evaluate each metric
    metric_levels = []
    metric_scores = []
    
    for criterion in self.criteria[dimension]:
      if criterion.metric_name in metrics:
        value = metrics[criterion.metric_name]
        level = criterion.evaluate(value)
        metric_levels.append(level)
        
        # Calculate score (0-100) based on achievement
        max_threshold = max(criterion.threshold_values.values())
        score = min((value / max_threshold) * 100, 100.0) if max_threshold > 0 else 0.0
        metric_scores.append(score * criterion.weight)
    
    # Calculate dimension level and score
    if metric_levels:
      current_level = min(metric_levels)  # Conservative approach
      dimension_score = sum(metric_scores) / sum(
          c.weight for c in self.criteria[dimension]
      )
    else:
      current_level = AutonomyLevel.LEVEL_0_MANUAL
      dimension_score = 0.0
    
    # Determine capabilities and gaps
    capabilities = self.framework.get_capabilities_for_level(
        dimension, current_level
    )
    
    gaps = []
    if current_level < (target_level or AutonomyLevel.LEVEL_3_CONDITIONAL):
      next_level = AutonomyLevel(current_level + 1)
      next_capabilities = self.framework.get_capabilities_for_level(
          dimension, next_level
      )
      gaps = [f"Need: {cap}" for cap in next_capabilities]
    
    # Generate recommendations
    recommendations = self._generate_recommendations(
        dimension, current_level, metrics
    )
    
    return MaturityDimension(
        name=dimension,
        current_level=current_level,
        target_level=target_level or AutonomyLevel.LEVEL_3_CONDITIONAL,
        score=round(dimension_score, 2),
        capabilities=capabilities,
        gaps=gaps,
        recommendations=recommendations,
    )
  
  def _generate_recommendations(
      self, dimension: str, current_level: AutonomyLevel, metrics: Dict[str, float]
  ) -> List[str]:
    """Generate improvement recommendations.
    
    Args:
        dimension: The dimension
        current_level: Current maturity level
        metrics: Current metrics
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    if dimension == "decision_making":
      if current_level < AutonomyLevel.LEVEL_3_CONDITIONAL:
        recommendations.append("Implement decision logging and analysis")
        recommendations.append("Expand decision tree coverage")
      if metrics.get("decision_accuracy", 0) < 80:
        recommendations.append("Improve decision models with more training data")
        
    elif dimension == "learning_capability":
      if current_level < AutonomyLevel.LEVEL_2_PARTIAL:
        recommendations.append("Implement feedback collection mechanism")
      if current_level < AutonomyLevel.LEVEL_4_HIGH:
        recommendations.append("Add reinforcement learning capabilities")
        
    elif dimension == "error_handling":
      if metrics.get("error_recovery_rate", 0) < 60:
        recommendations.append("Implement automated error recovery procedures")
      if current_level < AutonomyLevel.LEVEL_3_CONDITIONAL:
        recommendations.append("Add error pattern recognition")
    
    # Generic recommendations
    if current_level < AutonomyLevel.LEVEL_3_CONDITIONAL:
      recommendations.append(f"Increase automation in {dimension}")
      recommendations.append("Enhance monitoring and metrics collection")
    
    return recommendations
  
  def compare_assessments(
      self, assessment1: MaturityAssessment, assessment2: MaturityAssessment
  ) -> Dict[str, Any]:
    """Compare two maturity assessments to track progress.
    
    Args:
        assessment1: First (usually earlier) assessment
        assessment2: Second (usually later) assessment
        
    Returns:
        Comparison results
    """
    comparison = {
        "agent_name": assessment2.agent_name,
        "time_period": {
            "from": assessment1.assessment_date,
            "to": assessment2.assessment_date,
        },
        "overall_progress": {
            "level_change": assessment2.overall_level - assessment1.overall_level,
            "score_change": assessment2.overall_score - assessment1.overall_score,
            "improved": assessment2.overall_score > assessment1.overall_score,
        },
        "dimension_changes": {},
        "achievements": [],
        "concerns": [],
    }
    
    # Compare dimensions
    for dim_name in assessment2.dimensions:
      if dim_name in assessment1.dimensions:
        dim1 = assessment1.dimensions[dim_name]
        dim2 = assessment2.dimensions[dim_name]
        
        change = {
            "level_change": dim2.current_level - dim1.current_level,
            "score_change": dim2.score - dim1.score,
            "gaps_resolved": len(dim1.gaps) - len(dim2.gaps),
        }
        
        comparison["dimension_changes"][dim_name] = change
        
        # Track achievements
        if change["level_change"] > 0:
          comparison["achievements"].append(
              f"Advanced {dim_name} from Level {dim1.current_level} to {dim2.current_level}"
          )
        elif change["score_change"] > 10:
          comparison["achievements"].append(
              f"Significant improvement in {dim_name} (+{change['score_change']:.1f})"
          )
        
        # Track concerns
        if change["score_change"] < -5:
          comparison["concerns"].append(
              f"Regression in {dim_name} (-{abs(change['score_change']):.1f})"
          )
    
    return comparison