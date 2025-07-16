"""Enhanced State Memory Client for Orchestrator Kernel."""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EnhancedStateSnapshot:
    """Enhanced snapshot of FSA state for agent context."""
    tenant_id: str
    fsa_id: str
    version: int
    state: Dict[str, Any]
    summary: str
    
    # Quick accessors for common needs
    @property
    def active_tasks(self) -> Dict[str, Any]:
        """Get tasks that aren't completed."""
        return {
            tid: task for tid, task in self.state.get("tasks", {}).items()
            if task.get("status") not in ["COMPLETED", "CANCELLED"]
        }
    
    @property
    def current_sprint(self) -> str:
        """Get current sprint."""
        return self.state.get("active_state", {}).get("current_sprint", "")
    
    @property 
    def available_budget(self) -> float:
        """Get available budget."""
        return self.state.get("resources", {}).get("cash_balance_usd", 0)
    
    @property
    def my_aml_level(self) -> int:
        """Get AML level for current pillar."""
        # This would be set based on the request context
        return 0


class EnhancedStateMemoryClient:
    """Enhanced client for comprehensive state management."""
    
    def __init__(self, sms_base_url: str = "http://localhost:8000"):
        self.base_url = sms_base_url
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            
    async def get_state(self, tenant_id: str, fsa_id: str, 
                       include_summary: bool = True) -> Optional[EnhancedStateSnapshot]:
        """Retrieve current state with summary."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/state/{tenant_id}/{fsa_id}"
            params = {"summary": include_summary}
            
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract state and summary
                    if include_summary and "summary" in data:
                        state = {}  # Will fetch full state separately if needed
                        summary = data["summary"]
                        version = data["version"]
                    else:
                        state = data
                        version = state.get("lineage_version", 0)
                        summary = self._create_agent_summary(state)
                    
                    # If we need full state but only got summary
                    if include_summary and "summary" in data:
                        async with self._session.get(url) as resp2:
                            if resp2.status == 200:
                                state = await resp2.json()
                    
                    return EnhancedStateSnapshot(
                        tenant_id=tenant_id,
                        fsa_id=fsa_id,
                        version=version,
                        state=state,
                        summary=summary
                    )
                else:
                    logger.warning(f"Failed to get state: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching state: {e}")
            return None
            
    async def apply_delta(self, tenant_id: str, fsa_id: str, delta: Dict[str, Any],
                         actor: str, lineage_id: str, pillar: str = "",
                         aml_level: int = 0) -> bool:
        """Apply a state delta through SMS."""
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
            
    async def add_comment(self, tenant_id: str, fsa_id: str, task_id: str,
                         author: str, body: str, lineage_id: str,
                         is_blocker: bool = False) -> Optional[str]:
        """Add a comment to a task."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/tasks/{tenant_id}/{fsa_id}/{task_id}/comment"
            params = {
                "author": author,
                "body": body,
                "lineage_id": lineage_id,
                "is_blocker": is_blocker
            }
            
            async with self._session.post(url, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("comment_id")
                else:
                    logger.warning(f"Failed to add comment: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return None
            
    async def get_task_comments(self, tenant_id: str, fsa_id: str, task_id: str,
                               limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent comments for a task."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/tasks/{tenant_id}/{fsa_id}/{task_id}/comments"
            params = {"limit": limit}
            
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("comments", [])
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []
            
    async def update_heartbeat(self, tenant_id: str, fsa_id: str, agent_name: str) -> bool:
        """Update agent heartbeat."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        try:
            url = f"{self.base_url}/agents/{tenant_id}/{fsa_id}/{agent_name}/heartbeat"
            
            async with self._session.post(url) as resp:
                if resp.status == 200:
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")
            return False
            
    def _create_agent_summary(self, state: Dict[str, Any]) -> str:
        """Create a focused summary for agent context."""
        parts = []
        
        # Current context
        active = state.get("active_state", {})
        if active:
            parts.append(f"Current: {active.get('current_sprint', 'N/A')} - {active.get('phase', 'N/A')}")
        
        # My tasks (would filter by assigned_team in real implementation)
        tasks = state.get("tasks", {})
        my_tasks = [t for t in tasks.values() if t.get("status") == "RUNNING"]
        if my_tasks:
            parts.append(f"Active tasks: {len(my_tasks)}")
        
        # Key constraints
        resources = state.get("resources", {})
        if "cash_balance_usd" in resources:
            parts.append(f"Budget: ${resources['cash_balance_usd']:,.0f}")
            
        # Recent metrics
        metrics = state.get("metrics", {})
        if metrics:
            key_metrics = []
            if "ctr_last_24h" in metrics:
                key_metrics.append(f"CTR: {metrics['ctr_last_24h']}%")
            if "daily_active_users" in metrics:
                key_metrics.append(f"DAU: {metrics['daily_active_users']:,}")
            if key_metrics:
                parts.append(" | ".join(key_metrics))
        
        return "\n".join(parts)
        

class StateAwareAgentHelper:
    """Helper for agents to work with comprehensive state."""
    
    def __init__(self, state_client: EnhancedStateMemoryClient):
        self.state_client = state_client
        
    async def get_my_tasks(self, state: EnhancedStateSnapshot, team: str) -> List[Dict[str, Any]]:
        """Get tasks assigned to my team."""
        my_tasks = []
        for task_id, task in state.state.get("tasks", {}).items():
            if task.get("assigned_team") == team:
                my_tasks.append(task)
        return my_tasks
        
    async def check_budget_available(self, state: EnhancedStateSnapshot, amount: float) -> bool:
        """Check if budget is available for spending."""
        current_balance = state.state.get("resources", {}).get("cash_balance_usd", 0)
        daily_limit = state.state.get("policy_caps", {}).get("max_po_per_day", float('inf'))
        
        # Would also check today's spending from audit trail
        return amount <= min(current_balance, daily_limit)
        
    async def get_task_context(self, state: EnhancedStateSnapshot, task_id: str,
                             include_comments: bool = True) -> Dict[str, Any]:
        """Get full context for a task including comments."""
        task = state.state.get("tasks", {}).get(task_id)
        if not task:
            return {}
            
        context = {
            "task": task,
            "depends_on": []
        }
        
        # Get dependency status
        for dep_id in task.get("depends_on", []):
            dep_task = state.state.get("tasks", {}).get(dep_id)
            if dep_task:
                context["depends_on"].append({
                    "task_id": dep_id,
                    "status": dep_task.get("status")
                })
        
        # Get recent comments
        if include_comments:
            comments = await self.state_client.get_task_comments(
                state.tenant_id, state.fsa_id, task_id
            )
            context["comments"] = comments
            
        return context
        
    def create_task_delta(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Create a delta for updating a task."""
        delta = {}
        for key, value in updates.items():
            delta[f"tasks.{task_id}.{key}"] = value
        delta[f"tasks.{task_id}.updated_at"] = datetime.utcnow().isoformat()
        return delta
        
    def create_metric_delta(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create a delta for updating metrics."""
        delta = {}
        for key, value in metrics.items():
            delta[f"metrics.{key}"] = value
        return delta