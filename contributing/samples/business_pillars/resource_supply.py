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

"""Resource & Supply Pillar - Plan, source, make/deliver, pay."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import AgentRole, BusinessPillar, BusinessPillarAgent, PillarType, WorkflowResult, WorkflowStep


class ForecastPlanner(BusinessPillarAgent):
  """Agent for demand forecasting and planning."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="forecast_planner",
      role=AgentRole.PLANNER,
      pillar=PillarType.RESOURCE_SUPPLY,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("generate_demand_forecast", self._generate_demand_forecast, cost=1.5)
    self.register_tool("optimize_inventory_levels", self._optimize_inventory_levels, cost=1.0)
  
  async def _generate_demand_forecast(self, product_id: str, horizon_days: int) -> Dict[str, Any]:
    return {
      "product_id": product_id,
      "forecast_horizon": horizon_days,
      "predicted_demand": 850,
      "confidence_interval": [750, 950],
      "seasonality_factor": 1.2
    }
  
  async def _optimize_inventory_levels(self, products: List[str]) -> Dict[str, Any]:
    return {
      "products": products,
      "optimal_stock_levels": {p: 100 + hash(p) % 200 for p in products},
      "reorder_points": {p: 50 + hash(p) % 50 for p in products}
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "demand_planning":
      forecast = await self._generate_demand_forecast(context["product_id"], context.get("horizon", 30))
      inventory = await self._optimize_inventory_levels([context["product_id"]])
      return {"forecast": forecast, "inventory_optimization": inventory}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["demand_forecasting", "inventory_optimization", "supply_planning"]


class POIssuer(BusinessPillarAgent):
  """Agent for purchase order creation and management."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="po_issuer",
      role=AgentRole.WORKER,
      pillar=PillarType.RESOURCE_SUPPLY,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("create_purchase_order", self._create_purchase_order, cost=2.0)
    self.register_tool("validate_supplier", self._validate_supplier, cost=0.5)
  
  async def _create_purchase_order(self, supplier_id: str, items: List[Dict], total_amount: float) -> Dict[str, Any]:
    po_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Check spending ceiling (guardrail)
    ceiling_limit = 50000  # Example limit
    if total_amount > ceiling_limit:
      return {
        "success": False,
        "error": f"Amount ${total_amount} exceeds ceiling limit of ${ceiling_limit}",
        "po_id": None
      }
    
    return {
      "success": True,
      "po_id": po_id,
      "supplier_id": supplier_id,
      "items": items,
      "total_amount": total_amount,
      "status": "pending_approval",
      "created_at": datetime.now().isoformat()
    }
  
  async def _validate_supplier(self, supplier_id: str) -> Dict[str, Any]:
    return {
      "supplier_id": supplier_id,
      "validation_status": "approved",
      "risk_score": 0.15,
      "certifications": ["ISO9001", "SOC2"]
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "create_po":
      validation = await self._validate_supplier(context["supplier_id"])
      if validation["validation_status"] == "approved":
        po = await self._create_purchase_order(
          context["supplier_id"],
          context["items"],
          context["total_amount"]
        )
        return {"supplier_validation": validation, "purchase_order": po}
      else:
        return {"success": False, "error": "Supplier validation failed"}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["purchase_order_creation", "supplier_validation", "procurement_management"]


class PayablesMatcher(BusinessPillarAgent):
  """Agent for accounts payable and 3-way matching."""
  
  def __init__(self, **kwargs):
    super().__init__(
      agent_id="payables_matcher",
      role=AgentRole.CRITIC,
      pillar=PillarType.RESOURCE_SUPPLY,
      **kwargs
    )
    self._setup_tools()
  
  def _setup_tools(self):
    self.register_tool("perform_three_way_match", self._perform_three_way_match, cost=1.0)
    self.register_tool("approve_payment", self._approve_payment, cost=0.5)
  
  async def _perform_three_way_match(self, po_id: str, invoice_id: str, receipt_id: str) -> Dict[str, Any]:
    # Mock 3-way match validation
    return {
      "po_id": po_id,
      "invoice_id": invoice_id,
      "receipt_id": receipt_id,
      "match_status": "matched",
      "discrepancies": [],
      "amount_variance": 0.0,
      "approved_for_payment": True
    }
  
  async def _approve_payment(self, invoice_id: str, amount: float) -> Dict[str, Any]:
    return {
      "invoice_id": invoice_id,
      "payment_approved": True,
      "payment_amount": amount,
      "payment_date": datetime.now().isoformat(),
      "payment_method": "ACH"
    }
  
  async def execute_task(self, task: str, context: Dict[str, Any], workflow_id: Optional[str] = None) -> Dict[str, Any]:
    if task == "process_invoice":
      match_result = await self._perform_three_way_match(
        context["po_id"],
        context["invoice_id"],
        context["receipt_id"]
      )
      if match_result["approved_for_payment"]:
        payment = await self._approve_payment(context["invoice_id"], context["amount"])
        return {"three_way_match": match_result, "payment_approval": payment}
      else:
        return {"three_way_match": match_result, "payment_approved": False}
    else:
      raise ValueError(f"Unknown task: {task}")
  
  def get_capabilities(self) -> List[str]:
    return ["three_way_matching", "payment_approval", "invoice_validation"]


class ResourceSupplyPillar(BusinessPillar):
  """Resource & Supply pillar coordinating procurement and supply chain."""
  
  def __init__(self, **kwargs):
    super().__init__(PillarType.RESOURCE_SUPPLY, **kwargs)
    self._setup_agents()
  
  def _setup_agents(self):
    """Setup all agents for this pillar."""
    self.register_agent(ForecastPlanner(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(POIssuer(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
    
    self.register_agent(PayablesMatcher(
      control_plane_agent=None,
      event_bus=self.event_bus,
      lineage_service=self.lineage_service
    ))
  
  async def execute_workflow(self, workflow_type: str, inputs: Dict[str, Any], requester: Optional[str] = None) -> WorkflowResult:
    """Execute procurement workflows."""
    workflow_id = f"supply_{workflow_type}_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowResult(workflow_id=workflow_id, pillar=self.pillar_type)
    
    if workflow_type == "procurement_cycle":
      return await self._execute_procurement_cycle(workflow, inputs)
    else:
      workflow.fail(f"Unknown workflow type: {workflow_type}")
      return workflow
  
  async def _execute_procurement_cycle(self, workflow: WorkflowResult, inputs: Dict[str, Any]) -> WorkflowResult:
    """Execute full procurement cycle."""
    try:
      # Step 1: Demand planning
      planner = self.get_agent(AgentRole.PLANNER)
      step1 = WorkflowStep(
        step_id="demand_planning",
        agent_role=AgentRole.PLANNER,
        action="demand_planning",
        inputs=inputs
      )
      step1.start()
      workflow.add_step(step1)
      
      planning = await planner.execute_task("demand_planning", inputs, workflow.workflow_id)
      step1.complete(planning)
      
      # Step 2: Create PO
      po_issuer = self.get_agent(AgentRole.WORKER)
      step2 = WorkflowStep(
        step_id="create_po",
        agent_role=AgentRole.WORKER,
        action="create_po",
        inputs=inputs
      )
      step2.start()
      workflow.add_step(step2)
      
      po_result = await po_issuer.execute_task("create_po", inputs, workflow.workflow_id)
      step2.complete(po_result)
      
      workflow.complete({
        "demand_planning": planning,
        "purchase_order": po_result
      })
      
    except Exception as e:
      workflow.fail(str(e))
    
    return workflow
  
  def get_workflow_types(self) -> List[str]:
    return ["procurement_cycle"]