"""State Memory Service client for Orchestrator Kernel."""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """Snapshot of FSA state for agent context."""
    tenant_id: str
    fsa_id: str
    version: int
    state: Dict[str, Any]
    summary: str  # Token-limited summary for prompt


class StateMemoryClient:
    """Client for interacting with State Memory Service."""
    
    def __init__(self, sms_base_url: str = "http://localhost:8000"):
        self.base_url = sms_base_url
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            
    async def get_state(self, tenant_id: str, fsa_id: str) -> Optional[StateSnapshot]:
        """Retrieve current state from SMS."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/state/{tenant_id}/{fsa_id}"
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Create summary for prompt inclusion
                    summary = self._summarize_state(data.get("state", {}))
                    
                    return StateSnapshot(
                        tenant_id=tenant_id,
                        fsa_id=fsa_id,
                        version=data.get("version", 0),
                        state=data.get("state", {}),
                        summary=summary
                    )
                else:
                    logger.warning(f"Failed to get state: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching state: {e}")
            return None
            
    async def apply_delta(self, tenant_id: str, fsa_id: str, delta: Dict[str, Any],
                         actor: str, lineage_id: str) -> bool:
        """Apply a state delta through SMS."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/state/{tenant_id}/{fsa_id}/delta"
            params = {"actor": actor, "lineage_id": lineage_id}
            
            async with self._session.post(url, json=delta, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("success", False)
                else:
                    logger.warning(f"Failed to apply delta: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error applying delta: {e}")
            return False
            
    def _summarize_state(self, state: Dict[str, Any], max_tokens: int = 2000) -> str:
        """Create a token-limited summary of state for prompt inclusion."""
        # Simple JSON summary - in production, use token counting
        summary_parts = []
        
        # Extract key information
        if "task_status" in state:
            summary_parts.append(f"Tasks: {json.dumps(state['task_status'], indent=2)}")
            
        if "inventory" in state:
            summary_parts.append(f"Inventory: {json.dumps(state['inventory'], indent=2)}")
            
        if "budget_remaining" in state:
            summary_parts.append(f"Budget: ${state['budget_remaining']}")
            
        # Add other important fields
        for key, value in state.items():
            if key not in ["task_status", "inventory", "budget_remaining", "_metadata"]:
                if isinstance(value, (str, int, float, bool)):
                    summary_parts.append(f"{key}: {value}")
                    
        summary = "\n".join(summary_parts)
        
        # Truncate if too long (simple char limit for now)
        if len(summary) > max_tokens:
            summary = summary[:max_tokens-3] + "..."
            
        return summary