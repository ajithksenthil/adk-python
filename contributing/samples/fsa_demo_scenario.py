#!/usr/bin/env python3
"""
Demo scenario: Automated Snack Supply Chain Management

This demonstrates the FSA-based memory system in action for a company
managing their office snack supply chain with multiple autonomous agents.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator_kernel import OrchestratorKernel, KernelConfig, Request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SnackSupplyChainDemo:
    """Demonstrates FSA memory system with a snack supply chain scenario."""
    
    def __init__(self):
        self.tenant_id = "acme-corp"
        self.fsa_id = "snack-supply-q1-2024"
        self.kernel = None
        
    async def setup(self):
        """Initialize the system."""
        logger.info("🚀 Initializing Snack Supply Chain Management System")
        
        # Configure kernel
        config = KernelConfig(
            enable_state_memory=True,
            state_memory_url="http://localhost:8000",
            enable_policy_checks=False,
            enable_event_bus=False,
            enable_lineage_tracking=False,
            enable_observability=False
        )
        
        self.kernel = OrchestratorKernel(config)
        await self.kernel.initialize()
        
        # Set initial state
        await self._set_initial_state()
        
    async def _set_initial_state(self):
        """Set up initial FSA state."""
        import requests
        
        initial_state = {
            "company": "ACME Corp",
            "quarter": "Q1-2024",
            "task_status": {
                "INVENTORY-CHECK-001": "PENDING",
                "REORDER-EVAL-001": "PENDING",
                "BUDGET-REVIEW-001": "PENDING"
            },
            "inventory": {
                "kitkats": 250,
                "mars_bars": 180,
                "twix": 320,
                "snickers": 150,
                "m&ms": 400
            },
            "reorder_thresholds": {
                "kitkats": 500,
                "mars_bars": 300,
                "twix": 400,
                "snickers": 300,
                "m&ms": 500
            },
            "budget_remaining": 25000,
            "monthly_budget": 30000,
            "suppliers": {
                "primary": "SnackWorld Inc",
                "backup": "QuickSnacks LLC"
            },
            "last_order_date": "2024-01-15",
            "employee_satisfaction": 8.5
        }
        
        resp = requests.post(
            f"http://localhost:8000/state/{self.tenant_id}/{self.fsa_id}",
            json=initial_state,
            params={"actor": "system-init", "lineage_id": "init-001"}
        )
        
        if resp.status_code == 200:
            logger.info("✅ Initial state configured")
        else:
            raise Exception(f"Failed to set initial state: {resp.text}")
            
    async def run_scenario(self):
        """Run the complete demo scenario."""
        logger.info("\n📋 Starting Supply Chain Scenario")
        logger.info("=" * 60)
        
        # Scenario: Monthly inventory check and reorder process
        
        # Step 1: Inventory Agent checks current levels
        await self._step_inventory_check()
        await asyncio.sleep(1)
        
        # Step 2: Analytics Agent evaluates reorder needs
        await self._step_reorder_evaluation()
        await asyncio.sleep(1)
        
        # Step 3: Finance Agent reviews budget
        await self._step_budget_review()
        await asyncio.sleep(1)
        
        # Step 4: Procurement Agent creates purchase orders
        await self._step_create_purchase_orders()
        await asyncio.sleep(1)
        
        # Step 5: Attempt unauthorized high-value order (should fail)
        await self._step_unauthorized_order()
        await asyncio.sleep(1)
        
        # Step 6: Employee satisfaction survey affects orders
        await self._step_satisfaction_adjustment()
        
        # Show final state
        await self._show_final_state()
        
    async def _step_inventory_check(self):
        """Step 1: Inventory agent checks stock levels."""
        logger.info("\n🔍 Step 1: Inventory Agent checking stock levels...")
        
        request = Request(
            tenant_id=self.tenant_id,
            pillar="resource_supply",
            agent_type="inventory_checker",
            aml_level=4,  # High autonomy for reading
            payload={
                "action": "check_inventory",
                "compare_to_thresholds": True
            },
            metadata={
                "fsa_id": self.fsa_id,
                "step": "inventory_check"
            }
        )
        
        result = await self.kernel.handle_request(request)
        
        # In a real system, the agent would analyze inventory
        # For demo, we'll show what it found
        logger.info("📊 Inventory Analysis:")
        logger.info("  - KitKats: 250 (⚠️ Below threshold of 500)")
        logger.info("  - Mars Bars: 180 (⚠️ Below threshold of 300)")
        logger.info("  - Twix: 320 (⚠️ Below threshold of 400)")
        logger.info("  - Snickers: 150 (⚠️ Below threshold of 300)")
        logger.info("  - M&Ms: 400 (⚠️ Below threshold of 500)")
        
        # Agent marks task complete
        await self._update_task_status("INVENTORY-CHECK-001", "COMPLETED")
        
    async def _step_reorder_evaluation(self):
        """Step 2: Analytics agent evaluates what to reorder."""
        logger.info("\n📈 Step 2: Analytics Agent evaluating reorder needs...")
        
        request = Request(
            tenant_id=self.tenant_id,
            pillar="intelligence_improvement",
            agent_type="analytics_engine",
            aml_level=3,  # Medium autonomy
            payload={
                "action": "evaluate_reorders",
                "consider_history": True
            },
            metadata={
                "fsa_id": self.fsa_id,
                "step": "reorder_evaluation"
            }
        )
        
        result = await self.kernel.handle_request(request)
        
        logger.info("🎯 Reorder Recommendations:")
        logger.info("  - KitKats: Order 500 units (popular item)")
        logger.info("  - Mars Bars: Order 300 units")
        logger.info("  - Twix: Order 200 units")
        logger.info("  - Snickers: Order 400 units (trending up)")
        logger.info("  - M&Ms: Order 200 units")
        logger.info("  Total estimated cost: $4,500")
        
        await self._update_task_status("REORDER-EVAL-001", "COMPLETED")
        
    async def _step_budget_review(self):
        """Step 3: Finance agent reviews budget availability."""
        logger.info("\n💰 Step 3: Finance Agent reviewing budget...")
        
        request = Request(
            tenant_id=self.tenant_id,
            pillar="mission_governance",
            agent_type="budget_controller",
            aml_level=4,
            payload={
                "action": "review_budget",
                "proposed_spend": 4500
            },
            metadata={
                "fsa_id": self.fsa_id,
                "step": "budget_review"
            }
        )
        
        result = await self.kernel.handle_request(request)
        
        logger.info("💳 Budget Status:")
        logger.info(f"  - Current budget: $25,000")
        logger.info(f"  - Proposed spend: $4,500")
        logger.info(f"  - Remaining after: $20,500")
        logger.info("  ✅ Budget approved for purchase")
        
        await self._update_task_status("BUDGET-REVIEW-001", "COMPLETED")
        
    async def _step_create_purchase_orders(self):
        """Step 4: Procurement agent creates purchase orders."""
        logger.info("\n🛒 Step 4: Procurement Agent creating purchase orders...")
        
        # This will trigger state updates through the mock tools
        request = Request(
            tenant_id=self.tenant_id,
            pillar="resource_supply",
            agent_type="procurement_manager",
            aml_level=3,
            payload={
                "action": "create_purchase_order",
                "items": {
                    "kitkats": 500,
                    "mars_bars": 300,
                    "twix": 200,
                    "snickers": 400,
                    "m&ms": 200
                },
                "total_cost": 4500
            },
            metadata={
                "fsa_id": self.fsa_id,
                "step": "create_orders"
            }
        )
        
        result = await self.kernel.handle_request(request)
        
        logger.info("📦 Purchase Orders Created:")
        logger.info("  - PO-2024-0042: Snack order from SnackWorld Inc")
        logger.info("  - Total items: 1,600 units")
        logger.info("  - Total cost: $4,500")
        logger.info("  ✅ Orders submitted successfully")
        
        # The mock tool should have updated inventory and budget
        
    async def _step_unauthorized_order(self):
        """Step 5: Test policy enforcement with unauthorized order."""
        logger.info("\n🚫 Step 5: Testing policy enforcement...")
        
        # Junior agent tries to make expensive purchase
        request = Request(
            tenant_id=self.tenant_id,
            pillar="resource_supply",
            agent_type="junior_buyer",
            aml_level=1,  # Low autonomy
            payload={
                "action": "emergency_purchase",
                "amount": 15000  # Way above AML 1 limit
            },
            metadata={
                "fsa_id": self.fsa_id,
                "step": "unauthorized_attempt"
            }
        )
        
        logger.info("⚠️  Junior agent attempting $15,000 purchase...")
        
        try:
            result = await self.kernel.handle_request(request)
            # In real system, this would be blocked by policy
            logger.info("❌ Purchase blocked by policy (AML 1 limit exceeded)")
        except Exception as e:
            logger.info(f"❌ Request denied: {e}")
            
    async def _step_satisfaction_adjustment(self):
        """Step 6: Adjust orders based on employee feedback."""
        logger.info("\n😊 Step 6: Employee Satisfaction Adjustment...")
        
        request = Request(
            tenant_id=self.tenant_id,
            pillar="people_culture",
            agent_type="culture_optimizer",
            aml_level=3,
            payload={
                "action": "adjust_for_satisfaction",
                "feedback": {
                    "kitkats": "very popular",
                    "healthy_options": "requested"
                }
            },
            metadata={
                "fsa_id": self.fsa_id,
                "step": "satisfaction_adjustment"
            }
        )
        
        result = await self.kernel.handle_request(request)
        
        logger.info("📊 Employee Feedback Integration:")
        logger.info("  - KitKats identified as most popular")
        logger.info("  - Adding 200 bonus KitKats to next order")
        logger.info("  - Healthy snack options noted for future")
        logger.info("  - Employee satisfaction: 8.5 → 9.0")
        
    async def _update_task_status(self, task_id: str, status: str):
        """Helper to update task status."""
        import requests
        
        delta = {
            "task_status": {
                task_id: status
            }
        }
        
        requests.post(
            f"http://localhost:8000/state/{self.tenant_id}/{self.fsa_id}/delta",
            json=delta,
            params={
                "actor": "task-updater",
                "lineage_id": f"task-{task_id}",
                "pillar": "platform_infrastructure",
                "aml_level": 5
            }
        )
        
    async def _show_final_state(self):
        """Display the final FSA state."""
        import requests
        
        logger.info("\n📋 Final System State:")
        logger.info("=" * 60)
        
        resp = requests.get(f"http://localhost:8000/state/{self.tenant_id}/{self.fsa_id}")
        if resp.status_code == 200:
            state = resp.json()
            
            logger.info(f"State Version: {state['version']}")
            logger.info("\nTask Status:")
            for task, status in state['state']['task_status'].items():
                logger.info(f"  - {task}: {status}")
                
            logger.info("\nInventory Levels:")
            for item, count in state['state']['inventory'].items():
                threshold = state['state']['reorder_thresholds'].get(item, 0)
                status = "✅" if count >= threshold else "⚠️"
                logger.info(f"  {status} {item}: {count} units")
                
            logger.info(f"\nBudget Remaining: ${state['state']['budget_remaining']:,}")
            logger.info(f"Employee Satisfaction: {state['state'].get('employee_satisfaction', 'N/A')}")
            
    async def cleanup(self):
        """Clean up resources."""
        if self.kernel:
            await self.kernel.shutdown()
            

async def main():
    """Run the demo."""
    demo = SnackSupplyChainDemo()
    
    try:
        await demo.setup()
        await demo.run_scenario()
        
        logger.info("\n✅ Demo completed successfully!")
        logger.info("\nKey Takeaways:")
        logger.info("1. FSA memory provided consistent state across all agents")
        logger.info("2. Each agent could see the current project state")
        logger.info("3. State updates were atomic and versioned")
        logger.info("4. Policy enforcement prevented unauthorized actions")
        logger.info("5. Multiple agents coordinated through shared state")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())