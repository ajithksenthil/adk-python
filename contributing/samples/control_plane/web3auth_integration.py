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
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuthProvider(Enum):
  """Supported Web3Auth providers."""
  GOOGLE = "google"
  FACEBOOK = "facebook"
  TWITTER = "twitter"
  DISCORD = "discord"
  EMAIL_PASSWORDLESS = "email_passwordless"
  METAMASK = "metamask"
  WALLET_CONNECT = "wallet_connect"


class Web3AuthNetwork(Enum):
  """Web3Auth network environments."""
  MAINNET = "mainnet"
  TESTNET = "testnet"
  CYAN = "cyan"
  AQUA = "aqua"


@dataclass
class Web3AuthConfig:
  """Web3Auth configuration."""
  client_id: str
  network: Web3AuthNetwork = Web3AuthNetwork.TESTNET
  redirect_url: str = "http://localhost:8000/auth/callback"
  whitelist_urls: List[str] = field(default_factory=list)
  login_provider: AuthProvider = AuthProvider.GOOGLE
  chain_namespace: str = "eip155"
  chain_id: str = "0x1"  # Ethereum mainnet
  rpc_target: Optional[str] = None
  display_name: str = "ADK Control Plane"
  logo_light: Optional[str] = None
  logo_dark: Optional[str] = None
  default_language: str = "en"
  custom_auth_args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Web3AuthUser:
  """Authenticated Web3Auth user."""
  email: str
  name: str
  profile_image: Optional[str]
  verifier: str
  verifier_id: str
  type_of_login: str
  aggregated_id: str
  dapp_share: Optional[str]
  id_token: Optional[str]
  oauth_id_token: Optional[str]
  oauth_access_token: Optional[str]
  private_key: Optional[str]  # User's private key (handle with care!)
  public_address: str  # Ethereum address
  session_id: str
  authenticated_at: datetime = field(default_factory=datetime.now)
  
  def to_signer_info(self) -> Dict[str, str]:
    """Convert to signer information for blockchain operations."""
    return {
      "address": self.public_address,
      "email": self.email,
      "name": self.name,
      "verifier": self.verifier,
      "authenticated": True
    }


class Web3AuthClient:
  """Web3Auth client for authentication and key management."""
  
  def __init__(self, config: Web3AuthConfig):
    self.config = config
    self.client = httpx.AsyncClient(timeout=30.0)
    self.base_url = self._get_base_url()
    self._user_sessions: Dict[str, Web3AuthUser] = {}
  
  def _get_base_url(self) -> str:
    """Get Web3Auth API base URL based on network."""
    network_urls = {
      Web3AuthNetwork.MAINNET: "https://auth.web3auth.io",
      Web3AuthNetwork.TESTNET: "https://testnet.web3auth.io",
      Web3AuthNetwork.CYAN: "https://cyan.web3auth.io",
      Web3AuthNetwork.AQUA: "https://aqua.web3auth.io"
    }
    return network_urls.get(self.config.network, "https://testnet.web3auth.io")
  
  async def init_auth_session(
    self,
    user_email: str,
    login_hint: Optional[str] = None
  ) -> Dict[str, Any]:
    """Initialize Web3Auth session for user."""
    try:
      # Prepare auth request
      auth_params = {
        "client_id": self.config.client_id,
        "redirect_uri": self.config.redirect_url,
        "network": self.config.network.value,
        "login_provider": self.config.login_provider.value,
        "email": user_email,
        "chain_namespace": self.config.chain_namespace,
        "chain_id": self.config.chain_id,
        "display": "page",
        "prompt": "select_account",
        "max_age": 86400,
        "ui_locales": self.config.default_language,
        "id_token_hint": login_hint,
        **self.config.custom_auth_args
      }
      
      # For email passwordless
      if self.config.login_provider == AuthProvider.EMAIL_PASSWORDLESS:
        auth_params["login_hint"] = user_email
      
      # Generate state for CSRF protection
      state = hashlib.sha256(
        f"{user_email}{datetime.now().isoformat()}".encode()
      ).hexdigest()[:32]
      auth_params["state"] = state
      
      # Build authorization URL
      auth_url = f"{self.base_url}/auth"
      query_params = "&".join([f"{k}={v}" for k, v in auth_params.items()])
      
      return {
        "auth_url": f"{auth_url}?{query_params}",
        "state": state,
        "session_id": hashlib.sha256(f"{user_email}{state}".encode()).hexdigest()
      }
      
    except Exception as e:
      logger.error(f"Error initializing Web3Auth session: {e}")
      raise
  
  async def handle_auth_callback(
    self,
    callback_params: Dict[str, str]
  ) -> Optional[Web3AuthUser]:
    """Handle Web3Auth callback and extract user info."""
    try:
      # Extract auth response
      id_token = callback_params.get("id_token")
      access_token = callback_params.get("access_token")
      private_key = callback_params.get("privateKey")
      public_address = callback_params.get("publicAddress")
      user_info = callback_params.get("userInfo", {})
      
      if not public_address:
        logger.error("No public address in callback")
        return None
      
      # Parse user info
      if isinstance(user_info, str):
        user_info = json.loads(user_info)
      
      # Create authenticated user
      user = Web3AuthUser(
        email=user_info.get("email", ""),
        name=user_info.get("name", ""),
        profile_image=user_info.get("profileImage"),
        verifier=user_info.get("verifier", self.config.login_provider.value),
        verifier_id=user_info.get("verifierId", ""),
        type_of_login=user_info.get("typeOfLogin", self.config.login_provider.value),
        aggregated_id=user_info.get("aggregateVerifier", ""),
        dapp_share=user_info.get("dappShare"),
        id_token=id_token,
        oauth_id_token=user_info.get("oAuthIdToken"),
        oauth_access_token=access_token,
        private_key=private_key,  # Handle with extreme care!
        public_address=public_address,
        session_id=hashlib.sha256(f"{public_address}{datetime.now()}".encode()).hexdigest()
      )
      
      # Store session
      self._user_sessions[user.session_id] = user
      
      return user
      
    except Exception as e:
      logger.error(f"Error handling Web3Auth callback: {e}")
      return None
  
  async def get_user_info(self, session_id: str) -> Optional[Web3AuthUser]:
    """Get user info from session."""
    return self._user_sessions.get(session_id)
  
  async def logout(self, session_id: str) -> bool:
    """Logout user and clear session."""
    if session_id in self._user_sessions:
      # Clear sensitive data
      user = self._user_sessions[session_id]
      user.private_key = None  # Clear private key
      user.id_token = None
      user.oauth_access_token = None
      
      # Remove session
      del self._user_sessions[session_id]
      return True
    return False
  
  async def refresh_session(self, session_id: str) -> bool:
    """Refresh user session."""
    user = self._user_sessions.get(session_id)
    if not user:
      return False
    
    # Check if session is still valid (24 hours)
    if (datetime.now() - user.authenticated_at) > timedelta(hours=24):
      # Session expired, need re-authentication
      return False
    
    # Refresh timestamp
    user.authenticated_at = datetime.now()
    return True
  
  async def close(self):
    """Close HTTP client."""
    await self.client.aclose()


class Web3AuthBlockchainSigner:
  """Blockchain signer using Web3Auth authenticated users."""
  
  def __init__(self, web3auth_client: Web3AuthClient):
    self.web3auth = web3auth_client
    self._signing_sessions: Dict[str, Dict[str, Any]] = {}
  
  async def request_signature(
    self,
    session_id: str,
    transaction_data: Dict[str, Any],
    message: str
  ) -> Optional[str]:
    """Request transaction signature from authenticated user."""
    user = await self.web3auth.get_user_info(session_id)
    if not user:
      logger.error("User session not found")
      return None
    
    # Create signing request
    signing_id = hashlib.sha256(
      f"{session_id}{transaction_data}{datetime.now()}".encode()
    ).hexdigest()[:16]
    
    self._signing_sessions[signing_id] = {
      "session_id": session_id,
      "user_address": user.public_address,
      "transaction": transaction_data,
      "message": message,
      "created_at": datetime.now(),
      "status": "pending"
    }
    
    # In production, would:
    # 1. Send signing request to user's device
    # 2. Use Web3Auth's signing SDK
    # 3. Handle user approval/rejection
    
    # For demo, return mock signature
    mock_signature = f"0x{hashlib.sha256(f'{user.public_address}{transaction_data}'.encode()).hexdigest()}"
    
    self._signing_sessions[signing_id]["status"] = "signed"
    self._signing_sessions[signing_id]["signature"] = mock_signature
    
    return mock_signature
  
  async def verify_signature(
    self,
    address: str,
    message: str,
    signature: str
  ) -> bool:
    """Verify signature from address."""
    # In production, would use web3.py or ethers.js to verify
    # For demo, check format
    return (
      signature.startswith("0x") and
      len(signature) == 66 and
      address.startswith("0x") and
      len(address) == 42
    )
  
  def get_pending_signatures(self) -> List[Dict[str, Any]]:
    """Get all pending signature requests."""
    pending = []
    for sig_id, session in self._signing_sessions.items():
      if session["status"] == "pending":
        pending.append({
          "id": sig_id,
          "user_address": session["user_address"],
          "message": session["message"],
          "created_at": session["created_at"].isoformat()
        })
    return pending


class Web3AuthTreasuryIntegration:
  """Integration between Web3Auth and blockchain treasury."""
  
  def __init__(
    self,
    blockchain_treasury: Any,  # BlockchainTreasury instance
    web3auth_config: Web3AuthConfig
  ):
    self.treasury = blockchain_treasury
    self.web3auth = Web3AuthClient(web3auth_config)
    self.signer = Web3AuthBlockchainSigner(self.web3auth)
    self._authorized_signers: Dict[str, Web3AuthUser] = {}
  
  async def authorize_signer(
    self,
    email: str,
    pillar: str,
    role: str = "signer"
  ) -> Dict[str, Any]:
    """Authorize a new signer for a pillar using Web3Auth."""
    # Initialize auth session
    auth_session = await self.web3auth.init_auth_session(email)
    
    return {
      "auth_url": auth_session["auth_url"],
      "session_id": auth_session["session_id"],
      "pillar": pillar,
      "role": role,
      "status": "pending_authentication"
    }
  
  async def complete_signer_authorization(
    self,
    callback_params: Dict[str, str],
    pillar: str
  ) -> bool:
    """Complete signer authorization after Web3Auth callback."""
    # Handle callback
    user = await self.web3auth.handle_auth_callback(callback_params)
    if not user:
      return False
    
    # Add to authorized signers
    self._authorized_signers[user.public_address] = user
    
    # Update treasury wallet configuration
    wallet = self.treasury.wallets.get(pillar)
    if wallet and user.public_address not in wallet.owners:
      wallet.owners.append(user.public_address)
      logger.info(f"Added {user.email} as signer for {pillar}")
    
    return True
  
  async def sign_transaction_web3auth(
    self,
    blockchain_tx_id: str,
    session_id: str
  ) -> bool:
    """Sign a blockchain transaction using Web3Auth."""
    # Get user
    user = await self.web3auth.get_user_info(session_id)
    if not user:
      logger.error("User session not found")
      return False
    
    # Get transaction
    blockchain_tx = self.treasury.blockchain_txs.get(blockchain_tx_id)
    if not blockchain_tx:
      logger.error("Transaction not found")
      return False
    
    # Verify user is authorized for this pillar
    pillar = self.treasury._get_pillar_from_wallet(blockchain_tx.wallet_address)
    wallet = self.treasury.wallets.get(pillar)
    
    if not wallet or user.public_address not in wallet.owners:
      logger.error(f"User {user.email} not authorized for {pillar}")
      return False
    
    # Request signature
    tx_data = {
      "to": blockchain_tx.to_address,
      "value": blockchain_tx.amount,
      "data": blockchain_tx.data or "0x"
    }
    
    signature = await self.signer.request_signature(
      session_id,
      tx_data,
      f"Approve ${blockchain_tx.amount} transfer for {pillar}"
    )
    
    if signature:
      # Use treasury's sign method
      return await self.treasury.sign_transaction(
        blockchain_tx_id,
        user.public_address
      )
    
    return False
  
  async def get_signer_dashboard(
    self,
    session_id: str
  ) -> Dict[str, Any]:
    """Get signer dashboard with pending transactions."""
    user = await self.web3auth.get_user_info(session_id)
    if not user:
      return {"error": "Session not found"}
    
    # Find pillars user can sign for
    authorized_pillars = []
    for pillar, wallet in self.treasury.wallets.items():
      if user.public_address in wallet.owners:
        authorized_pillars.append(pillar)
    
    # Get pending transactions for those pillars
    pending_txs = []
    for tx in self.treasury.blockchain_txs.values():
      if tx.status == "pending":
        pillar = self.treasury._get_pillar_from_wallet(tx.wallet_address)
        if pillar in authorized_pillars:
          # Check if user already signed
          user_signed = user.public_address in tx.signatures
          pending_txs.append({
            "id": tx.id,
            "pillar": pillar,
            "amount": tx.amount,
            "description": f"Treasury TX: {tx.treasury_tx_id}",
            "signatures": len(tx.signatures),
            "required": tx.required_signatures,
            "user_signed": user_signed,
            "can_sign": not user_signed
          })
    
    return {
      "user": {
        "email": user.email,
        "name": user.name,
        "address": user.public_address,
        "profile_image": user.profile_image
      },
      "authorized_pillars": authorized_pillars,
      "pending_transactions": pending_txs,
      "stats": {
        "total_pending": len(pending_txs),
        "awaiting_signature": len([t for t in pending_txs if t["can_sign"]])
      }
    }
  
  async def enable_social_recovery(
    self,
    session_id: str,
    recovery_emails: List[str]
  ) -> bool:
    """Enable social recovery for a signer using Web3Auth."""
    user = await self.web3auth.get_user_info(session_id)
    if not user:
      return False
    
    # In production, would:
    # 1. Use Web3Auth's social recovery feature
    # 2. Set up guardian accounts
    # 3. Configure recovery threshold
    
    logger.info(f"Social recovery configured for {user.email}")
    return True
  
  async def close(self):
    """Clean up resources."""
    await self.web3auth.close()


# Example configuration
def create_web3auth_config(
  client_id: str,
  environment: str = "testnet"
) -> Web3AuthConfig:
  """Create Web3Auth configuration."""
  return Web3AuthConfig(
    client_id=client_id,
    network=Web3AuthNetwork.TESTNET if environment == "testnet" else Web3AuthNetwork.MAINNET,
    redirect_url="http://localhost:8000/auth/callback",
    whitelist_urls=["http://localhost:8000", "http://localhost:3000"],
    login_provider=AuthProvider.GOOGLE,
    chain_namespace="eip155",
    chain_id="0x1" if environment == "mainnet" else "0x5",  # Goerli for testnet
    display_name="ADK Control Plane Treasury",
    custom_auth_args={
      "prompt": "select_account",
      "access_type": "offline",
      "response_type": "code id_token"
    }
  )