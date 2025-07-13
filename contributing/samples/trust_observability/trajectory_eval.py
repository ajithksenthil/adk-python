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

"""Trajectory evaluation pipelines for step-wise grading of agent reasoning."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from .audit_trail import SpanData, AuditTrailManager

logger = logging.getLogger(__name__)


class EvaluationMode(Enum):
    """Evaluation execution modes."""
    BATCH = "batch"           # Nightly replay of spans
    STREAMING = "streaming"   # Real-time inline evaluation
    AD_HOC = "ad_hoc"        # On-demand evaluation


class EvaluationMetric(Enum):
    """Types of evaluation metrics."""
    REASONING_QUALITY = "reasoning_quality"
    FACTUAL_ACCURACY = "factual_accuracy"
    POLICY_COMPLIANCE = "policy_compliance"
    SAFETY_SCORE = "safety_score"
    EFFICIENCY_SCORE = "efficiency_score"
    HALLUCINATION_RATE = "hallucination_rate"
    COST_EFFECTIVENESS = "cost_effectiveness"


@dataclass
class EvaluationCriteria:
    """Criteria for evaluating agent trajectories."""
    metric: EvaluationMetric
    weight: float = 1.0
    threshold: Optional[float] = None
    description: str = ""
    
    # Evaluation-specific parameters
    gold_standard_path: Optional[str] = None
    reference_answers: List[str] = field(default_factory=list)
    custom_evaluator_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Result of trajectory evaluation."""
    evaluation_id: str
    span_id: str
    trace_id: str
    agent_id: str
    pillar: str
    
    # Evaluation metadata
    mode: EvaluationMode
    timestamp: datetime
    evaluator_version: str
    
    # Scoring results
    overall_score: float  # 0.0 to 1.0
    metric_scores: Dict[EvaluationMetric, float] = field(default_factory=dict)
    pass_fail_status: bool = True
    
    # Detailed analysis
    reasoning_analysis: Optional[str] = None
    improvement_suggestions: List[str] = field(default_factory=list)
    safety_concerns: List[str] = field(default_factory=list)
    
    # Performance metrics
    evaluation_latency_ms: Optional[float] = None
    evaluation_cost_usd: Optional[float] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_span_attributes(self) -> Dict[str, Any]:
        """Convert evaluation result to span attributes for storage."""
        return {
            "eval.id": self.evaluation_id,
            "eval.mode": self.mode.value,
            "eval.score.overall": self.overall_score,
            "eval.pass_fail": self.pass_fail_status,
            "eval.latency_ms": self.evaluation_latency_ms,
            "eval.cost_usd": self.evaluation_cost_usd,
            "eval.version": self.evaluator_version,
            "eval.metric_scores": json.dumps({m.value: s for m, s in self.metric_scores.items()}),
            "eval.safety_concerns": json.dumps(self.safety_concerns) if self.safety_concerns else None,
            "eval.improvement_suggestions": json.dumps(self.improvement_suggestions) if self.improvement_suggestions else None
        }


class TrajectoryEvaluator(ABC):
    """Abstract base class for trajectory evaluators."""
    
    @abstractmethod
    async def evaluate_span(
        self,
        span_data: SpanData,
        criteria: List[EvaluationCriteria],
        mode: EvaluationMode = EvaluationMode.STREAMING
    ) -> EvaluationResult:
        """Evaluate a single span."""
        pass
    
    @abstractmethod
    async def evaluate_trace(
        self,
        trace_spans: List[SpanData],
        criteria: List[EvaluationCriteria],
        mode: EvaluationMode = EvaluationMode.BATCH
    ) -> List[EvaluationResult]:
        """Evaluate an entire trace (multiple spans)."""
        pass


class LangSmithEvaluator(TrajectoryEvaluator):
    """LangSmith-based trajectory evaluator (mock implementation)."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_name: str = "adk-trajectory-eval",
        evaluator_version: str = "1.0.0"
    ):
        self.api_key = api_key
        self.project_name = project_name
        self.evaluator_version = evaluator_version
        logger.info(f"Initialized LangSmith evaluator: {project_name}")
    
    async def evaluate_span(
        self,
        span_data: SpanData,
        criteria: List[EvaluationCriteria],
        mode: EvaluationMode = EvaluationMode.STREAMING
    ) -> EvaluationResult:
        """Evaluate a single span using LangSmith."""
        start_time = datetime.now()
        
        # Mock LangSmith evaluation
        metric_scores = {}
        overall_score = 0.0
        safety_concerns = []
        improvement_suggestions = []
        
        for criterion in criteria:
            # Mock scoring based on criterion type
            score = await self._evaluate_metric(span_data, criterion)
            metric_scores[criterion.metric] = score
            overall_score += score * criterion.weight
            
            # Check thresholds and generate recommendations
            if criterion.threshold and score < criterion.threshold:
                safety_concerns.append(f"Score {score:.2f} below threshold {criterion.threshold} for {criterion.metric.value}")
                improvement_suggestions.append(f"Improve {criterion.metric.value} to meet quality standards")
        
        # Normalize overall score
        total_weight = sum(c.weight for c in criteria)
        if total_weight > 0:
            overall_score /= total_weight
        
        evaluation_latency = (datetime.now() - start_time).total_seconds() * 1000
        
        return EvaluationResult(
            evaluation_id=f"eval_{span_data.span_id}",
            span_id=span_data.span_id,
            trace_id=span_data.trace_id,
            agent_id=span_data.agent_id or "unknown",
            pillar=span_data.pillar or "unknown",
            mode=mode,
            timestamp=datetime.now(),
            evaluator_version=self.evaluator_version,
            overall_score=overall_score,
            metric_scores=metric_scores,
            pass_fail_status=overall_score >= 0.7,  # Default threshold
            safety_concerns=safety_concerns,
            improvement_suggestions=improvement_suggestions,
            evaluation_latency_ms=evaluation_latency,
            evaluation_cost_usd=0.001  # Mock cost
        )
    
    async def evaluate_trace(
        self,
        trace_spans: List[SpanData],
        criteria: List[EvaluationCriteria],
        mode: EvaluationMode = EvaluationMode.BATCH
    ) -> List[EvaluationResult]:
        """Evaluate all spans in a trace."""
        results = []
        
        for span in trace_spans:
            # Only evaluate agent execution and tool call spans
            if span.span_type.value in ["agent.execution", "agent.tool_call"]:
                result = await self.evaluate_span(span, criteria, mode)
                results.append(result)
        
        return results
    
    async def _evaluate_metric(
        self,
        span_data: SpanData,
        criterion: EvaluationCriteria
    ) -> float:
        """Mock evaluation of a specific metric."""
        import random
        
        # Mock scoring with some realistic variations
        base_score = 0.8
        
        if criterion.metric == EvaluationMetric.REASONING_QUALITY:
            # Mock reasoning quality based on tool usage
            if span_data.tool_name:
                base_score = 0.85 + random.uniform(-0.1, 0.1)
            else:
                base_score = 0.75 + random.uniform(-0.15, 0.15)
        
        elif criterion.metric == EvaluationMetric.POLICY_COMPLIANCE:
            # High score if policy decision was allow
            if span_data.policy_decision == "allow":
                base_score = 0.95 + random.uniform(-0.05, 0.05)
            elif span_data.policy_decision == "deny":
                base_score = 0.6 + random.uniform(-0.1, 0.1)
            else:
                base_score = 0.8 + random.uniform(-0.1, 0.1)
        
        elif criterion.metric == EvaluationMetric.COST_EFFECTIVENESS:
            # Score based on cost efficiency
            if span_data.cost_usd and span_data.cost_usd > 0:
                # Lower cost = higher score (with some randomness)
                normalized_cost = min(span_data.cost_usd / 10.0, 1.0)
                base_score = 1.0 - normalized_cost + random.uniform(-0.1, 0.1)
            else:
                base_score = 0.9 + random.uniform(-0.05, 0.05)
        
        elif criterion.metric == EvaluationMetric.SAFETY_SCORE:
            # High safety unless there were errors
            if span_data.status.value == "error":
                base_score = 0.4 + random.uniform(-0.1, 0.2)
            else:
                base_score = 0.95 + random.uniform(-0.05, 0.05)
        
        else:
            # Default scoring
            base_score = 0.8 + random.uniform(-0.1, 0.1)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, base_score))


class StreamingEvaluationPipeline:
    """Real-time evaluation pipeline for critical operations."""
    
    def __init__(
        self,
        evaluator: TrajectoryEvaluator,
        audit_manager: AuditTrailManager,
        critical_pillars: List[str] = None,
        evaluation_frequency: int = 10,  # Evaluate every N requests
        latency_budget_ms: float = 50.0
    ):
        self.evaluator = evaluator
        self.audit_manager = audit_manager
        self.critical_pillars = critical_pillars or ["Mission & Governance", "Platform & Infra"]
        self.evaluation_frequency = evaluation_frequency
        self.latency_budget_ms = latency_budget_ms
        self._request_counter = 0
        
        # Default criteria for streaming evaluation
        self.default_criteria = [
            EvaluationCriteria(
                metric=EvaluationMetric.SAFETY_SCORE,
                weight=1.0,
                threshold=0.8,
                description="Real-time safety check"
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.POLICY_COMPLIANCE,
                weight=1.0,
                threshold=0.9,
                description="Policy compliance check"
            )
        ]
    
    async def maybe_evaluate_span(self, span_data: SpanData) -> Optional[EvaluationResult]:
        """Conditionally evaluate span based on frequency and pillar criticality."""
        self._request_counter += 1
        
        # Check if this span should be evaluated
        should_evaluate = (
            span_data.pillar in self.critical_pillars or
            self._request_counter % self.evaluation_frequency == 0
        )
        
        if not should_evaluate:
            return None
        
        # Evaluate with latency budget
        start_time = datetime.now()
        try:
            result = await asyncio.wait_for(
                self.evaluator.evaluate_span(
                    span_data,
                    self.default_criteria,
                    EvaluationMode.STREAMING
                ),
                timeout=self.latency_budget_ms / 1000.0
            )
            
            # Append evaluation results to the span
            await self._update_span_with_evaluation(span_data, result)
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Streaming evaluation timed out for span {span_data.span_id}")
            return None
        except Exception as e:
            logger.error(f"Streaming evaluation failed for span {span_data.span_id}: {e}")
            return None
    
    async def _update_span_with_evaluation(
        self,
        span_data: SpanData,
        result: EvaluationResult
    ):
        """Update span attributes with evaluation results."""
        eval_attributes = result.to_span_attributes()
        span_data.attributes.update(eval_attributes)


class BatchEvaluationPipeline:
    """Nightly batch evaluation pipeline for comprehensive analysis."""
    
    def __init__(
        self,
        evaluator: TrajectoryEvaluator,
        audit_manager: AuditTrailManager,
        evaluation_window_hours: int = 24
    ):
        self.evaluator = evaluator
        self.audit_manager = audit_manager
        self.evaluation_window_hours = evaluation_window_hours
        
        # Comprehensive criteria for batch evaluation
        self.batch_criteria = [
            EvaluationCriteria(
                metric=EvaluationMetric.REASONING_QUALITY,
                weight=0.3,
                threshold=0.8,
                description="Quality of reasoning chain"
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.FACTUAL_ACCURACY,
                weight=0.2,
                threshold=0.9,
                description="Factual correctness"
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.POLICY_COMPLIANCE,
                weight=0.2,
                threshold=0.95,
                description="Policy adherence"
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.SAFETY_SCORE,
                weight=0.15,
                threshold=0.9,
                description="Safety assessment"
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.COST_EFFECTIVENESS,
                weight=0.1,
                threshold=0.7,
                description="Cost efficiency"
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.EFFICIENCY_SCORE,
                weight=0.05,
                threshold=0.8,
                description="Execution efficiency"
            )
        ]
    
    async def run_nightly_evaluation(self) -> Dict[str, Any]:
        """Run comprehensive evaluation of last 24 hours."""
        logger.info("Starting nightly trajectory evaluation")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.evaluation_window_hours)
        
        # Get all spans from the evaluation window
        spans = await self.audit_manager.storage.get_spans(
            start_time=start_time,
            end_time=end_time,
            limit=10000  # Large limit for batch processing
        )
        
        logger.info(f"Found {len(spans)} spans for evaluation")
        
        # Group spans by trace
        traces = {}
        for span in spans:
            if span.trace_id not in traces:
                traces[span.trace_id] = []
            traces[span.trace_id].append(span)
        
        # Evaluate each trace
        all_results = []
        agent_scores = {}
        pillar_scores = {}
        
        for trace_id, trace_spans in traces.items():
            try:
                results = await self.evaluator.evaluate_trace(
                    trace_spans,
                    self.batch_criteria,
                    EvaluationMode.BATCH
                )
                all_results.extend(results)
                
                # Aggregate scores by agent and pillar
                for result in results:
                    if result.agent_id not in agent_scores:
                        agent_scores[result.agent_id] = []
                    agent_scores[result.agent_id].append(result.overall_score)
                    
                    if result.pillar not in pillar_scores:
                        pillar_scores[result.pillar] = []
                    pillar_scores[result.pillar].append(result.overall_score)
                
            except Exception as e:
                logger.error(f"Failed to evaluate trace {trace_id}: {e}")
        
        # Calculate summary statistics
        summary = {
            "evaluation_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": self.evaluation_window_hours
            },
            "spans_evaluated": len(spans),
            "traces_evaluated": len(traces),
            "results_generated": len(all_results),
            "agent_performance": {
                agent_id: {
                    "average_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "evaluation_count": len(scores)
                }
                for agent_id, scores in agent_scores.items()
                if scores
            },
            "pillar_performance": {
                pillar: {
                    "average_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "evaluation_count": len(scores)
                }
                for pillar, scores in pillar_scores.items()
                if scores
            },
            "overall_statistics": {
                "average_score": sum(r.overall_score for r in all_results) / len(all_results) if all_results else 0.0,
                "pass_rate": sum(1 for r in all_results if r.pass_fail_status) / len(all_results) if all_results else 0.0
            }
        }
        
        logger.info(f"Nightly evaluation completed: {len(all_results)} evaluations, "
                   f"average score {summary['overall_statistics']['average_score']:.3f}")
        
        return summary


class TrajectoryEvaluationOrchestrator:
    """Main orchestrator for trajectory evaluation across batch and streaming modes."""
    
    def __init__(
        self,
        audit_manager: AuditTrailManager,
        evaluator: Optional[TrajectoryEvaluator] = None
    ):
        self.audit_manager = audit_manager
        self.evaluator = evaluator or LangSmithEvaluator()
        
        # Initialize pipelines
        self.streaming_pipeline = StreamingEvaluationPipeline(
            self.evaluator,
            self.audit_manager
        )
        
        self.batch_pipeline = BatchEvaluationPipeline(
            self.evaluator,
            self.audit_manager
        )
        
        self._batch_job_running = False
    
    async def evaluate_span_realtime(self, span_data: SpanData) -> Optional[EvaluationResult]:
        """Evaluate span in real-time if conditions are met."""
        return await self.streaming_pipeline.maybe_evaluate_span(span_data)
    
    async def run_batch_evaluation(self) -> Dict[str, Any]:
        """Run comprehensive batch evaluation."""
        if self._batch_job_running:
            logger.warning("Batch evaluation already running, skipping")
            return {"status": "skipped", "reason": "already_running"}
        
        self._batch_job_running = True
        try:
            return await self.batch_pipeline.run_nightly_evaluation()
        finally:
            self._batch_job_running = False
    
    async def get_evaluation_summary(
        self,
        agent_id: Optional[str] = None,
        pillar: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get evaluation summary for agent or pillar."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        spans = await self.audit_manager.storage.get_spans(
            agent_id=agent_id,
            start_time=start_time,
            limit=1000
        )
        
        # Filter by pillar if specified
        if pillar:
            spans = [s for s in spans if s.pillar == pillar]
        
        # Extract evaluation data from span attributes
        evaluations = []
        for span in spans:
            if "eval.score.overall" in span.attributes:
                evaluations.append({
                    "span_id": span.span_id,
                    "overall_score": span.attributes["eval.score.overall"],
                    "pass_fail": span.attributes.get("eval.pass_fail", True),
                    "timestamp": span.start_time
                })
        
        if not evaluations:
            return {"message": "No evaluations found for the specified criteria"}
        
        # Calculate summary
        scores = [e["overall_score"] for e in evaluations]
        return {
            "period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "evaluation_count": len(evaluations),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "pass_rate": sum(1 for e in evaluations if e["pass_fail"]) / len(evaluations),
            "agent_id": agent_id,
            "pillar": pillar
        }