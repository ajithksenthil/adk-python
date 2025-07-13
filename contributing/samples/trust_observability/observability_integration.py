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

"""Integration layer for Trust & Observability Mesh with Control Plane and Data Mesh."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

try:
    from .audit_trail import AuditTrailManager, SpanType, agent_execution_span, tool_call_span, policy_check_span
    from .trajectory_eval import TrajectoryEvaluationOrchestrator
    from .drift_detection import DriftMonitor, DriftAlert, AlertSeverity
    from .compliance_reporting import ComplianceOrchestrator, ReportType
except ImportError:
    # Fallback for standalone execution
    from audit_trail import AuditTrailManager, SpanType, agent_execution_span, tool_call_span, policy_check_span
    from trajectory_eval import TrajectoryEvaluationOrchestrator
    from drift_detection import DriftMonitor, DriftAlert, AlertSeverity
    from compliance_reporting import ComplianceOrchestrator, ReportType

if TYPE_CHECKING:
    from control_plane.aml_registry_enhanced import EnhancedAMLRegistry
    from control_plane.policy_engine import PolicyEngine
    from data_mesh.event_bus import EventBus
    from data_mesh.lineage_service import LineageService

logger = logging.getLogger(__name__)


class ObservabilityIntegration:
    """Main integration class for Trust & Observability Mesh."""
    
    def __init__(
        self,
        aml_registry: Optional["EnhancedAMLRegistry"] = None,
        policy_engine: Optional["PolicyEngine"] = None,
        event_bus: Optional["EventBus"] = None,
        lineage_service: Optional["LineageService"] = None,
        enable_cloud_storage: bool = False,
        storage_config: Optional[Dict[str, Any]] = None
    ):
        # Core components
        self.aml_registry = aml_registry
        self.policy_engine = policy_engine
        self.event_bus = event_bus
        self.lineage_service = lineage_service
        
        # Initialize observability components
        self.audit_manager = self._initialize_audit_manager(enable_cloud_storage, storage_config)
        self.trajectory_evaluator = TrajectoryEvaluationOrchestrator(self.audit_manager)
        self.drift_monitor = DriftMonitor(self.audit_manager)
        self.compliance_orchestrator = ComplianceOrchestrator(self.audit_manager)
        
        # Integration state
        self._initialized = False
        self._alert_handlers_configured = False
    
    def _initialize_audit_manager(
        self,
        enable_cloud_storage: bool,
        storage_config: Optional[Dict[str, Any]]
    ) -> AuditTrailManager:
        """Initialize audit trail manager with appropriate storage."""
        if enable_cloud_storage and storage_config:
            from .audit_trail import CloudSpanStorage
            storage = CloudSpanStorage(
                worm_bucket=storage_config.get("worm_bucket", "ai-audit-worm"),
                hot_store_endpoint=storage_config.get("hot_store_endpoint", "https://clickhouse.company.com:8443"),
                project_id=storage_config.get("project_id")
            )
        else:
            from .audit_trail import InMemorySpanStorage
            storage = InMemorySpanStorage()
        
        return AuditTrailManager(storage=storage)
    
    async def initialize(self):
        """Initialize the observability integration."""
        if self._initialized:
            return
        
        logger.info("Initializing Trust & Observability Mesh")
        
        # Setup drift monitoring alert handlers
        await self._setup_alert_handlers()
        
        # Start drift monitoring
        await self.drift_monitor.start_monitoring()
        
        # Setup event bus integration if available
        if self.event_bus:
            await self._setup_event_integration()
        
        self._initialized = True
        logger.info("Trust & Observability Mesh initialized successfully")
    
    async def shutdown(self):
        """Shutdown observability components."""
        if not self._initialized:
            return
        
        logger.info("Shutting down Trust & Observability Mesh")
        
        # Stop drift monitoring
        await self.drift_monitor.stop_monitoring()
        
        self._initialized = False
        logger.info("Trust & Observability Mesh shutdown complete")
    
    async def _setup_alert_handlers(self):
        """Setup handlers for drift alerts."""
        if self._alert_handlers_configured:
            return
        
        # Add AML registry integration handler
        if self.aml_registry:
            self.drift_monitor.add_alert_handler(self._handle_aml_adjustment)
        
        # Add event bus notification handler
        if self.event_bus:
            self.drift_monitor.add_alert_handler(self._handle_alert_notification)
        
        # Add emergency response handler
        self.drift_monitor.add_alert_handler(self._handle_emergency_response)
        
        self._alert_handlers_configured = True
    
    async def _handle_aml_adjustment(self, alert: DriftAlert):
        """Handle drift alerts by adjusting AML levels."""
        if not self.aml_registry or not alert.agent_id:
            return
        
        try:
            # Demote agents on high/critical alerts
            if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                agent_group = f"{alert.agent_id}_group"
                
                success = await self.aml_registry.demote_agent_group(
                    agent_group=agent_group,
                    changed_by="drift_detector",
                    reason=f"Drift detected: {alert.title}"
                )
                
                if success:
                    logger.warning(f"Auto-demoted {agent_group} due to drift alert: {alert.alert_id}")
                
                # Emergency pause for critical issues
                if alert.severity == AlertSeverity.CRITICAL:
                    await self.aml_registry.emergency_pause(
                        agent_group=agent_group,
                        changed_by="drift_detector",
                        reason=f"Critical drift: {alert.description}"
                    )
                    logger.critical(f"Emergency pause activated for {agent_group}")
        
        except Exception as e:
            logger.error(f"Error handling AML adjustment for alert {alert.alert_id}: {e}")
    
    async def _handle_alert_notification(self, alert: DriftAlert):
        """Send alert notifications via event bus."""
        if not self.event_bus:
            return
        
        try:
            from data_mesh.event_bus import Event, EventMetadata, EventType, EventPriority
            
            # Determine priority based on severity
            priority_map = {
                AlertSeverity.LOW: EventPriority.LOW,
                AlertSeverity.MEDIUM: EventPriority.NORMAL,
                AlertSeverity.HIGH: EventPriority.HIGH,
                AlertSeverity.CRITICAL: EventPriority.URGENT
            }
            
            event = Event(
                event_type=EventType.ALERT,
                metadata=EventMetadata(
                    source_pillar="Trust & Observability",
                    source_agent="drift_monitor",
                    priority=priority_map.get(alert.severity, EventPriority.NORMAL),
                    trace_id=alert.alert_id,
                    tags={
                        "alert_type": alert.drift_type.value,
                        "severity": alert.severity.value,
                        "agent_id": alert.agent_id,
                        "pillar": alert.pillar
                    }
                ),
                payload=alert.to_dict()
            )
            
            # Publish to alerts topic
            from data_mesh.event_bus import Topics
            await self.event_bus.publish(Topics.ALERTS, event)
            
            logger.info(f"Published drift alert {alert.alert_id} to event bus")
        
        except Exception as e:
            logger.error(f"Error publishing alert notification: {e}")
    
    async def _handle_emergency_response(self, alert: DriftAlert):
        """Handle emergency response procedures."""
        if alert.severity != AlertSeverity.CRITICAL:
            return
        
        try:
            # Log critical alert
            logger.critical(f"CRITICAL DRIFT ALERT: {alert.title}")
            logger.critical(f"Description: {alert.description}")
            logger.critical(f"Affected Agent: {alert.agent_id}")
            logger.critical(f"Pillar: {alert.pillar}")
            logger.critical(f"Recommended Actions: {', '.join(alert.recommended_actions)}")
            
            # Mock PagerDuty notification
            self._send_pagerduty_alert(alert)
            
            # Mock Slack notification
            self._send_slack_notification(alert)
            
        except Exception as e:
            logger.error(f"Error in emergency response: {e}")
    
    def _send_pagerduty_alert(self, alert: DriftAlert):
        """Mock PagerDuty alert (replace with real integration)."""
        logger.info(f"🚨 PAGERDUTY ALERT: {alert.title}")
        logger.info(f"   Severity: {alert.severity.value}")
        logger.info(f"   Agent: {alert.agent_id}")
        logger.info(f"   Description: {alert.description}")
    
    def _send_slack_notification(self, alert: DriftAlert):
        """Mock Slack notification (replace with real integration)."""
        logger.info(f"💬 SLACK NOTIFICATION: Posted to #governance channel")
        logger.info(f"   Alert: {alert.title}")
        logger.info(f"   Trace Link: /grafana/trace/{alert.trace_ids[0] if alert.trace_ids else 'N/A'}")
    
    async def _setup_event_integration(self):
        """Setup integration with event bus for observability events."""
        if not self.event_bus:
            return
        
        # Subscribe to relevant events for observability
        from data_mesh.event_bus import Topics, EventHandler
        
        async def track_cross_pillar_events(event):
            """Track cross-pillar events for behavior analysis."""
            with self.create_span(
                operation_name="cross_pillar_event",
                span_type=SpanType.CROSS_PILLAR_EVENT,
                trace_id=event.metadata.trace_id
            ) as span:
                span.add_attribute("source_pillar", event.metadata.source_pillar)
                span.add_attribute("target_pillar", event.metadata.target_pillar)
                span.add_attribute("event_type", event.event_type.value)
                span.add_attribute("event_priority", event.metadata.priority.value)
        
        event_handler = EventHandler(handler_func=track_cross_pillar_events)
        
        # Subscribe to audit topic
        await self.event_bus.subscribe(Topics.AUDIT, event_handler)
        logger.info("Configured event bus integration for observability")
    
    def create_span(self, operation_name: str, span_type: SpanType, **kwargs):
        """Create an observability span."""
        return self.audit_manager.create_span(
            operation_name=operation_name,
            span_type=span_type,
            **kwargs
        )
    
    def track_agent_execution(
        self,
        agent_id: str,
        pillar: str,
        operation: str,
        aml_level: int,
        trace_id: Optional[str] = None
    ):
        """Track agent execution with full observability."""
        span = agent_execution_span(
            self.audit_manager,
            agent_id=agent_id,
            pillar=pillar,
            operation=operation,
            aml_level=aml_level,
            trace_id=trace_id
        )
        
        # Set up lineage tracking to be called during span execution
        if self.lineage_service and trace_id:
            span._lineage_service = self.lineage_service
            span._lineage_trace_id = trace_id
            span._lineage_agent_id = agent_id
            span._lineage_operation = operation
            span._lineage_pillar = pillar
        
        # Set up trajectory evaluation
        span._trajectory_evaluator = self.trajectory_evaluator
        
        return span
    
    async def track_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        tool_inputs: Dict[str, Any],
        tool_outputs: Dict[str, Any],
        cost: Optional[float] = None,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ):
        """Track tool call with observability."""
        span = tool_call_span(
            self.audit_manager,
            agent_id=agent_id,
            tool_name=tool_name,
            tool_inputs=tool_inputs,
            trace_id=trace_id,
            parent_span_id=parent_span_id
        )
        
        async with span:
            span.span_data.tool_outputs = tool_outputs
            span.span_data.cost_usd = cost
            
            # Track in lineage service
            if self.lineage_service and trace_id:
                await self.lineage_service.track_tool_invocation(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    trace_id=trace_id,
                    inputs=tool_inputs,
                    outputs=tool_outputs
                )
            
            return span
    
    async def track_policy_decision(
        self,
        agent_id: str,
        policy_decision: str,
        policy_reasons: List[str],
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ):
        """Track policy decision with observability."""
        span = policy_check_span(
            self.audit_manager,
            agent_id=agent_id,
            policy_decision=policy_decision,
            policy_reasons=policy_reasons,
            trace_id=trace_id,
            parent_span_id=parent_span_id
        )
        
        async with span:
            return span
    
    async def run_trajectory_evaluation(self, mode: str = "batch") -> Dict[str, Any]:
        """Run trajectory evaluation pipeline."""
        if mode == "batch":
            return await self.trajectory_evaluator.run_batch_evaluation()
        else:
            raise ValueError(f"Unknown evaluation mode: {mode}")
    
    async def run_drift_analysis(self, hours_back: int = 24) -> Dict[str, Any]:
        """Run drift analysis."""
        return await self.drift_monitor.run_drift_analysis(hours_back=hours_back)
    
    async def generate_compliance_report(
        self,
        report_type: ReportType,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Generate compliance report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        evidence_pack = await self.compliance_orchestrator.generate_report(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return evidence_pack.to_dict()
    
    async def get_observability_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive observability dashboard."""
        # Get compliance dashboard
        compliance_dashboard = await self.compliance_orchestrator.get_compliance_dashboard()
        
        # Get evaluation summary
        evaluation_summary = await self.trajectory_evaluator.get_evaluation_summary(hours=24)
        
        # Get drift analysis
        drift_analysis = await self.drift_monitor.run_drift_analysis(hours_back=24)
        
        # Get audit trail summary
        audit_summary = await self._get_audit_summary()
        
        return {
            "observability_status": {
                "system_status": "operational",
                "monitoring_active": self.drift_monitor._monitoring_active,
                "last_updated": datetime.now().isoformat()
            },
            "audit_trail": audit_summary,
            "trajectory_evaluation": evaluation_summary,
            "drift_detection": {
                "total_alerts": drift_analysis.get("total_alerts", 0),
                "alerts_by_severity": drift_analysis.get("alerts_by_severity", {}),
                "monitoring_window_hours": 24
            },
            "compliance": compliance_dashboard,
            "integration_status": {
                "aml_registry_connected": bool(self.aml_registry),
                "policy_engine_connected": bool(self.policy_engine),
                "event_bus_connected": bool(self.event_bus),
                "lineage_service_connected": bool(self.lineage_service)
            }
        }
    
    async def _get_audit_summary(self) -> Dict[str, Any]:
        """Get audit trail summary."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        spans = await self.audit_manager.storage.get_spans(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if not spans:
            return {"total_spans": 0, "message": "No spans found in the last 24 hours"}
        
        # Calculate summary statistics
        span_types = {}
        pillars = {}
        status_counts = {}
        
        for span in spans:
            # Count by span type
            span_type = span.span_type.value
            span_types[span_type] = span_types.get(span_type, 0) + 1
            
            # Count by pillar
            if span.pillar:
                pillars[span.pillar] = pillars.get(span.pillar, 0) + 1
            
            # Count by status
            status = span.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_spans": len(spans),
            "time_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": 24
            },
            "span_types": span_types,
            "pillars": pillars,
            "status_distribution": status_counts,
            "success_rate": round(status_counts.get("ok", 0) / len(spans) * 100, 2),
            "active_traces": len(self.audit_manager.get_active_traces())
        }


# Global observability integration instance
_global_observability: Optional[ObservabilityIntegration] = None


def get_observability() -> ObservabilityIntegration:
    """Get the global observability integration."""
    global _global_observability
    if _global_observability is None:
        _global_observability = ObservabilityIntegration()
    return _global_observability


def set_observability(observability: ObservabilityIntegration):
    """Set the global observability integration."""
    global _global_observability
    _global_observability = observability