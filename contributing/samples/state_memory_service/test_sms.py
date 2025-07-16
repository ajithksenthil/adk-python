"""Test script for State Memory Service."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_basic_operations():
    """Test basic SMS operations."""
    tenant_id = "test-tenant"
    fsa_id = "test-fsa-001"
    
    print("Testing State Memory Service...")
    
    # 1. Health check
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {resp.json()}")
    
    # 2. Get initial state (should be empty)
    resp = requests.get(f"{BASE_URL}/state/{tenant_id}/{fsa_id}")
    print(f"\nInitial state: {resp.json()}")
    
    # 3. Set initial state
    initial_state = {
        "task_status": {
            "SNACK-PO-0001": "PENDING"
        },
        "inventory": {
            "kitkats": 1000,
            "mars_bars": 500
        },
        "budget_remaining": 10000
    }
    
    resp = requests.post(
        f"{BASE_URL}/state/{tenant_id}/{fsa_id}",
        json=initial_state,
        params={"actor": "test-agent", "lineage_id": "test-lineage-001"}
    )
    print(f"\nSet state response: {resp.json()}")
    
    # 4. Get state after set
    resp = requests.get(f"{BASE_URL}/state/{tenant_id}/{fsa_id}")
    print(f"\nState after set: {resp.json()}")
    
    # 5. Apply delta
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
        f"{BASE_URL}/state/{tenant_id}/{fsa_id}/delta",
        json=delta,
        params={"actor": "purchase-agent", "lineage_id": "test-lineage-002"}
    )
    print(f"\nApply delta response: {resp.json()}")
    
    # 6. Get final state
    resp = requests.get(f"{BASE_URL}/state/{tenant_id}/{fsa_id}")
    final_state = resp.json()
    print(f"\nFinal state: {json.dumps(final_state, indent=2)}")
    
    # Verify results
    assert final_state["state"]["inventory"]["kitkats"] == 6000
    assert final_state["state"]["budget_remaining"] == 5000
    assert final_state["version"] == 2
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_basic_operations()