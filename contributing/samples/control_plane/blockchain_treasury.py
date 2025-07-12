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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WalletType(Enum):
  """Types of blockchain wallets."""
  GNOSIS_SAFE = "gnosis_safe"
  ETHEREUM_MULTISIG = "ethereum_multisig"
  MOCK = "mock"  # For testing without blockchain


class TransactionType(Enum):
  """Types of blockchain transactions."""
  TRANSFER = "transfer"
  CONTRACT_CALL = "contract_call"
  APPROVAL = "approval"
  REJECTION = "rejection"


@dataclass
class BlockchainTransaction:
  """Blockchain transaction representation."""
  id: str
  treasury_tx_id: str  # Link to treasury transaction
  wallet_address: str
  to_address: str
  amount: float
  gas_limit: Optional[int] = None
  nonce: Optional[int] = None
  data: Optional[str] = None
  tx_type: TransactionType = TransactionType.TRANSFER
  created_at: datetime = field(default_factory=datetime.now)
  confirmed_at: Optional[datetime] = None
  block_number: Optional[int] = None
  tx_hash: Optional[str] = None
  status: str = "pending"
  signatures: List[str] = field(default_factory=list)
  required_signatures: int = 1


@dataclass
class MultisigWallet:
  """Multisig wallet configuration."""
  address: str
  name: str
  wallet_type: WalletType
  owners: List[str]  # Ethereum addresses of owners
  required_confirmations: int
  daily_limit: float
  daily_spent: float = 0.0
  last_reset: datetime = field(default_factory=datetime.now)
  
  def can_spend(self, amount: float) -> bool:
    """Check if wallet can spend amount within daily limit."""
    # Reset daily counter if needed
    if (datetime.now() - self.last_reset).days >= 1:
      self.daily_spent = 0.0
      self.last_reset = datetime.now()
    
    return self.daily_spent + amount <= self.daily_limit
  
  def record_spending(self, amount: float):
    """Record spending against daily limit."""
    self.daily_spent += amount


class BlockchainConnector(ABC):
  """Abstract base class for blockchain connections."""
  
  @abstractmethod
  async def get_balance(self, address: str) -> float:
    """Get wallet balance."""
    pass
  
  @abstractmethod
  async def submit_transaction(self, tx: BlockchainTransaction) -> str:
    """Submit transaction to blockchain."""
    pass
  
  @abstractmethod
  async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
    """Get transaction status from blockchain."""
    pass
  
  @abstractmethod
  async def sign_transaction(self, tx: BlockchainTransaction, signer: str) -> str:
    """Sign a transaction."""
    pass


class MockBlockchainConnector(BlockchainConnector):
  """Mock blockchain connector for testing."""
  
  def __init__(self):
    self.balances: Dict[str, float] = {}
    self.transactions: Dict[str, BlockchainTransaction] = {}
    self.pending_signatures: Dict[str, Set[str]] = {}
  
  async def get_balance(self, address: str) -> float:
    """Get mock wallet balance."""
    return self.balances.get(address, 10000.0)  # Default balance
  
  async def submit_transaction(self, tx: BlockchainTransaction) -> str:
    """Submit mock transaction."""
    # Generate mock tx hash
    tx_hash = hashlib.sha256(
      f"{tx.id}{tx.wallet_address}{tx.to_address}{tx.amount}".encode()
    ).hexdigest()[:66]
    
    tx.tx_hash = tx_hash
    tx.status = "submitted"
    self.transactions[tx_hash] = tx
    
    # Auto-confirm small transactions
    if tx.amount < 100:
      tx.status = "confirmed"
      tx.confirmed_at = datetime.now()
      tx.block_number = 12345678
    
    return tx_hash
  
  async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
    """Get mock transaction status."""
    tx = self.transactions.get(tx_hash)
    if not tx:
      return {"status": "not_found"}
    
    return {
      "status": tx.status,
      "confirmations": 12 if tx.status == "confirmed" else 0,
      "block_number": tx.block_number,
      "gas_used": 21000,
    }
  
  async def sign_transaction(self, tx: BlockchainTransaction, signer: str) -> str:
    """Sign a mock transaction."""
    # Generate mock signature
    signature = hashlib.sha256(
      f"{tx.tx_hash}{signer}".encode()
    ).hexdigest()
    
    if tx.tx_hash not in self.pending_signatures:
      self.pending_signatures[tx.tx_hash] = set()
    
    self.pending_signatures[tx.tx_hash].add(signer)
    tx.signatures.append(signature)
    
    # Check if we have enough signatures
    if len(tx.signatures) >= tx.required_signatures:
      tx.status = "ready_to_execute"
    
    return signature


class GnosisSafeConnector(BlockchainConnector):
  """Gnosis Safe connector for production use."""
  
  def __init__(self, rpc_url: str, safe_address: str):
    self.rpc_url = rpc_url
    self.safe_address = safe_address
    # In production, would use web3.py or similar
    logger.info(f"Gnosis Safe connector initialized for {safe_address}")
  
  async def get_balance(self, address: str) -> float:
    """Get wallet balance from blockchain."""
    # Placeholder - would call actual blockchain
    logger.warning("Using mock balance for Gnosis Safe")
    return 10000.0
  
  async def submit_transaction(self, tx: BlockchainTransaction) -> str:
    """Submit transaction to Gnosis Safe."""
    # Placeholder - would interact with Gnosis Safe API
    logger.warning("Mock submission to Gnosis Safe")
    return f"0x{'0' * 64}"
  
  async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
    """Get transaction status from blockchain."""
    # Placeholder
    return {"status": "pending", "confirmations": 0}
  
  async def sign_transaction(self, tx: BlockchainTransaction, signer: str) -> str:
    """Sign transaction with Gnosis Safe."""
    # Placeholder
    return f"0x{'1' * 130}"


class BlockchainTreasury:
  """Enhanced treasury with blockchain integration."""
  
  def __init__(
    self,
    treasury: Any,  # Original treasury instance
    connector: Optional[BlockchainConnector] = None,
    default_wallet_type: WalletType = WalletType.MOCK
  ):
    self.treasury = treasury
    self.connector = connector or MockBlockchainConnector()
    self.default_wallet_type = default_wallet_type
    self.wallets: Dict[str, MultisigWallet] = {}
    self.blockchain_txs: Dict[str, BlockchainTransaction] = {}
    self.emergency_wallet: Optional[str] = None
    self._init_default_wallets()
  
  def _init_default_wallets(self):
    """Initialize default multisig wallets for each pillar."""
    # Default signers (in production, would be actual addresses)
    default_signers = [
      "0x1111111111111111111111111111111111111111",
      "0x2222222222222222222222222222222222222222",
      "0x3333333333333333333333333333333333333333",
      "0x4444444444444444444444444444444444444444",
    ]
    
    # Create wallets for each pillar
    for pillar in self.treasury.pillar_budgets.keys():
      wallet_address = f"0x{hashlib.sha256(pillar.encode()).hexdigest()[:40]}"
      
      # Determine required signatures based on pillar
      if pillar == "Mission & Governance":
        required_sigs = 3  # High security
      elif pillar in ["Growth Engine", "Customer Success"]:
        required_sigs = 2  # Medium security
      else:
        required_sigs = 1  # Standard security
      
      wallet = MultisigWallet(
        address=wallet_address,
        name=f"{pillar} Wallet",
        wallet_type=self.default_wallet_type,
        owners=default_signers[:4],
        required_confirmations=required_sigs,
        daily_limit=self.treasury.pillar_budgets[pillar].spending_limit.daily_limit
      )
      
      self.wallets[pillar] = wallet
    
    # Emergency wallet with all signers required
    self.emergency_wallet = "0xEMERGENCY1111111111111111111111111111111"
    self.wallets["EMERGENCY"] = MultisigWallet(
      address=self.emergency_wallet,
      name="Emergency Recovery Wallet",
      wallet_type=self.default_wallet_type,
      owners=default_signers,
      required_confirmations=4,  # All signers required
      daily_limit=float('inf')  # No limit for emergency
    )
  
  async def create_blockchain_transaction(
    self,
    treasury_tx_id: str,
    pillar: str,
    amount: float,
    recipient: str,
    metadata: Optional[Dict[str, Any]] = None
  ) -> BlockchainTransaction:
    """Create a blockchain transaction for treasury transaction."""
    wallet = self.wallets.get(pillar)
    if not wallet:
      raise ValueError(f"No wallet configured for pillar: {pillar}")
    
    # Check wallet daily limit
    if not wallet.can_spend(amount):
      raise ValueError(
        f"Transaction exceeds wallet daily limit. "
        f"Available: ${wallet.daily_limit - wallet.daily_spent:.2f}"
      )
    
    # Determine required signatures based on amount
    if amount >= 10000:  # High value requires more signatures
      required_sigs = min(len(wallet.owners), wallet.required_confirmations + 1)
    else:
      required_sigs = wallet.required_confirmations
    
    # Create blockchain transaction
    blockchain_tx = BlockchainTransaction(
      id=f"btx_{datetime.now().timestamp()}",
      treasury_tx_id=treasury_tx_id,
      wallet_address=wallet.address,
      to_address=recipient,
      amount=amount,
      required_signatures=required_sigs,
      data=json.dumps(metadata) if metadata else None
    )
    
    self.blockchain_txs[blockchain_tx.id] = blockchain_tx
    return blockchain_tx
  
  async def execute_transaction(
    self,
    treasury_tx_id: str,
    pillar: str,
    amount: float,
    recipient: str = "0x0000000000000000000000000000000000000000"
  ) -> BlockchainTransaction:
    """Execute a treasury transaction on blockchain."""
    # Create blockchain transaction
    blockchain_tx = await self.create_blockchain_transaction(
      treasury_tx_id=treasury_tx_id,
      pillar=pillar,
      amount=amount,
      recipient=recipient
    )
    
    # For low-value transactions with single sig requirement, auto-sign
    if blockchain_tx.required_signatures == 1 and amount < 100:
      wallet = self.wallets[pillar]
      signature = await self.connector.sign_transaction(
        blockchain_tx,
        wallet.owners[0]  # Use first owner for auto-sign
      )
      blockchain_tx.signatures.append(signature)
    
    # Submit to blockchain if signatures complete
    if len(blockchain_tx.signatures) >= blockchain_tx.required_signatures:
      tx_hash = await self.connector.submit_transaction(blockchain_tx)
      blockchain_tx.tx_hash = tx_hash
      
      # Update wallet spending
      wallet = self.wallets[pillar]
      wallet.record_spending(amount)
    
    return blockchain_tx
  
  async def sign_transaction(
    self,
    blockchain_tx_id: str,
    signer_address: str
  ) -> bool:
    """Add signature to a pending blockchain transaction."""
    blockchain_tx = self.blockchain_txs.get(blockchain_tx_id)
    if not blockchain_tx:
      return False
    
    # Verify signer is authorized
    pillar = self._get_pillar_from_wallet(blockchain_tx.wallet_address)
    wallet = self.wallets.get(pillar)
    if not wallet or signer_address not in wallet.owners:
      logger.warning(f"Unauthorized signer: {signer_address}")
      return False
    
    # Add signature
    signature = await self.connector.sign_transaction(
      blockchain_tx,
      signer_address
    )
    
    # Submit if we have enough signatures
    if len(blockchain_tx.signatures) >= blockchain_tx.required_signatures:
      tx_hash = await self.connector.submit_transaction(blockchain_tx)
      blockchain_tx.tx_hash = tx_hash
      blockchain_tx.status = "submitted"
      
      # Update wallet spending
      wallet.record_spending(blockchain_tx.amount)
      
      # Update treasury transaction
      treasury_tx = next(
        (t for t in self.treasury.transaction_history 
         if t.id == blockchain_tx.treasury_tx_id),
        None
      )
      if treasury_tx:
        treasury_tx.metadata["blockchain_tx_hash"] = tx_hash
    
    return True
  
  def _get_pillar_from_wallet(self, wallet_address: str) -> Optional[str]:
    """Get pillar name from wallet address."""
    for pillar, wallet in self.wallets.items():
      if wallet.address == wallet_address:
        return pillar
    return None
  
  async def check_transaction_status(self, blockchain_tx_id: str) -> Dict[str, Any]:
    """Check status of a blockchain transaction."""
    blockchain_tx = self.blockchain_txs.get(blockchain_tx_id)
    if not blockchain_tx or not blockchain_tx.tx_hash:
      return {"status": "not_found"}
    
    # Get status from blockchain
    status = await self.connector.get_transaction_status(blockchain_tx.tx_hash)
    
    # Update local record if confirmed
    if status.get("confirmations", 0) >= 12:
      blockchain_tx.status = "confirmed"
      blockchain_tx.confirmed_at = datetime.now()
      blockchain_tx.block_number = status.get("block_number")
    
    return status
  
  async def emergency_pause(self, reason: str) -> bool:
    """Emergency pause all blockchain operations."""
    logger.critical(f"EMERGENCY PAUSE INITIATED: {reason}")
    
    # In production, would:
    # 1. Pause all smart contracts
    # 2. Transfer funds to emergency wallet
    # 3. Notify all signers
    # 4. Create audit entry
    
    # For now, mark all wallets as paused
    for wallet in self.wallets.values():
      wallet.daily_limit = 0  # Effective pause
    
    # Create emergency audit entry
    self.treasury.transaction_history.append(
      self.treasury.Transaction(
        id=f"emergency_{datetime.now().timestamp()}",
        agent_name="SYSTEM",
        pillar="EMERGENCY",
        amount=0,
        description=f"Emergency pause: {reason}",
        status=self.treasury.TransactionStatus.EXECUTED,
        metadata={"type": "emergency_pause", "timestamp": datetime.now().isoformat()}
      )
    )
    
    return True
  
  async def get_wallet_summary(self) -> Dict[str, Any]:
    """Get summary of all blockchain wallets."""
    summary = {
      "total_wallets": len(self.wallets) - 1,  # Exclude emergency
      "wallets": {},
      "pending_transactions": 0,
      "daily_limits": {}
    }
    
    for pillar, wallet in self.wallets.items():
      if pillar == "EMERGENCY":
        continue
        
      # Get balance from blockchain
      balance = await self.connector.get_balance(wallet.address)
      
      summary["wallets"][pillar] = {
        "address": wallet.address,
        "balance": balance,
        "owners": len(wallet.owners),
        "required_signatures": wallet.required_confirmations,
        "daily_spent": wallet.daily_spent,
        "daily_remaining": wallet.daily_limit - wallet.daily_spent
      }
      
      summary["daily_limits"][pillar] = wallet.daily_limit
    
    # Count pending transactions
    for tx in self.blockchain_txs.values():
      if tx.status == "pending":
        summary["pending_transactions"] += 1
    
    return summary
  
  def get_pending_signatures(self) -> List[Dict[str, Any]]:
    """Get all transactions pending signatures."""
    pending = []
    
    for tx in self.blockchain_txs.values():
      if tx.status == "pending" and len(tx.signatures) < tx.required_signatures:
        pillar = self._get_pillar_from_wallet(tx.wallet_address)
        pending.append({
          "id": tx.id,
          "treasury_tx_id": tx.treasury_tx_id,
          "pillar": pillar,
          "amount": tx.amount,
          "signatures": len(tx.signatures),
          "required": tx.required_signatures,
          "created_at": tx.created_at.isoformat(),
          "wallet": tx.wallet_address
        })
    
    return pending


class SmartContractTreasury(BlockchainTreasury):
  """Advanced treasury using smart contracts for policy enforcement."""
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.contract_address: Optional[str] = None
    self.policy_contract: Optional[str] = None
  
  async def deploy_treasury_contract(self, initial_policies: List[Dict[str, Any]]) -> str:
    """Deploy treasury smart contract with policies."""
    # In production, would deploy actual smart contract
    # with embedded policy rules
    
    contract_data = {
      "type": "TreasuryContract",
      "version": "1.0.0",
      "policies": initial_policies,
      "wallets": {
        pillar: wallet.address 
        for pillar, wallet in self.wallets.items()
      },
      "deployed_at": datetime.now().isoformat()
    }
    
    # Mock contract deployment
    self.contract_address = f"0x{hashlib.sha256(json.dumps(contract_data).encode()).hexdigest()[:40]}"
    logger.info(f"Treasury contract deployed at: {self.contract_address}")
    
    return self.contract_address
  
  async def update_on_chain_policy(self, policy_rule: Dict[str, Any]) -> bool:
    """Update policy rules in smart contract."""
    # In production, would call smart contract method
    # to update on-chain policies
    
    logger.info(f"Updating on-chain policy: {policy_rule.get('name')}")
    
    # Mock policy update transaction
    policy_tx = BlockchainTransaction(
      id=f"policy_{datetime.now().timestamp()}",
      treasury_tx_id="POLICY_UPDATE",
      wallet_address=self.wallets["Mission & Governance"].address,
      to_address=self.contract_address or "0x0",
      amount=0,
      tx_type=TransactionType.CONTRACT_CALL,
      data=json.dumps(policy_rule),
      required_signatures=3  # Policy updates require multiple approvals
    )
    
    self.blockchain_txs[policy_tx.id] = policy_tx
    return True