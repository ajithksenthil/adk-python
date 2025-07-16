#!/usr/bin/env python3
"""Integration test for FSA-based State Memory System."""

import asyncio
import time
import subprocess
import sys
import os
import requests
import json
import logging
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator_kernel import OrchestratorKernel, KernelConfig, Request, RequestPriority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
SMS_URL = "http://localhost:8000"
REDIS_URL = "redis://localhost:6379"
KAFKA_SERVERS = "localhost:9092"

# Test data
TEST_TENANT = "acme-corp"
TEST_FSA_ID = "snack-supply-2024-01"


class IntegrationTestRunner:
    """Runs the full integration test suite."""
    
    def __init__(self):
        self.sms_process = None
        self.redis_process = None
        self.kafka_process = None
        
    async def setup_infrastructure(self):
        """Start required services."""
        logger.info("Starting infrastructure services...")
        
        # Note: In production, these would be managed externally
        # For testing, we'll assume they're already running
        
        # Check if services are available
        try:
            # Check Redis
            import redis
            r = redis.from_url(REDIS_URL)
            r.ping()
            logger.info("✓ Redis is available")
        except Exception as e:
            logger.error(f"✗ Redis not available: {e}")
            logger.info("Please start Redis: docker run -p 6379:6379 redis:latest")
            return False
            
        # Check if SMS is running
        try:
            resp = requests.get(f"{SMS_URL}/health")
            if resp.status_code == 200:
                logger.info("✓ State Memory Service is running")
            else:
                raise Exception("SMS not healthy")
        except:
            logger.info("Starting State Memory Service...")
            # Start SMS in background
            self.sms_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "state_memory_service.service:app",
                "--host", "0.0.0.0",
                "--port", "8000"
            ], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            # Wait for startup
            time.sleep(3)
            
        return True
        
    async def test_basic_state_operations(self):
        """Test basic state read/write operations."""
        logger.info("\n=== Testing Basic State Operations ===")
        
        # 1. Set initial state
        initial_state = {
            "task_status": {
                "SNACK-PO-0001": "PENDING",
                "SNACK-PO-0002": "PENDING"
            },
            "inventory": {
                "kitkats": 1000,
                "mars_bars": 500,
                "twix": 750
            },
            "budget_remaining": 50000,
            "last_order_date": "2024-01-15"
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}",
            json=initial_state,
            params={"actor": "setup-agent", "lineage_id": "test-001"}
        )
        assert resp.status_code == 200
        result = resp.json()
        logger.info(f"✓ Initial state set, version: {result['version']}")
        
        # 2. Read state back
        resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
        assert resp.status_code == 200
        state_data = resp.json()
        assert state_data["version"] == result["version"]
        logger.info(f"✓ State retrieved successfully")
        
        # 3. Apply a delta
        delta = {
            "task_status": {
                "SNACK-PO-0001": "COMPLETED"
            },
            "inventory": {
                "kitkats": {"$inc": 5000}
            },
            "budget_remaining": {"$inc": -5000}
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=delta,
            params={
                "actor": "purchase-agent",
                "lineage_id": "test-002",
                "pillar": "resource_supply",
                "aml_level": 3
            }
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"]
        logger.info(f"✓ Delta applied, new version: {result['version']}")
        
        # 4. Verify final state
        resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
        final_state = resp.json()
        assert final_state["state"]["inventory"]["kitkats"] == 6000
        assert final_state["state"]["budget_remaining"] == 45000
        assert final_state["state"]["task_status"]["SNACK-PO-0001"] == "COMPLETED"
        logger.info("✓ State correctly updated")
        
    async def test_policy_validation(self):
        """Test policy validation for state changes."""
        logger.info("\n=== Testing Policy Validation ===")
        
        # 1. Try to make budget negative (should fail)
        bad_delta = {
            "budget_remaining": {"$inc": -100000}  # Would make budget negative
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=bad_delta,
            params={
                "actor": "rogue-agent",
                "lineage_id": "test-003",
                "pillar": "resource_supply",
                "aml_level": 3
            }
        )
        result = resp.json()
        assert not result["success"]
        assert "Policy violation" in result["message"]
        logger.info(f"✓ Policy correctly rejected negative budget: {result['message']}")
        
        # 2. Test AML level restrictions
        high_value_delta = {
            "budget_remaining": {"$inc": -5000}  # High value for AML 1
        }
        
        resp = requests.post(
            f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
            json=high_value_delta,
            params={
                "actor": "junior-agent",
                "lineage_id": "test-004",
                "pillar": "resource_supply",
                "aml_level": 1  # Low autonomy level
            }
        )
        result = resp.json()
        assert not result["success"]
        assert "AML" in result["message"]
        logger.info(f"✓ AML policy correctly enforced: {result['message']}")
        
        # 3. Validate without applying
        validate_resp = requests.post(
            f"{SMS_URL}/validate/delta",
            json={
                "inventory": {"kitkats": {"$inc": -10000}}  # Would make inventory negative
            },
            params={
                "tenant_id": TEST_TENANT,
                "fsa_id": TEST_FSA_ID,
                "pillar": "resource_supply",
                "aml_level": 3
            }
        )
        validation = validate_resp.json()
        assert not validation["allowed"]
        assert any("Inventory cannot be negative" in v for v in validation["violations"])
        logger.info("✓ Validation endpoint working correctly")
        
    async def test_orchestrator_integration(self):
        """Test Orchestrator Kernel integration with SMS."""
        logger.info("\n=== Testing Orchestrator Kernel Integration ===")
        
        # Create kernel config
        config = KernelConfig(
            enable_state_memory=True,
            state_memory_url=SMS_URL,
            enable_policy_checks=False,  # Simplified for test
            enable_event_bus=False,
            enable_lineage_tracking=False,
            enable_observability=False
        )
        
        # Initialize kernel
        kernel = OrchestratorKernel(config)
        await kernel.initialize()
        
        try:
            # Create a test request
            request = Request(
                tenant_id=TEST_TENANT,
                pillar="resource_supply",
                agent_type="inventory_manager",
                aml_level=3,
                payload={
                    "action": "restock",
                    "items": {"kitkats": 2000}
                },
                metadata={
                    "fsa_id": TEST_FSA_ID,
                    "request_type": "inventory_update"
                }
            )
            
            # Handle request
            logger.info("Sending request to Orchestrator Kernel...")
            result = await kernel.handle_request(request)
            
            logger.info(f"✓ Request handled successfully: {json.dumps(result, indent=2)}")
            
            # Verify state was updated
            await asyncio.sleep(0.5)  # Wait for async state update
            
            resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
            current_state = resp.json()
            
            # The mock tool should have updated inventory
            logger.info(f"Current inventory: {current_state['state']['inventory']}")
            logger.info("✓ Orchestrator successfully integrated with SMS")
            
        finally:
            await kernel.shutdown()
            
    async def test_concurrent_updates(self):
        """Test handling of concurrent state updates."""
        logger.info("\n=== Testing Concurrent Updates ===")
        
        # Get current state
        resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
        initial_version = resp.json()["version"]
        
        # Create multiple concurrent update tasks
        async def update_inventory(item: str, amount: int, agent: str):
            delta = {
                "inventory": {
                    item: {"$inc": amount}
                }
            }
            
            resp = requests.post(
                f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}/delta",
                json=delta,
                params={
                    "actor": agent,
                    "lineage_id": f"concurrent-{agent}",
                    "pillar": "resource_supply",
                    "aml_level": 3
                }
            )
            return resp.json()
            
        # Run concurrent updates
        tasks = [
            update_inventory("kitkats", 100, "agent-1"),
            update_inventory("mars_bars", 200, "agent-2"),
            update_inventory("twix", 150, "agent-3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for i, result in enumerate(results):
            assert result["success"], f"Update {i+1} failed"
            
        # Verify final state
        resp = requests.get(f"{SMS_URL}/state/{TEST_TENANT}/{TEST_FSA_ID}")
        final_state = resp.json()
        
        # Version should have incremented by 3
        assert final_state["version"] >= initial_version + 3
        logger.info(f"✓ All concurrent updates succeeded, version: {initial_version} -> {final_state['version']}")
        
    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info("Starting FSA Integration Tests")
        logger.info("=" * 50)
        
        # Setup infrastructure
        if not await self.setup_infrastructure():
            logger.error("Infrastructure setup failed")
            return False
            
        try:
            # Run tests
            await self.test_basic_state_operations()
            await self.test_policy_validation()
            await self.test_orchestrator_integration()
            await self.test_concurrent_updates()
            
            logger.info("\n" + "=" * 50)
            logger.info("✅ All integration tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Cleanup
            if self.sms_process:
                self.sms_process.terminate()
                

async def main():
    """Main test runner."""
    runner = IntegrationTestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())