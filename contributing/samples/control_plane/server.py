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
import os
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.adk.cli import get_fast_api_app
from pydantic import BaseModel

from .agent import control_plane_setup, root_agent
from .aml_registry import AutonomyLevel, AutonomyCapabilities
from .blockchain_treasury import BlockchainTreasury
from .policy_compiler import BusinessRule, PolicyCompiler, RuleLanguage
from .web3auth_integration import (
  Web3AuthConfig,
  Web3AuthTreasuryIntegration,
  create_web3auth_config,
)

# Create FastAPI app using ADK's helper
app = get_fast_api_app(
  agents_dir="contributing/samples/control_plane",
  allow_origins=["http://localhost:3000", "http://localhost:8000"],
  web=True,
)

# Additional CORS for control plane endpoints
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


# Control Plane API Models
class PolicyRuleRequest(BaseModel):
  """Request to add a new policy rule."""
  name: str
  description: str
  rule_text: str
  language: str = "natural"
  pillar: str = "all"
  priority: int = 0


class AutonomyUpdateRequest(BaseModel):
  """Request to update agent autonomy level."""
  agent_name: str
  new_level: int


class BudgetAllocationRequest(BaseModel):
  """Request to update budget allocation."""
  pillar: str
  amount: float


class ApprovalRequest(BaseModel):
  """Request to approve/reject a transaction."""
  transaction_id: str
  approve: bool
  approver: str
  reason: str = ""


class BlockchainSignatureRequest(BaseModel):
  """Request to sign a blockchain transaction."""
  blockchain_tx_id: str
  signer_address: str


class EmergencyPauseRequest(BaseModel):
  """Request to emergency pause blockchain operations."""
  reason: str
  authorizer: str


class Web3AuthSignerRequest(BaseModel):
  """Request to authorize a new signer via Web3Auth."""
  email: str
  pillar: str
  role: str = "signer"


class Web3AuthCallbackRequest(BaseModel):
  """Web3Auth callback parameters."""
  callback_params: Dict[str, str]
  pillar: str


class Web3AuthSignRequest(BaseModel):
  """Request to sign transaction via Web3Auth."""
  blockchain_tx_id: str
  session_id: str


# Control Plane API Endpoints
@app.get("/control-plane/status")
async def get_control_plane_status():
  """Get overall control plane status."""
  aml_registry = control_plane_setup["aml_registry"]
  treasury = control_plane_setup["treasury"]
  policy_engine = control_plane_setup["policy_engine"]
  
  # Get pillar summaries
  pillar_summary = aml_registry.get_pillar_summary()
  budget_summary = treasury.get_budget_summary()
  policies = await policy_engine.list_policies()
  
  return {
    "status": "operational",
    "pillars": pillar_summary,
    "budget": budget_summary,
    "active_policies": len(policies),
    "pending_approvals": len(treasury.get_pending_approvals())
  }


@app.get("/control-plane/agents/{agent_name}")
async def get_agent_status(agent_name: str):
  """Get specific agent status and constraints."""
  aml_registry = control_plane_setup["aml_registry"]
  profile = aml_registry.get_profile(agent_name)
  
  if not profile:
    raise HTTPException(status_code=404, detail="Agent not found")
  
  # Find the controlled agent
  controlled_agent = None
  for name, agent in control_plane_setup.items():
    if hasattr(agent, "_wrapped_agent") and agent._wrapped_agent.name == agent_name:
      controlled_agent = agent
      break
  
  if controlled_agent:
    policy_summary = await controlled_agent.get_policy_summary()
    audit_log = controlled_agent.get_audit_log()
  else:
    policy_summary = {}
    audit_log = []
  
  return {
    "agent_name": agent_name,
    "pillar": profile.pillar,
    "autonomy_level": profile.current_level.name,
    "capabilities": profile.capabilities.__dict__ if profile.capabilities else {},
    "performance_metrics": profile.performance_metrics,
    "drift_incidents": profile.drift_incidents,
    "policy_summary": policy_summary,
    "recent_audit_log": audit_log[-10:]  # Last 10 entries
  }


@app.post("/control-plane/policies")
async def add_policy_rule(request: PolicyRuleRequest):
  """Add a new policy rule."""
  policy_engine = control_plane_setup["policy_engine"]
  compiler = PolicyCompiler()
  
  # Create business rule
  rule = BusinessRule(
    name=request.name,
    description=request.description,
    rule_text=request.rule_text,
    language=RuleLanguage(request.language),
    pillar=request.pillar,
    priority=request.priority
  )
  
  # Compile rule
  compiled = compiler.compile(rule)
  
  if compiled.validation_errors:
    raise HTTPException(
      status_code=400,
      detail=f"Policy compilation failed: {', '.join(compiled.validation_errors)}"
    )
  
  # Add to policy engine
  success = await policy_engine.add_policy(compiled.policy_rule)
  
  return {
    "success": success,
    "policy_name": compiled.policy_rule.name,
    "policy_type": compiled.policy_rule.policy_type.value,
    "opa_rego": compiled.opa_rego,
    "warnings": compiled.warnings
  }


@app.put("/control-plane/autonomy")
async def update_autonomy_level(request: AutonomyUpdateRequest):
  """Update an agent's autonomy level."""
  aml_registry = control_plane_setup["aml_registry"]
  profile = aml_registry.get_profile(request.agent_name)
  
  if not profile:
    raise HTTPException(status_code=404, detail="Agent not found")
  
  if request.new_level < 0 or request.new_level > 5:
    raise HTTPException(status_code=400, detail="Invalid autonomy level (0-5)")
  
  old_level = profile.current_level
  profile.current_level = AutonomyLevel(request.new_level)
  profile.capabilities = AutonomyCapabilities(level=profile.current_level)
  
  # Update in controlled agent
  for name, agent in control_plane_setup.items():
    if hasattr(agent, "_wrapped_agent") and agent._wrapped_agent.name == request.agent_name:
      await agent.update_autonomy_level(AutonomyLevel(request.new_level))
      break
  
  return {
    "agent_name": request.agent_name,
    "old_level": old_level.name,
    "new_level": profile.current_level.name,
    "updated": True
  }


@app.get("/control-plane/treasury/summary")
async def get_treasury_summary():
  """Get treasury budget summary."""
  treasury = control_plane_setup["treasury"]
  return treasury.get_budget_summary()


@app.get("/control-plane/treasury/pending")
async def get_pending_approvals():
  """Get pending treasury approvals."""
  treasury = control_plane_setup["treasury"]
  pending = treasury.get_pending_approvals()
  
  return {
    "count": len(pending),
    "approvals": [
      {
        "id": t.id,
        "agent": t.agent_name,
        "pillar": t.pillar,
        "amount": t.amount,
        "description": t.description,
        "timestamp": t.timestamp.isoformat(),
        "approval_requirement": t.approval_requirement.value
      }
      for t in pending
    ]
  }


@app.post("/control-plane/treasury/approve")
async def handle_approval(request: ApprovalRequest):
  """Approve or reject a pending transaction."""
  treasury = control_plane_setup["treasury"]
  
  if request.approve:
    success = treasury.approve_transaction(
      request.transaction_id,
      request.approver
    )
  else:
    success = treasury.reject_transaction(
      request.transaction_id,
      request.reason
    )
  
  if not success:
    raise HTTPException(
      status_code=404,
      detail="Transaction not found or already processed"
    )
  
  return {
    "transaction_id": request.transaction_id,
    "action": "approved" if request.approve else "rejected",
    "success": True
  }


@app.get("/control-plane/audit/{pillar}")
async def get_audit_log(pillar: str, limit: int = 100):
  """Get audit log for a specific pillar."""
  treasury = control_plane_setup["treasury"]
  
  # Get transaction history
  audit_entries = []
  for transaction in treasury.transaction_history[-limit:]:
    if transaction.pillar == pillar:
      audit_entries.append({
        "timestamp": transaction.timestamp.isoformat(),
        "type": "transaction",
        "agent": transaction.agent_name,
        "amount": transaction.amount,
        "status": transaction.status.value,
        "description": transaction.description
      })
  
  # Get policy decisions from agents
  for name, agent in control_plane_setup.items():
    if hasattr(agent, "_pillar") and agent._pillar == pillar:
      audit_log = agent.get_audit_log()
      for entry in audit_log[-limit:]:
        audit_entries.append({
          "timestamp": entry.get("timestamp"),
          "type": "policy_decision",
          "agent": agent._wrapped_agent.name,
          "tool": entry.get("tool"),
          "decision": entry.get("decision"),
          "reasons": entry.get("reasons", [])
        })
  
  # Sort by timestamp
  audit_entries.sort(key=lambda x: x["timestamp"], reverse=True)
  
  return {
    "pillar": pillar,
    "entries": audit_entries[:limit]
  }


# Blockchain-specific endpoints
@app.get("/control-plane/blockchain/wallets")
async def get_blockchain_wallets():
  """Get blockchain wallet information."""
  treasury = control_plane_setup["treasury"]
  
  if not isinstance(treasury, BlockchainTreasury):
    raise HTTPException(
      status_code=400,
      detail="Blockchain treasury not enabled"
    )
  
  return await treasury.get_wallet_summary()


@app.get("/control-plane/blockchain/pending-signatures")
async def get_pending_signatures():
  """Get transactions pending blockchain signatures."""
  treasury = control_plane_setup["treasury"]
  
  if not isinstance(treasury, BlockchainTreasury):
    raise HTTPException(
      status_code=400,
      detail="Blockchain treasury not enabled"
    )
  
  return {
    "pending": treasury.get_pending_signatures()
  }


@app.post("/control-plane/blockchain/sign")
async def sign_blockchain_transaction(request: BlockchainSignatureRequest):
  """Sign a blockchain transaction."""
  treasury = control_plane_setup["treasury"]
  
  if not isinstance(treasury, BlockchainTreasury):
    raise HTTPException(
      status_code=400,
      detail="Blockchain treasury not enabled"
    )
  
  success = await treasury.sign_transaction(
    request.blockchain_tx_id,
    request.signer_address
  )
  
  if not success:
    raise HTTPException(
      status_code=400,
      detail="Failed to sign transaction"
    )
  
  # Get updated transaction status
  blockchain_tx = treasury.blockchain_txs.get(request.blockchain_tx_id)
  
  return {
    "success": True,
    "blockchain_tx_id": request.blockchain_tx_id,
    "signatures": len(blockchain_tx.signatures) if blockchain_tx else 0,
    "required": blockchain_tx.required_signatures if blockchain_tx else 0,
    "status": blockchain_tx.status if blockchain_tx else "unknown"
  }


@app.get("/control-plane/blockchain/transaction/{tx_id}")
async def get_blockchain_transaction_status(tx_id: str):
  """Get blockchain transaction status."""
  treasury = control_plane_setup["treasury"]
  
  if not isinstance(treasury, BlockchainTreasury):
    raise HTTPException(
      status_code=400,
      detail="Blockchain treasury not enabled"
    )
  
  status = await treasury.check_transaction_status(tx_id)
  
  if status.get("status") == "not_found":
    raise HTTPException(
      status_code=404,
      detail="Transaction not found"
    )
  
  return status


@app.post("/control-plane/blockchain/emergency-pause")
async def emergency_pause(request: EmergencyPauseRequest):
  """Emergency pause blockchain operations."""
  treasury = control_plane_setup["treasury"]
  
  if not isinstance(treasury, BlockchainTreasury):
    raise HTTPException(
      status_code=400,
      detail="Blockchain treasury not enabled"
    )
  
  # In production, would verify authorizer identity
  success = await treasury.emergency_pause(request.reason)
  
  return {
    "success": success,
    "reason": request.reason,
    "timestamp": datetime.now().isoformat(),
    "emergency_wallet": treasury.emergency_wallet
  }


# Health check endpoint
@app.get("/control-plane/health")
async def health_check():
  """Health check for control plane."""
  treasury = control_plane_setup["treasury"]
  blockchain_enabled = isinstance(treasury, BlockchainTreasury)
  
  return {
    "status": "healthy",
    "components": {
      "policy_engine": "operational",
      "aml_registry": "operational",
      "treasury": "operational",
      "blockchain": "operational" if blockchain_enabled else "not_enabled",
      "agents": len([k for k in control_plane_setup if hasattr(control_plane_setup[k], "_wrapped_agent")])
    }
  }


# Web3Auth Integration Endpoints
# Initialize Web3Auth integration (singleton)
web3auth_integration: Optional[Web3AuthTreasuryIntegration] = None


@app.on_event("startup")
async def initialize_web3auth():
  """Initialize Web3Auth integration on startup."""
  global web3auth_integration
  
  # Check if blockchain treasury is enabled
  treasury = control_plane_setup.get("treasury")
  if isinstance(treasury, BlockchainTreasury):
    # Get Web3Auth client ID from environment
    web3auth_client_id = os.getenv("WEB3AUTH_CLIENT_ID")
    if web3auth_client_id:
      try:
        config = create_web3auth_config(
          client_id=web3auth_client_id,
          environment=os.getenv("WEB3AUTH_NETWORK", "testnet")
        )
        web3auth_integration = Web3AuthTreasuryIntegration(
          blockchain_treasury=treasury,
          web3auth_config=config
        )
        logger.info("Web3Auth integration initialized")
      except Exception as e:
        logger.error(f"Failed to initialize Web3Auth: {e}")


@app.on_event("shutdown")
async def shutdown_web3auth():
  """Clean up Web3Auth resources."""
  global web3auth_integration
  if web3auth_integration:
    await web3auth_integration.close()


@app.post("/control-plane/web3auth/authorize-signer")
async def authorize_web3auth_signer(request: Web3AuthSignerRequest):
  """Start Web3Auth authorization flow for a new signer."""
  if not web3auth_integration:
    raise HTTPException(
      status_code=400,
      detail="Web3Auth not configured. Set WEB3AUTH_CLIENT_ID environment variable."
    )
  
  try:
    result = await web3auth_integration.authorize_signer(
      email=request.email,
      pillar=request.pillar,
      role=request.role
    )
    
    return {
      "success": True,
      "auth_url": result["auth_url"],
      "session_id": result["session_id"],
      "message": f"Redirect user to auth_url to complete authorization"
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/control-plane/web3auth/callback")
async def handle_web3auth_callback(request: Web3AuthCallbackRequest):
  """Handle Web3Auth callback after user authentication."""
  if not web3auth_integration:
    raise HTTPException(
      status_code=400,
      detail="Web3Auth not configured"
    )
  
  try:
    success = await web3auth_integration.complete_signer_authorization(
      callback_params=request.callback_params,
      pillar=request.pillar
    )
    
    if success:
      return {
        "success": True,
        "message": "Signer successfully authorized",
        "pillar": request.pillar
      }
    else:
      raise HTTPException(
        status_code=400,
        detail="Failed to authorize signer"
      )
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/control-plane/web3auth/dashboard/{session_id}")
async def get_web3auth_dashboard(session_id: str):
  """Get signer dashboard for Web3Auth user."""
  if not web3auth_integration:
    raise HTTPException(
      status_code=400,
      detail="Web3Auth not configured"
    )
  
  try:
    dashboard = await web3auth_integration.get_signer_dashboard(session_id)
    
    if "error" in dashboard:
      raise HTTPException(status_code=404, detail=dashboard["error"])
    
    return dashboard
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/control-plane/web3auth/sign")
async def sign_with_web3auth(request: Web3AuthSignRequest):
  """Sign a blockchain transaction using Web3Auth."""
  if not web3auth_integration:
    raise HTTPException(
      status_code=400,
      detail="Web3Auth not configured"
    )
  
  try:
    success = await web3auth_integration.sign_transaction_web3auth(
      blockchain_tx_id=request.blockchain_tx_id,
      session_id=request.session_id
    )
    
    if success:
      # Get updated transaction status
      treasury = control_plane_setup["treasury"]
      blockchain_tx = treasury.blockchain_txs.get(request.blockchain_tx_id)
      
      return {
        "success": True,
        "blockchain_tx_id": request.blockchain_tx_id,
        "signatures": len(blockchain_tx.signatures) if blockchain_tx else 0,
        "required": blockchain_tx.required_signatures if blockchain_tx else 0,
        "status": blockchain_tx.status if blockchain_tx else "unknown"
      }
    else:
      raise HTTPException(
        status_code=400,
        detail="Failed to sign transaction"
      )
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/control-plane/web3auth/logout/{session_id}")
async def logout_web3auth(session_id: str):
  """Logout Web3Auth user."""
  if not web3auth_integration:
    raise HTTPException(
      status_code=400,
      detail="Web3Auth not configured"
    )
  
  success = await web3auth_integration.web3auth.logout(session_id)
  
  if success:
    return {"success": True, "message": "User logged out"}
  else:
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/control-plane/web3auth/status")
async def get_web3auth_status():
  """Get Web3Auth integration status."""
  return {
    "enabled": web3auth_integration is not None,
    "network": web3auth_integration.web3auth.config.network.value if web3auth_integration else None,
    "login_provider": web3auth_integration.web3auth.config.login_provider.value if web3auth_integration else None,
    "configured": bool(os.getenv("WEB3AUTH_CLIENT_ID"))
  }


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)