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

"""Example demonstrating Web3Auth integration with blockchain treasury."""

import asyncio
import logging
import os
from typing import Dict

from .blockchain_treasury import BlockchainTreasury, MockBlockchainConnector
from .treasury import Treasury
from .web3auth_integration import (
  AuthProvider,
  Web3AuthConfig,
  Web3AuthNetwork,
  Web3AuthTreasuryIntegration,
  create_web3auth_config,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_web3auth_flow():
  """Demonstrate Web3Auth integration flow."""
  
  print("=== Web3Auth Integration Demo ===\n")
  
  # 1. Initialize components
  base_treasury = Treasury(total_budget=1000000.0)
  blockchain_treasury = BlockchainTreasury(
    treasury=base_treasury,
    connector=MockBlockchainConnector()
  )
  
  # Create Web3Auth config
  web3auth_config = Web3AuthConfig(
    client_id="YOUR_WEB3AUTH_CLIENT_ID",  # Replace with actual client ID
    network=Web3AuthNetwork.TESTNET,
    login_provider=AuthProvider.GOOGLE,
    display_name="ADK Treasury Control",
    chain_id="0x5",  # Goerli testnet
  )
  
  # Initialize integration
  web3auth_integration = Web3AuthTreasuryIntegration(
    blockchain_treasury=blockchain_treasury,
    web3auth_config=web3auth_config
  )
  
  print("1. Web3Auth Configuration:")
  print(f"   Network: {web3auth_config.network.value}")
  print(f"   Login Provider: {web3auth_config.login_provider.value}")
  print(f"   Chain: {web3auth_config.chain_id}")
  print()
  
  # 2. Authorize a new signer
  print("2. Authorizing New Signer:")
  
  auth_result = await web3auth_integration.authorize_signer(
    email="treasurer@company.com",
    pillar="Mission & Governance",
    role="treasury_admin"
  )
  
  print(f"   Auth URL: {auth_result['auth_url'][:50]}...")
  print(f"   Session ID: {auth_result['session_id']}")
  print("   Status: User needs to visit auth URL to complete")
  print()
  
  # 3. Simulate callback (in production, this would come from Web3Auth)
  print("3. Simulating Web3Auth Callback:")
  
  mock_callback = {
    "publicAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
    "privateKey": "0x" + "0" * 64,  # Never log real private keys!
    "userInfo": {
      "email": "treasurer@company.com",
      "name": "Treasury Admin",
      "profileImage": "https://example.com/avatar.jpg",
      "verifier": "google",
      "verifierId": "treasurer@company.com",
      "typeOfLogin": "google"
    }
  }
  
  success = await web3auth_integration.complete_signer_authorization(
    callback_params=mock_callback,
    pillar="Mission & Governance"
  )
  
  print(f"   Authorization Success: {success}")
  print(f"   Signer Address: {mock_callback['publicAddress']}")
  print()
  
  # 4. Create a transaction requiring signature
  print("4. Creating High-Value Transaction:")
  
  # Request treasury transaction
  tx = base_treasury.request_transaction(
    agent_name="governance_agent",
    pillar="Mission & Governance",
    amount=50000.0,
    description="Strategic investment allocation"
  )
  
  # Create blockchain transaction
  blockchain_tx = await blockchain_treasury.create_blockchain_transaction(
    treasury_tx_id=tx.id,
    pillar="Mission & Governance",
    amount=50000.0,
    recipient="0xRecipient1234567890123456789012345678901234"
  )
  
  print(f"   Amount: ${blockchain_tx.amount:,.2f}")
  print(f"   Required Signatures: {blockchain_tx.required_signatures}")
  print(f"   Blockchain TX ID: {blockchain_tx.id}")
  print()
  
  # 5. Get signer dashboard
  print("5. Signer Dashboard:")
  
  # Get the session from the authorization
  session_id = list(web3auth_integration.web3auth._user_sessions.keys())[0]
  
  dashboard = await web3auth_integration.get_signer_dashboard(session_id)
  
  print(f"   User: {dashboard['user']['name']} ({dashboard['user']['email']})")
  print(f"   Authorized Pillars: {', '.join(dashboard['authorized_pillars'])}")
  print(f"   Pending Transactions: {dashboard['stats']['total_pending']}")
  print(f"   Awaiting Signature: {dashboard['stats']['awaiting_signature']}")
  
  if dashboard['pending_transactions']:
    print("\n   Transactions:")
    for tx in dashboard['pending_transactions']:
      print(f"     - {tx['pillar']}: ${tx['amount']:,.2f} "
            f"({tx['signatures']}/{tx['required']} signatures)")
  print()
  
  # 6. Sign transaction via Web3Auth
  print("6. Signing Transaction with Web3Auth:")
  
  sign_success = await web3auth_integration.sign_transaction_web3auth(
    blockchain_tx_id=blockchain_tx.id,
    session_id=session_id
  )
  
  print(f"   Signature Success: {sign_success}")
  print(f"   Updated Signatures: {len(blockchain_tx.signatures)}/{blockchain_tx.required_signatures}")
  print(f"   Transaction Status: {blockchain_tx.status}")
  print()
  
  # Clean up
  await web3auth_integration.close()
  
  print("=== Demo Complete ===")


async def demonstrate_social_login_options():
  """Demonstrate different social login providers."""
  
  print("\n=== Social Login Providers Demo ===\n")
  
  providers = [
    (AuthProvider.GOOGLE, "Sign in with Google"),
    (AuthProvider.FACEBOOK, "Sign in with Facebook"),
    (AuthProvider.TWITTER, "Sign in with Twitter"),
    (AuthProvider.DISCORD, "Sign in with Discord"),
    (AuthProvider.EMAIL_PASSWORDLESS, "Sign in with Email (Passwordless)"),
  ]
  
  for provider, description in providers:
    config = Web3AuthConfig(
      client_id="YOUR_CLIENT_ID",
      login_provider=provider,
      display_name="ADK Treasury",
    )
    
    print(f"{description}:")
    print(f"  Provider: {provider.value}")
    print(f"  Auth Flow: OAuth 2.0 / OpenID Connect")
    print(f"  User Info: Email, Name, Profile Picture")
    print()


async def demonstrate_multi_pillar_signing():
  """Demonstrate multi-pillar signing scenario."""
  
  print("\n=== Multi-Pillar Signing Demo ===\n")
  
  # Setup
  base_treasury = Treasury(total_budget=5000000.0)
  blockchain_treasury = BlockchainTreasury(treasury=base_treasury)
  
  # Create Web3Auth integration
  web3auth_config = create_web3auth_config(
    client_id="YOUR_CLIENT_ID",
    environment="testnet"
  )
  
  web3auth_integration = Web3AuthTreasuryIntegration(
    blockchain_treasury=blockchain_treasury,
    web3auth_config=web3auth_config
  )
  
  # Simulate multiple signers from different departments
  signers = [
    {
      "email": "cfo@company.com",
      "name": "Chief Financial Officer",
      "pillar": "Mission & Governance",
      "address": "0xCFO1234567890123456789012345678901234567"
    },
    {
      "email": "cto@company.com", 
      "name": "Chief Technology Officer",
      "pillar": "Platform & Infra",
      "address": "0xCTO1234567890123456789012345678901234567"
    },
    {
      "email": "cmo@company.com",
      "name": "Chief Marketing Officer",
      "pillar": "Growth Engine",
      "address": "0xCMO1234567890123456789012345678901234567"
    }
  ]
  
  print("1. Authorized Signers:")
  for signer in signers:
    print(f"   - {signer['name']} ({signer['email']})")
    print(f"     Pillar: {signer['pillar']}")
    print(f"     Address: {signer['address'][:10]}...")
    
    # Add to wallet
    wallet = blockchain_treasury.wallets[signer['pillar']]
    if signer['address'] not in wallet.owners:
      wallet.owners.append(signer['address'])
  print()
  
  # Create cross-pillar transaction
  print("2. Cross-Pillar Transaction Requiring Multiple Signatures:")
  
  # Large transaction affecting multiple pillars
  tx = base_treasury.request_transaction(
    agent_name="strategic_planning",
    pillar="Mission & Governance",
    amount=100000.0,
    description="Company-wide digital transformation initiative",
    metadata={
      "affects_pillars": ["Mission & Governance", "Platform & Infra", "Growth Engine"],
      "approval_required_from": ["CFO", "CTO", "CMO"]
    }
  )
  
  blockchain_tx = await blockchain_treasury.create_blockchain_transaction(
    treasury_tx_id=tx.id,
    pillar="Mission & Governance",
    amount=100000.0,
    recipient="0xTransformation123456789012345678901234567890"
  )
  
  # Override to require 3 signatures
  blockchain_tx.required_signatures = 3
  
  print(f"   Initiative: Digital Transformation")
  print(f"   Budget: ${blockchain_tx.amount:,.2f}")
  print(f"   Required Approvals: CFO, CTO, CMO")
  print(f"   Blockchain Signatures Required: {blockchain_tx.required_signatures}")
  print()
  
  # Simulate approval workflow
  print("3. Approval Workflow:")
  
  for i, signer in enumerate(signers[:3]):
    print(f"\n   Step {i+1}: {signer['name']} reviews and signs")
    
    # In production, each signer would use Web3Auth
    # Here we simulate the signature
    success = await blockchain_treasury.sign_transaction(
      blockchain_tx.id,
      signer['address']
    )
    
    print(f"   Signature Added: {success}")
    print(f"   Progress: {len(blockchain_tx.signatures)}/{blockchain_tx.required_signatures}")
    
    if len(blockchain_tx.signatures) >= blockchain_tx.required_signatures:
      print(f"\n   ✓ All signatures collected!")
      print(f"   Transaction Status: {blockchain_tx.status}")
      print(f"   TX Hash: {blockchain_tx.tx_hash[:20]}...")
  
  await web3auth_integration.close()
  
  print("\n=== Multi-Pillar Demo Complete ===")


if __name__ == "__main__":
  # Check for Web3Auth client ID
  if not os.getenv("WEB3AUTH_CLIENT_ID"):
    print("Note: Set WEB3AUTH_CLIENT_ID environment variable for production use")
    print("Get your client ID from: https://dashboard.web3auth.io\n")
  
  # Run demonstrations
  asyncio.run(demonstrate_web3auth_flow())
  asyncio.run(demonstrate_social_login_options())
  asyncio.run(demonstrate_multi_pillar_signing())