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

"""Example usage of the Control Plane with Policy Engine."""

import asyncio
import logging

from google.adk.runners import InMemoryRunner

from .agent import control_plane_setup, root_agent
from .aml_registry import AutonomyLevel
from .policy_compiler import BusinessRule, RuleLanguage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_control_plane():
  """Demonstrate various control plane features."""
  
  print("=== ADK Control Plane Demonstration ===\n")
  
  # Get components
  aml_registry = control_plane_setup["aml_registry"]
  treasury = control_plane_setup["treasury"]
  policy_engine = control_plane_setup["policy_engine"]
  
  # 1. Show initial state
  print("1. Initial System State:")
  print(f"   Total Budget: ${treasury.total_budget:,.2f}")
  pillar_summary = aml_registry.get_pillar_summary()
  for pillar, info in pillar_summary.items():
    print(f"   {pillar}: {info['agent_count']} agents, avg AML: {info['average_level']:.1f}")
  print()
  
  # 2. Add a new policy using natural language
  print("2. Adding Natural Language Policy:")
  new_rule = BusinessRule(
    name="weekend_restrictions",
    description="Restrict high-cost operations on weekends",
    rule_text="Maximum cost per action is $50 on weekends, require approval above $25",
    language=RuleLanguage.NATURAL,
    pillar="all"
  )
  
  from .policy_compiler import PolicyCompiler
  compiler = PolicyCompiler()
  compiled = compiler.compile(new_rule)
  
  if not compiled.validation_errors:
    await policy_engine.add_policy(compiled.policy_rule)
    print(f"   ✓ Added policy: {new_rule.name}")
  else:
    print(f"   ✗ Failed to compile: {compiled.validation_errors}")
  print()
  
  # 3. Test agent execution with policies
  print("3. Testing Agent Execution with Policies:")
  
  # Create a runner
  runner = InMemoryRunner(agent=root_agent)
  
  # Test 1: Low-cost operation (should succeed)
  print("\n   Test 1: Low-cost data analysis")
  response = await runner.run("Please analyze sales data for last week")
  print(f"   Response: {response[:100]}...")
  
  # Test 2: High-cost operation (may require approval)
  print("\n   Test 2: High-cost report generation")
  try:
    response = await runner.run(
      "Generate comprehensive reports for all departments and email them"
    )
    print(f"   Response: {response[:100]}...")
  except Exception as e:
    print(f"   Policy blocked: {str(e)}")
  
  # 4. Check treasury status
  print("\n4. Treasury Status:")
  budget_summary = treasury.get_budget_summary()
  print(f"   Total Allocated: ${budget_summary['total_budget']:,.2f}")
  print(f"   Total Spent: ${budget_summary['total_spent']:,.2f}")
  print(f"   Pending Approvals: {len(treasury.get_pending_approvals())}")
  
  # 5. Demonstrate autonomy level change
  print("\n5. Autonomy Level Management:")
  
  # Get governance agent profile
  governance_profile = aml_registry.get_profile("governance_agent")
  if governance_profile:
    print(f"   Governance Agent - Current AML: {governance_profile.current_level.name}")
    
    # Simulate good performance metrics
    aml_registry.update_metrics("governance_agent", {
      "success_rate": 0.99,
      "response_time": 1.2,
      "user_satisfaction": 0.95
    })
    
    # Check promotion eligibility
    if aml_registry.evaluate_promotion("governance_agent"):
      governance_profile.promote()
      print(f"   ✓ Promoted to AML: {governance_profile.current_level.name}")
    else:
      print("   ✗ Not eligible for promotion yet")
  
  # 6. Simulate drift incident
  print("\n6. Drift Incident Handling:")
  marketing_profile = aml_registry.get_profile("marketing_agent")
  if marketing_profile:
    print(f"   Marketing Agent - Current AML: {marketing_profile.current_level.name}")
    print(f"   Drift incidents before: {marketing_profile.drift_incidents}")
    
    # Simulate a drift incident
    aml_registry.handle_drift("marketing_agent", severity="medium")
    print(f"   Drift incidents after: {marketing_profile.drift_incidents}")
    print(f"   New AML: {marketing_profile.current_level.name}")
  
  # 7. Audit trail
  print("\n7. Recent Audit Trail:")
  for agent_name, agent in control_plane_setup.items():
    if hasattr(agent, "get_audit_log"):
      audit_log = agent.get_audit_log()
      if audit_log:
        print(f"\n   {agent._wrapped_agent.name}:")
        for entry in audit_log[-3:]:  # Last 3 entries
          print(f"     - {entry.get('tool', 'N/A')}: {entry.get('decision', 'N/A')}")
  
  print("\n=== Demonstration Complete ===")


async def demonstrate_approval_workflow():
  """Demonstrate the approval workflow."""
  
  print("\n=== Approval Workflow Demonstration ===\n")
  
  treasury = control_plane_setup["treasury"]
  
  # Request a high-value transaction
  print("1. Requesting high-value transaction:")
  transaction = treasury.request_transaction(
    agent_name="marketing_agent",
    pillar="Growth Engine",
    amount=750.0,  # Above approval threshold
    description="Major advertising campaign",
    metadata={"campaign": "Q1-2025", "channels": ["Google", "Facebook"]}
  )
  
  print(f"   Transaction ID: {transaction.id}")
  print(f"   Status: {transaction.status.value}")
  print(f"   Approval Required: {transaction.approval_requirement.value}")
  
  if transaction.status.value == "pending":
    print("\n2. Approving transaction:")
    success = treasury.approve_transaction(
      transaction.id,
      "finance_manager"
    )
    print(f"   Approval Success: {success}")
    
    # Check updated status
    budget_summary = treasury.get_budget_summary()
    growth_budget = budget_summary["pillars"]["Growth Engine"]
    print(f"\n3. Updated Growth Engine Budget:")
    print(f"   Total Budget: ${growth_budget['budget']:,.2f}")
    print(f"   Spent: ${growth_budget['spent']:,.2f}")
    print(f"   Available: ${growth_budget['available']:,.2f}")


async def demonstrate_policy_compilation():
  """Demonstrate policy compilation from different formats."""
  
  print("\n=== Policy Compilation Demonstration ===\n")
  
  from .policy_compiler import PolicyCompiler, compile_business_rules
  
  # Define rules in different formats
  rules = [
    # Natural language
    BusinessRule(
      name="data_security",
      description="Data security policy",
      rule_text="Require tags: encrypted, classified. Data must stay in US, EU",
      language=RuleLanguage.NATURAL
    ),
    
    # YAML format
    BusinessRule(
      name="compute_budget",
      description="Compute resource budget",
      rule_text="""
type: budget
parameters:
  max_cost_per_action: 50
  max_daily_cost: 500
  require_approval_above: 100
generate_rego: true
""",
      language=RuleLanguage.YAML
    ),
    
    # Tool access control
    BusinessRule(
      name="tool_restrictions",
      description="Tool access by autonomy level",
      rule_text="Minimum autonomy level 3, deny tools: execute_trade, modify_database",
      language=RuleLanguage.NATURAL
    )
  ]
  
  # Compile all rules
  results = compile_business_rules(rules, output_format="full")
  
  print(f"Compilation Results:")
  print(f"  Successfully compiled: {results['compiled']}")
  print(f"  Failed: {results['failed']}")
  
  for i, result in enumerate(results['results']):
    rule = rules[i]
    print(f"\n  Rule: {rule.name}")
    if result['validation_errors']:
      print(f"    ✗ Errors: {result['validation_errors']}")
    else:
      print(f"    ✓ Type: {result['policy_rule']['policy_type']}")
      if result['opa_rego']:
        print(f"    ✓ Generated OPA Rego code")


if __name__ == "__main__":
  # Run demonstrations
  asyncio.run(demonstrate_control_plane())
  asyncio.run(demonstrate_approval_workflow())
  asyncio.run(demonstrate_policy_compilation())