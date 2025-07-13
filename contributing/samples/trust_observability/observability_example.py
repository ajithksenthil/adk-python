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

"""Comprehensive example demonstrating Advanced Observability features."""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List

# Import observability components
from observability_integration import ObservabilityIntegration
from audit_trail import SpanType, SpanStatus
from trajectory_eval import EvaluationMode, TrajectoryEvaluationOrchestrator
from drift_detection import DriftMonitor, DriftType, AlertSeverity
from compliance_reporting import ComplianceOrchestrator, ReportType

# Import existing infrastructure for integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from control_plane.aml_registry_enhanced import EnhancedAMLRegistry, AutonomyLevel
from control_plane.policy_engine import LocalPolicyEngine, PolicyContext, PolicyDecision
from data_mesh.event_bus import EventBusFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObservabilityDemo:
    """Comprehensive demonstration of Advanced Observability features."""
    
    def __init__(self):
        # Initialize infrastructure components
        self.aml_registry = EnhancedAMLRegistry()
        self.policy_engine = LocalPolicyEngine(aml_registry=self.aml_registry)
        self.event_bus = EventBusFactory.create("memory")
        
        # Initialize observability integration
        self.observability = ObservabilityIntegration(
            aml_registry=self.aml_registry,
            policy_engine=self.policy_engine,
            event_bus=self.event_bus,
            enable_cloud_storage=False  # Use in-memory for demo
        )
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("🚀 Initializing Advanced Observability Demo")
        
        # Initialize AML registry
        await self.aml_registry.initialize()
        
        # Register demo agents
        await self._register_demo_agents()
        
        # Initialize observability
        await self.observability.initialize()
        
        logger.info("✅ Demo initialization complete")
    
    async def _register_demo_agents(self):
        """Register demo agent groups."""
        agents = [
            ("pricing_bot_agents", "Growth Engine", AutonomyLevel.AML_3),
            ("security_sentinel_agents", "Platform & Infra", AutonomyLevel.AML_1),
            ("customer_support_agents", "Customer Success", AutonomyLevel.AML_2),
            ("risk_auditor_agents", "Mission & Governance", AutonomyLevel.AML_1)
        ]
        
        for agent_group, pillar, level in agents:
            await self.aml_registry.register_agent_group(
                agent_group=agent_group,
                pillar=pillar,
                initial_level=level
            )
            logger.info(f"Registered {agent_group} at {level.name}")
    
    async def demonstrate_live_incident(self):
        """Demonstrate the live incident scenario from the specification."""
        logger.info("\n" + "="*80)
        logger.info("🚨 DEMONSTRATING LIVE INCIDENT SCENARIO")
        logger.info("Scenario: Pricing-Bot submits 60% markdown on high-demand SKU")
        logger.info("="*80)
        
        # Step 1: Anomaly appears - Pricing-Bot submits problematic pricing
        logger.info("\n1. 🔍 Anomaly Detection: Pricing-Bot unusual behavior")
        trace_id = await self._simulate_pricing_anomaly()
        
        # Step 2: Policy check - Engine sees margin floor violation
        logger.info("\n2. 🛡️ Policy Check: Margin floor violation detected")
        await self._simulate_policy_check(trace_id)
        
        # Step 3: Audit stream - Span hits collector
        logger.info("\n3. 📊 Audit Stream: Spans recorded in hot store")
        await self._demonstrate_audit_stream()
        
        # Step 4: Trajectory evaluation - Streaming evaluator flags violations
        logger.info("\n4. 🎯 Trajectory Evaluation: Real-time quality assessment")
        await self._demonstrate_trajectory_evaluation()
        
        # Step 5: Drift alert - Behavior drift watcher detects spike
        logger.info("\n5. 🚨 Drift Detection: Unusual pattern spike detected")
        await self._demonstrate_drift_detection()
        
        # Step 6: AML change - Control plane demotes autonomy
        logger.info("\n6. ⬇️ AML Adjustment: Automatic autonomy demotion")
        await self._demonstrate_aml_adjustment()
        
        # Step 7: Notification - Security-Sentinel opens alerts
        logger.info("\n7. 📢 Alerting: PagerDuty and Slack notifications")
        await self._demonstrate_alerting()
        
        # Step 8: Compliance log - Incident auto-logged
        logger.info("\n8. 📋 Compliance Logging: Incident recorded for audit")
        await self._demonstrate_compliance_logging()
        
        logger.info("\n✅ Live incident scenario demonstration complete!")
        return trace_id
    
    async def _simulate_pricing_anomaly(self) -> str:
        """Simulate pricing bot anomaly."""
        # Create span for pricing bot operation
        async with self.observability.create_span(
            operation_name="calculate_optimal_price",
            span_type=SpanType.TOOL_CALL,
            agent_id="pricing_bot_001",
            pillar="Growth Engine",
            aml_level=3,
            tool_name="calculate_price"
        ) as span:
            
            # Simulate problematic pricing decision
            span.span_data.tool_inputs = {
                "product_sku": "HIGH_DEMAND_WIDGET_PRO",
                "current_price": 299.99,
                "demand_level": "high",
                "competitor_prices": [289.99, 309.99, 279.99]
            }
            
            span.span_data.tool_outputs = {
                "recommended_price": 119.99,  # 60% markdown!
                "margin_percentage": 15.0,     # Below 25% floor
                "confidence": 0.8,
                "reasoning": "Aggressive pricing to capture market share"
            }
            
            span.span_data.cost_usd = 0.05
            span.add_attribute("anomaly_detected", True)
            span.add_attribute("margin_violation", True)
            
            logger.info(f"   📉 Pricing anomaly: ${299.99} → ${119.99} (60% markdown)")
            logger.info(f"   ⚠️ Margin: 15% (below 25% policy floor)")
            
            return span.span_data.trace_id
    
    async def _simulate_policy_check(self, trace_id: str):
        """Simulate policy engine check."""
        async with self.observability.create_span(
            operation_name="policy.check",
            span_type=SpanType.POLICY_CHECK,
            trace_id=trace_id,
            agent_id="pricing_bot_001"
        ) as span:
            
            # Simulate policy evaluation
            context = PolicyContext(
                agent_name="pricing_bot_001",
                tool_name="calculate_price",
                action="execute_tool",
                parameters={
                    "recommended_price": 119.99,
                    "margin_percentage": 15.0
                },
                autonomy_level=3
            )
            
            # Policy engine denies due to margin floor violation
            span.span_data.policy_decision = "deny"
            span.span_data.policy_reasons = [
                "Margin 15% below policy floor of 25%",
                "Price reduction exceeds 50% threshold"
            ]
            
            span.add_attribute("policy_rule_violated", "margin_floor_policy")
            span.add_attribute("violation_severity", "high")
            
            logger.info(f"   ❌ Policy Decision: DENY")
            logger.info(f"   📋 Reasons: {', '.join(span.span_data.policy_reasons)}")
    
    async def _demonstrate_audit_stream(self):
        """Demonstrate audit trail collection."""
        # Get recent spans to show audit collection
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        
        spans = await self.observability.audit_manager.storage.get_spans(
            start_time=start_time,
            limit=10
        )
        
        logger.info(f"   📊 Audit Trail: {len(spans)} spans recorded in last 5 minutes")
        logger.info(f"   💾 Storage: Hot query store + WORM bucket")
        
        for span in spans[-3:]:  # Show last 3 spans
            logger.info(f"   📝 Span: {span.operation_name} | {span.status.value} | {span.pillar}")
    
    async def _demonstrate_trajectory_evaluation(self):
        """Demonstrate trajectory evaluation."""
        # Run evaluation on recent spans
        evaluation_summary = await self.observability.trajectory_evaluator.get_evaluation_summary(
            agent_id="pricing_bot_001",
            hours=1
        )
        
        if evaluation_summary.get("evaluation_count", 0) > 0:
            logger.info(f"   🎯 Evaluations: {evaluation_summary['evaluation_count']} completed")
            logger.info(f"   📊 Average Score: {evaluation_summary.get('average_score', 0):.3f}")
            logger.info(f"   ✅ Pass Rate: {evaluation_summary.get('pass_rate', 0):.1%}")
        else:
            logger.info("   🎯 Trajectory Evaluation: Ready for streaming analysis")
            logger.info("   ⚡ Latency Budget: <50ms for critical operations")
    
    async def _demonstrate_drift_detection(self):
        """Demonstrate drift detection."""
        # Run drift analysis
        drift_analysis = await self.observability.run_drift_analysis(hours_back=1)
        
        total_alerts = drift_analysis.get("total_alerts", 0)
        logger.info(f"   🚨 Drift Analysis: {total_alerts} alerts generated")
        
        if total_alerts > 0:
            alerts_by_severity = drift_analysis.get("alerts_by_severity", {})
            for severity, count in alerts_by_severity.items():
                if count > 0:
                    logger.info(f"   📊 {severity.upper()}: {count} alerts")
        else:
            logger.info("   ✅ No significant drift detected in analysis window")
    
    async def _demonstrate_aml_adjustment(self):
        """Demonstrate automatic AML adjustment."""
        # Get current AML level
        profile = await self.aml_registry.get_agent_profile("pricing_bot_agents")
        if profile:
            current_level = profile.aml_level
            logger.info(f"   📊 Current AML Level: {current_level.name}")
            
            # Simulate automatic demotion due to policy violations
            success = await self.aml_registry.demote_agent_group(
                agent_group="pricing_bot_agents",
                changed_by="drift_detector",
                reason="Repeated margin floor violations detected"
            )
            
            if success:
                new_profile = await self.aml_registry.get_agent_profile("pricing_bot_agents")
                new_level = new_profile.aml_level
                logger.info(f"   ⬇️ Demoted: {current_level.name} → {new_level.name}")
                logger.info(f"   🔒 Effect: All pricing actions now require human approval")
    
    async def _demonstrate_alerting(self):
        """Demonstrate alerting system."""
        # This would trigger real PagerDuty/Slack in production
        logger.info("   🚨 PagerDuty: High-severity incident opened")
        logger.info("   💬 Slack: Alert posted to #governance channel")
        logger.info("   🔗 Grafana: Trace link included for investigation")
        logger.info("   📞 On-call: Engineering team automatically notified")
    
    async def _demonstrate_compliance_logging(self):
        """Demonstrate compliance logging."""
        # Generate mini compliance report
        evidence_pack = await self.observability.compliance_orchestrator.generate_report(
            report_type=ReportType.ISO_42001,
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now()
        )
        
        logger.info(f"   📋 Evidence Pack: {evidence_pack.evidence_id}")
        logger.info(f"   🔐 Digital Signature: {evidence_pack.signature[:20]}...")
        logger.info(f"   📊 Metrics Captured: {len(evidence_pack.metrics)}")
        logger.info(f"   📅 Next Reports: Weekly ISO 42001, SOC 2")
    
    async def demonstrate_comprehensive_features(self):
        """Demonstrate all observability features comprehensively."""
        logger.info("\n" + "="*80)
        logger.info("🔬 COMPREHENSIVE OBSERVABILITY FEATURES DEMONSTRATION")
        logger.info("="*80)
        
        # 1. Audit Trail Generation
        await self._demo_audit_trail_generation()
        
        # 2. Trajectory Evaluation Pipelines
        await self._demo_trajectory_evaluation_pipelines()
        
        # 3. Drift Detection System
        await self._demo_drift_detection_system()
        
        # 4. Compliance Reporting
        await self._demo_compliance_reporting()
        
        # 5. Integration Dashboard
        await self._demo_observability_dashboard()
    
    async def _demo_audit_trail_generation(self):
        """Demo audit trail generation."""
        logger.info("\n📊 1. AUDIT TRAIL GENERATION")
        logger.info("-" * 50)
        
        # Generate sample agent activities
        agents = ["pricing_bot_001", "support_agent_002", "risk_auditor_003"]
        operations = ["analyze_customer", "process_refund", "assess_risk", "generate_report"]
        
        for i in range(5):
            agent = random.choice(agents)
            operation = random.choice(operations)
            
            async with self.observability.create_span(
                operation_name=operation,
                span_type=SpanType.AGENT_EXECUTION,
                agent_id=agent,
                pillar="Growth Engine" if "pricing" in agent else "Customer Success" if "support" in agent else "Mission & Governance",
                aml_level=random.randint(1, 4)
            ) as span:
                span.add_attribute("demo_operation", True)
                span.span_data.cost_usd = random.uniform(0.01, 1.0)
                
                # Simulate some operations having errors
                if random.random() < 0.1:
                    span.set_status(SpanStatus.ERROR, "Simulated error for demo")
                
                await asyncio.sleep(0.1)  # Simulate work
        
        # Show audit trail summary
        audit_summary = await self.observability._get_audit_summary()
        logger.info(f"✅ Generated spans: {audit_summary['total_spans']}")
        logger.info(f"📈 Success rate: {audit_summary['success_rate']}%")
        logger.info(f"🏢 Pillars active: {len(audit_summary['pillars'])}")
    
    async def _demo_trajectory_evaluation_pipelines(self):
        """Demo trajectory evaluation."""
        logger.info("\n🎯 2. TRAJECTORY EVALUATION PIPELINES")
        logger.info("-" * 50)
        
        # Run batch evaluation
        batch_results = await self.observability.run_trajectory_evaluation("batch")
        
        logger.info(f"📊 Batch Evaluation Results:")
        logger.info(f"   Evaluation Period: {batch_results.get('evaluation_period', {}).get('hours', 0)} hours")
        logger.info(f"   Spans Evaluated: {batch_results.get('spans_evaluated', 0)}")
        logger.info(f"   Results Generated: {batch_results.get('results_generated', 0)}")
        
        overall_stats = batch_results.get('overall_statistics', {})
        logger.info(f"   Average Score: {overall_stats.get('average_score', 0):.3f}")
        logger.info(f"   Pass Rate: {overall_stats.get('pass_rate', 0):.1%}")
        
        # Show agent performance
        agent_perf = batch_results.get('agent_performance', {})
        if agent_perf:
            logger.info("🏆 Agent Performance:")
            for agent_id, perf in list(agent_perf.items())[:3]:
                logger.info(f"   {agent_id}: {perf['average_score']:.3f} avg, {perf['evaluation_count']} evals")
    
    async def _demo_drift_detection_system(self):
        """Demo drift detection system."""
        logger.info("\n🚨 3. DRIFT DETECTION SYSTEM")
        logger.info("-" * 50)
        
        # Run drift analysis
        drift_results = await self.observability.run_drift_analysis(hours_back=2)
        
        logger.info(f"🔍 Drift Analysis Results:")
        logger.info(f"   Time Window: {drift_results.get('time_window_hours', 0)} hours")
        logger.info(f"   Current Spans: {drift_results.get('current_spans', 0)}")
        logger.info(f"   Baseline Spans: {drift_results.get('baseline_spans', 0)}")
        logger.info(f"   Total Alerts: {drift_results.get('total_alerts', 0)}")
        
        alerts_by_type = drift_results.get('alerts_by_type', {})
        if any(count > 0 for count in alerts_by_type.values()):
            logger.info("🚨 Alerts by Type:")
            for drift_type, count in alerts_by_type.items():
                if count > 0:
                    logger.info(f"   {drift_type}: {count}")
        else:
            logger.info("✅ No drift alerts in current analysis window")
        
        # Show detector performance
        detector_results = drift_results.get('detector_results', {})
        logger.info("🔧 Detector Performance:")
        for detector, result in detector_results.items():
            if 'error' in result:
                logger.info(f"   {detector}: ❌ {result['error']}")
            else:
                logger.info(f"   {detector}: ✅ {result.get('alerts_generated', 0)} alerts")
    
    async def _demo_compliance_reporting(self):
        """Demo compliance reporting."""
        logger.info("\n📋 4. COMPLIANCE REPORTING")
        logger.info("-" * 50)
        
        # Generate ISO 42001 report
        iso_report = await self.observability.generate_compliance_report(
            report_type=ReportType.ISO_42001,
            days_back=1
        )
        
        logger.info(f"📊 ISO 42001 Report Generated:")
        logger.info(f"   Evidence ID: {iso_report['evidence_id']}")
        logger.info(f"   Metrics Count: {len(iso_report['metrics'])}")
        logger.info(f"   Signature: {iso_report['signature'][:20]}...")
        
        # Show key metrics
        logger.info("🎯 Key Compliance Metrics:")
        for metric in iso_report['metrics'][:3]:
            status = "✅" if metric['status'] == "compliant" else "⚠️"
            logger.info(f"   {status} {metric['name']}: {metric['value']} {metric.get('unit', '')}")
        
        # Generate SOC 2 report
        soc2_report = await self.observability.generate_compliance_report(
            report_type=ReportType.SOC_2,
            days_back=1
        )
        
        logger.info(f"\n🔒 SOC 2 Report Generated:")
        logger.info(f"   Evidence ID: {soc2_report['evidence_id']}")
        logger.info(f"   Access Logs: {len(soc2_report['access_logs'])}")
        logger.info(f"   Encryption Status: {len(soc2_report['encryption_status'])} components verified")
    
    async def _demo_observability_dashboard(self):
        """Demo comprehensive observability dashboard."""
        logger.info("\n📊 5. OBSERVABILITY DASHBOARD")
        logger.info("-" * 50)
        
        dashboard = await self.observability.get_observability_dashboard()
        
        # System status
        status = dashboard['observability_status']
        logger.info(f"🚀 System Status: {status['system_status']}")
        logger.info(f"📡 Monitoring Active: {status['monitoring_active']}")
        
        # Audit trail summary
        audit = dashboard['audit_trail']
        logger.info(f"\n📊 Audit Trail (24h):")
        logger.info(f"   Total Spans: {audit['total_spans']}")
        logger.info(f"   Success Rate: {audit['success_rate']}%")
        logger.info(f"   Active Traces: {audit['active_traces']}")
        
        # Integration status
        integration = dashboard['integration_status']
        logger.info(f"\n🔗 Integration Status:")
        logger.info(f"   AML Registry: {'✅' if integration['aml_registry_connected'] else '❌'}")
        logger.info(f"   Policy Engine: {'✅' if integration['policy_engine_connected'] else '❌'}")
        logger.info(f"   Event Bus: {'✅' if integration['event_bus_connected'] else '❌'}")
        logger.info(f"   Lineage Service: {'✅' if integration['lineage_service_connected'] else '❌'}")
        
        # Compliance overview
        compliance = dashboard['compliance']
        overall_metrics = compliance['overall_metrics']
        logger.info(f"\n🏛️ Compliance Overview (30d):")
        logger.info(f"   Total Operations: {overall_metrics['total_operations']:,}")
        logger.info(f"   Policy Compliance: {overall_metrics['policy_compliance_rate']}%")
        logger.info(f"   System Availability: {overall_metrics['availability_estimate']}%")
    
    async def cleanup(self):
        """Cleanup demo resources."""
        logger.info("\n🧹 Cleaning up demo resources...")
        
        await self.observability.shutdown()
        await self.aml_registry.shutdown()
        await self.event_bus.close()
        
        logger.info("✅ Cleanup complete")


async def main():
    """Run the comprehensive observability demonstration."""
    print("🚀 Advanced Observability Demo - Trust & Observability Mesh")
    print("=" * 80)
    print("This demo showcases the complete observability architecture:")
    print("- OpenTelemetry audit trail generation")
    print("- Trajectory evaluation pipelines (batch & streaming)")
    print("- Drift detection and alerting")
    print("- Compliance reporting (ISO 42001, SOC 2)")
    print("- End-to-end incident response")
    print("=" * 80)
    
    demo = ObservabilityDemo()
    
    try:
        # Initialize demo
        await demo.initialize()
        
        # Run live incident demonstration
        trace_id = await demo.demonstrate_live_incident()
        
        # Wait a moment for processing
        await asyncio.sleep(1)
        
        # Run comprehensive features demo
        await demo.demonstrate_comprehensive_features()
        
        print("\n" + "="*80)
        print("🎉 ADVANCED OBSERVABILITY DEMONSTRATION COMPLETE!")
        print("="*80)
        print("\nKey capabilities demonstrated:")
        print("✅ Real-time audit trail with OpenTelemetry spans")
        print("✅ Automatic policy enforcement and violation tracking")
        print("✅ Trajectory evaluation for reasoning quality")
        print("✅ Multi-modal drift detection (data, model, behavior)")
        print("✅ Automatic AML level adjustments on anomalies")
        print("✅ Emergency response and alerting workflows")
        print("✅ Compliance-ready evidence generation")
        print("✅ Immutable audit trail with digital signatures")
        print("\nThe AI-native enterprise now has complete observability:")
        print("🔍 Glass-box transparency into all agent decisions")
        print("🛡️ Autonomous safety response to anomalies")
        print("📊 Audit-ready compliance reporting")
        print("🚨 Real-time incident detection and response")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())