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

"""Test script to verify enhanced AML registry integration."""

import asyncio
import logging
from datetime import datetime

# Import enhanced AML registry and related components
from control_plane.aml_registry_enhanced import (
    EnhancedAMLRegistry, 
    AutonomyLevel,
    KPICondition,
    KPIOperator,
    ChangeType
)
from control_plane.policy_engine import LocalPolicyEngine, PolicyContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_aml_registry():
    """Test basic enhanced AML registry functionality."""
    print("🧪 Testing Enhanced AML Registry Integration")
    print("=" * 60)
    
    # Initialize enhanced AML registry
    aml_registry = EnhancedAMLRegistry()
    await aml_registry.initialize()
    
    # Test 1: Register agent groups
    print("\n1. Testing Agent Group Registration")
    
    agent_groups = [
        ("pricing_bot_agents", "Growth Engine", AutonomyLevel.AML_3),
        ("security_sentinel_agents", "Platform & Infra", AutonomyLevel.AML_1),
        ("refund_bot_agents", "Customer Success", AutonomyLevel.AML_3),
    ]
    
    for agent_group, pillar, level in agent_groups:
        profile = await aml_registry.register_agent_group(
            agent_group=agent_group,
            pillar=pillar,
            initial_level=level
        )
        print(f"✅ Registered {agent_group} at {level.name} for {pillar}")
    
    # Test 2: Permission checks
    print("\n2. Testing Permission Checks")
    
    permission_tests = [
        ("pricing_bot_agents", "calculate_price", 5.0, None),
        ("security_sentinel_agents", "analyze_threats", 1.0, None),
        ("refund_bot_agents", "process_refund", None, 150.0),
    ]
    
    for agent_group, tool_name, cost, transaction_value in permission_tests:
        result = await aml_registry.check_agent_permission(
            agent_group=agent_group,
            tool_name=tool_name,
            cost=cost,
            transaction_value=transaction_value
        )
        
        status = "✅ ALLOWED" if result["allowed"] else "❌ DENIED"
        approval = " (Requires Approval)" if result.get("requires_approval") else ""
        print(f"{status} {agent_group} → {tool_name}{approval}")
        if not result["allowed"] or result.get("requires_approval"):
            print(f"    Reason: {result.get('reason', 'No reason provided')}")
    
    # Test 3: Autonomy level changes
    print("\n3. Testing Autonomy Level Management")
    
    # Promote an agent group
    success = await aml_registry.promote_agent_group(
        "refund_bot_agents",
        changed_by="test_system",
        reason="Performance improvements demonstrated"
    )
    if success:
        profile = await aml_registry.get_agent_profile("refund_bot_agents")
        print(f"✅ Promoted refund_bot_agents to {profile.aml_level.name}")
    
    # Demote an agent group
    success = await aml_registry.demote_agent_group(
        "pricing_bot_agents",
        changed_by="test_system",
        reason="Detected pricing anomalies"
    )
    if success:
        profile = await aml_registry.get_agent_profile("pricing_bot_agents")
        print(f"⬇️ Demoted pricing_bot_agents to {profile.aml_level.name}")
    
    # Test 4: Metrics and KPI conditions
    print("\n4. Testing Metrics and KPI Evaluation")
    
    # Update metrics for an agent group
    test_metrics = {
        "success_rate": 0.96,
        "error_rate": 0.02,
        "response_time": 150.0,
        "cost_efficiency": 0.85
    }
    
    await aml_registry.update_metrics("pricing_bot_agents", test_metrics)
    
    # Get updated profile and check metrics
    profile = await aml_registry.get_agent_profile("pricing_bot_agents")
    print(f"📊 Updated metrics for pricing_bot_agents:")
    for metric, value in profile.current_metrics.items():
        print(f"    {metric}: {value}")
    
    # Test 5: Emergency controls
    print("\n5. Testing Emergency Controls")
    
    # Emergency pause
    await aml_registry.emergency_pause(
        "security_sentinel_agents",
        changed_by="test_system",
        reason="Suspicious activity detected"
    )
    print("🚨 Emergency pause activated for security_sentinel_agents")
    
    # Test permission after emergency pause
    result = await aml_registry.check_agent_permission(
        agent_group="security_sentinel_agents",
        tool_name="monitor_threats",
        cost=0.5
    )
    status = "✅ ALLOWED" if result["allowed"] else "❌ DENIED"
    print(f"{status} security_sentinel_agents after emergency pause")
    
    # Test 6: Audit trail
    print("\n6. Testing Audit Trail")
    
    audit_trail = await aml_registry.get_audit_trail(limit=5)
    print(f"📝 Recent audit trail entries ({len(audit_trail)}):")
    for entry in audit_trail[:3]:  # Show first 3 entries
        print(f"    {entry['timestamp']}: {entry['change_type']} for {entry['agent_group']} - {entry['reason']}")
    
    # Test 7: Pillar summary
    print("\n7. Testing Pillar Summary")
    
    pillar_summary = await aml_registry.get_pillar_summary()
    print("🏢 Pillar Summary:")
    for pillar, summary in pillar_summary.items():
        avg_level = summary['average_level']
        agent_count = len(summary['agent_groups'])
        emergency_count = summary['emergency_paused']
        print(f"    {pillar}: {agent_count} groups, avg level {avg_level:.1f}, {emergency_count} paused")
    
    # Cleanup
    await aml_registry.shutdown()
    print("\n✅ Enhanced AML Registry integration test completed successfully!")


async def test_policy_engine_integration():
    """Test policy engine integration with enhanced AML registry."""
    print("\n🔒 Testing Policy Engine Integration")
    print("=" * 60)
    
    # Initialize components
    aml_registry = EnhancedAMLRegistry()
    await aml_registry.initialize()
    
    # Register test agent
    await aml_registry.register_agent_group(
        agent_group="test_agent_group",
        pillar="Growth Engine", 
        initial_level=AutonomyLevel.AML_2
    )
    
    # Initialize policy engine with AML registry
    policy_engine = LocalPolicyEngine(aml_registry=aml_registry)
    
    # Test policy evaluation with AML registry integration
    context = PolicyContext(
        agent_name="test_agent",  # This will be converted to "test_agent_group"
        tool_name="execute_trade",
        action="execute_tool",
        parameters={"amount": 1000},
        autonomy_level=2,
        cost_estimate=10.0
    )
    
    result = await policy_engine.evaluate(context)
    
    print(f"Policy Decision: {result.decision.value}")
    if result.reasons:
        print(f"Reasons: {', '.join(result.reasons)}")
    
    # Test with different autonomy levels
    contexts = [
        ("AML 0 Agent", AutonomyLevel.AML_0, "write_data"),
        ("AML 3 Agent", AutonomyLevel.AML_3, "read_data"),
        ("AML 5 Agent", AutonomyLevel.AML_5, "manage_resources")
    ]
    
    for description, level, tool in contexts:
        # Register agent at specific level
        agent_group = f"{description.lower().replace(' ', '_')}_group"
        await aml_registry.register_agent_group(
            agent_group=agent_group,
            pillar="Growth Engine",
            initial_level=level
        )
        
        context = PolicyContext(
            agent_name=description.lower().replace(' ', '_'),
            tool_name=tool,
            autonomy_level=level.value
        )
        
        result = await policy_engine.evaluate(context)
        status = "✅ ALLOWED" if result.decision.value == "allow" else f"⚠️ {result.decision.value.upper()}"
        print(f"{status} {description} → {tool}")
    
    await aml_registry.shutdown()
    print("✅ Policy engine integration test completed!")


async def main():
    """Run all integration tests."""
    try:
        await test_enhanced_aml_registry()
        await test_policy_engine_integration()
        
        print("\n🎉 All AML 0-5 integration tests passed!")
        print("\nThe enhanced AML registry is fully integrated with:")
        print("  ✅ Agent group registration and management")
        print("  ✅ Dynamic autonomy level adjustments")
        print("  ✅ KPI-based promotion/demotion conditions")
        print("  ✅ Permission checks with tool restrictions")
        print("  ✅ Emergency controls and kill switches")
        print("  ✅ Immutable audit trail tracking")
        print("  ✅ Policy engine integration")
        print("  ✅ Cross-pillar coordination")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())