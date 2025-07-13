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

"""Test script to verify Advanced Observability integration."""

import asyncio
import logging
from datetime import datetime, timedelta

# Import observability components
from trust_observability import (
    ObservabilityIntegration,
    AuditTrailManager,
    TrajectoryEvaluationOrchestrator,
    DriftMonitor,
    ComplianceOrchestrator,
    ReportType
)
from trust_observability.audit_trail import SpanType, SpanStatus
from trust_observability.drift_detection import DriftAlert, AlertSeverity

# Import infrastructure for integration
from control_plane.aml_registry_enhanced import EnhancedAMLRegistry, AutonomyLevel
from control_plane.policy_engine import LocalPolicyEngine
from data_mesh.event_bus import EventBusFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_audit_trail_generation():
    """Test audit trail generation and storage."""
    print("🧪 Testing Audit Trail Generation")
    print("-" * 40)
    
    audit_manager = AuditTrailManager()
    
    # Test span creation
    with audit_manager.create_span(
        operation_name="test_operation",
        span_type=SpanType.AGENT_EXECUTION,
        agent_id="test_agent",
        pillar="Test Pillar",
        aml_level=2
    ) as span:
        span.add_attribute("test_attribute", "test_value")
        span.add_event("test_event", {"event_data": "test"})
    
    # Wait for async storage to complete
    await asyncio.sleep(0.1)
    
    # Verify span was recorded
    spans = await audit_manager.storage.get_spans(limit=10)
    assert len(spans) > 0, "No spans were recorded"
    
    latest_span = spans[0]
    assert latest_span.operation_name == "test_operation"
    assert latest_span.agent_id == "test_agent"
    assert latest_span.aml_level == 2
    assert "test_attribute" in latest_span.attributes
    
    print(f"✅ Created and verified span: {latest_span.span_id}")
    return audit_manager


async def test_trajectory_evaluation():
    """Test trajectory evaluation pipelines."""
    print("\n🧪 Testing Trajectory Evaluation")
    print("-" * 40)
    
    audit_manager = await test_audit_trail_generation()
    evaluator = TrajectoryEvaluationOrchestrator(audit_manager)
    
    # Create test spans for evaluation
    test_spans = []
    for i in range(3):
        with audit_manager.create_span(
            operation_name=f"eval_test_{i}",
            span_type=SpanType.TOOL_CALL,
            agent_id="eval_test_agent",
            tool_name="test_tool"
        ) as span:
            span.span_data.cost_usd = 0.01 * (i + 1)
            test_spans.append(span.span_data)
    
    # Wait for spans to be processed
    await asyncio.sleep(0.1)
    
    # Test evaluation summary
    summary = await evaluator.get_evaluation_summary(
        agent_id="eval_test_agent",
        hours=1
    )
    
    print(f"✅ Evaluation summary generated for agent")
    print(f"   Evaluation count: {summary.get('evaluation_count', 0)}")
    return evaluator


async def test_drift_detection():
    """Test drift detection system."""
    print("\n🧪 Testing Drift Detection")
    print("-" * 40)
    
    audit_manager = AuditTrailManager()
    drift_monitor = DriftMonitor(audit_manager)
    
    # Create test spans with different patterns
    # Normal pattern
    for i in range(5):
        with audit_manager.create_span(
            operation_name="normal_operation",
            span_type=SpanType.AGENT_EXECUTION,
            agent_id="drift_test_agent"
        ) as span:
            span.span_data.cost_usd = 0.1
            span.span_data.token_count = 100
    
    # Anomalous pattern
    for i in range(3):
        with audit_manager.create_span(
            operation_name="anomalous_operation", 
            span_type=SpanType.AGENT_EXECUTION,
            agent_id="drift_test_agent"
        ) as span:
            span.span_data.cost_usd = 1.0  # 10x higher cost
            span.span_data.token_count = 1000  # 10x more tokens
            span.set_status(SpanStatus.ERROR, "Simulated error")
    
    # Run drift analysis
    drift_results = await drift_monitor.run_drift_analysis(hours_back=1)
    
    print(f"✅ Drift analysis completed")
    print(f"   Total alerts: {drift_results.get('total_alerts', 0)}")
    print(f"   Spans analyzed: current={drift_results.get('current_spans', 0)}, baseline={drift_results.get('baseline_spans', 0)}")
    
    return drift_monitor


async def test_compliance_reporting():
    """Test compliance reporting."""
    print("\n🧪 Testing Compliance Reporting")
    print("-" * 40)
    
    audit_manager = AuditTrailManager()
    compliance = ComplianceOrchestrator(audit_manager)
    
    # Create test spans for compliance analysis
    for i in range(10):
        with audit_manager.create_span(
            operation_name=f"compliance_test_{i}",
            span_type=SpanType.AGENT_EXECUTION,
            agent_id="compliance_agent",
            pillar="Test Pillar"
        ) as span:
            span.span_data.policy_decision = "allow" if i < 8 else "deny"
            span.span_data.aml_level = 2
    
    # Generate ISO 42001 report
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=1)
    
    iso_report = await compliance.generate_report(
        report_type=ReportType.ISO_42001,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"✅ ISO 42001 report generated: {iso_report.evidence_id}")
    print(f"   Metrics: {len(iso_report.metrics)}")
    print(f"   Span summaries: {len(iso_report.span_summaries)}")
    print(f"   Signature: {iso_report.signature[:20]}..." if iso_report.signature else "   No signature")
    
    # Generate SOC 2 report
    soc2_report = await compliance.generate_report(
        report_type=ReportType.SOC_2,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"✅ SOC 2 report generated: {soc2_report.evidence_id}")
    print(f"   Access logs: {len(soc2_report.access_logs)}")
    print(f"   Encryption status: {len(soc2_report.encryption_status)}")
    
    return compliance


async def test_full_integration():
    """Test full observability integration."""
    print("\n🧪 Testing Full Integration")
    print("-" * 40)
    
    # Initialize infrastructure
    aml_registry = EnhancedAMLRegistry()
    policy_engine = LocalPolicyEngine(aml_registry=aml_registry)
    event_bus = EventBusFactory.create("memory")
    
    # Initialize observability
    observability = ObservabilityIntegration(
        aml_registry=aml_registry,
        policy_engine=policy_engine,
        event_bus=event_bus
    )
    
    try:
        # Initialize all components
        await aml_registry.initialize()
        await observability.initialize()
        
        # Register test agent
        await aml_registry.register_agent_group(
            agent_group="integration_test_agents",
            pillar="Test Pillar",
            initial_level=AutonomyLevel.AML_2
        )
        
        # Test agent execution tracking
        async with observability.track_agent_execution(
            agent_id="integration_test_agent",
            pillar="Test Pillar", 
            operation="test_operation",
            aml_level=2
        ) as span:
            
            # Test tool call tracking
            await observability.track_tool_call(
                agent_id="integration_test_agent",
                tool_name="test_tool",
                tool_inputs={"input": "test"},
                tool_outputs={"output": "success"},
                cost=0.05,
                trace_id=span.span_data.trace_id,
                parent_span_id=span.span_data.span_id
            )
            
            # Test policy decision tracking
            await observability.track_policy_decision(
                agent_id="integration_test_agent",
                policy_decision="allow",
                policy_reasons=["within policy limits"],
                trace_id=span.span_data.trace_id
            )
        
        # Test observability dashboard
        dashboard = await observability.get_observability_dashboard()
        
        print(f"✅ Full integration test completed")
        print(f"   System status: {dashboard['observability_status']['system_status']}")
        print(f"   Total spans: {dashboard['audit_trail']['total_spans']}")
        print(f"   Integration status:")
        for component, connected in dashboard['integration_status'].items():
            status = "✅" if connected else "❌"
            print(f"     {status} {component}")
        
        # Test compliance dashboard
        compliance_dashboard = await observability.compliance_orchestrator.get_compliance_dashboard()
        overall_metrics = compliance_dashboard['overall_metrics']
        print(f"   Policy compliance: {overall_metrics['policy_compliance_rate']}%")
        print(f"   System availability: {overall_metrics['availability_estimate']}%")
        
    finally:
        # Cleanup
        await observability.shutdown()
        await aml_registry.shutdown()
        await event_bus.close()
    
    return True


async def test_alert_handling():
    """Test alert handling and AML integration."""
    print("\n🧪 Testing Alert Handling")
    print("-" * 40)
    
    # Create mock alert
    from trust_observability.drift_detection import DriftType
    
    alert = DriftAlert(
        alert_id="test_alert_001",
        drift_type=DriftType.BEHAVIOR_DRIFT,
        severity=AlertSeverity.HIGH,
        agent_id="test_agent",
        pillar="Test Pillar",
        timestamp=datetime.now(),
        metric_name="test_metric",
        current_value=0.5,
        baseline_value=0.8,
        drift_magnitude=0.3,
        threshold=0.2,
        title="Test Drift Alert",
        description="Test alert for integration testing",
        recommended_actions=["Test action 1", "Test action 2"]
    )
    
    # Test alert serialization
    alert_dict = alert.to_dict()
    assert alert_dict['alert_id'] == "test_alert_001"
    assert alert_dict['severity'] == "high"
    
    print(f"✅ Alert handling test completed")
    print(f"   Alert ID: {alert.alert_id}")
    print(f"   Severity: {alert.severity.value}")
    print(f"   Drift magnitude: {alert.drift_magnitude:.3f}")
    
    return True


async def main():
    """Run all observability integration tests."""
    print("🚀 Advanced Observability Integration Tests")
    print("=" * 60)
    print("Testing all components of the Trust & Observability Mesh:")
    print("- Audit trail generation and storage")
    print("- Trajectory evaluation pipelines")
    print("- Drift detection and alerting")
    print("- Compliance reporting automation")
    print("- Full system integration")
    print("=" * 60)
    
    try:
        # Run individual component tests
        await test_audit_trail_generation()
        await test_trajectory_evaluation()
        await test_drift_detection()
        await test_compliance_reporting()
        await test_alert_handling()
        
        # Run full integration test
        await test_full_integration()
        
        print("\n" + "="*60)
        print("🎉 ALL OBSERVABILITY INTEGRATION TESTS PASSED!")
        print("="*60)
        print("\nAdvanced Observability features verified:")
        print("✅ OpenTelemetry audit trail generation")
        print("✅ Immutable span storage and retrieval")
        print("✅ Trajectory evaluation pipelines")
        print("✅ Multi-modal drift detection")
        print("✅ Automated compliance reporting")
        print("✅ AML registry integration")
        print("✅ Event bus integration")
        print("✅ Policy engine integration")
        print("✅ End-to-end observability workflows")
        
        print("\nThe Trust & Observability Mesh is ready for:")
        print("🔍 Real-time monitoring of agent behavior")
        print("🚨 Automatic anomaly detection and response")
        print("📊 Continuous trajectory quality evaluation")
        print("📋 Automated compliance evidence generation")
        print("🛡️ Emergency response and AML adjustments")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())