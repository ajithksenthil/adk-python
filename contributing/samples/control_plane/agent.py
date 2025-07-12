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

import asyncio
import logging
from typing import Any, Dict

from google.adk.agents import Agent

from .aml_registry import AMLRegistry, AutonomyLevel
from .control_plane_agent import ControlPlaneAgent
from .policy_compiler import BusinessRule, PolicyCompiler, RuleLanguage
from .policy_engine import (
  AutonomyPolicyRule,
  BudgetPolicyRule,
  LocalPolicyEngine,
  PolicyType,
)
from .treasury import Treasury

logger = logging.getLogger(__name__)


# Example tools with cost metadata
def analyze_data(query: str) -> str:
  """Analyze data based on query. Cost: $0.01 per analysis."""
  return f"Analysis complete for query: {query}"


def generate_report(topic: str, format: str = "pdf") -> str:
  """Generate a report on the given topic. Cost: $0.05 per report."""
  return f"Generated {format} report on: {topic}"


def send_email(to: str, subject: str, body: str) -> str:
  """Send an email. Cost: $0.001 per email."""
  return f"Email sent to {to} with subject: {subject}"


def execute_trade(symbol: str, quantity: int, action: str) -> str:
  """Execute a trade order. Cost: $0.10 per trade."""
  return f"Executed {action} order for {quantity} shares of {symbol}"


def modify_database(table: str, operation: str, data: Dict[str, Any]) -> str:
  """Modify database records. Cost: $0.02 per operation."""
  return f"Database operation {operation} on table {table} completed"


# Tool cost metadata for policy engine
TOOL_COSTS = {
  "analyze_data": 0.01,
  "generate_report": 0.05,
  "send_email": 0.001,
  "execute_trade": 0.10,
  "modify_database": 0.02,
}


# Create example agents for different business pillars

# Mission & Governance Agent - Low autonomy, high compliance
mission_agent = Agent(
  name="governance_agent",
  model="gemini-2.0-flash",
  instruction="""You are a governance agent responsible for policy compliance 
  and risk management. You can analyze data and generate reports, but cannot 
  take direct actions without approval.""",
  tools=[analyze_data, generate_report, send_email],
)

# Growth Engine Agent - Medium autonomy, budget constraints
growth_agent = Agent(
  name="marketing_agent",
  model="gemini-2.0-flash",
  instruction="""You are a marketing agent responsible for growth initiatives.
  You can analyze market data, generate reports, and send communications.
  You have budget constraints for campaign spending.""",
  tools=[analyze_data, generate_report, send_email],
)

# Customer Success Agent - Medium autonomy, can handle refunds
customer_agent = Agent(
  name="support_agent",
  model="gemini-2.0-flash",
  instruction="""You are a customer support agent. You can analyze customer
  issues, generate reports, send emails, and process refunds within limits.""",
  tools=[analyze_data, generate_report, send_email, modify_database],
)

# Platform & Infra Agent - Higher autonomy for technical operations
platform_agent = Agent(
  name="infrastructure_agent",
  model="gemini-2.0-flash",
  instruction="""You are an infrastructure agent responsible for platform
  operations. You can analyze system metrics, generate reports, and make
  database modifications for system maintenance.""",
  tools=[analyze_data, generate_report, modify_database],
)


def setup_control_plane(enable_blockchain: bool = False):
  """Set up the control plane with policies and agents."""
  
  # Initialize components
  policy_engine = LocalPolicyEngine()
  aml_registry = AMLRegistry()
  base_treasury = Treasury(total_budget=100000.0)  # $100k total budget
  
  # Optionally wrap with blockchain
  if enable_blockchain:
    from .blockchain_treasury import BlockchainTreasury, WalletType
    treasury = BlockchainTreasury(
      treasury=base_treasury,
      default_wallet_type=WalletType.MOCK
    )
  else:
    treasury = base_treasury
  
  # Set up business rule compiler
  compiler = PolicyCompiler()
  
  # Define business rules in natural language
  business_rules = [
    BusinessRule(
      name="governance_budget_limit",
      description="Governance pillar spending limits",
      rule_text="Maximum daily spend is $100, require approval above $50",
      language=RuleLanguage.NATURAL,
      pillar="Mission & Governance"
    ),
    BusinessRule(
      name="growth_campaign_budget",
      description="Marketing campaign budget constraints",
      rule_text="Daily limit is $1000, require approval above $500 for campaigns",
      language=RuleLanguage.NATURAL,
      pillar="Growth Engine"
    ),
    BusinessRule(
      name="support_refund_policy",
      description="Customer support refund limits",
      rule_text="Maximum refund is $100 without approval, daily limit $500",
      language=RuleLanguage.NATURAL,
      pillar="Customer Success"
    ),
    BusinessRule(
      name="platform_autonomy",
      description="Platform operations autonomy",
      rule_text="Minimum autonomy level 2, allow tools: analyze_data, generate_report, modify_database",
      language=RuleLanguage.NATURAL,
      pillar="Platform & Infra"
    ),
    BusinessRule(
      name="compliance_tags",
      description="Required compliance tags",
      rule_text="Require tags: reviewed, approved, compliant",
      language=RuleLanguage.NATURAL,
      pillar="all"
    ),
  ]
  
  # Compile and add policies
  for rule in business_rules:
    compiled = compiler.compile(rule)
    if not compiled.validation_errors:
      asyncio.run(policy_engine.add_policy(compiled.policy_rule))
      if compiled.opa_rego:
        logger.info(f"Generated OPA Rego for {rule.name}")
    else:
      logger.error(f"Failed to compile {rule.name}: {compiled.validation_errors}")
  
  # Add some direct policies
  asyncio.run(policy_engine.add_policy(
    BudgetPolicyRule(
      name="global_transaction_limit",
      description="Global per-transaction spending limit",
      policy_type=PolicyType.BUDGET,
      max_cost_per_action=1000.0,
      priority=10
    )
  ))
  
  asyncio.run(policy_engine.add_policy(
    AutonomyPolicyRule(
      name="trade_restriction",
      description="Restrict financial trades to high autonomy agents",
      policy_type=PolicyType.AUTONOMY,
      min_autonomy_level=4,
      max_autonomy_level=5,
      denied_tools=["execute_trade"],
      priority=20
    )
  ))
  
  # Create controlled agents
  controlled_mission = ControlPlaneAgent(
    wrapped_agent=mission_agent,
    pillar="Mission & Governance",
    policy_engine=policy_engine,
    aml_registry=aml_registry,
    treasury=treasury,
    initial_autonomy_level=AutonomyLevel.AML_1
  )
  
  controlled_growth = ControlPlaneAgent(
    wrapped_agent=growth_agent,
    pillar="Growth Engine",
    policy_engine=policy_engine,
    aml_registry=aml_registry,
    treasury=treasury,
    initial_autonomy_level=AutonomyLevel.AML_3
  )
  
  controlled_customer = ControlPlaneAgent(
    wrapped_agent=customer_agent,
    pillar="Customer Success",
    policy_engine=policy_engine,
    aml_registry=aml_registry,
    treasury=treasury,
    initial_autonomy_level=AutonomyLevel.AML_3
  )
  
  controlled_platform = ControlPlaneAgent(
    wrapped_agent=platform_agent,
    pillar="Platform & Infra",
    policy_engine=policy_engine,
    aml_registry=aml_registry,
    treasury=treasury,
    initial_autonomy_level=AutonomyLevel.AML_2
  )
  
  return {
    "mission": controlled_mission,
    "growth": controlled_growth,
    "customer": controlled_customer,
    "platform": controlled_platform,
    "policy_engine": policy_engine,
    "aml_registry": aml_registry,
    "treasury": treasury
  }


# Create a coordinator agent that manages the controlled agents
def create_coordinator_agent(controlled_agents: Dict[str, ControlPlaneAgent]) -> Agent:
  """Create a coordinator agent that manages controlled agents."""
  
  coordinator = Agent(
    name="control_plane_coordinator",
    model="gemini-2.0-flash",
    instruction="""You are the Control Plane Coordinator managing multiple
    business pillar agents with different autonomy levels and policies.
    
    Available agents:
    - Mission & Governance (AML 1): Policy compliance and risk management
    - Growth Engine (AML 3): Marketing and growth initiatives
    - Customer Success (AML 3): Customer support and refunds
    - Platform & Infra (AML 2): Technical operations
    
    You coordinate between these agents based on user requests, ensuring
    compliance with policies and budget constraints. Explain any policy
    violations or approval requirements to users.""",
    sub_agents=list(controlled_agents.values()),
  )
  
  return coordinator


# Main setup
control_plane_setup = setup_control_plane()
root_agent = create_coordinator_agent({
  k: v for k, v in control_plane_setup.items()
  if isinstance(v, ControlPlaneAgent)
})


# Export for use
__all__ = ["root_agent", "control_plane_setup"]