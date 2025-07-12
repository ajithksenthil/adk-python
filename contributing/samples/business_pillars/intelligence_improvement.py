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

"""Intelligence & Improvement Pillar - Measure, learn, optimise."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep


class MetricCollector(BusinessPillarAgent):
  """Agent for collecting and analyzing metrics."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="metric_collector",
      role=AgentRole.WORKER,
      pillar=PillarType.INTELLIGENCE_IMPROVEMENT,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("collect_metrics", self._collect_metrics, cost=0.5)
    self.register_tool("analyze_trends", self._analyze_trends, cost=1.0)
    self.register_tool("generate_insights", self._generate_insights, cost=1.5)
  
  async def _collect_metrics(self, metric_types: List[str], time_range: str) -> Dict[str, Any]:
    # Mock metric collection
    metrics = {}
    for metric_type in metric_types:
      if metric_type == "revenue":
        metrics[metric_type] = {"value": 125000, "change": 0.15}
      elif metric_type == "customer_satisfaction":
        metrics[metric_type] = {"value": 4.2, "change": -0.05}
      elif metric_type == "user_engagement":
        metrics[metric_type] = {"value": 0.68, "change": 0.08}
    
    return {
      "metrics": metrics,
      "time_range": time_range,
      "collected_at": datetime.now().isoformat()
    }
  
  async def _analyze_trends(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
    trends = {}
    for metric, data in metrics.items():
      if data["change"] > 0.1:
        trends[metric] = "strong_growth"
      elif data["change"] > 0:
        trends[metric] = "growth"
      elif data["change"] < -0.1:
        trends[metric] = "decline"
      else:
        trends[metric] = "stable"
    
    return {"trends": trends, "analysis_date": datetime.now().isoformat()}
  
  async def _generate_insights(self, trends: Dict[str, Any]) -> Dict[str, Any]:
    insights = []
    
    for metric, trend in trends.items():
      if trend == "decline":
        insights.append(f"{metric} showing concerning decline - investigate root causes")
      elif trend == "strong_growth":
        insights.append(f"{metric} performing excellently - maintain current strategies")
    
    return {"insights": insights, "priority_actions": insights[:3]}
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "metrics_analysis":
      metrics = await self._collect_metrics(
        context.get("metric_types", ["revenue", "customer_satisfaction"]),
        context.get("time_range", "30d")
      )
      trends = await self._analyze_trends(metrics["metrics"])
      insights = await self._generate_insights(trends["trends"])
      
      return {"metrics": metrics, "trends": trends, "insights": insights}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["metric_collection", "trend_analysis", "insight_generation"]


class ExperimentDesigner(BusinessPillarAgent):
  """Agent for A/B testing and experimentation."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="experiment_designer",
      role=AgentRole.PLANNER,
      pillar=PillarType.INTELLIGENCE_IMPROVEMENT,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("design_experiment", self._design_experiment, cost=1.0)
    self.register_tool("analyze_results", self._analyze_results, cost=1.5)
    self.register_tool("recommend_rollout", self._recommend_rollout, cost=0.8)
  
  async def _design_experiment(self, hypothesis: str, target_metric: str) -> Dict[str, Any]:
    experiment_id = f"EXP-{uuid.uuid4().hex[:8]}"
    return {
      "experiment_id": experiment_id,
      "hypothesis": hypothesis,
      "target_metric": target_metric,
      "sample_size": 1000,
      "duration_days": 14,
      "traffic_split": {"control": 0.5, "treatment": 0.5},
      "success_criteria": "5% improvement with p < 0.05"
    }
  
  async def _analyze_results(self, experiment_id: str) -> Dict[str, Any]:
    # Mock experiment results
    return {
      "experiment_id": experiment_id,
      "control_metric": 0.15,
      "treatment_metric": 0.18,
      "uplift": 0.20,  # 20% improvement
      "p_value": 0.02,
      "confidence_interval": [0.05, 0.35],
      "statistical_significance": True
    }
  
  async def _recommend_rollout(self, results: Dict[str, Any]) -> Dict[str, Any]:
    uplift = results["uplift"]
    p_value = results["p_value"]
    
    # Auto-promote only if uplift > X% and statistically significant (guardrail)
    auto_promote_threshold = 0.10  # 10% minimum uplift
    
    if uplift > auto_promote_threshold and p_value < 0.05:
      recommendation = "auto_promote"
    elif p_value < 0.05:
      recommendation = "manual_review"
    else:
      recommendation = "reject"
    
    return {
      "experiment_id": results["experiment_id"],
      "recommendation": recommendation,
      "auto_promotable": recommendation == "auto_promote",
      "reasoning": f"Uplift: {uplift:.1%}, p-value: {p_value:.3f}"
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "run_experiment":
      experiment = await self._design_experiment(context["hypothesis"], context["target_metric"])
      results = await self._analyze_results(experiment["experiment_id"])
      recommendation = await self._recommend_rollout(results)
      
      return {"experiment": experiment, "results": results, "recommendation": recommendation}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["experiment_design", "statistical_analysis", "automated_rollout"]


class DriftDetector(BusinessPillarAgent):
  """Agent for detecting model and performance drift."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="drift_detector",
      role=AgentRole.CRITIC,
      pillar=PillarType.INTELLIGENCE_IMPROVEMENT,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("monitor_model_drift", self._monitor_model_drift, cost=1.0)
    self.register_tool("detect_performance_anomalies", self._detect_performance_anomalies, cost=0.8)
    self.register_tool("recommend_retraining", self._recommend_retraining, cost=0.5)
  
  async def _monitor_model_drift(self, model_id: str) -> Dict[str, Any]:
    # Mock drift detection
    return {
      "model_id": model_id,
      "drift_score": 0.15,  # 0-1 scale
      "drift_threshold": 0.20,
      "drift_detected": False,
      "feature_drift": {
        "feature_a": 0.12,
        "feature_b": 0.08,
        "feature_c": 0.22  # Above threshold
      },
      "monitoring_date": datetime.now().isoformat()
    }
  
  async def _detect_performance_anomalies(self, metrics: Dict[str, float]) -> Dict[str, Any]:
    anomalies = []
    
    for metric, value in metrics.items():
      # Simple anomaly detection based on thresholds
      if metric == "accuracy" and value < 0.85:
        anomalies.append({"metric": metric, "value": value, "threshold": 0.85})
      elif metric == "latency" and value > 500:
        anomalies.append({"metric": metric, "value": value, "threshold": 500})
    
    return {
      "anomalies_detected": len(anomalies),
      "anomalies": anomalies,
      "severity": "high" if len(anomalies) > 2 else "medium" if len(anomalies) > 0 else "low"
    }
  
  async def _recommend_retraining(self, drift_data: Dict[str, Any], performance_data: Dict[str, Any]) -> Dict[str, Any]:
    should_retrain = (
      drift_data["drift_detected"] or 
      performance_data["severity"] in ["high", "medium"]
    )
    
    return {
      "retrain_recommended": should_retrain,
      "urgency": "high" if performance_data["severity"] == "high" else "medium",
      "estimated_improvement": "10-15%" if should_retrain else "N/A"
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "drift_monitoring":
      drift = await self._monitor_model_drift(context["model_id"])
      performance_anomalies = await self._detect_performance_anomalies(context.get("metrics", {}))
      retraining_rec = await self._recommend_retraining(drift, performance_anomalies)
      
      return {
        "drift_analysis": drift,
        "performance_anomalies": performance_anomalies,
        "retraining_recommendation": retraining_rec
      }
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["drift_detection", "anomaly_detection", "model_monitoring"]


class IntelligenceImprovementPillar(BusinessPillar):
  """Intelligence & Improvement pillar coordinating analytics and optimization."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.INTELLIGENCE_IMPROVEMENT, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    self.register_agent(MetricCollector(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(ExperimentDesigner(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(DriftDetector(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
  
  async def execute_workflow(self, workflow_type: str, inputs: Dict[str, Any], requester: Optional[str] = None) -> WorkflowResult:
    """Execute intelligence workflows."""
    workflow_id = f"intelligence_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "optimization_cycle":
      return await self._execute_optimization_cycle(workflow, inputs)
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_optimization_cycle(self, workflow: WorkflowResult, inputs: Dict[str, Any]) -> WorkflowResult:
    """Execute optimization cycle workflow."""
    try:
      # Step 1: Collect metrics
      metric_collector = self.get_agent(AgentRole.WORKER)
      step1 = WorkflowStep(
        step_id="collect_metrics",
        agent_role=AgentRole.WORKER,
        action="metrics_analysis",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      metrics = await metric_collector.execute_task("metrics_analysis", inputs, workflow.workflow_id)
      step1.complete(metrics)
      
      # Step 2: Design experiment
      experiment_designer = self.get_agent(AgentRole.PLANNER)
      step2 = WorkflowStep(
        step_id="design_experiment",
        agent_role=AgentRole.PLANNER,
        action="run_experiment",
        inputs=inputs
      )
      step2.start()
      workflow.add_step(step2)
      
      experiment = await experiment_designer.execute_task("run_experiment", inputs, workflow.workflow_id)
      step2.complete(experiment)
      
      # Step 3: Monitor for drift
      drift_detector = self.get_agent(AgentRole.CRITIC)
      step3 = WorkflowStep(
        step_id="drift_monitoring",
        agent_role=AgentRole.CRITIC,
        action="drift_monitoring",
        inputs=inputs
      )
      step3.start()
      workflow.add_step(step3)
      
      drift_monitoring = await drift_detector.execute_task("drift_monitoring", inputs, workflow.workflow_id)
      step3.complete(drift_monitoring)
      
      workflow.complete({
        "metrics_analysis": metrics,
        "experiment": experiment,
        "drift_monitoring": drift_monitoring
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    return ["optimization_cycle"]