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

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
  """Status of a treasury transaction."""
  PENDING = "pending"
  APPROVED = "approved"
  REJECTED = "rejected"
  EXECUTED = "executed"
  FAILED = "failed"


class ApprovalRequirement(Enum):
  """Types of approval requirements."""
  NONE = "none"
  SINGLE = "single"
  MULTISIG = "multisig"
  TREASURY_BOARD = "treasury_board"


@dataclass
class SpendingLimit:
  """Spending limit configuration."""
  daily_limit: float
  monthly_limit: float
  per_transaction_limit: float
  approval_threshold: float  # Transactions above this require approval
  multisig_threshold: float  # Transactions above this require multisig


@dataclass
class Transaction:
  """Treasury transaction record."""
  id: str
  agent_name: str
  pillar: str
  amount: float
  description: str
  timestamp: datetime = field(default_factory=datetime.now)
  status: TransactionStatus = TransactionStatus.PENDING
  approval_requirement: ApprovalRequirement = ApprovalRequirement.NONE
  approvers: List[str] = field(default_factory=list)
  metadata: Dict[str, Any] = field(default_factory=dict)
  
  def requires_approval(self, limit: SpendingLimit) -> ApprovalRequirement:
    """Determine approval requirement based on amount."""
    if self.amount >= limit.multisig_threshold:
      return ApprovalRequirement.MULTISIG
    elif self.amount >= limit.approval_threshold:
      return ApprovalRequirement.SINGLE
    return ApprovalRequirement.NONE


class PillarBudget(BaseModel):
  """Budget allocation for a business pillar."""
  pillar: str
  total_budget: float
  spent: float = 0.0
  reserved: float = 0.0  # Pending transactions
  spending_limit: SpendingLimit
  transactions: List[Transaction] = Field(default_factory=list)
  
  @property
  def available(self) -> float:
    """Calculate available budget."""
    return self.total_budget - self.spent - self.reserved
  
  def can_afford(self, amount: float) -> bool:
    """Check if pillar can afford a transaction."""
    return self.available >= amount


class Treasury:
  """Treasury management for budget caps and spending controls."""
  
  def __init__(
    self,
    total_budget: float,
    default_daily_limit: float = 10000.0,
    default_approval_threshold: float = 1000.0,
    default_multisig_threshold: float = 10000.0
  ):
    self.total_budget = total_budget
    self.pillar_budgets: Dict[str, PillarBudget] = {}
    self.default_spending_limit = SpendingLimit(
      daily_limit=default_daily_limit,
      monthly_limit=default_daily_limit * 30,
      per_transaction_limit=default_daily_limit,
      approval_threshold=default_approval_threshold,
      multisig_threshold=default_multisig_threshold
    )
    self.pending_approvals: Dict[str, Transaction] = {}
    self.transaction_history: List[Transaction] = []
    self._init_default_budgets()
  
  def _init_default_budgets(self):
    """Initialize default budget allocations by pillar."""
    # Default allocation percentages
    allocations = {
      "Mission & Governance": 0.05,
      "Product & Experience": 0.25,
      "Growth Engine": 0.20,
      "Customer Success": 0.15,
      "Resource & Supply": 0.15,
      "People & Culture": 0.10,
      "Intelligence & Improvement": 0.05,
      "Platform & Infra": 0.05,
    }
    
    for pillar, percentage in allocations.items():
      budget = PillarBudget(
        pillar=pillar,
        total_budget=self.total_budget * percentage,
        spending_limit=self.default_spending_limit
      )
      self.pillar_budgets[pillar] = budget
  
  def request_transaction(
    self,
    agent_name: str,
    pillar: str,
    amount: float,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
  ) -> Transaction:
    """Request a new transaction."""
    # Create transaction
    transaction = Transaction(
      id=f"txn_{datetime.now().timestamp()}",
      agent_name=agent_name,
      pillar=pillar,
      amount=amount,
      description=description,
      metadata=metadata or {}
    )
    
    # Get pillar budget
    budget = self.pillar_budgets.get(pillar)
    if not budget:
      transaction.status = TransactionStatus.REJECTED
      transaction.metadata["rejection_reason"] = f"Unknown pillar: {pillar}"
      return transaction
    
    # Check if budget allows
    if not budget.can_afford(amount):
      transaction.status = TransactionStatus.REJECTED
      transaction.metadata["rejection_reason"] = "Insufficient budget"
      transaction.metadata["available_budget"] = budget.available
      return transaction
    
    # Check daily spending limit
    daily_spent = self._calculate_daily_spending(pillar)
    if daily_spent + amount > budget.spending_limit.daily_limit:
      transaction.status = TransactionStatus.REJECTED
      transaction.metadata["rejection_reason"] = "Daily spending limit exceeded"
      transaction.metadata["daily_limit"] = budget.spending_limit.daily_limit
      transaction.metadata["daily_spent"] = daily_spent
      return transaction
    
    # Determine approval requirement
    transaction.approval_requirement = transaction.requires_approval(
      budget.spending_limit
    )
    
    if transaction.approval_requirement == ApprovalRequirement.NONE:
      # Auto-approve small transactions
      transaction.status = TransactionStatus.APPROVED
      self._execute_transaction(transaction)
    else:
      # Reserve funds for pending transaction
      budget.reserved += amount
      self.pending_approvals[transaction.id] = transaction
      transaction.metadata["approval_required"] = True
    
    budget.transactions.append(transaction)
    self.transaction_history.append(transaction)
    
    return transaction
  
  def approve_transaction(
    self,
    transaction_id: str,
    approver: str
  ) -> bool:
    """Approve a pending transaction."""
    transaction = self.pending_approvals.get(transaction_id)
    if not transaction:
      return False
    
    transaction.approvers.append(approver)
    
    # Check if approval requirements are met
    if transaction.approval_requirement == ApprovalRequirement.SINGLE:
      transaction.status = TransactionStatus.APPROVED
      self._execute_transaction(transaction)
      del self.pending_approvals[transaction_id]
      return True
    elif transaction.approval_requirement == ApprovalRequirement.MULTISIG:
      # Require at least 2 approvers for multisig
      if len(transaction.approvers) >= 2:
        transaction.status = TransactionStatus.APPROVED
        self._execute_transaction(transaction)
        del self.pending_approvals[transaction_id]
        return True
    
    return False
  
  def reject_transaction(
    self,
    transaction_id: str,
    reason: str
  ) -> bool:
    """Reject a pending transaction."""
    transaction = self.pending_approvals.get(transaction_id)
    if not transaction:
      return False
    
    transaction.status = TransactionStatus.REJECTED
    transaction.metadata["rejection_reason"] = reason
    
    # Release reserved funds
    budget = self.pillar_budgets.get(transaction.pillar)
    if budget:
      budget.reserved -= transaction.amount
    
    del self.pending_approvals[transaction_id]
    return True
  
  def _execute_transaction(self, transaction: Transaction):
    """Execute an approved transaction."""
    budget = self.pillar_budgets.get(transaction.pillar)
    if not budget:
      transaction.status = TransactionStatus.FAILED
      return
    
    # Update budget
    if transaction.status == TransactionStatus.APPROVED:
      budget.spent += transaction.amount
      if transaction.amount <= budget.reserved:
        budget.reserved -= transaction.amount
      transaction.status = TransactionStatus.EXECUTED
  
  def _calculate_daily_spending(self, pillar: str) -> float:
    """Calculate spending for a pillar in the last 24 hours."""
    budget = self.pillar_budgets.get(pillar)
    if not budget:
      return 0.0
    
    cutoff = datetime.now() - timedelta(days=1)
    daily_transactions = [
      t for t in budget.transactions
      if t.timestamp >= cutoff and t.status == TransactionStatus.EXECUTED
    ]
    
    return sum(t.amount for t in daily_transactions)
  
  def get_budget_summary(self) -> Dict[str, Any]:
    """Get summary of all budgets."""
    summary = {
      "total_budget": self.total_budget,
      "total_spent": sum(b.spent for b in self.pillar_budgets.values()),
      "total_reserved": sum(b.reserved for b in self.pillar_budgets.values()),
      "pillars": {}
    }
    
    for pillar, budget in self.pillar_budgets.items():
      summary["pillars"][pillar] = {
        "budget": budget.total_budget,
        "spent": budget.spent,
        "reserved": budget.reserved,
        "available": budget.available,
        "utilization": (budget.spent / budget.total_budget * 100) if budget.total_budget > 0 else 0
      }
    
    return summary
  
  def get_pending_approvals(
    self,
    pillar: Optional[str] = None
  ) -> List[Transaction]:
    """Get list of pending approvals."""
    pending = list(self.pending_approvals.values())
    if pillar:
      pending = [t for t in pending if t.pillar == pillar]
    return pending
  
  def update_spending_limit(
    self,
    pillar: str,
    **kwargs
  ):
    """Update spending limits for a pillar."""
    budget = self.pillar_budgets.get(pillar)
    if not budget:
      return
    
    limit = budget.spending_limit
    for key, value in kwargs.items():
      if hasattr(limit, key):
        setattr(limit, key, value)
  
  def export_audit_log(
    self,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
  ) -> List[Dict[str, Any]]:
    """Export audit log of transactions."""
    transactions = self.transaction_history
    
    if start_date:
      transactions = [t for t in transactions if t.timestamp >= start_date]
    if end_date:
      transactions = [t for t in transactions if t.timestamp <= end_date]
    
    return [
      {
        "id": t.id,
        "timestamp": t.timestamp.isoformat(),
        "agent": t.agent_name,
        "pillar": t.pillar,
        "amount": t.amount,
        "description": t.description,
        "status": t.status.value,
        "approvers": t.approvers,
        "metadata": t.metadata
      }
      for t in transactions
    ]