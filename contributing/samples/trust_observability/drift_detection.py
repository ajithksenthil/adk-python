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

"""Drift detection and alerting system for agent behavior monitoring."""

import asyncio
import json
import logging
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import hashlib

from .audit_trail import SpanData, AuditTrailManager

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift that can be detected."""
    DATA_DRIFT = "data_drift"           # Feature distribution changes
    MODEL_DRIFT = "model_drift"         # Performance degradation
    BEHAVIOR_DRIFT = "behavior_drift"   # Tool usage pattern changes
    POLICY_DRIFT = "policy_drift"       # Policy violation rate changes
    COST_DRIFT = "cost_drift"          # Unexpected cost increases
    LATENCY_DRIFT = "latency_drift"    # Performance slowdowns


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Alert generated when drift is detected."""
    alert_id: str
    drift_type: DriftType
    severity: AlertSeverity
    agent_id: Optional[str]
    pillar: Optional[str]
    
    # Detection details
    timestamp: datetime
    metric_name: str
    current_value: float
    baseline_value: float
    drift_magnitude: float
    threshold: float
    
    # Alert content
    title: str
    description: str
    recommended_actions: List[str] = field(default_factory=list)
    
    # Context
    affected_spans: List[str] = field(default_factory=list)
    trace_ids: List[str] = field(default_factory=list)
    time_window: str = ""
    
    # Metadata
    detector_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "agent_id": self.agent_id,
            "pillar": self.pillar,
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "drift_magnitude": self.drift_magnitude,
            "threshold": self.threshold,
            "title": self.title,
            "description": self.description,
            "recommended_actions": self.recommended_actions,
            "affected_spans": self.affected_spans,
            "trace_ids": self.trace_ids,
            "time_window": self.time_window,
            "detector_version": self.detector_version,
            "metadata": self.metadata
        }


class DriftDetector(ABC):
    """Abstract base class for drift detectors."""
    
    @abstractmethod
    async def detect_drift(
        self,
        current_spans: List[SpanData],
        baseline_spans: List[SpanData]
    ) -> List[DriftAlert]:
        """Detect drift by comparing current spans to baseline."""
        pass


class DataDriftDetector(DriftDetector):
    """Detector for data distribution drift using statistical tests."""
    
    def __init__(
        self,
        ks_threshold: float = 0.1,  # Kolmogorov-Smirnov D statistic threshold
        feature_extractors: Optional[Dict[str, Callable]] = None
    ):
        self.ks_threshold = ks_threshold
        self.feature_extractors = feature_extractors or {
            "token_count": lambda span: span.token_count or 0,
            "cost_usd": lambda span: span.cost_usd or 0.0,
            "duration_ms": lambda span: span.duration_ms() or 0.0,
            "tool_usage": lambda span: 1 if span.tool_name else 0
        }
    
    async def detect_drift(
        self,
        current_spans: List[SpanData],
        baseline_spans: List[SpanData]
    ) -> List[DriftAlert]:
        """Detect data drift using Kolmogorov-Smirnov test."""
        alerts = []
        
        for feature_name, extractor in self.feature_extractors.items():
            try:
                # Extract feature values
                current_values = [extractor(span) for span in current_spans if extractor(span) is not None]
                baseline_values = [extractor(span) for span in baseline_spans if extractor(span) is not None]
                
                if len(current_values) < 10 or len(baseline_values) < 10:
                    continue  # Skip if insufficient data
                
                # Perform KS test (simplified implementation)
                ks_statistic = self._ks_test(current_values, baseline_values)
                
                if ks_statistic > self.ks_threshold:
                    severity = self._determine_severity(ks_statistic, self.ks_threshold)
                    
                    alert = DriftAlert(
                        alert_id=f"data_drift_{feature_name}_{int(datetime.now().timestamp())}",
                        drift_type=DriftType.DATA_DRIFT,
                        severity=severity,
                        agent_id=None,  # Data drift affects multiple agents
                        pillar=None,
                        timestamp=datetime.now(),
                        metric_name=feature_name,
                        current_value=statistics.mean(current_values),
                        baseline_value=statistics.mean(baseline_values),
                        drift_magnitude=ks_statistic,
                        threshold=self.ks_threshold,
                        title=f"Data Drift Detected: {feature_name}",
                        description=f"Feature distribution for {feature_name} has significantly changed "
                                  f"(KS statistic: {ks_statistic:.3f}, threshold: {self.ks_threshold})",
                        recommended_actions=[
                            "Review recent changes to data sources",
                            "Check for data quality issues",
                            "Consider retraining models with new data distribution",
                            "Monitor related metrics for continued drift"
                        ],
                        affected_spans=[span.span_id for span in current_spans[:10]],  # Sample
                        time_window="Current vs baseline comparison"
                    )
                    
                    alerts.append(alert)
                    
            except Exception as e:
                logger.error(f"Error detecting drift for feature {feature_name}: {e}")
        
        return alerts
    
    def _ks_test(self, sample1: List[float], sample2: List[float]) -> float:
        """Simplified Kolmogorov-Smirnov test implementation."""
        # Sort both samples
        sorted1 = sorted(sample1)
        sorted2 = sorted(sample2)
        
        # Get all unique values
        all_values = sorted(set(sorted1 + sorted2))
        
        max_diff = 0.0
        
        for value in all_values:
            # Calculate empirical CDFs
            cdf1 = sum(1 for x in sorted1 if x <= value) / len(sorted1)
            cdf2 = sum(1 for x in sorted2 if x <= value) / len(sorted2)
            
            # Track maximum difference
            diff = abs(cdf1 - cdf2)
            max_diff = max(max_diff, diff)
        
        return max_diff
    
    def _determine_severity(self, ks_statistic: float, threshold: float) -> AlertSeverity:
        """Determine alert severity based on KS statistic."""
        if ks_statistic > threshold * 3:
            return AlertSeverity.CRITICAL
        elif ks_statistic > threshold * 2:
            return AlertSeverity.HIGH
        elif ks_statistic > threshold * 1.5:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW


class ModelDriftDetector(DriftDetector):
    """Detector for model performance drift."""
    
    def __init__(
        self,
        error_rate_threshold: float = 0.1,  # 10% increase in error rate
        latency_threshold: float = 0.2,     # 20% increase in latency
        cost_threshold: float = 0.15        # 15% increase in cost
    ):
        self.error_rate_threshold = error_rate_threshold
        self.latency_threshold = latency_threshold
        self.cost_threshold = cost_threshold
    
    async def detect_drift(
        self,
        current_spans: List[SpanData],
        baseline_spans: List[SpanData]
    ) -> List[DriftAlert]:
        """Detect model performance drift."""
        alerts = []
        
        # Calculate performance metrics
        current_metrics = self._calculate_performance_metrics(current_spans)
        baseline_metrics = self._calculate_performance_metrics(baseline_spans)
        
        # Check error rate drift
        if "error_rate" in current_metrics and "error_rate" in baseline_metrics:
            drift = self._calculate_relative_drift(
                current_metrics["error_rate"],
                baseline_metrics["error_rate"]
            )
            
            if drift > self.error_rate_threshold:
                alert = self._create_model_drift_alert(
                    "error_rate",
                    current_metrics["error_rate"],
                    baseline_metrics["error_rate"],
                    drift,
                    self.error_rate_threshold,
                    current_spans
                )
                alerts.append(alert)
        
        # Check latency drift
        if "avg_latency" in current_metrics and "avg_latency" in baseline_metrics:
            drift = self._calculate_relative_drift(
                current_metrics["avg_latency"],
                baseline_metrics["avg_latency"]
            )
            
            if drift > self.latency_threshold:
                alert = self._create_model_drift_alert(
                    "avg_latency",
                    current_metrics["avg_latency"],
                    baseline_metrics["avg_latency"],
                    drift,
                    self.latency_threshold,
                    current_spans
                )
                alerts.append(alert)
        
        # Check cost drift
        if "avg_cost" in current_metrics and "avg_cost" in baseline_metrics:
            drift = self._calculate_relative_drift(
                current_metrics["avg_cost"],
                baseline_metrics["avg_cost"]
            )
            
            if drift > self.cost_threshold:
                alert = self._create_model_drift_alert(
                    "avg_cost",
                    current_metrics["avg_cost"],
                    baseline_metrics["avg_cost"],
                    drift,
                    self.cost_threshold,
                    current_spans
                )
                alerts.append(alert)
        
        return alerts
    
    def _calculate_performance_metrics(self, spans: List[SpanData]) -> Dict[str, float]:
        """Calculate performance metrics from spans."""
        if not spans:
            return {}
        
        error_count = sum(1 for span in spans if span.status.value == "error")
        total_count = len(spans)
        
        latencies = [span.duration_ms() for span in spans if span.duration_ms() is not None]
        costs = [span.cost_usd for span in spans if span.cost_usd is not None]
        
        metrics = {
            "error_rate": error_count / total_count if total_count > 0 else 0.0
        }
        
        if latencies:
            metrics["avg_latency"] = statistics.mean(latencies)
        
        if costs:
            metrics["avg_cost"] = statistics.mean(costs)
        
        return metrics
    
    def _calculate_relative_drift(self, current: float, baseline: float) -> float:
        """Calculate relative drift percentage."""
        if baseline == 0:
            return 1.0 if current > 0 else 0.0
        return abs(current - baseline) / baseline
    
    def _create_model_drift_alert(
        self,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        drift: float,
        threshold: float,
        spans: List[SpanData]
    ) -> DriftAlert:
        """Create model drift alert."""
        severity = AlertSeverity.HIGH if drift > threshold * 2 else AlertSeverity.MEDIUM
        
        return DriftAlert(
            alert_id=f"model_drift_{metric_name}_{int(datetime.now().timestamp())}",
            drift_type=DriftType.MODEL_DRIFT,
            severity=severity,
            agent_id=None,
            pillar=None,
            timestamp=datetime.now(),
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            drift_magnitude=drift,
            threshold=threshold,
            title=f"Model Performance Drift: {metric_name}",
            description=f"Model {metric_name} has degraded by {drift:.1%} "
                       f"(current: {current_value:.3f}, baseline: {baseline_value:.3f})",
            recommended_actions=[
                "Review recent model deployments",
                "Check for input data quality issues",
                "Consider rolling back to previous model version",
                "Retrain model with recent data",
                "Scale up compute resources if latency-related"
            ],
            affected_spans=[span.span_id for span in spans[:20]]
        )


class BehaviorDriftDetector(DriftDetector):
    """Detector for agent behavior drift using sequence analysis."""
    
    def __init__(
        self,
        similarity_threshold: float = 0.7,  # Minimum similarity for normal behavior
        sequence_length: int = 5             # Length of tool call sequences to analyze
    ):
        self.similarity_threshold = similarity_threshold
        self.sequence_length = sequence_length
    
    async def detect_drift(
        self,
        current_spans: List[SpanData],
        baseline_spans: List[SpanData]
    ) -> List[DriftAlert]:
        """Detect behavior drift using sequence similarity."""
        alerts = []
        
        # Extract tool call sequences
        current_sequences = self._extract_tool_sequences(current_spans)
        baseline_sequences = self._extract_tool_sequences(baseline_spans)
        
        if not current_sequences or not baseline_sequences:
            return alerts
        
        # Calculate sequence similarity
        similarity = self._calculate_sequence_similarity(current_sequences, baseline_sequences)
        
        if similarity < self.similarity_threshold:
            # Identify specific agents with behavior drift
            agent_similarities = self._analyze_agent_behavior(current_spans, baseline_spans)
            
            for agent_id, agent_similarity in agent_similarities.items():
                if agent_similarity < self.similarity_threshold:
                    alert = DriftAlert(
                        alert_id=f"behavior_drift_{agent_id}_{int(datetime.now().timestamp())}",
                        drift_type=DriftType.BEHAVIOR_DRIFT,
                        severity=self._determine_behavior_severity(agent_similarity),
                        agent_id=agent_id,
                        pillar=self._get_agent_pillar(agent_id, current_spans),
                        timestamp=datetime.now(),
                        metric_name="sequence_similarity",
                        current_value=agent_similarity,
                        baseline_value=self.similarity_threshold,
                        drift_magnitude=self.similarity_threshold - agent_similarity,
                        threshold=self.similarity_threshold,
                        title=f"Behavior Drift Detected: {agent_id}",
                        description=f"Agent {agent_id} showing unusual tool usage patterns "
                                   f"(similarity: {agent_similarity:.3f}, threshold: {self.similarity_threshold})",
                        recommended_actions=[
                            "Review recent agent prompt changes",
                            "Check for potential prompt injection attacks",
                            "Verify agent context and memory state",
                            "Consider temporary AML demotion",
                            "Investigate policy bypass attempts"
                        ],
                        affected_spans=[span.span_id for span in current_spans if span.agent_id == agent_id][:10]
                    )
                    alerts.append(alert)
        
        return alerts
    
    def _extract_tool_sequences(self, spans: List[SpanData]) -> List[List[str]]:
        """Extract tool call sequences from spans."""
        sequences = []
        
        # Group spans by trace
        traces = {}
        for span in spans:
            if span.trace_id not in traces:
                traces[span.trace_id] = []
            traces[span.trace_id].append(span)
        
        # Extract tool sequences from each trace
        for trace_spans in traces.values():
            # Sort by start time
            trace_spans.sort(key=lambda x: x.start_time)
            
            # Extract tool names
            tools = [span.tool_name for span in trace_spans if span.tool_name]
            
            # Create sequences of specified length
            for i in range(len(tools) - self.sequence_length + 1):
                sequence = tools[i:i + self.sequence_length]
                sequences.append(sequence)
        
        return sequences
    
    def _calculate_sequence_similarity(
        self,
        current_sequences: List[List[str]],
        baseline_sequences: List[List[str]]
    ) -> float:
        """Calculate overall similarity between sequence sets."""
        if not current_sequences or not baseline_sequences:
            return 0.0
        
        # Convert sequences to normalized frequency distributions
        current_freq = self._sequence_frequency(current_sequences)
        baseline_freq = self._sequence_frequency(baseline_sequences)
        
        # Calculate cosine similarity
        return self._cosine_similarity(current_freq, baseline_freq)
    
    def _sequence_frequency(self, sequences: List[List[str]]) -> Dict[str, float]:
        """Calculate normalized frequency distribution of sequences."""
        freq = {}
        for sequence in sequences:
            seq_str = " -> ".join(sequence)
            freq[seq_str] = freq.get(seq_str, 0) + 1
        
        total = len(sequences)
        return {seq: count / total for seq, count in freq.items()}
    
    def _cosine_similarity(self, freq1: Dict[str, float], freq2: Dict[str, float]) -> float:
        """Calculate cosine similarity between frequency distributions."""
        all_sequences = set(freq1.keys()) | set(freq2.keys())
        
        if not all_sequences:
            return 1.0
        
        dot_product = sum(freq1.get(seq, 0) * freq2.get(seq, 0) for seq in all_sequences)
        norm1 = sum(val ** 2 for val in freq1.values()) ** 0.5
        norm2 = sum(val ** 2 for val in freq2.values()) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _analyze_agent_behavior(
        self,
        current_spans: List[SpanData],
        baseline_spans: List[SpanData]
    ) -> Dict[str, float]:
        """Analyze behavior similarity per agent."""
        agent_similarities = {}
        
        # Get unique agents
        agents = set(span.agent_id for span in current_spans + baseline_spans if span.agent_id)
        
        for agent_id in agents:
            current_agent_spans = [s for s in current_spans if s.agent_id == agent_id]
            baseline_agent_spans = [s for s in baseline_spans if s.agent_id == agent_id]
            
            if current_agent_spans and baseline_agent_spans:
                current_seq = self._extract_tool_sequences(current_agent_spans)
                baseline_seq = self._extract_tool_sequences(baseline_agent_spans)
                
                similarity = self._calculate_sequence_similarity(current_seq, baseline_seq)
                agent_similarities[agent_id] = similarity
        
        return agent_similarities
    
    def _determine_behavior_severity(self, similarity: float) -> AlertSeverity:
        """Determine alert severity based on behavior similarity."""
        if similarity < 0.3:
            return AlertSeverity.CRITICAL
        elif similarity < 0.5:
            return AlertSeverity.HIGH
        elif similarity < 0.6:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def _get_agent_pillar(self, agent_id: str, spans: List[SpanData]) -> Optional[str]:
        """Get pillar for an agent from spans."""
        for span in spans:
            if span.agent_id == agent_id and span.pillar:
                return span.pillar
        return None


class DriftMonitor:
    """Orchestrator for drift detection and alerting."""
    
    def __init__(
        self,
        audit_manager: AuditTrailManager,
        detectors: Optional[List[DriftDetector]] = None,
        monitoring_window_hours: int = 1,
        baseline_window_days: int = 7
    ):
        self.audit_manager = audit_manager
        self.monitoring_window_hours = monitoring_window_hours
        self.baseline_window_days = baseline_window_days
        
        # Initialize detectors
        self.detectors = detectors or [
            DataDriftDetector(),
            ModelDriftDetector(),
            BehaviorDriftDetector()
        ]
        
        # Alert handlers
        self.alert_handlers: List[Callable[[DriftAlert], None]] = []
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
    
    def add_alert_handler(self, handler: Callable[[DriftAlert], None]):
        """Add handler for drift alerts."""
        self.alert_handlers.append(handler)
    
    async def start_monitoring(self):
        """Start continuous drift monitoring."""
        if self._monitoring_active:
            logger.warning("Drift monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started drift monitoring")
    
    async def stop_monitoring(self):
        """Stop drift monitoring."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped drift monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                await self._check_for_drift()
                await asyncio.sleep(self.monitoring_window_hours * 3600)  # Convert to seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in drift monitoring loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_for_drift(self):
        """Check for drift across all detectors."""
        current_time = datetime.now()
        
        # Get current window spans
        current_start = current_time - timedelta(hours=self.monitoring_window_hours)
        current_spans = await self.audit_manager.storage.get_spans(
            start_time=current_start,
            end_time=current_time,
            limit=5000
        )
        
        # Get baseline window spans
        baseline_end = current_time - timedelta(days=1)  # Skip recent day to avoid overlap
        baseline_start = baseline_end - timedelta(days=self.baseline_window_days)
        baseline_spans = await self.audit_manager.storage.get_spans(
            start_time=baseline_start,
            end_time=baseline_end,
            limit=10000
        )
        
        if not current_spans or not baseline_spans:
            logger.debug("Insufficient data for drift detection")
            return
        
        # Run all detectors
        all_alerts = []
        for detector in self.detectors:
            try:
                alerts = await detector.detect_drift(current_spans, baseline_spans)
                all_alerts.extend(alerts)
            except Exception as e:
                logger.error(f"Error in {detector.__class__.__name__}: {e}")
        
        # Process alerts
        for alert in all_alerts:
            await self._handle_alert(alert)
        
        if all_alerts:
            logger.info(f"Detected {len(all_alerts)} drift alerts")
    
    async def _handle_alert(self, alert: DriftAlert):
        """Handle a drift alert."""
        logger.warning(f"DRIFT ALERT [{alert.severity.value.upper()}]: {alert.title}")
        
        # Notify all handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    async def run_drift_analysis(
        self,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Run ad-hoc drift analysis."""
        current_time = datetime.now()
        
        # Split time window into current and baseline
        split_time = current_time - timedelta(hours=hours_back // 2)
        
        current_spans = await self.audit_manager.storage.get_spans(
            start_time=split_time,
            end_time=current_time,
            limit=5000
        )
        
        baseline_spans = await self.audit_manager.storage.get_spans(
            start_time=current_time - timedelta(hours=hours_back),
            end_time=split_time,
            limit=5000
        )
        
        # Run drift detection
        all_alerts = []
        detector_results = {}
        
        for detector in self.detectors:
            detector_name = detector.__class__.__name__
            try:
                alerts = await detector.detect_drift(current_spans, baseline_spans)
                all_alerts.extend(alerts)
                detector_results[detector_name] = {
                    "alerts_generated": len(alerts),
                    "alert_severities": [a.severity.value for a in alerts]
                }
            except Exception as e:
                detector_results[detector_name] = {"error": str(e)}
        
        return {
            "analysis_timestamp": current_time.isoformat(),
            "time_window_hours": hours_back,
            "current_spans": len(current_spans),
            "baseline_spans": len(baseline_spans),
            "total_alerts": len(all_alerts),
            "alerts_by_type": {
                drift_type.value: len([a for a in all_alerts if a.drift_type == drift_type])
                for drift_type in DriftType
            },
            "alerts_by_severity": {
                severity.value: len([a for a in all_alerts if a.severity == severity])
                for severity in AlertSeverity
            },
            "detector_results": detector_results,
            "alerts": [alert.to_dict() for alert in all_alerts]
        }