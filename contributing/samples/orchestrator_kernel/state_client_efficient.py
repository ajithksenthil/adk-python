"""Efficient State Memory Client using slice-based queries."""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass 
class StateSlice:
    """Efficient state slice with summary."""
    tenant_id: str
    fsa_id: str
    version: int
    slice_data: Dict[str, Any]
    summary: str
    slice_pattern: str
    
    @property
    def tasks(self) -> Dict[str, Any]:
        """Get tasks from slice if present."""
        return self.slice_data.get("tasks", {})
        
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get metrics from slice if present."""
        return self.slice_data.get("metrics", {})
        
    @property
    def resources(self) -> Dict[str, Any]:
        """Get resources from slice if present."""
        return self.slice_data.get("resources", {})


class EfficientStateMemoryClient:
    """
    Efficient state client that uses slice queries to minimize data transfer.
    
    This implements the "read-small" part of the efficiency pattern.
    """
    
    def __init__(self, sms_base_url: str = "http://localhost:8000"):
        self.base_url = sms_base_url
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            
    async def get_slice(self, tenant_id: str, fsa_id: str, 
                       slice_pattern: str, k: Optional[int] = None) -> Optional[StateSlice]:
        """
        Get a slice of state efficiently.
        
        Args:
            tenant_id: Tenant ID
            fsa_id: FSA ID
            slice_pattern: Pattern like "task:DESIGN_*" or "resources.inventory"
            k: Limit number of results
            
        Returns:
            StateSlice with just the requested data
        """
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/state/{tenant_id}/{fsa_id}/slice"
            params = {"slice": slice_pattern}
            if k:
                params["k"] = k
                
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return StateSlice(
                        tenant_id=tenant_id,
                        fsa_id=fsa_id,
                        version=data.get("version", 0),
                        slice_data=data.get("slice", {}),
                        summary=data.get("summary", ""),
                        slice_pattern=slice_pattern
                    )
                else:
                    logger.warning(f"Failed to get slice: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching slice: {e}")
            return None
            
    async def get_my_tasks(self, tenant_id: str, fsa_id: str, 
                          team: str, limit: int = 10) -> Optional[StateSlice]:
        """Get tasks assigned to my team."""
        # Use wildcard to get all tasks, then filter client-side
        # In production, could add team-based patterns
        return await self.get_slice(tenant_id, fsa_id, "task:*", k=limit)
        
    async def get_task_context(self, tenant_id: str, fsa_id: str,
                              task_id: str) -> Optional[StateSlice]:
        """Get specific task context."""
        return await self.get_slice(tenant_id, fsa_id, f"task:{task_id}")
        
    async def get_resources_summary(self, tenant_id: str, fsa_id: str) -> Optional[StateSlice]:
        """Get just the resources section."""
        return await self.get_slice(tenant_id, fsa_id, "resources.*")
        
    async def get_metrics_snapshot(self, tenant_id: str, fsa_id: str,
                                  metric_prefix: str = "") -> Optional[StateSlice]:
        """Get metrics, optionally filtered by prefix."""
        if metric_prefix:
            return await self.get_slice(tenant_id, fsa_id, f"metric:{metric_prefix}*")
        else:
            return await self.get_slice(tenant_id, fsa_id, "metric:*", k=20)
            
    async def get_online_agents(self, tenant_id: str, fsa_id: str,
                               pattern: str = "*") -> Optional[StateSlice]:
        """Get online agents matching pattern."""
        return await self.get_slice(tenant_id, fsa_id, f"agent:{pattern}")
        
    async def apply_delta(self, tenant_id: str, fsa_id: str, delta: Dict[str, Any],
                         actor: str, lineage_id: str, pillar: str = "",
                         aml_level: int = 0) -> bool:
        """Apply a state delta (write-small)."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/state/{tenant_id}/{fsa_id}/delta"
            params = {
                "actor": actor,
                "lineage_id": lineage_id,
                "pillar": pillar,
                "aml_level": aml_level
            }
            
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


class AgentContextBuilder:
    """
    Helper to build efficient agent context using slices.
    
    This demonstrates the "laser-cut READ" pattern.
    """
    
    def __init__(self, client: EfficientStateMemoryClient):
        self.client = client
        
    async def build_agent_context(self, tenant_id: str, fsa_id: str,
                                 agent_name: str, agent_type: str) -> str:
        """
        Build minimal context for an agent using targeted slices.
        
        This is what gets injected into the agent's prompt.
        """
        context_parts = []
        
        # Based on agent type, fetch only relevant slices
        if "task" in agent_type or "worker" in agent_type:
            # Get active tasks
            slice_data = await self.client.get_slice(
                tenant_id, fsa_id, "task:*", k=5
            )
            if slice_data and slice_data.summary:
                context_parts.append(f"=== Active Tasks ===\n{slice_data.summary}")
                
        elif "metrics" in agent_type or "analytics" in agent_type:
            # Get recent metrics
            slice_data = await self.client.get_slice(
                tenant_id, fsa_id, "metric:*", k=10
            )
            if slice_data and slice_data.summary:
                context_parts.append(f"=== Metrics ===\n{slice_data.summary}")
                
        elif "resource" in agent_type or "budget" in agent_type:
            # Get resources and caps
            slice_data = await self.client.get_slice(
                tenant_id, fsa_id, "resources.*"
            )
            if slice_data and slice_data.summary:
                context_parts.append(f"=== Resources ===\n{slice_data.summary}")
                
        # Always include agent's own status
        agent_slice = await self.client.get_slice(
            tenant_id, fsa_id, f"agent:{agent_name}"
        )
        if agent_slice:
            context_parts.append(f"=== My Status ===\nLast heartbeat: v{agent_slice.version}")
            
        # Combine into minimal context (1-2K tokens)
        return "\n\n".join(context_parts) if context_parts else "No context available"
        
    async def get_task_working_set(self, tenant_id: str, fsa_id: str,
                                  task_pattern: str) -> Dict[str, Any]:
        """Get minimal working set for a task."""
        working_set = {}
        
        # Get the specific tasks
        task_slice = await self.client.get_slice(
            tenant_id, fsa_id, f"task:{task_pattern}"
        )
        if task_slice:
            working_set["tasks"] = task_slice.tasks
            working_set["version"] = task_slice.version
            
        # Get related resources if needed
        if "budget" in task_pattern.lower() or "purchase" in task_pattern.lower():
            resource_slice = await self.client.get_slice(
                tenant_id, fsa_id, "resources.cash_balance_usd"
            )
            if resource_slice:
                working_set["budget"] = resource_slice.resources.get("cash_balance_usd", 0)
                
        return working_set