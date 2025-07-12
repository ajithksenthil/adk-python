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

"""
Integrated example showing how to combine all ADK enterprise patterns:
- Control Plane with policy enforcement
- Business Pillar agents
- Autonomy Maturity Levels
- Event Bus communication
"""

from google.adk.control_plane import (
    ControlPlaneAgent,
    ResourcePolicy,
    SecurityPolicy,
    CompliancePolicy,
)
from google.adk.business_pillars import (
    FinancePillarAgent,
    OperationsPillarAgent,
    MarketingPillarAgent,
    HRPillarAgent,
    ITPillarAgent,
    PillarOrchestrator,
)
from google.adk.autonomy_maturity import (
    AdaptiveAutonomyAgent,
    AutonomyLevel,
)
from google.adk.event_bus import (
    EventBusAgent,
    InMemoryEventBus,
)

# Step 1: Create the event bus for all agents to communicate
event_bus = InMemoryEventBus()

# Step 2: Create Business Pillar agents with event bus integration
class EventAwareFinancePillar(FinancePillarAgent, EventBusAgent):
    """Finance pillar that can communicate via events."""
    pass

class EventAwareOperationsPillar(OperationsPillarAgent, EventBusAgent):
    """Operations pillar that can communicate via events."""
    pass

# Create event-aware pillar agents
finance_agent = EventAwareFinancePillar(
    name="finance_pillar",
    model="gemini-2.0-flash",
    event_bus=event_bus,
    agent_topics=["pillar.finance", "pillar.all"],
    publish_topics=["finance.reports", "finance.alerts"],
)

operations_agent = EventAwareOperationsPillar(
    name="operations_pillar",
    model="gemini-2.0-flash",
    event_bus=event_bus,
    agent_topics=["pillar.operations", "pillar.all"],
    publish_topics=["operations.metrics", "operations.alerts"],
)

marketing_agent = MarketingPillarAgent(
    name="marketing_pillar",
    model="gemini-2.0-flash",
)

hr_agent = HRPillarAgent(
    name="hr_pillar",
    model="gemini-2.0-flash",
)

it_agent = ITPillarAgent(
    name="it_pillar",
    model="gemini-2.0-flash",
)

# Step 3: Create Pillar Orchestrator with adaptive autonomy
class AdaptivePillarOrchestrator(PillarOrchestrator, AdaptiveAutonomyAgent):
    """Orchestrator that can adapt its autonomy level."""
    pass

orchestrator = AdaptivePillarOrchestrator(
    name="adaptive_orchestrator",
    model="gemini-2.0-flash",
    description="Orchestrates business pillars with adaptive autonomy",
    sub_agents=[finance_agent, operations_agent, marketing_agent, hr_agent, it_agent],
    # Autonomy settings
    current_autonomy_level=AutonomyLevel.LEVEL_2_PARTIAL,
    target_autonomy_level=AutonomyLevel.LEVEL_4_HIGH,
    allow_dynamic_adjustment=True,
)

# Step 4: Create Control Plane with policies
control_plane = ControlPlaneAgent(
    name="enterprise_control_plane",
    model="gemini-2.0-flash",
    description="Enterprise control plane with policy enforcement",
    sub_agents=[orchestrator],
    enforce_policies=True,
)

# Define enterprise policies
enterprise_resource_policy = ResourcePolicy(
    name="enterprise_resources",
    description="Controls access to enterprise resources",
    allowed_resources=[
        "public/*",
        "department/*/public/*",
        "shared/*",
    ],
    denied_resources=[
        "*/confidential/*",
        "*/pii/*",
        "executive/*",
    ],
    priority=100,
)

enterprise_security_policy = SecurityPolicy(
    name="enterprise_security",
    description="Enterprise security controls",
    require_authentication=True,
    allowed_actions=[
        "read_*",
        "analyze_*",
        "report_*",
        "coordinate_*",
    ],
    denied_actions=[
        "delete_production_*",
        "modify_security_*",
        "bypass_*",
    ],
    priority=90,
)

enterprise_compliance_policy = CompliancePolicy(
    name="enterprise_compliance",
    description="Regulatory compliance requirements",
    data_retention_days=2555,  # 7 years
    require_audit_trail=True,
    pii_handling={
        "ssn": "encryption_required",
        "credit_card": "tokenization_required",
        "health_data": "hipaa_compliance_required",
    },
    geographic_restrictions=["US", "EU", "UK", "CA"],
    priority=95,
)

# Register policies
control_plane.register_policies([
    enterprise_resource_policy,
    enterprise_security_policy,
    enterprise_compliance_policy,
])

# Step 5: Set up event-driven coordination
async def setup_event_handlers():
    """Set up cross-pillar event handlers."""
    
    # Finance alerts trigger operations review
    async def handle_finance_alert(event):
        if event.payload.get("alert_type") == "budget_overrun":
            # Operations should review efficiency
            await event_bus.publish(
                topic="pillar.operations",
                event_type="review.efficiency",
                source="system",
                payload={
                    "reason": "Budget overrun detected",
                    "department": event.payload.get("department"),
                },
            )
    
    # Operations issues trigger IT investigation
    async def handle_operations_issue(event):
        if event.payload.get("metric") == "system_performance":
            await event_bus.publish(
                topic="pillar.it",
                event_type="investigate.performance",
                source="system",
                payload={
                    "system": event.payload.get("system"),
                    "performance_drop": event.payload.get("value"),
                },
            )
    
    # Subscribe to events
    await event_bus.subscribe(
        subscriber_id="cross_pillar_coordinator",
        topics=["finance.alerts"],
        handler=handle_finance_alert,
    )
    
    await event_bus.subscribe(
        subscriber_id="cross_pillar_coordinator",
        topics=["operations.metrics"],
        handler=handle_operations_issue,
    )

# The complete enterprise system now has:
# 1. Control Plane enforcing policies on all operations
# 2. Business Pillars managing their domains
# 3. Adaptive autonomy that adjusts based on performance
# 4. Event bus enabling real-time communication
# 5. Cross-functional coordination through the orchestrator

# Usage in agent.py:
root_agent = control_plane

# The system can now:
# - Enforce enterprise policies before any action
# - Coordinate across all business functions
# - Adapt autonomy levels based on maturity
# - Communicate via events for real-time coordination
# - Scale by adding more specialized agents
# - Maintain compliance and security standards