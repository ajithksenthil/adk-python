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

"""Comprehensive example demonstrating all Business Pillar Agents working together."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

# Import our infrastructure
from ..control_plane.control_plane_agent import ControlPlaneAgent
from ..control_plane.treasury import Treasury
from ..control_plane.policy_engine import LocalPolicyEngine
from ..control_plane.aml_registry_enhanced import EnhancedAMLRegistry, AutonomyLevel
from ..data_mesh.event_bus import EventBusFactory, EventHandler, Topics
from ..data_mesh.lineage_service import LineageService

# Import all business pillars
from .base import PillarRegistry
from .mission_governance import MissionGovernancePillar
from .product_experience import ProductExperiencePillar
from .growth_engine import GrowthEnginePillar
from .customer_success import CustomerSuccessPillar
from .resource_supply import ResourceSupplyPillar
from .people_culture import PeopleCulturePillar
from .intelligence_improvement import IntelligenceImprovementPillar
from .platform_infrastructure import PlatformInfrastructurePillar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnterpriseOrchestrator:
  """Orchestrates the entire AI-native enterprise."""
  
  def __init__(self):
    # Initialize infrastructure
    self.event_bus = EventBusFactory.create("memory")
    self.lineage_service = LineageService()
    self.treasury = Treasury(total_budget=1000000.0)
    self.policy_engine = LocalPolicyEngine()
    self.aml_registry = EnhancedAMLRegistry()
    
    # Initialize pillar registry
    self.pillar_registry = PillarRegistry()
    
    # Event tracking
    self.processed_events = []
    
  async def initialize(self):
    """Initialize all business pillars and their agents."""
    logger.info("🚀 Initializing AI-Native Enterprise Architecture")
    
    # Initialize enhanced AML registry
    await self.aml_registry.initialize()
    
    # Setup event handlers for cross-pillar communication
    await self._setup_event_handlers()
    
    # Initialize all 8 business pillars
    pillars = [
      MissionGovernancePillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service,
        treasury=self.treasury,
        policy_engine=self.policy_engine
      ),
      ProductExperiencePillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      ),
      GrowthEnginePillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      ),
      CustomerSuccessPillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      ),
      ResourceSupplyPillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      ),
      PeopleCulturePillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      ),
      IntelligenceImprovementPillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      ),
      PlatformInfrastructurePillar(
        event_bus=self.event_bus,
        lineage_service=self.lineage_service
      )
    ]
    
    # Register all pillars
    for pillar in pillars:
      self.pillar_registry.register_pillar(pillar)
    
    # Setup autonomy levels for agents
    await self._configure_autonomy_levels()
    
    logger.info("✅ Enterprise architecture initialized with 8 business pillars")
  
  async def _setup_event_handlers(self):
    """Setup cross-pillar event handlers."""
    async def track_all_events(event):
      self.processed_events.append({
        "timestamp": datetime.now().isoformat(),
        "source_pillar": event.metadata.source_pillar,
        "source_agent": event.metadata.source_agent,
        "event_type": event.event_type.value,
        "payload": event.payload
      })
    
    # Track all events for monitoring
    event_tracker = EventHandler(handler_func=track_all_events)
    
    # Subscribe to all pillar topics
    for pillar_name in [
      "Mission & Governance", "Product & Experience", "Growth Engine",
      "Customer Success", "Resource & Supply", "People & Culture",
      "Intelligence & Improvement", "Platform & Infra"
    ]:
      topic = Topics.for_pillar(pillar_name)
      await self.event_bus.subscribe(topic, event_tracker)
    
    # Subscribe to system topics
    await self.event_bus.subscribe(Topics.AUDIT, event_tracker)
    await self.event_bus.subscribe(Topics.ALERTS, event_tracker)
  
  async def _configure_autonomy_levels(self):
    """Configure autonomy levels for different agents."""
    autonomy_config = {
      # High autonomy for well-tested operations
      "ad_bidder_agents": {"level": AutonomyLevel.AML_4, "pillar": "Growth Engine"},
      "pricing_bot_agents": {"level": AutonomyLevel.AML_3, "pillar": "Growth Engine"},
      "refund_bot_agents": {"level": AutonomyLevel.AML_3, "pillar": "Customer Success"},
      
      # Medium autonomy for standard operations
      "support_responder_agents": {"level": AutonomyLevel.AML_2, "pillar": "Customer Success"},
      "quote_generator_agents": {"level": AutonomyLevel.AML_2, "pillar": "Growth Engine"},
      "po_issuer_agents": {"level": AutonomyLevel.AML_2, "pillar": "Resource & Supply"},
      
      # Lower autonomy for critical operations
      "budget_governor_agents": {"level": AutonomyLevel.AML_1, "pillar": "Mission & Governance"},
      "risk_auditor_agents": {"level": AutonomyLevel.AML_1, "pillar": "Mission & Governance"},
      "security_sentinel_agents": {"level": AutonomyLevel.AML_1, "pillar": "Platform & Infra"},
    }
    
    for agent_group, config in autonomy_config.items():
      await self.aml_registry.register_agent_group(
        agent_group=agent_group,
        pillar=config["pillar"],
        initial_level=config["level"]
      )
      logger.info(f"Registered {agent_group} at {config['level'].name} for {config['pillar']}")
  
  async def simulate_enterprise_day(self):
    """Simulate a full day of enterprise operations."""
    logger.info("🌅 Starting Enterprise Day Simulation")
    
    # Morning: Strategic planning and budget review
    await self._morning_strategic_planning()
    
    # Mid-morning: Product development cycle
    await self._product_development_cycle()
    
    # Midday: Customer success and growth activities
    await self._customer_growth_activities()
    
    # Afternoon: Operations and supply chain
    await self._operations_and_supply_chain()
    
    # Evening: Analytics and optimization
    await self._analytics_and_optimization()
    
    # End of day: Platform health check
    await self._platform_health_check()
    
    logger.info("🌙 Enterprise Day Simulation Complete")
    
    # Print summary
    await self._print_day_summary()
  
  async def _morning_strategic_planning(self):
    """Morning strategic planning activities."""
    logger.info("☀️ Morning: Strategic Planning & Governance")
    
    mission_pillar = self.pillar_registry.get_pillar(self.pillar_registry.pillars.keys().__iter__().__next__())
    
    # Budget allocation review
    budget_result = await mission_pillar.execute_workflow(
      "budget_allocation_review",
      {
        "Growth Engine_budget": 200000,
        "Product & Experience_budget": 150000,
        "Customer Success_budget": 100000,
        "Growth Engine_justification": "Q1 growth targets require increased marketing spend",
        "Product & Experience_justification": "New feature development for enterprise customers",
        "Customer Success_justification": "Scale support team for growing customer base"
      }
    )
    
    logger.info(f"📊 Budget allocation completed: {budget_result.status}")
    
    # Risk assessment
    risk_result = await mission_pillar.execute_workflow(
      "quarterly_risk_assessment",
      {"assessment_type": "comprehensive"}
    )
    
    logger.info(f"⚠️ Risk assessment completed: {risk_result.status}")
  
  async def _product_development_cycle(self):
    """Product development activities."""
    logger.info("🛠️ Mid-Morning: Product Development")
    
    from .base import PillarType
    product_pillar = self.pillar_registry.get_pillar(PillarType.PRODUCT_EXPERIENCE)
    
    # Feature development workflow
    feature_result = await product_pillar.execute_workflow(
      "feature_development",
      {
        "feature_name": "Advanced Analytics Dashboard",
        "segment": "enterprise",
        "competitors": ["tableau", "powerbi"],
        "sources": ["customer_interviews", "support_tickets"]
      }
    )
    
    logger.info(f"🎯 Feature development completed: {feature_result.status}")
    
    # This triggers events that other pillars can react to
    if feature_result.status == "completed":
      # Growth Engine might create marketing campaigns for the new feature
      growth_pillar = self.pillar_registry.get_pillar(PillarType.GROWTH_ENGINE)
      
      campaign_result = await growth_pillar.execute_workflow(
        "campaign_optimization",
        {
          "campaign_id": "new_feature_launch",
          "feature_name": "Advanced Analytics Dashboard"
        }
      )
      
      logger.info(f"📈 Marketing campaign launched: {campaign_result.status}")
  
  async def _customer_growth_activities(self):
    """Customer success and growth activities."""
    logger.info("🎯 Midday: Customer Success & Growth")
    
    from .base import PillarType
    
    # Customer success workflow
    customer_pillar = self.pillar_registry.get_pillar(PillarType.CUSTOMER_SUCCESS)
    
    # Handle customer ticket
    ticket_result = await customer_pillar.execute_workflow(
      "ticket_to_resolution",
      {
        "customer_id": "cust_enterprise_001",
        "subject": "Dashboard performance issues",
        "description": "Advanced analytics dashboard is loading slowly",
        "priority": "high",
        "auto_resolve": True
      }
    )
    
    logger.info(f"🎧 Customer ticket resolved: {ticket_result.status}")
    
    # Churn prevention analysis
    churn_result = await customer_pillar.execute_workflow(
      "churn_prevention",
      {"customer_id": "cust_enterprise_001"}
    )
    
    logger.info(f"🛡️ Churn prevention analysis: {churn_result.status}")
    
    # Growth engine activities
    growth_pillar = self.pillar_registry.get_pillar(PillarType.GROWTH_ENGINE)
    
    # Lead to quote conversion
    quote_result = await growth_pillar.execute_workflow(
      "lead_to_quote",
      {
        "customer_id": "prospect_tech_corp",
        "product_id": "enterprise_analytics",
        "customer_segment": "enterprise",
        "deal_size": "large",
        "quantity": 100
      }
    )
    
    logger.info(f"💰 Quote generated: {quote_result.status}")
  
  async def _operations_and_supply_chain(self):
    """Operations and supply chain activities."""
    logger.info("🏭 Afternoon: Operations & Supply Chain")
    
    from .base import PillarType
    
    # Resource & Supply workflow
    supply_pillar = self.pillar_registry.get_pillar(PillarType.RESOURCE_SUPPLY)
    
    procurement_result = await supply_pillar.execute_workflow(
      "procurement_cycle",
      {
        "product_id": "server_hardware",
        "supplier_id": "tech_supplier_001",
        "items": [
          {"name": "Server Rack", "quantity": 5, "unit_cost": 2500},
          {"name": "Network Switch", "quantity": 2, "unit_cost": 1200}
        ],
        "total_amount": 15000
      }
    )
    
    logger.info(f"📦 Procurement cycle completed: {procurement_result.status}")
    
    # People & Culture workflow
    people_pillar = self.pillar_registry.get_pillar(PillarType.PEOPLE_CULTURE)
    
    hiring_result = await people_pillar.execute_workflow(
      "hire_to_onboard",
      {
        "role": "Senior Software Engineer",
        "employee_id": "emp_2024_001",
        "candidate_id": "candidate_jane_doe",
        "requirements": {"experience": "5+ years", "skills": ["Python", "React"]}
      }
    )
    
    logger.info(f"👥 Hiring and onboarding completed: {hiring_result.status}")
  
  async def _analytics_and_optimization(self):
    """Analytics and optimization activities."""
    logger.info("📊 Evening: Analytics & Optimization")
    
    from .base import PillarType
    
    # Intelligence & Improvement workflow
    intel_pillar = self.pillar_registry.get_pillar(PillarType.INTELLIGENCE_IMPROVEMENT)
    
    optimization_result = await intel_pillar.execute_workflow(
      "optimization_cycle",
      {
        "metric_types": ["revenue", "customer_satisfaction", "user_engagement"],
        "time_range": "30d",
        "hypothesis": "New dashboard improves user engagement",
        "target_metric": "user_engagement",
        "model_id": "engagement_predictor_v2",
        "metrics": {"accuracy": 0.87, "latency": 450}
      }
    )
    
    logger.info(f"🔬 Optimization cycle completed: {optimization_result.status}")
  
  async def _platform_health_check(self):
    """Platform health check activities."""
    logger.info("🏗️ End of Day: Platform Health Check")
    
    from .base import PillarType
    
    # Platform & Infrastructure workflow
    platform_pillar = self.pillar_registry.get_pillar(PillarType.PLATFORM_INFRASTRUCTURE)
    
    health_result = await platform_pillar.execute_workflow(
      "platform_health_check",
      {
        "workflow_spec": {"pillars": ["all"]},
        "resource_type": "compute",
        "action": "scale",
        "coordination_request": {"type": "health_check", "pillars": ["all"]},
        "alert_thresholds": {"monthly_budget": 45000}
      }
    )
    
    logger.info(f"🏥 Platform health check completed: {health_result.status}")
  
  async def _print_day_summary(self):
    """Print summary of the day's activities."""
    logger.info("\n" + "="*60)
    logger.info("📋 ENTERPRISE DAY SUMMARY")
    logger.info("="*60)
    
    # Event summary
    logger.info(f"📨 Total Events Processed: {len(self.processed_events)}")
    
    # Events by pillar
    pillar_events = {}
    for event in self.processed_events:
      pillar = event["source_pillar"]
      if pillar not in pillar_events:
        pillar_events[pillar] = 0
      pillar_events[pillar] += 1
    
    logger.info("\n📊 Events by Pillar:")
    for pillar, count in sorted(pillar_events.items()):
      logger.info(f"  {pillar}: {count} events")
    
    # Lineage summary
    from .base import LineageQuery
    lineage_query = LineageQuery(direction="both", max_depth=3)
    lineage_data = await self.lineage_service.query_lineage(lineage_query)
    
    logger.info(f"\n🔗 Data Lineage:")
    logger.info(f"  Total Nodes: {lineage_data['stats']['total_nodes']}")
    logger.info(f"  Total Edges: {lineage_data['stats']['total_edges']}")
    logger.info(f"  Pillars Involved: {', '.join(lineage_data['stats']['pillars_involved'])}")
    
    # System status
    system_status = self.pillar_registry.get_system_status()
    
    logger.info(f"\n🏢 System Status:")
    logger.info(f"  Active Pillars: {system_status['total_pillars']}")
    logger.info(f"  Total Agents: {sum(len(pillar['agents']) for pillar in system_status['pillars'].values())}")
    
    # Sample recent events
    logger.info(f"\n📰 Recent Events (last 5):")
    for event in self.processed_events[-5:]:
      logger.info(f"  {event['timestamp']}: {event['source_pillar']} → {event['event_type']}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ AI-NATIVE ENTERPRISE OPERATING SUCCESSFULLY")
    logger.info("="*60)


async def demonstrate_cross_pillar_workflow():
  """Demonstrate a complex cross-pillar workflow."""
  logger.info("\n🔄 CROSS-PILLAR WORKFLOW DEMONSTRATION")
  logger.info("Scenario: New Enterprise Customer Acquisition & Onboarding")
  
  orchestrator = EnterpriseOrchestrator()
  await orchestrator.initialize()
  
  from .base import PillarType
  
  # This workflow involves multiple pillars coordinating
  result = await orchestrator.pillar_registry.execute_cross_pillar_workflow(
    primary_pillar=PillarType.GROWTH_ENGINE,
    workflow_type="enterprise_customer_acquisition",
    inputs={
      "prospect_company": "TechCorp Inc",
      "deal_size": 150000,
      "employee_count": 500,
      "requirements": ["enterprise_features", "dedicated_support", "custom_integration"]
    },
    involved_pillars=[
      PillarType.GROWTH_ENGINE,      # Lead qualification and pricing
      PillarType.CUSTOMER_SUCCESS,    # Account setup and onboarding
      PillarType.PRODUCT_EXPERIENCE,  # Custom feature requirements
      PillarType.RESOURCE_SUPPLY,     # Infrastructure provisioning
      PillarType.PEOPLE_CULTURE       # Dedicated account team assignment
    ]
  )
  
  logger.info(f"Cross-pillar workflow result: {result['success']}")
  logger.info(f"Trace ID: {result['trace_id']}")
  
  await orchestrator.aml_registry.shutdown()
  await orchestrator.event_bus.close()


async def main():
  """Run the comprehensive business pillars demonstration."""
  print("🚀 ADK Business Pillar Agents Demonstration\n")
  print("This demo shows the complete AI-native enterprise architecture:")
  print("- 8 Business Pillars with specialized agents")
  print("- Cross-cutting Control Plane, Data Mesh, and lineage tracking")
  print("- Event-driven coordination between pillars")
  print("- Real-time policy enforcement and budget controls")
  print("- End-to-end enterprise workflows\n")
  
  try:
    # Initialize the enterprise
    orchestrator = EnterpriseOrchestrator()
    await orchestrator.initialize()
    
    # Simulate a full enterprise day
    await orchestrator.simulate_enterprise_day()
    
    # Demonstrate cross-pillar coordination
    await demonstrate_cross_pillar_workflow()
    
    # Cleanup
    await orchestrator.aml_registry.shutdown()
    await orchestrator.event_bus.close()
    
    print("\n✅ All demonstrations completed successfully!")
    print("\nThe AI-native enterprise is now operating with:")
    print("- Autonomous agents handling routine operations")
    print("- Policy-enforced guardrails and budget controls") 
    print("- Real-time cross-pillar coordination via events")
    print("- Complete audit trail and data lineage tracking")
    print("- Adaptive autonomy levels based on performance")
    
  except Exception as e:
    logger.error(f"Demo failed: {e}")
    raise


if __name__ == "__main__":
  asyncio.run(main())