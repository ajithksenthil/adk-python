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

"""Growth Engine Pillar - Generate demand and revenue."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep

logger = logging.getLogger(__name__)


class AdBidder(BusinessPillarAgent):
  """Agent responsible for managing advertising campaigns and bidding."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="ad_bidder",
      role=AgentRole.WORKER,
      pillar=PillarType.GROWTH_ENGINE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup advertising tools."""
    self.register_tool("create_campaign", self._create_campaign, cost=5.0)
    self.register_tool("adjust_bids", self._adjust_bids, cost=2.0)
    self.register_tool("pause_campaign", self._pause_campaign, cost=0.5)
    self.register_tool("analyze_performance", self._analyze_performance, cost=1.0)
    self.register_tool("optimize_targeting", self._optimize_targeting, cost=3.0)
    self.register_tool("check_budget_utilization", self._check_budget_utilization, cost=0.3)
  
  async def _create_campaign(
    self,
    campaign_name: str,
    channel: str,
    budget: float,
    target_audience: Dict[str, Any],
    campaign_type: str = "search"
  ) -> Dict[str, Any]:
    """Create a new advertising campaign."""
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
    
    # Validate budget against daily limits
    daily_limit = 2000  # From governance guardrails
    if budget > daily_limit:
      return {
        "success": False,
        "error": f"Campaign budget ${budget} exceeds daily limit of ${daily_limit}",
        "campaign_id": None
      }
    
    # Mock campaign creation
    campaign_data = {
      "campaign_id": campaign_id,
      "name": campaign_name,
      "channel": channel,
      "type": campaign_type,
      "budget": budget,
      "daily_budget": min(budget / 30, daily_limit),  # Monthly to daily
      "target_audience": target_audience,
      "status": "active",
      "created_at": datetime.now().isoformat(),
      "estimated_reach": self._estimate_reach(budget, channel),
      "expected_cpc": self._estimate_cpc(channel, target_audience),
      "keywords": self._generate_keywords(target_audience)
    }
    
    return {
      "success": True,
      "campaign": campaign_data,
      "recommendations": [
        "Monitor performance for first 48 hours",
        "Consider A/B testing ad creatives",
        f"Expected daily spend: ${campaign_data['daily_budget']:.2f}"
      ]
    }
  
  def _estimate_reach(self, budget: float, channel: str) -> int:
    """Estimate campaign reach based on budget and channel."""
    reach_multipliers = {
      "google": 100,   # $1 = 100 impressions
      "facebook": 150,
      "linkedin": 50,
      "twitter": 80
    }
    
    multiplier = reach_multipliers.get(channel.lower(), 75)
    return int(budget * multiplier)
  
  def _estimate_cpc(self, channel: str, target_audience: Dict[str, Any]) -> float:
    """Estimate cost per click based on channel and audience."""
    base_cpc = {
      "google": 2.50,
      "facebook": 1.20,
      "linkedin": 5.80,
      "twitter": 1.80
    }
    
    cpc = base_cpc.get(channel.lower(), 2.00)
    
    # Adjust for audience targeting
    if target_audience.get("age_range") == "25-34":
      cpc *= 1.2  # Higher competition
    if target_audience.get("income_level") == "high":
      cpc *= 1.5
    if "enterprise" in str(target_audience).lower():
      cpc *= 2.0
    
    return round(cpc, 2)
  
  def _generate_keywords(self, target_audience: Dict[str, Any]) -> List[str]:
    """Generate keyword suggestions based on target audience."""
    base_keywords = ["software", "solution", "platform", "service"]
    
    audience_keywords = []
    if target_audience.get("industry"):
      audience_keywords.extend([
        f"{target_audience['industry']} software",
        f"{target_audience['industry']} solution"
      ])
    
    if target_audience.get("company_size") == "enterprise":
      audience_keywords.extend(["enterprise software", "enterprise solution"])
    
    return base_keywords + audience_keywords
  
  async def _adjust_bids(
    self,
    campaign_id: str,
    adjustment_type: str,
    adjustment_value: float,
    reason: str
  ) -> Dict[str, Any]:
    """Adjust bidding for a campaign."""
    # Mock bid adjustment
    current_bid = 2.50
    
    if adjustment_type == "percentage":
      new_bid = current_bid * (1 + adjustment_value / 100)
    elif adjustment_type == "absolute":
      new_bid = current_bid + adjustment_value
    else:
      return {"success": False, "error": "Invalid adjustment type"}
    
    # Ensure bid doesn't exceed reasonable limits
    max_bid = 50.0
    new_bid = min(new_bid, max_bid)
    
    return {
      "success": True,
      "campaign_id": campaign_id,
      "previous_bid": current_bid,
      "new_bid": round(new_bid, 2),
      "adjustment_type": adjustment_type,
      "adjustment_value": adjustment_value,
      "reason": reason,
      "adjusted_at": datetime.now().isoformat()
    }
  
  async def _pause_campaign(
    self,
    campaign_id: str,
    reason: str
  ) -> Dict[str, Any]:
    """Pause an advertising campaign."""
    return {
      "success": True,
      "campaign_id": campaign_id,
      "status": "paused",
      "reason": reason,
      "paused_at": datetime.now().isoformat(),
      "estimated_savings": 150.0  # Daily budget saved
    }
  
  async def _analyze_performance(
    self,
    campaign_id: str,
    time_period: str = "7d"
  ) -> Dict[str, Any]:
    """Analyze campaign performance."""
    # Mock performance data
    performance = {
      "campaign_id": campaign_id,
      "time_period": time_period,
      "metrics": {
        "impressions": 25000,
        "clicks": 750,
        "conversions": 35,
        "spend": 1875.50,
        "revenue": 8750.00
      },
      "calculated_metrics": {
        "ctr": 3.0,  # click-through rate
        "conversion_rate": 4.7,
        "cpc": 2.50,  # cost per click
        "roas": 4.67,  # return on ad spend
        "cpa": 53.59   # cost per acquisition
      },
      "performance_grade": "B+",
      "recommendations": [
        "CTR is above industry average",
        "Consider increasing budget for high-performing keywords",
        "Test new ad creatives to improve conversion rate"
      ]
    }
    
    return performance
  
  async def _optimize_targeting(
    self,
    campaign_id: str,
    optimization_goals: List[str]
  ) -> Dict[str, Any]:
    """Optimize campaign targeting."""
    optimizations = []
    
    for goal in optimization_goals:
      if goal == "reduce_cpc":
        optimizations.append({
          "type": "audience_refinement",
          "action": "exclude_low_converting_demographics",
          "expected_impact": "10-15% CPC reduction"
        })
      elif goal == "increase_conversions":
        optimizations.append({
          "type": "lookalike_audience",
          "action": "expand_to_similar_profiles",
          "expected_impact": "20-30% conversion increase"
        })
      elif goal == "improve_roas":
        optimizations.append({
          "type": "bid_strategy",
          "action": "switch_to_target_roas_bidding",
          "expected_impact": "15-25% ROAS improvement"
        })
    
    return {
      "campaign_id": campaign_id,
      "optimization_goals": optimization_goals,
      "optimizations": optimizations,
      "estimated_implementation_time": "2-4 hours",
      "optimized_at": datetime.now().isoformat()
    }
  
  async def _check_budget_utilization(
    self,
    time_period: str = "today"
  ) -> Dict[str, Any]:
    """Check advertising budget utilization."""
    daily_budget = 2000  # From guardrails
    
    # Mock utilization data
    if time_period == "today":
      spent = 1650.75
      remaining = daily_budget - spent
      utilization = (spent / daily_budget) * 100
    else:
      spent = 12500.50
      remaining = 14000 - spent  # Weekly budget
      utilization = (spent / 14000) * 100
    
    return {
      "time_period": time_period,
      "budget_allocated": daily_budget if time_period == "today" else 14000,
      "amount_spent": spent,
      "remaining_budget": remaining,
      "utilization_percentage": round(utilization, 1),
      "pacing": "on_track" if 80 <= utilization <= 95 else "under_pacing" if utilization < 80 else "over_pacing",
      "recommendations": [
        "Increase bids on high-performing campaigns" if utilization < 80 else
        "Monitor spending closely to avoid overspend" if utilization > 95 else
        "Pacing is optimal"
      ]
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute advertising tasks."""
    if task == "launch_campaign":
      return await self._create_campaign(
        campaign_name=context["campaign_name"],
        channel=context["channel"],
        budget=context["budget"],
        target_audience=context["target_audience"],
        campaign_type=context.get("campaign_type", "search")
      )
    
    elif task == "optimize_performance":
      campaign_id = context["campaign_id"]
      
      # Analyze current performance
      performance = await self._analyze_performance(campaign_id)
      
      # Determine optimization needs
      roas = performance["calculated_metrics"]["roas"]
      cpc = performance["calculated_metrics"]["cpc"]
      
      optimization_goals = []
      if roas < 3.0:
        optimization_goals.append("improve_roas")
      if cpc > 3.0:
        optimization_goals.append("reduce_cpc")
      
      # Apply optimizations
      optimizations = await self._optimize_targeting(campaign_id, optimization_goals)
      
      return {
        "performance_analysis": performance,
        "optimizations_applied": optimizations
      }
    
    elif task == "budget_monitoring":
      utilization = await self._check_budget_utilization()
      
      # Take action if needed
      if utilization["pacing"] == "over_pacing":
        # Pause low-performing campaigns
        await self.publish_event(
          "campaign.budget_alert",
          {
            "alert_type": "over_pacing",
            "utilization": utilization["utilization_percentage"],
            "action_needed": "pause_low_performers"
          },
          trace_id=workflow_id
        )
      
      return utilization
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get ad bidder capabilities."""
    return [
      "campaign_creation",
      "bid_management",
      "performance_optimization",
      "budget_monitoring",
      "audience_targeting",
      "keyword_optimization"
    ]


class PricingBot(BusinessPillarAgent):
  """Agent responsible for dynamic pricing and quote optimization."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="pricing_bot",
      role=AgentRole.PLANNER,
      pillar=PillarType.GROWTH_ENGINE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup pricing tools."""
    self.register_tool("calculate_optimal_price", self._calculate_optimal_price, cost=0.8)
    self.register_tool("apply_discount", self._apply_discount, cost=0.3)
    self.register_tool("analyze_price_elasticity", self._analyze_price_elasticity, cost=1.2)
    self.register_tool("generate_pricing_recommendations", self._generate_pricing_recommendations, cost=0.6)
    self.register_tool("validate_margin_floor", self._validate_margin_floor, cost=0.2)
  
  async def _calculate_optimal_price(
    self,
    product_id: str,
    customer_segment: str,
    deal_size: str,
    competitive_landscape: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Calculate optimal pricing for a product/service."""
    # Base pricing model
    base_prices = {
      "starter": {"small": 99, "medium": 199, "large": 399},
      "professional": {"small": 299, "medium": 599, "large": 999},
      "enterprise": {"small": 999, "medium": 2499, "large": 4999}
    }
    
    product_tier = product_id.split("_")[0] if "_" in product_id else "professional"
    base_price = base_prices.get(product_tier, base_prices["professional"]).get(deal_size, 599)
    
    # Apply segment adjustments
    segment_multipliers = {
      "enterprise": 1.5,
      "mid_market": 1.2,
      "smb": 1.0,
      "startup": 0.8
    }
    
    segment_price = base_price * segment_multipliers.get(customer_segment, 1.0)
    
    # Competitive adjustments
    competitive_factor = competitive_landscape.get("competitive_intensity", 1.0)
    market_price = segment_price * (0.9 if competitive_factor > 1.2 else 1.0)
    
    # Margin validation
    margin_floor = 0.25  # 25% minimum margin from guardrails
    cost = market_price * 0.6  # Assume 60% cost ratio
    minimum_price = cost / (1 - margin_floor)
    
    optimal_price = max(market_price, minimum_price)
    
    return {
      "product_id": product_id,
      "customer_segment": customer_segment,
      "deal_size": deal_size,
      "base_price": base_price,
      "segment_adjusted_price": segment_price,
      "market_price": market_price,
      "optimal_price": round(optimal_price, 2),
      "margin_percentage": round(((optimal_price - cost) / optimal_price) * 100, 1),
      "pricing_rationale": {
        "segment_factor": segment_multipliers.get(customer_segment, 1.0),
        "competitive_factor": competitive_factor,
        "margin_floor_applied": optimal_price > market_price
      }
    }
  
  async def _apply_discount(
    self,
    original_price: float,
    discount_type: str,
    discount_value: float,
    justification: str
  ) -> Dict[str, Any]:
    """Apply discount while respecting margin floors."""
    if discount_type == "percentage":
      discounted_price = original_price * (1 - discount_value / 100)
    elif discount_type == "fixed":
      discounted_price = original_price - discount_value
    else:
      return {"success": False, "error": "Invalid discount type"}
    
    # Check margin floor
    margin_floor = 0.25
    cost = original_price * 0.6
    minimum_price = cost / (1 - margin_floor)
    
    if discounted_price < minimum_price:
      return {
        "success": False,
        "error": "Discount would violate margin floor policy",
        "requested_price": discounted_price,
        "minimum_allowed_price": minimum_price,
        "margin_floor": margin_floor * 100
      }
    
    final_margin = ((discounted_price - cost) / discounted_price) * 100
    
    return {
      "success": True,
      "original_price": original_price,
      "discount_type": discount_type,
      "discount_value": discount_value,
      "discounted_price": round(discounted_price, 2),
      "final_margin_percentage": round(final_margin, 1),
      "discount_amount": original_price - discounted_price,
      "justification": justification,
      "applied_at": datetime.now().isoformat()
    }
  
  async def _analyze_price_elasticity(
    self,
    product_id: str,
    price_changes: List[Dict[str, Any]]
  ) -> Dict[str, Any]:
    """Analyze price elasticity based on historical data."""
    # Mock elasticity analysis
    elasticity_data = {
      "product_id": product_id,
      "analysis_period": "90d",
      "price_elasticity_coefficient": -1.2,  # 1% price increase = 1.2% demand decrease
      "optimal_price_range": {"min": 450, "max": 650},
      "revenue_impact": {
        "price_increase_10_percent": -8.5,  # % revenue change
        "price_decrease_10_percent": 15.2
      },
      "recommendations": [
        "Product shows elastic demand - consider promotional pricing",
        "Sweet spot appears to be $525-575 range",
        "Monitor competitor pricing closely"
      ]
    }
    
    return elasticity_data
  
  async def _generate_pricing_recommendations(
    self,
    market_conditions: Dict[str, Any],
    business_goals: List[str]
  ) -> Dict[str, Any]:
    """Generate pricing strategy recommendations."""
    recommendations = []
    
    # Goal-based recommendations
    for goal in business_goals:
      if goal == "market_share_growth":
        recommendations.append({
          "strategy": "penetration_pricing",
          "description": "Price 10-15% below competitors to gain market share",
          "risk_level": "medium",
          "expected_impact": "20-30% demand increase"
        })
      elif goal == "profit_maximization":
        recommendations.append({
          "strategy": "premium_pricing",
          "description": "Price at premium with value justification",
          "risk_level": "low",
          "expected_impact": "15-25% margin improvement"
        })
      elif goal == "customer_acquisition":
        recommendations.append({
          "strategy": "freemium_model",
          "description": "Free tier with premium upsell",
          "risk_level": "high",
          "expected_impact": "50-100% user growth"
        })
    
    # Market condition adjustments
    market_phase = market_conditions.get("phase", "growth")
    if market_phase == "recession":
      recommendations.append({
        "strategy": "value_pricing",
        "description": "Emphasize ROI and cost savings in pricing",
        "risk_level": "low",
        "expected_impact": "Maintained demand during downturn"
      })
    
    return {
      "market_conditions": market_conditions,
      "business_goals": business_goals,
      "recommendations": recommendations,
      "implementation_timeline": "2-4 weeks",
      "generated_at": datetime.now().isoformat()
    }
  
  async def _validate_margin_floor(
    self,
    price: float,
    cost: float,
    margin_requirement: float = 0.25
  ) -> Dict[str, Any]:
    """Validate that pricing meets margin floor requirements."""
    actual_margin = (price - cost) / price if price > 0 else 0
    meets_requirement = actual_margin >= margin_requirement
    
    return {
      "price": price,
      "cost": cost,
      "actual_margin": round(actual_margin * 100, 1),
      "required_margin": round(margin_requirement * 100, 1),
      "meets_requirement": meets_requirement,
      "minimum_price": cost / (1 - margin_requirement) if margin_requirement < 1 else cost * 2,
      "validated_at": datetime.now().isoformat()
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute pricing tasks."""
    if task == "optimize_pricing":
      return await self._calculate_optimal_price(
        product_id=context["product_id"],
        customer_segment=context["customer_segment"],
        deal_size=context["deal_size"],
        competitive_landscape=context.get("competitive_landscape", {})
      )
    
    elif task == "approve_discount":
      discount_result = await self._apply_discount(
        original_price=context["original_price"],
        discount_type=context["discount_type"],
        discount_value=context["discount_value"],
        justification=context["justification"]
      )
      
      # Publish event if discount is significant
      if discount_result.get("success") and context["discount_value"] > 20:
        await self.publish_event(
          "pricing.significant_discount_applied",
          discount_result,
          trace_id=workflow_id
        )
      
      return discount_result
    
    elif task == "pricing_strategy_review":
      return await self._generate_pricing_recommendations(
        market_conditions=context["market_conditions"],
        business_goals=context["business_goals"]
      )
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get pricing bot capabilities."""
    return [
      "dynamic_pricing",
      "discount_optimization",
      "margin_protection",
      "price_elasticity_analysis",
      "competitive_pricing",
      "revenue_optimization"
    ]


class QuoteGenerator(BusinessPillarAgent):
  """Agent responsible for generating and managing sales quotes."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="quote_generator",
      role=AgentRole.WORKER,
      pillar=PillarType.GROWTH_ENGINE,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    """Setup quote generation tools."""
    self.register_tool("generate_quote", self._generate_quote, cost=1.0)
    self.register_tool("update_quote", self._update_quote, cost=0.5)
    self.register_tool("send_quote", self._send_quote, cost=0.3)
    self.register_tool("track_quote_status", self._track_quote_status, cost=0.2)
    self.register_tool("calculate_commission", self._calculate_commission, cost=0.4)
  
  async def _generate_quote(
    self,
    customer_id: str,
    products: List[Dict[str, Any]],
    discount_percentage: float = 0,
    valid_days: int = 30
  ) -> Dict[str, Any]:
    """Generate a sales quote."""
    quote_id = f"Q{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    line_items = []
    subtotal = 0
    
    for product in products:
      unit_price = product["unit_price"]
      quantity = product["quantity"]
      line_total = unit_price * quantity
      
      line_item = {
        "product_id": product["product_id"],
        "product_name": product.get("product_name", f"Product {product['product_id']}"),
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total
      }
      
      line_items.append(line_item)
      subtotal += line_total
    
    # Apply discount
    discount_amount = subtotal * (discount_percentage / 100)
    total_after_discount = subtotal - discount_amount
    
    # Tax calculation (mock)
    tax_rate = 0.08  # 8% tax
    tax_amount = total_after_discount * tax_rate
    final_total = total_after_discount + tax_amount
    
    # Expiration date
    expiration_date = datetime.now() + timedelta(days=valid_days)
    
    quote = {
      "quote_id": quote_id,
      "customer_id": customer_id,
      "line_items": line_items,
      "subtotal": round(subtotal, 2),
      "discount_percentage": discount_percentage,
      "discount_amount": round(discount_amount, 2),
      "total_after_discount": round(total_after_discount, 2),
      "tax_rate": tax_rate,
      "tax_amount": round(tax_amount, 2),
      "final_total": round(final_total, 2),
      "status": "draft",
      "created_at": datetime.now().isoformat(),
      "expires_at": expiration_date.isoformat(),
      "valid_days": valid_days,
      "terms_and_conditions": [
        "Payment due within 30 days of invoice",
        "Prices valid until expiration date",
        "Subject to standard terms of service"
      ]
    }
    
    return quote
  
  async def _update_quote(
    self,
    quote_id: str,
    updates: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Update an existing quote."""
    # Mock quote update
    allowed_updates = ["discount_percentage", "valid_days", "products", "notes"]
    applied_updates = {k: v for k, v in updates.items() if k in allowed_updates}
    
    return {
      "quote_id": quote_id,
      "updates_applied": applied_updates,
      "updated_at": datetime.now().isoformat(),
      "status": "updated",
      "version": "1.1"
    }
  
  async def _send_quote(
    self,
    quote_id: str,
    delivery_method: str = "email",
    recipient_email: str = None
  ) -> Dict[str, Any]:
    """Send quote to customer."""
    # Mock quote sending
    if delivery_method == "email" and not recipient_email:
      return {
        "success": False,
        "error": "Email address required for email delivery"
      }
    
    return {
      "success": True,
      "quote_id": quote_id,
      "delivery_method": delivery_method,
      "recipient": recipient_email,
      "sent_at": datetime.now().isoformat(),
      "tracking_id": f"TRK-{uuid.uuid4().hex[:8].upper()}",
      "estimated_delivery": "Immediate" if delivery_method == "email" else "1-2 business days"
    }
  
  async def _track_quote_status(
    self,
    quote_id: str
  ) -> Dict[str, Any]:
    """Track the status of a quote."""
    # Mock status tracking
    statuses = ["draft", "sent", "viewed", "under_review", "accepted", "rejected", "expired"]
    current_status = "viewed"  # Mock current status
    
    return {
      "quote_id": quote_id,
      "status": current_status,
      "status_history": [
        {"status": "draft", "timestamp": (datetime.now() - timedelta(days=2)).isoformat()},
        {"status": "sent", "timestamp": (datetime.now() - timedelta(days=1)).isoformat()},
        {"status": "viewed", "timestamp": datetime.now().isoformat()}
      ],
      "days_since_sent": 1,
      "follow_up_recommended": True,
      "follow_up_reason": "Quote viewed but no response received"
    }
  
  async def _calculate_commission(
    self,
    quote_total: float,
    sales_rep_id: str,
    commission_rate: float = 0.05
  ) -> Dict[str, Any]:
    """Calculate sales commission for a quote."""
    commission_amount = quote_total * commission_rate
    
    # Tiered commission rates
    if quote_total > 50000:
      commission_rate = 0.08  # 8% for large deals
    elif quote_total > 20000:
      commission_rate = 0.06  # 6% for medium deals
    
    commission_amount = quote_total * commission_rate
    
    return {
      "quote_total": quote_total,
      "sales_rep_id": sales_rep_id,
      "commission_rate": commission_rate,
      "commission_amount": round(commission_amount, 2),
      "tier": "large" if quote_total > 50000 else "medium" if quote_total > 20000 else "standard",
      "calculated_at": datetime.now().isoformat()
    }
  
  async def execute_task(
    self,
    task: str,
    context: Dict[str, Any],
    workflow_id: Optional[str] = None
  ) -> Dict[str, Any]:
    """Execute quote generation tasks."""
    if task == "create_quote":
      quote = await self._generate_quote(
        customer_id=context["customer_id"],
        products=context["products"],
        discount_percentage=context.get("discount_percentage", 0),
        valid_days=context.get("valid_days", 30)
      )
      
      # Calculate commission
      commission = await self._calculate_commission(
        quote_total=quote["final_total"],
        sales_rep_id=context.get("sales_rep_id", "unknown")
      )
      
      quote["commission_info"] = commission
      return quote
    
    elif task == "quote_follow_up":
      quote_id = context["quote_id"]
      status = await self._track_quote_status(quote_id)
      
      # Determine follow-up action
      if status["follow_up_recommended"]:
        follow_up_action = {
          "action": "send_follow_up_email",
          "reason": status["follow_up_reason"],
          "suggested_message": "Following up on your quote - any questions?"
        }
        
        # Publish follow-up event
        await self.publish_event(
          "quote.follow_up_needed",
          {
            "quote_id": quote_id,
            "status": status,
            "follow_up_action": follow_up_action
          },
          trace_id=workflow_id
        )
      
      return {"status": status, "follow_up_needed": status["follow_up_recommended"]}
    
    elif task == "quote_to_deal":
      quote_id = context["quote_id"]
      
      # Convert quote to deal (mock)
      deal_data = {
        "deal_id": f"DEAL-{uuid.uuid4().hex[:8].upper()}",
        "quote_id": quote_id,
        "amount": context["quote_total"],
        "stage": "proposal",
        "probability": 75,
        "expected_close_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "created_at": datetime.now().isoformat()
      }
      
      return deal_data
    
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    """Get quote generator capabilities."""
    return [
      "quote_generation",
      "pricing_calculation",
      "discount_application",
      "quote_tracking",
      "commission_calculation",
      "deal_conversion"
    ]


class GrowthEnginePillar(BusinessPillar):
  """Growth Engine pillar coordinating revenue generation agents."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.GROWTH_ENGINE, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    # Ad Bidder (Worker)
    ad_bidder = AdBidder(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(ad_bidder)
    
    # Pricing Bot (Planner)
    pricing_bot = PricingBot(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    self.register_agent(pricing_bot)
    
    # Quote Generator (Worker - different worker role)
    quote_generator = QuoteGenerator(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    )
    # Register as critic since we already have a worker
    quote_generator.role = AgentRole.CRITIC
    self.register_agent(quote_generator)
  
  async def execute_workflow(
    self,
    workflow_type: str,
    inputs: Dict[str, Any],
    requester: Optional[str] = None
  ) -> WorkflowResult:
    """Execute growth engine workflows."""
    workflow_id = f"growth_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "lead_to_quote":
      return await self._execute_lead_to_quote_workflow(workflow, inputs)
    
    elif workflow_type == "campaign_optimization":
      return await self._execute_campaign_optimization_workflow(workflow, inputs)
    
    elif workflow_type == "pricing_review":
      return await self._execute_pricing_review_workflow(workflow, inputs)
    
    elif workflow_type == "revenue_acceleration":
      return await self._execute_revenue_acceleration_workflow(workflow, inputs)
    
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_lead_to_quote_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute lead to quote conversion workflow."""
    pricing_bot = self.get_agent(AgentRole.PLANNER)
    quote_generator = self.get_agent(AgentRole.CRITIC)
    
    try:
      # Step 1: Calculate optimal pricing
      step1 = WorkflowStep(
        step_id="calculate_pricing",
        agent_role=AgentRole.PLANNER,
        action="optimize_pricing",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      pricing_result = await pricing_bot.execute_task(
        "optimize_pricing",
        inputs,
        workflow.workflow_id
      )
      step1.complete(pricing_result)
      
      # Step 2: Generate quote
      step2 = WorkflowStep(
        step_id="generate_quote",
        agent_role=AgentRole.CRITIC,
        action="create_quote",
        inputs={
          "customer_id": inputs["customer_id"],
          "products": [{
            "product_id": inputs["product_id"],
            "unit_price": pricing_result["optimal_price"],
            "quantity": inputs.get("quantity", 1)
          }]
        }
      )
      step2.start()
      workflow.add_step(step2)
      
      quote_result = await quote_generator.execute_task(
        "create_quote",
        step2.inputs,
        workflow.workflow_id
      )
      step2.complete(quote_result)
      
      workflow.complete({
        "pricing": pricing_result,
        "quote": quote_result
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_campaign_optimization_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute campaign optimization workflow."""
    ad_bidder = self.get_agent(AgentRole.WORKER)
    
    try:
      # Optimize campaign performance
      step1 = WorkflowStep(
        step_id="optimize_campaigns",
        agent_role=AgentRole.WORKER,
        action="optimize_performance",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      optimization_result = await ad_bidder.execute_task(
        "optimize_performance",
        inputs,
        workflow.workflow_id
      )
      step1.complete(optimization_result)
      
      workflow.complete(optimization_result)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_pricing_review_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute pricing strategy review workflow."""
    pricing_bot = self.get_agent(AgentRole.PLANNER)
    
    try:
      # Review pricing strategy
      step1 = WorkflowStep(
        step_id="pricing_strategy_review",
        agent_role=AgentRole.PLANNER,
        action="pricing_strategy_review",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      strategy_result = await pricing_bot.execute_task(
        "pricing_strategy_review",
        inputs,
        workflow.workflow_id
      )
      step1.complete(strategy_result)
      
      workflow.complete(strategy_result)
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  async def _execute_revenue_acceleration_workflow(
    self,
    workflow: WorkflowResult,
    inputs: Dict[str, Any]
  ) -> WorkflowResult:
    """Execute revenue acceleration workflow."""
    try:
      # Cross-agent coordination for revenue boost
      
      # Step 1: Budget check and campaign launch
      ad_bidder = self.get_agent(AgentRole.WORKER)
      step1 = WorkflowStep(
        step_id="launch_boost_campaign",
        agent_role=AgentRole.WORKER,
        action="launch_campaign",
        inputs={
          "campaign_name": "Revenue Acceleration Campaign",
          "channel": inputs.get("channel", "google"),
          "budget": inputs.get("budget", 5000),
          "target_audience": inputs.get("target_audience", {"segment": "enterprise"})
        }
      )
      step1.start()
      workflow.add_step(step1)
      
      campaign_result = await ad_bidder.execute_task(
        "launch_campaign",
        step1.inputs,
        workflow.workflow_id
      )
      step1.complete(campaign_result)
      
      # Step 2: Pricing optimization
      pricing_bot = self.get_agent(AgentRole.PLANNER)
      step2 = WorkflowStep(
        step_id="optimize_pricing",
        agent_role=AgentRole.PLANNER,
        action="optimize_pricing",
        inputs=inputs
      )
      step2.start()
      workflow.add_step(step2)
      
      pricing_result = await pricing_bot.execute_task(
        "optimize_pricing",
        inputs,
        workflow.workflow_id
      )
      step2.complete(pricing_result)
      
      workflow.complete({
        "campaign": campaign_result,
        "pricing": pricing_result,
        "expected_revenue_lift": "15-25%"
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    """Get supported workflow types."""
    return [
      "lead_to_quote",
      "campaign_optimization",
      "pricing_review",
      "revenue_acceleration"
    ]