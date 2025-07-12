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

"""Customer Success Pillar - Delight, support and retain users."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep

logger = logging.getLogger(__name__)


class SupportResponder(BusinessPillarAgent):
  """Agent responsible for customer support and issue resolution."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="support_responder",
      role=AgentRole.WORKER,
      pillar=PillarType.CUSTOMER_SUCCESS,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup support tools."""
    self.register_tool("create_ticket", self._create_ticket, cost=0.5)
    self.register_tool("respond_to_ticket", self._respond_to_ticket, cost=1.0)
    self.register_tool("escalate_ticket", self._escalate_ticket, cost=0.3)
    self.register_tool("close_ticket", self._close_ticket, cost=0.2)
    self.register_tool("search_knowledge_base", self._search_knowledge_base, cost=0.4)
    self.register_tool("update_customer_health", self._update_customer_health, cost=0.6)
  
  async def _create_ticket(
    self,
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    category: str = "general"
  ) -> Dict[str, Any]:
    """Create a new support ticket."""
    ticket_id = f"TIK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Auto-assign priority based on keywords
    urgent_keywords = ["urgent", "critical", "down", "broken", "error", "cannot", "unable"]
    if any(keyword in description.lower() for keyword in urgent_keywords):
      priority = "high"
    
    # Categorize based on content
    category_keywords = {
      "billing": ["payment", "invoice", "billing", "charge", "refund"],
      "technical": ["bug", "error", "api", "integration", "code"],
      "account": ["login", "password", "access", "permissions", "user"]
    }
    
    for cat, keywords in category_keywords.items():
      if any(keyword in description.lower() for keyword in keywords):
        category = cat
        break
    
    # SLA calculation
    sla_hours = {"high": 4, "medium": 24, "low": 72}
    response_sla = datetime.now() + timedelta(hours=sla_hours.get(priority, 24))
    
    ticket = {
      "ticket_id": ticket_id,
      "customer_id": customer_id,
      "subject": subject,
      "description": description,
      "priority": priority,
      "category": category,
      "status": "open",
      "created_at": datetime.now().isoformat(),
      "response_sla": response_sla.isoformat(),
      "assigned_to": "auto-responder",
      "tags": self._extract_tags(description)
    }
    
    return ticket
  
  def _extract_tags(self, description: str) -> List[str]:
    """Extract relevant tags from ticket description."""
    tags = []
    
    # Product tags
    if "api" in description.lower():
      tags.append("api")
    if "dashboard" in description.lower():
      tags.append("dashboard")
    if "mobile" in description.lower():
      tags.append("mobile")
    
    # Issue type tags
    if "slow" in description.lower() or "performance" in description.lower():
      tags.append("performance")
    if "bug" in description.lower() or "error" in description.lower():
      tags.append("bug")
    
    return tags
  
  async def _respond_to_ticket(
    self,
    ticket_id: str,
    response_type: str = "initial",
    custom_message: Optional[str] = None
  ) -> Dict[str, Any]:
    """Generate and send response to a ticket."""
    # Knowledge base search for relevant solutions
    kb_results = await self._search_knowledge_base(ticket_id)
    
    if response_type == "initial":
      if kb_results["relevant_articles"]:
        message = f"""Thank you for contacting support. I found some resources that might help:

{kb_results['suggested_response']}

If this doesn't resolve your issue, I'll investigate further and get back to you within our SLA timeframe.

Best regards,
Customer Support Team"""
      else:
        message = """Thank you for contacting support. I've received your request and am looking into it. 
        
I'll provide an update within our SLA timeframe. If this is urgent, please let me know.

Best regards,
Customer Support Team"""
    
    elif response_type == "solution":
      message = custom_message or "I've found a solution to your issue. Please try the following steps..."
    
    elif response_type == "escalation":
      message = """I'm escalating your ticket to our specialist team for further investigation. 
      
They will reach out to you directly within the next business day.

Thank you for your patience."""
    
    else:
      message = custom_message or "Thank you for your patience while we investigate this issue."
    
    response = {
      "ticket_id": ticket_id,
      "response_type": response_type,
      "message": message,
      "sent_at": datetime.now().isoformat(),
      "knowledge_base_used": len(kb_results.get("relevant_articles", [])) > 0,
      "estimated_resolution_time": self._estimate_resolution_time(response_type)
    }
    
    return response
  
  def _estimate_resolution_time(self, response_type: str) -> str:
    """Estimate resolution time based on response type."""
    estimates = {
      "initial": "Within SLA timeframe",
      "solution": "Immediate",
      "escalation": "1-2 business days",
      "follow_up": "24-48 hours"
    }
    return estimates.get(response_type, "Under investigation")
  
  async def _escalate_ticket(
    self,
    ticket_id: str,
    escalation_reason: str,
    target_team: str = "tier2"
  ) -> Dict[str, Any]:
    """Escalate ticket to higher support tier."""
    escalation_data = {
      "ticket_id": ticket_id,
      "escalated_to": target_team,
      "escalation_reason": escalation_reason,
      "escalated_at": datetime.now().isoformat(),
      "escalated_by": "support_responder",
      "previous_attempts": 1,  # Mock data
      "customer_impact": self._assess_customer_impact(escalation_reason)
    }
    
    return escalation_data
  
  def _assess_customer_impact(self, reason: str) -> str:
    """Assess customer impact level."""
    high_impact_keywords = ["production", "critical", "revenue", "urgent"]
    medium_impact_keywords = ["feature", "functionality", "workflow"]
    
    reason_lower = reason.lower()
    
    if any(keyword in reason_lower for keyword in high_impact_keywords):
      return "high"
    elif any(keyword in reason_lower for keyword in medium_impact_keywords):
      return "medium"
    else:
      return "low"
  
  async def _close_ticket(
    self,
    ticket_id: str,
    resolution_summary: str,
    customer_satisfaction: Optional[int] = None
  ) -> Dict[str, Any]:
    """Close a support ticket."""
    closure_data = {
      "ticket_id": ticket_id,
      "status": "closed",
      "resolution_summary": resolution_summary,
      "closed_at": datetime.now().isoformat(),
      "resolution_time_hours": 8,  # Mock resolution time
      "customer_satisfaction_score": customer_satisfaction,
      "follow_up_required": customer_satisfaction and customer_satisfaction < 4
    }
    
    return closure_data
  
  async def _search_knowledge_base(
    self,
    query: str
  ) -> Dict[str, Any]:
    """Search knowledge base for relevant articles."""
    # Mock knowledge base search
    kb_articles = [
      {
        "article_id": "KB001",
        "title": "API Authentication Issues",
        "relevance_score": 0.85,
        "solution_steps": [
          "Check API key format",
          "Verify permissions",
          "Test with curl command"
        ]
      },
      {
        "article_id": "KB002", 
        "title": "Dashboard Loading Problems",
        "relevance_score": 0.72,
        "solution_steps": [
          "Clear browser cache",
          "Disable browser extensions", 
          "Try incognito mode"
        ]
      }
    ]
    
    # Filter relevant articles (mock relevance scoring)
    relevant_articles = [article for article in kb_articles if article["relevance_score"] > 0.7]
    
    if relevant_articles:
      top_article = relevant_articles[0]
      suggested_response = f"""Based on our knowledge base, this might be related to: {top_article['title']}

Try these steps:
{chr(10).join(f"• {step}" for step in top_article['solution_steps'])}

Article reference: {top_article['article_id']}"""
    else:
      suggested_response = "I'm researching this issue and will provide a detailed response shortly."
    
    return {
      "query": query,
      "relevant_articles": relevant_articles,
      "suggested_response": suggested_response,
      "search_timestamp": datetime.now().isoformat()
    }
  
  async def _update_customer_health(
    self,
    customer_id: str,
    health_impact: str,
    interaction_type: str = "support"
  ) -> Dict[str, Any]:
    """Update customer health score based on support interaction."""
    # Mock health score calculation
    current_health = 75  # Out of 100
    
    health_adjustments = {
      "positive": 5,
      "neutral": 0,
      "negative": -10,
      "critical": -20
    }
    
    adjustment = health_adjustments.get(health_impact, 0)
    new_health = max(0, min(100, current_health + adjustment))
    
    return {
      "customer_id": customer_id,
      "previous_health_score": current_health,
      "health_adjustment": adjustment,
      "new_health_score": new_health,
      "health_trend": "improving" if adjustment > 0 else "stable" if adjustment == 0 else "declining",
      "interaction_type": interaction_type,
      "updated_at": datetime.now().isoformat()
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute support tasks."""
    if task == "handle_new_ticket":
      # Create ticket
      ticket = await self._create_ticket(
        customer_id=context["customer_id"],
        subject=context["subject"],
        description=context["description"],
        priority=context.get("priority", "medium")
      )
      
      # Send initial response
      response = await self._respond_to_ticket(ticket["ticket_id"], "initial")
      
      # Update customer health
      health_update = await self._update_customer_health(
        customer_id=context["customer_id"],
        health_impact="neutral",  # Initial contact is neutral
        interaction_type="support_request"
      )
      
      return {
        "ticket": ticket,
        "initial_response": response,
        "health_update": health_update
      }
    
    elif task == "resolve_ticket":
      ticket_id = context["ticket_id"]
      resolution = context["resolution_summary"]
      
      # Send solution response
      response = await self._respond_to_ticket(
        ticket_id, 
        "solution", 
        context.get("solution_message")
      )
      
      # Close ticket
      closure = await self._close_ticket(
        ticket_id,
        resolution,
        context.get("satisfaction_score")
      )
      
      # Update customer health positively
      health_update = await self._update_customer_health(
        customer_id=context["customer_id"],
        health_impact="positive",
        interaction_type="issue_resolved"
      )
      
      return {
        "response": response,
        "closure": closure,
        "health_update": health_update
      }
    
    elif task == "escalate_complex_issue":
      escalation = await self._escalate_ticket(
        ticket_id=context["ticket_id"],
        escalation_reason=context["reason"],
        target_team=context.get("target_team", "tier2")
      )
      
      # Notify customer
      response = await self._respond_to_ticket(
        context["ticket_id"],
        "escalation"
      )
      
      return {
        "escalation": escalation,
        "customer_notification": response
      }
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get support responder capabilities."""
    return [
      "ticket_management",
      "automated_responses",
      "knowledge_base_search",
      "issue_escalation",
      "customer_health_tracking",
      "sla_management"
    ]


class RefundBot(BusinessPillarAgent):
  """Agent responsible for processing refunds and billing adjustments."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="refund_bot",
      role=AgentRole.WORKER,
      pillar=PillarType.CUSTOMER_SUCCESS,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup refund processing tools."""
    self.register_tool("process_refund", self._process_refund, cost=2.0)
    self.register_tool("validate_refund_eligibility", self._validate_refund_eligibility, cost=0.5)
    self.register_tool("calculate_refund_amount", self._calculate_refund_amount, cost=0.3)
    self.register_tool("notify_customer", self._notify_customer, cost=0.2)
    self.register_tool("update_billing_system", self._update_billing_system, cost=1.0)
  
  async def _validate_refund_eligibility(
    self,
    customer_id: str,
    transaction_id: str,
    refund_reason: str
  ) -> Dict[str, Any]:
    """Validate if a refund request is eligible."""
    # Mock transaction lookup
    transaction = {
      "transaction_id": transaction_id,
      "customer_id": customer_id,
      "amount": 299.99,
      "date": "2024-01-15T10:30:00Z",
      "product": "Professional Plan",
      "status": "completed"
    }
    
    # Calculate days since transaction
    transaction_date = datetime.fromisoformat(transaction["date"].replace('Z', '+00:00'))
    days_since = (datetime.now(transaction_date.tzinfo) - transaction_date).days
    
    # Eligibility rules
    eligible = True
    reasons = []
    
    # Time limit check (30 days)
    if days_since > 30:
      eligible = False
      reasons.append("Transaction older than 30-day refund window")
    
    # Amount check (auto-approve up to $100 per guardrails)
    auto_approve = transaction["amount"] <= 100
    
    # Reason validation
    valid_reasons = ["billing_error", "service_issue", "duplicate_charge", "cancellation", "dissatisfaction"]
    if refund_reason not in valid_reasons:
      eligible = False
      reasons.append("Invalid refund reason")
    
    return {
      "transaction": transaction,
      "eligible": eligible,
      "auto_approve": auto_approve and eligible,
      "requires_manual_review": eligible and not auto_approve,
      "ineligibility_reasons": reasons,
      "days_since_transaction": days_since,
      "validation_timestamp": datetime.now().isoformat()
    }
  
  async def _calculate_refund_amount(
    self,
    transaction_amount: float,
    refund_type: str = "full",
    proration_days: Optional[int] = None
  ) -> Dict[str, Any]:
    """Calculate the refund amount based on type and proration."""
    if refund_type == "full":
      refund_amount = transaction_amount
      
    elif refund_type == "partial":
      # Default to 50% for partial refunds
      refund_amount = transaction_amount * 0.5
      
    elif refund_type == "prorated" and proration_days:
      # Calculate based on unused days (assuming monthly billing)
      daily_rate = transaction_amount / 30
      refund_amount = daily_rate * proration_days
      
    else:
      refund_amount = 0
    
    # Apply any processing fees
    processing_fee = min(refund_amount * 0.029, 5.0)  # 2.9% or $5 max
    net_refund = max(0, refund_amount - processing_fee)
    
    return {
      "original_amount": transaction_amount,
      "refund_type": refund_type,
      "gross_refund": round(refund_amount, 2),
      "processing_fee": round(processing_fee, 2),
      "net_refund": round(net_refund, 2),
      "proration_days": proration_days,
      "calculated_at": datetime.now().isoformat()
    }
  
  async def _process_refund(
    self,
    customer_id: str,
    transaction_id: str,
    refund_amount: float,
    refund_reason: str,
    auto_approved: bool = False
  ) -> Dict[str, Any]:
    """Process a refund request."""
    refund_id = f"REF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Check auto-approval limit
    if auto_approved and refund_amount > 100:
      return {
        "success": False,
        "error": "Auto-approval limited to $100 per company policy",
        "refund_id": None,
        "requires_manual_approval": True
      }
    
    # Mock refund processing
    processing_time = "1-3 business days" if refund_amount > 50 else "immediate"
    
    refund_data = {
      "refund_id": refund_id,
      "customer_id": customer_id,
      "transaction_id": transaction_id,
      "refund_amount": refund_amount,
      "refund_reason": refund_reason,
      "status": "processed" if auto_approved else "pending_review",
      "auto_approved": auto_approved,
      "processing_time": processing_time,
      "processed_at": datetime.now().isoformat(),
      "expected_completion": (datetime.now() + timedelta(days=3)).isoformat()
    }
    
    return {"success": True, "refund": refund_data}
  
  async def _notify_customer(
    self,
    customer_id: str,
    refund_data: Dict[str, Any],
    notification_type: str = "confirmation"
  ) -> Dict[str, Any]:
    """Send refund notification to customer."""
    if notification_type == "confirmation":
      message = f"""Your refund request has been processed.

Refund ID: {refund_data['refund_id']}
Amount: ${refund_data['refund_amount']}
Status: {refund_data['status']}
Expected completion: {refund_data['processing_time']}

Thank you for your patience."""
    
    elif notification_type == "completion":
      message = f"""Your refund has been completed.

Refund ID: {refund_data['refund_id']}
Amount: ${refund_data['refund_amount']}

The refund should appear in your account within 1-2 business days."""
    
    else:
      message = "Refund notification sent."
    
    return {
      "customer_id": customer_id,
      "notification_type": notification_type,
      "message": message,
      "sent_at": datetime.now().isoformat(),
      "delivery_method": "email"
    }
  
  async def _update_billing_system(
    self,
    refund_data: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Update billing system with refund information."""
    # Mock billing system update
    return {
      "billing_system_updated": True,
      "refund_id": refund_data["refund_id"],
      "account_credited": refund_data["refund_amount"],
      "updated_at": datetime.now().isoformat(),
      "next_bill_adjustment": f"-${refund_data['refund_amount']}"
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute refund processing tasks."""
    if task == "process_refund_request":
      # Step 1: Validate eligibility
      eligibility = await self._validate_refund_eligibility(
        customer_id=context["customer_id"],
        transaction_id=context["transaction_id"],
        refund_reason=context["refund_reason"]
      )
      
      if not eligibility["eligible"]:
        return {
          "success": False,
          "reason": "Not eligible for refund",
          "details": eligibility
        }
      
      # Step 2: Calculate refund amount
      refund_calc = await self._calculate_refund_amount(
        transaction_amount=eligibility["transaction"]["amount"],
        refund_type=context.get("refund_type", "full"),
        proration_days=context.get("proration_days")
      )
      
      # Step 3: Process refund
      refund_result = await self._process_refund(
        customer_id=context["customer_id"],
        transaction_id=context["transaction_id"],
        refund_amount=refund_calc["net_refund"],
        refund_reason=context["refund_reason"],
        auto_approved=eligibility["auto_approve"]
      )
      
      if refund_result["success"]:
        # Step 4: Notify customer
        notification = await self._notify_customer(
          customer_id=context["customer_id"],
          refund_data=refund_result["refund"],
          notification_type="confirmation"
        )
        
        # Step 5: Update billing
        billing_update = await self._update_billing_system(refund_result["refund"])
        
        return {
          "success": True,
          "eligibility": eligibility,
          "calculation": refund_calc,
          "refund": refund_result["refund"],
          "notification": notification,
          "billing_update": billing_update
        }
      else:
        return refund_result
    
    elif task == "review_pending_refunds":
      # Mock pending refunds review
      pending_refunds = [
        {
          "refund_id": "REF-20241201-ABC123",
          "customer_id": "cust_456",
          "amount": 150.00,
          "reason": "service_issue",
          "days_pending": 2
        },
        {
          "refund_id": "REF-20241201-DEF456", 
          "customer_id": "cust_789",
          "amount": 299.99,
          "reason": "cancellation",
          "days_pending": 1
        }
      ]
      
      recommendations = []
      for refund in pending_refunds:
        if refund["days_pending"] > 1:
          recommendations.append({
            "refund_id": refund["refund_id"],
            "action": "approve",
            "reason": "Standard refund within policy"
          })
      
      return {
        "pending_refunds": pending_refunds,
        "recommendations": recommendations,
        "total_pending_amount": sum(r["amount"] for r in pending_refunds)
      }
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get refund bot capabilities."""
    return [
      "refund_eligibility_validation",
      "automated_refund_processing",
      "proration_calculations", 
      "billing_system_integration",
      "customer_notifications",
      "policy_compliance"
    ]


class ChurnSentinel(BusinessPillarAgent):
  """Agent responsible for detecting and preventing customer churn."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="churn_sentinel",
      role=AgentRole.CRITIC,
      pillar=PillarType.CUSTOMER_SUCCESS,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup churn detection tools."""
    self.register_tool("analyze_churn_risk", self._analyze_churn_risk, cost=1.0)
    self.register_tool("detect_usage_patterns", self._detect_usage_patterns, cost=0.8)
    self.register_tool("calculate_customer_lifetime_value", self._calculate_clv, cost=0.6)
    self.register_tool("recommend_retention_actions", self._recommend_retention_actions, cost=0.7)
    self.register_tool("monitor_nps_trends", self._monitor_nps_trends, cost=0.5)
    self.register_tool("trigger_retention_campaign", self._trigger_retention_campaign, cost=1.5)
  
  async def _analyze_churn_risk(
    self,
    customer_id: str,
    analysis_period_days: int = 30
  ) -> Dict[str, Any]:
    """Analyze customer churn risk based on multiple factors."""
    # Mock customer data
    customer_data = {
      "customer_id": customer_id,
      "account_age_days": 180,
      "subscription_tier": "professional",
      "monthly_revenue": 299,
      "last_login_days_ago": 5,
      "support_tickets_30d": 2,
      "feature_usage_score": 0.65,  # 0-1 scale
      "payment_failures": 0,
      "contract_renewal_date": "2024-06-15",
      "nps_score": 7
    }
    
    # Calculate risk factors
    risk_factors = {}
    
    # Usage-based factors
    if customer_data["last_login_days_ago"] > 14:
      risk_factors["login_inactivity"] = 0.8
    elif customer_data["last_login_days_ago"] > 7:
      risk_factors["login_inactivity"] = 0.4
    else:
      risk_factors["login_inactivity"] = 0.1
    
    # Feature adoption
    if customer_data["feature_usage_score"] < 0.3:
      risk_factors["low_feature_adoption"] = 0.7
    elif customer_data["feature_usage_score"] < 0.5:
      risk_factors["low_feature_adoption"] = 0.4
    else:
      risk_factors["low_feature_adoption"] = 0.1
    
    # Support activity
    if customer_data["support_tickets_30d"] > 3:
      risk_factors["high_support_volume"] = 0.6
    else:
      risk_factors["high_support_volume"] = 0.1
    
    # NPS score
    if customer_data["nps_score"] < 6:
      risk_factors["low_satisfaction"] = 0.9
    elif customer_data["nps_score"] < 8:
      risk_factors["low_satisfaction"] = 0.5
    else:
      risk_factors["low_satisfaction"] = 0.1
    
    # Payment issues
    if customer_data["payment_failures"] > 0:
      risk_factors["payment_issues"] = 0.8
    else:
      risk_factors["payment_issues"] = 0.0
    
    # Calculate composite risk score
    risk_score = sum(risk_factors.values()) / len(risk_factors)
    
    # Risk categorization
    if risk_score > 0.7:
      risk_level = "high"
    elif risk_score > 0.4:
      risk_level = "medium"
    else:
      risk_level = "low"
    
    # Contract renewal proximity
    renewal_date = datetime.fromisoformat(customer_data["contract_renewal_date"])
    days_to_renewal = (renewal_date - datetime.now()).days
    
    return {
      "customer_id": customer_id,
      "customer_data": customer_data,
      "risk_factors": risk_factors,
      "composite_risk_score": round(risk_score, 2),
      "risk_level": risk_level,
      "days_to_renewal": days_to_renewal,
      "churn_probability": min(0.95, risk_score),
      "analysis_date": datetime.now().isoformat(),
      "recommended_actions": self._get_risk_actions(risk_level, risk_factors)
    }
  
  def _get_risk_actions(self, risk_level: str, risk_factors: Dict[str, float]) -> List[str]:
    """Get recommended actions based on risk level and factors."""
    actions = []
    
    if risk_level == "high":
      actions.append("Immediate customer success manager outreach")
      actions.append("Offer discount or incentive")
      actions.append("Schedule executive check-in call")
    
    # Factor-specific actions
    if risk_factors.get("login_inactivity", 0) > 0.5:
      actions.append("Send product engagement email campaign")
      actions.append("Offer onboarding assistance")
    
    if risk_factors.get("low_feature_adoption", 0) > 0.5:
      actions.append("Provide feature training session")
      actions.append("Send feature highlight documentation")
    
    if risk_factors.get("high_support_volume", 0) > 0.5:
      actions.append("Escalate to technical account manager")
      actions.append("Conduct root cause analysis of issues")
    
    if risk_factors.get("low_satisfaction", 0) > 0.5:
      actions.append("Schedule satisfaction survey follow-up")
      actions.append("Executive relationship review")
    
    return actions
  
  async def _detect_usage_patterns(
    self,
    customer_id: str,
    lookback_days: int = 90
  ) -> Dict[str, Any]:
    """Detect changes in customer usage patterns."""
    # Mock usage pattern analysis
    patterns = {
      "customer_id": customer_id,
      "analysis_period": f"{lookback_days} days",
      "usage_trends": {
        "daily_active_users": {"trend": "declining", "change_percent": -15},
        "feature_adoption": {"trend": "stable", "change_percent": 2},
        "api_calls": {"trend": "declining", "change_percent": -22},
        "support_interactions": {"trend": "increasing", "change_percent": 45}
      },
      "anomalies_detected": [
        {
          "type": "usage_drop",
          "metric": "api_calls",
          "severity": "medium",
          "detected_on": (datetime.now() - timedelta(days=7)).isoformat()
        }
      ],
      "usage_health_score": 0.62,  # Declining from baseline
      "baseline_comparison": "Below 30-day average"
    }
    
    return patterns
  
  async def _calculate_clv(
    self,
    customer_id: str,
    projection_months: int = 12
  ) -> Dict[str, Any]:
    """Calculate customer lifetime value."""
    # Mock CLV calculation
    monthly_revenue = 299
    retention_rate = 0.85  # Monthly
    gross_margin = 0.75
    acquisition_cost = 500
    
    # Simple CLV calculation
    clv = (monthly_revenue * gross_margin * retention_rate) / (1 - retention_rate) - acquisition_cost
    
    # Projected value
    projected_clv = monthly_revenue * projection_months * retention_rate * gross_margin
    
    return {
      "customer_id": customer_id,
      "monthly_revenue": monthly_revenue,
      "retention_rate": retention_rate,
      "gross_margin": gross_margin,
      "acquisition_cost": acquisition_cost,
      "calculated_clv": round(clv, 2),
      "projected_clv": round(projected_clv, 2),
      "projection_months": projection_months,
      "clv_segment": "high" if clv > 2000 else "medium" if clv > 500 else "low",
      "calculated_at": datetime.now().isoformat()
    }
  
  async def _recommend_retention_actions(
    self,
    churn_risk: Dict[str, Any],
    clv_data: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Recommend specific retention actions based on risk and value."""
    risk_level = churn_risk["risk_level"]
    clv_segment = clv_data["clv_segment"]
    
    # Tailor actions based on value and risk
    if clv_segment == "high" and risk_level == "high":
      actions = [
        {
          "action": "executive_intervention",
          "priority": "urgent",
          "description": "CEO/VP customer call within 24 hours",
          "cost": 0,
          "expected_impact": 0.8
        },
        {
          "action": "custom_discount",
          "priority": "high",
          "description": "25% discount for next 6 months",
          "cost": 448.5,  # 25% of 6 months revenue
          "expected_impact": 0.7
        }
      ]
    elif clv_segment == "medium" and risk_level in ["medium", "high"]:
      actions = [
        {
          "action": "csm_outreach",
          "priority": "medium",
          "description": "Customer success manager check-in call",
          "cost": 50,
          "expected_impact": 0.6
        },
        {
          "action": "feature_training",
          "priority": "medium", 
          "description": "Personalized feature training session",
          "cost": 100,
          "expected_impact": 0.5
        }
      ]
    else:
      actions = [
        {
          "action": "automated_outreach",
          "priority": "low",
          "description": "Automated email campaign",
          "cost": 5,
          "expected_impact": 0.3
        }
      ]
    
    return {
      "customer_id": churn_risk["customer_id"],
      "risk_level": risk_level,
      "clv_segment": clv_segment,
      "recommended_actions": actions,
      "total_retention_investment": sum(action["cost"] for action in actions),
      "expected_roi": clv_data["calculated_clv"] / max(1, sum(action["cost"] for action in actions)),
      "generated_at": datetime.now().isoformat()
    }
  
  async def _monitor_nps_trends(
    self,
    time_period: str = "30d"
  ) -> Dict[str, Any]:
    """Monitor NPS trends and detect drops."""
    # Mock NPS data
    nps_data = {
      "current_period": time_period,
      "current_nps": 42,
      "previous_nps": 48,
      "nps_change": -6,
      "response_rate": 0.23,
      "detractors_percent": 15,
      "passives_percent": 28,
      "promoters_percent": 57,
      "trend": "declining",
      "alert_triggered": True,  # NPS drop > 5 points
      "segment_breakdown": {
        "enterprise": {"nps": 38, "change": -8},
        "mid_market": {"nps": 45, "change": -4},
        "smb": {"nps": 44, "change": -2}
      }
    }
    
    return nps_data
  
  async def _trigger_retention_campaign(
    self,
    customer_segments: List[str],
    campaign_type: str,
    urgency: str = "medium"
  ) -> Dict[str, Any]:
    """Trigger a retention campaign for at-risk customers."""
    campaign_id = f"RET-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    campaign_data = {
      "campaign_id": campaign_id,
      "campaign_type": campaign_type,
      "target_segments": customer_segments,
      "urgency": urgency,
      "launched_at": datetime.now().isoformat(),
      "estimated_reach": len(customer_segments) * 50,  # Mock reach
      "budget_allocated": 5000 if urgency == "high" else 2000,
      "success_metrics": {
        "target_retention_improvement": "15%",
        "target_engagement_increase": "25%"
      }
    }
    
    return campaign_data
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute churn detection and prevention tasks."""
    if task == "assess_customer_risk":
      customer_id = context["customer_id"]
      
      # Analyze churn risk
      risk_analysis = await self._analyze_churn_risk(customer_id)
      
      # Get usage patterns
      usage_patterns = await self._detect_usage_patterns(customer_id)
      
      # Calculate CLV
      clv_data = await self._calculate_clv(customer_id)
      
      # Generate recommendations
      recommendations = await self._recommend_retention_actions(risk_analysis, clv_data)
      
      # Trigger alerts for high-risk, high-value customers
      if risk_analysis["risk_level"] == "high" and clv_data["clv_segment"] == "high":
        await self.publish_event(
          "churn.high_value_at_risk",
          {
            "customer_id": customer_id,
            "risk_score": risk_analysis["composite_risk_score"],
            "clv": clv_data["calculated_clv"],
            "urgent_action_required": True
          },
          target_pillar="Customer Success",
          trace_id=workflow_id
        )
      
      return {
        "risk_analysis": risk_analysis,
        "usage_patterns": usage_patterns,
        "clv_data": clv_data,
        "recommendations": recommendations
      }
    
    elif task == "nps_monitoring":
      nps_trends = await self._monitor_nps_trends()
      
      # Trigger alert if NPS dropped significantly
      if nps_trends["alert_triggered"]:
        await self.publish_event(
          "nps.significant_drop",
          nps_trends,
          target_pillar="Mission & Governance",  # Alert leadership
          trace_id=workflow_id
        )
        
        # Launch retention campaign
        campaign = await self._trigger_retention_campaign(
          customer_segments=["detractors", "at_risk_passives"],
          campaign_type="satisfaction_recovery",
          urgency="high"
        )
        
        return {
          "nps_trends": nps_trends,
          "retention_campaign": campaign
        }
      
      return {"nps_trends": nps_trends}
    
    elif task == "bulk_risk_assessment":
      # Assess multiple customers
      customer_ids = context["customer_ids"]
      results = []
      
      for customer_id in customer_ids:
        risk_analysis = await self._analyze_churn_risk(customer_id)
        results.append({
          "customer_id": customer_id,
          "risk_level": risk_analysis["risk_level"],
          "risk_score": risk_analysis["composite_risk_score"]
        })
      
      # Segment by risk
      high_risk = [r for r in results if r["risk_level"] == "high"]
      medium_risk = [r for r in results if r["risk_level"] == "medium"]
      
      return {
        "total_assessed": len(results),
        "high_risk_count": len(high_risk),
        "medium_risk_count": len(medium_risk),
        "high_risk_customers": high_risk,
        "assessment_summary": results
      }
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get churn sentinel capabilities."""
    return [
      "churn_risk_analysis",
      "usage_pattern_detection",
      "customer_lifetime_value_calculation",
      "retention_strategy_recommendations",
      "nps_monitoring",
      "automated_retention_campaigns"
    ]


class CustomerSuccessPillar(BusinessPillar):
  """Customer Success pillar coordinating customer retention agents."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.CUSTOMER_SUCCESS, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    # Support Responder (Worker)
    support_responder = SupportResponder(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(support_responder)
    
    # Refund Bot (Worker - billing focus)
    refund_bot = RefundBot(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    # Register as planner since we already have a worker
    refund_bot.role = AgentRole.PLANNER
    self.register_agent(refund_bot)
    
    # Churn Sentinel (Critic)
    churn_sentinel = ChurnSentinel(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(churn_sentinel)
  
  async def execute_workflow(
    self,
    workflow_type: str,
    inputs: Dict[str, Any],
    requester: Optional[str] = None
  ) -> WorkflowResult:
    """Execute customer success workflows."""
    workflow_id = f"customer_success_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "ticket_to_resolution":
      return await self._execute_ticket_resolution_workflow(workflow, inputs)
    
    elif workflow_type == "refund_processing":
      return await self._execute_refund_workflow(workflow, inputs)
    
    elif workflow_type == "churn_prevention":
      return await self._execute_churn_prevention_workflow(workflow, inputs)
    
    elif workflow_type == "customer_health_check":
      return await self._execute_health_check_workflow(workflow, inputs)
    
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_ticket_resolution_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute end-to-end ticket resolution workflow."""
    support_responder = self.get_agent(AgentRole.WORKER)
    churn_sentinel = self.get_agent(AgentRole.CRITIC)
    
    try:
      # Step 1: Handle new ticket
      step1 = WorkflowStep(
        step_id="handle_ticket",
        agent_role=AgentRole.WORKER,
        action="handle_new_ticket",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      ticket_result = await support_responder.execute_task(
        "handle_new_ticket",
        inputs,
        workflow.workflow_id
      )
      step1.complete(ticket_result)
      
      # Step 2: Assess customer risk impact
      step2 = WorkflowStep(
        step_id="assess_risk_impact",
        agent_role=AgentRole.CRITIC,
        action="assess_customer_risk",
        inputs={"customer_id": inputs["customer_id"]}
      )
      step2.start()
      workflow.add_step(step2)
      
      risk_assessment = await churn_sentinel.execute_task(
        "assess_customer_risk",
        {"customer_id": inputs["customer_id"]},
        workflow.workflow_id
      )
      step2.complete(risk_assessment)
      
      # Step 3: Resolve ticket if needed
      if inputs.get("auto_resolve"):
        step3 = WorkflowStep(
          step_id="resolve_ticket",
          agent_role=AgentRole.WORKER,
          action="resolve_ticket",
          inputs={
            "ticket_id": ticket_result["ticket"]["ticket_id"],
            "customer_id": inputs["customer_id"],
            "resolution_summary": "Issue resolved via automated workflow"
          }
        )
        step3.start()
        workflow.add_step(step3)
        
        resolution_result = await support_responder.execute_task(
          "resolve_ticket",
          step3.inputs,
          workflow.workflow_id
        )
        step3.complete(resolution_result)
        
        final_output = {
          "ticket_handling": ticket_result,
          "risk_assessment": risk_assessment,
          "resolution": resolution_result
        }
      else:
        final_output = {
          "ticket_handling": ticket_result,
          "risk_assessment": risk_assessment,
          "status": "pending_manual_resolution"
        }
      
      workflow.complete(final_output)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_refund_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute refund processing workflow."""
    refund_bot = self.get_agent(AgentRole.PLANNER)
    
    try:
      # Process refund request
      step1 = WorkflowStep(
        step_id="process_refund",
        agent_role=AgentRole.PLANNER,
        action="process_refund_request",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      refund_result = await refund_bot.execute_task(
        "process_refund_request",
        inputs,
        workflow.workflow_id
      )
      step1.complete(refund_result)
      
      workflow.complete(refund_result)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_churn_prevention_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute churn prevention workflow."""
    churn_sentinel = self.get_agent(AgentRole.CRITIC)
    
    try:
      # Assess churn risk
      step1 = WorkflowStep(
        step_id="churn_risk_assessment",
        agent_role=AgentRole.CRITIC,
        action="assess_customer_risk",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      risk_result = await churn_sentinel.execute_task(
        "assess_customer_risk",
        inputs,
        workflow.workflow_id
      )
      step1.complete(risk_result)
      
      workflow.complete(risk_result)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_health_check_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute customer health check workflow."""
    churn_sentinel = self.get_agent(AgentRole.CRITIC)
    
    try:
      # Monitor NPS trends
      step1 = WorkflowStep(
        step_id="nps_monitoring",
        agent_role=AgentRole.CRITIC,
        action="nps_monitoring",
        inputs={}
      )
      step1.start()
      workflow.add_step(step1)
      
      nps_result = await churn_sentinel.execute_task(
        "nps_monitoring",
        {},
        workflow.workflow_id
      )
      step1.complete(nps_result)
      
      workflow.complete(nps_result)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    """Get supported workflow types."""
    return [
      "ticket_to_resolution",
      "refund_processing",
      "churn_prevention",
      "customer_health_check"
    ]