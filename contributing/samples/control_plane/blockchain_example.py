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

"""Example demonstrating blockchain treasury with multisig wallets."""

import asyncio
import logging
from typing import Dict, List

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
# Tools are defined inline below

from .aml_registry import AMLRegistry, AutonomyLevel
from .blockchain_treasury import (
  BlockchainTreasury,
  BlockchainTransaction,
  MockBlockchainConnector,
  SmartContractTreasury,
  WalletType,
)
from .control_plane_agent import ControlPlaneAgent
from .policy_engine import (
  BudgetPolicyRule,
  LocalPolicyEngine,
  PolicyType,
)
from .treasury import Treasury

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# High-value tools requiring blockchain approval
def execute_large_trade(symbol: str, quantity: int, action: str) -> str:
  """Execute a large financial trade. Cost: $5,000 per trade."""
  return f"Executed {action} order for {quantity} shares of {symbol}"


def transfer_funds(from_account: str, to_account: str, amount: float) -> str:
  """Transfer funds between accounts. Cost: $1,000 per transfer."""
  return f"Transferred ${amount} from {from_account} to {to_account}"


def approve_vendor_payment(vendor: str, invoice_id: str, amount: float) -> str:
  """Approve vendor payment. Cost: $2,500 per payment."""
  return f"Approved payment of ${amount} to {vendor} for invoice {invoice_id}"


async def demonstrate_blockchain_treasury():
  """Demonstrate blockchain treasury with multisig wallets."""
  
  print("=== Blockchain Treasury Demonstration ===\n")
  
  # 1. Initialize components
  policy_engine = LocalPolicyEngine()
  aml_registry = AMLRegistry()
  base_treasury = Treasury(total_budget=1000000.0)
  
  # Create blockchain treasury with mock connector
  blockchain_treasury = BlockchainTreasury(
    treasury=base_treasury,
    connector=MockBlockchainConnector(),
    default_wallet_type=WalletType.MOCK
  )
  
  # Add policies
  await policy_engine.add_policy(
    BudgetPolicyRule(
      name="high_value_multisig",
      description="High value transactions require multisig",
      policy_type=PolicyType.BUDGET,
      max_cost_per_action=10000.0,
      require_approval_above=1000.0,
      priority=10
    )
  )
  
  # 2. Show wallet configuration
  print("1. Blockchain Wallet Configuration:")
  wallet_summary = await blockchain_treasury.get_wallet_summary()
  for pillar, info in wallet_summary["wallets"].items():
    print(f"\n   {pillar}:")
    print(f"     Address: {info['address']}")
    print(f"     Balance: ${info['balance']:,.2f}")
    print(f"     Required Signatures: {info['required_signatures']}/{info['owners']}")
    print(f"     Daily Limit: ${info['daily_remaining']:,.2f} remaining")
  print()
  
  # 3. Create a finance agent with blockchain treasury
  finance_agent = Agent(
    name="finance_operations",
    model="gemini-2.0-flash",
    instruction="You handle financial operations requiring blockchain approval.",
    tools=[execute_large_trade, transfer_funds, approve_vendor_payment]
  )
  
  controlled_finance = ControlPlaneAgent(
    wrapped_agent=finance_agent,
    pillar="Mission & Governance",
    policy_engine=policy_engine,
    aml_registry=aml_registry,
    treasury=blockchain_treasury,
    initial_autonomy_level=AutonomyLevel.AML_3,
    enable_blockchain=True
  )
  
  # 4. Attempt high-value transaction
  print("2. High-Value Transaction Test:")
  print("   Requesting $5,000 trade execution...")
  
  # Request treasury transaction
  transaction = base_treasury.request_transaction(
    agent_name="finance_operations",
    pillar="Mission & Governance",
    amount=5000.0,
    description="Large trade execution",
    metadata={"type": "trade", "symbol": "GOOGL", "quantity": 100}
  )
  
  print(f"   Treasury Transaction ID: {transaction.id}")
  print(f"   Status: {transaction.status.value}")
  print(f"   Approval Required: {transaction.approval_requirement.value}")
  
  # Create blockchain transaction
  if transaction.status.value != "rejected":
    blockchain_tx = await blockchain_treasury.create_blockchain_transaction(
      treasury_tx_id=transaction.id,
      pillar="Mission & Governance",
      amount=5000.0,
      recipient="0xTRADING_PLATFORM_ADDRESS_123456789012345678"
    )
    
    print(f"\n   Blockchain Transaction ID: {blockchain_tx.id}")
    print(f"   Required Signatures: {blockchain_tx.required_signatures}")
    print(f"   Current Signatures: {len(blockchain_tx.signatures)}")
    print(f"   Status: {blockchain_tx.status}")
  
  # 5. Demonstrate multisig approval process
  print("\n3. Multisig Approval Process:")
  
  # Get signers
  wallet = blockchain_treasury.wallets["Mission & Governance"]
  signers = wallet.owners[:blockchain_tx.required_signatures]
  
  # Collect signatures
  for i, signer in enumerate(signers):
    print(f"\n   Signer {i+1} ({signer[:10]}...):")
    success = await blockchain_treasury.sign_transaction(
      blockchain_tx.id,
      signer
    )
    print(f"     Signature Added: {success}")
    print(f"     Total Signatures: {len(blockchain_tx.signatures)}/{blockchain_tx.required_signatures}")
    
    if len(blockchain_tx.signatures) >= blockchain_tx.required_signatures:
      print(f"     ✓ Transaction ready for execution!")
      print(f"     TX Hash: {blockchain_tx.tx_hash}")
  
  # 6. Check transaction status
  print("\n4. Transaction Status Check:")
  status = await blockchain_treasury.check_transaction_status(blockchain_tx.id)
  print(f"   Blockchain Status: {status.get('status')}")
  print(f"   Confirmations: {status.get('confirmations', 0)}")
  if status.get('block_number'):
    print(f"   Block Number: {status.get('block_number')}")
  
  # 7. Show updated wallet status
  print("\n5. Updated Wallet Status:")
  updated_summary = await blockchain_treasury.get_wallet_summary()
  pillar_info = updated_summary["wallets"]["Mission & Governance"]
  print(f"   Daily Spent: ${pillar_info['daily_spent']:,.2f}")
  print(f"   Daily Remaining: ${pillar_info['daily_remaining']:,.2f}")
  
  # 8. Demonstrate pending signatures view
  print("\n6. Pending Signatures Summary:")
  pending = blockchain_treasury.get_pending_signatures()
  if pending:
    for tx in pending:
      print(f"   - {tx['pillar']}: ${tx['amount']:,.2f} "
            f"({tx['signatures']}/{tx['required']} signatures)")
  else:
    print("   No transactions pending signatures")
  
  print("\n=== Demonstration Complete ===")


async def demonstrate_smart_contract_treasury():
  """Demonstrate smart contract-based treasury."""
  
  print("\n=== Smart Contract Treasury Demonstration ===\n")
  
  # Initialize smart contract treasury
  base_treasury = Treasury(total_budget=1000000.0)
  smart_treasury = SmartContractTreasury(
    treasury=base_treasury,
    default_wallet_type=WalletType.GNOSIS_SAFE
  )
  
  # 1. Deploy treasury contract with policies
  print("1. Deploying Treasury Smart Contract:")
  
  initial_policies = [
    {
      "name": "daily_limits",
      "type": "budget",
      "rules": {
        "Mission & Governance": 10000,
        "Growth Engine": 50000,
        "Customer Success": 20000
      }
    },
    {
      "name": "multisig_thresholds",
      "type": "approval",
      "rules": {
        "below_1000": 1,
        "below_10000": 2,
        "above_10000": 3
      }
    }
  ]
  
  contract_address = await smart_treasury.deploy_treasury_contract(initial_policies)
  print(f"   Contract Address: {contract_address}")
  print(f"   Policies Embedded: {len(initial_policies)}")
  
  # 2. Update on-chain policy
  print("\n2. Updating On-Chain Policy:")
  
  new_policy = {
    "name": "weekend_restrictions",
    "type": "time_based",
    "rules": {
      "max_weekend_transaction": 500,
      "blocked_hours": [0, 1, 2, 3, 4, 5]  # 12am-6am
    }
  }
  
  success = await smart_treasury.update_on_chain_policy(new_policy)
  print(f"   Policy Update Initiated: {success}")
  print(f"   Requires Multisig Approval: Yes (3 signatures)")
  
  # 3. Emergency pause demonstration
  print("\n3. Emergency Pause Capability:")
  print("   In case of security breach, the system can:")
  print("   - Pause all smart contracts")
  print("   - Transfer funds to emergency wallet")
  print("   - Require all signers for recovery")
  print(f"   Emergency Wallet: {smart_treasury.emergency_wallet}")
  
  print("\n=== Smart Contract Demo Complete ===")


async def demonstrate_transaction_approval_workflow():
  """Demonstrate complete transaction approval workflow."""
  
  print("\n=== Transaction Approval Workflow ===\n")
  
  # Setup
  base_treasury = Treasury(total_budget=1000000.0)
  blockchain_treasury = BlockchainTreasury(treasury=base_treasury)
  
  # Simulate different transaction scenarios
  scenarios = [
    {
      "name": "Small Auto-Approved Transaction",
      "pillar": "Platform & Infra",
      "amount": 50.0,
      "description": "Routine maintenance"
    },
    {
      "name": "Medium Transaction (Single Sig)",
      "pillar": "Customer Success",
      "amount": 500.0,
      "description": "Customer refund"
    },
    {
      "name": "Large Transaction (Multisig)",
      "pillar": "Growth Engine",
      "amount": 15000.0,
      "description": "Marketing campaign"
    },
    {
      "name": "Critical Transaction (Treasury Board)",
      "pillar": "Mission & Governance",
      "amount": 50000.0,
      "description": "Strategic investment"
    }
  ]
  
  for scenario in scenarios:
    print(f"\n{scenario['name']}:")
    print(f"  Amount: ${scenario['amount']:,.2f}")
    
    # Request transaction
    tx = base_treasury.request_transaction(
      agent_name="test_agent",
      pillar=scenario["pillar"],
      amount=scenario["amount"],
      description=scenario["description"]
    )
    
    if tx.status.value == "approved":
      # Create blockchain transaction
      blockchain_tx = await blockchain_treasury.create_blockchain_transaction(
        treasury_tx_id=tx.id,
        pillar=scenario["pillar"],
        amount=scenario["amount"],
        recipient="0x" + "0" * 40
      )
      
      print(f"  Treasury Status: {tx.status.value}")
      print(f"  Blockchain Signatures Required: {blockchain_tx.required_signatures}")
      
      # Auto-sign if single sig
      if blockchain_tx.required_signatures == 1:
        wallet = blockchain_treasury.wallets[scenario["pillar"]]
        await blockchain_treasury.sign_transaction(
          blockchain_tx.id,
          wallet.owners[0]
        )
        print(f"  Auto-signed and submitted")
        print(f"  TX Hash: {blockchain_tx.tx_hash[:16]}...")
      else:
        print(f"  Status: Awaiting {blockchain_tx.required_signatures} signatures")
    else:
      print(f"  Treasury Status: {tx.status.value}")
      if tx.metadata.get("rejection_reason"):
        print(f"  Reason: {tx.metadata['rejection_reason']}")
  
  print("\n=== Workflow Demo Complete ===")


if __name__ == "__main__":
  # Run all demonstrations
  asyncio.run(demonstrate_blockchain_treasury())
  asyncio.run(demonstrate_smart_contract_treasury())
  asyncio.run(demonstrate_transaction_approval_workflow())