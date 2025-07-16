"""Slice-based state reading for efficiency."""

import fnmatch
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StateSliceReader:
    """Efficient slice-based state reading."""
    
    def extract_slice(self, state: Dict[str, Any], slice_pattern: str, 
                      k: Optional[int] = None) -> Dict[str, Any]:
        """
        Extract a slice of state matching the pattern.
        
        Args:
            state: Full state dictionary
            slice_pattern: Pattern like "task:DESIGN_*" or "resources.inventory"
            k: Limit number of results
            
        Returns:
            Sliced state containing only matching fields
        """
        if ":" in slice_pattern:
            # Handle patterns like "task:DESIGN_*"
            field, pattern = slice_pattern.split(":", 1)
            return self._extract_pattern_slice(state, field, pattern, k)
        else:
            # Handle direct paths like "resources.inventory"
            return self._extract_path_slice(state, slice_pattern)
    
    def _extract_pattern_slice(self, state: Dict[str, Any], field: str, 
                              pattern: str, k: Optional[int]) -> Dict[str, Any]:
        """Extract slice matching a pattern."""
        result = {}
        
        # Special handling for common fields
        if field == "task":
            tasks = state.get("tasks", {})
            matched_tasks = {}
            
            for task_id, task_data in tasks.items():
                if fnmatch.fnmatch(task_id, pattern):
                    matched_tasks[task_id] = task_data
                    if k and len(matched_tasks) >= k:
                        break
                        
            if matched_tasks:
                result["tasks"] = matched_tasks
                
        elif field == "metric":
            metrics = state.get("metrics", {})
            matched_metrics = {}
            
            for metric_name, value in metrics.items():
                if fnmatch.fnmatch(metric_name, pattern):
                    matched_metrics[metric_name] = value
                    if k and len(matched_metrics) >= k:
                        break
                        
            if matched_metrics:
                result["metrics"] = matched_metrics
                
        elif field == "agent":
            agents = state.get("agents_online", {})
            matched_agents = {}
            
            for agent_name, heartbeat in agents.items():
                if fnmatch.fnmatch(agent_name, pattern):
                    matched_agents[agent_name] = heartbeat
                    if k and len(matched_agents) >= k:
                        break
                        
            if matched_agents:
                result["agents_online"] = matched_agents
        
        # Always include version
        if "lineage_version" in state:
            result["lineage_version"] = state["lineage_version"]
            
        return result
    
    def _extract_path_slice(self, state: Dict[str, Any], path: str) -> Dict[str, Any]:
        """Extract slice for a specific path."""
        parts = path.split(".")
        current = state
        
        # Navigate to the value
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {"lineage_version": state.get("lineage_version", 0)}
        
        # Reconstruct the path in the result
        result = {"lineage_version": state.get("lineage_version", 0)}
        temp = result
        
        for i, part in enumerate(parts[:-1]):
            temp[part] = {}
            temp = temp[part]
            
        temp[parts[-1]] = current
        
        return result
    
    def create_slice_summary(self, slice_data: Dict[str, Any], 
                           context: str = "") -> str:
        """Create a summary for the slice."""
        parts = []
        
        if context:
            parts.append(f"Context: {context}")
            
        # Summarize tasks if present
        if "tasks" in slice_data:
            task_count = len(slice_data["tasks"])
            task_statuses = {}
            for task in slice_data["tasks"].values():
                status = task.get("status", "UNKNOWN")
                task_statuses[status] = task_statuses.get(status, 0) + 1
                
            parts.append(f"Tasks ({task_count}): " + 
                        ", ".join(f"{s}:{c}" for s, c in task_statuses.items()))
        
        # Summarize metrics if present
        if "metrics" in slice_data:
            parts.append(f"Metrics: {', '.join(slice_data['metrics'].keys())}")
            
        # Summarize agents if present
        if "agents_online" in slice_data:
            parts.append(f"Agents online: {len(slice_data['agents_online'])}")
        
        # Add any resource info
        if "resources" in slice_data:
            if "cash_balance_usd" in slice_data["resources"]:
                parts.append(f"Budget: ${slice_data['resources']['cash_balance_usd']:,.0f}")
                
        return "\n".join(parts) if parts else "Empty slice"


class SliceCache:
    """Cache for slice summaries."""
    
    def __init__(self, ttl_seconds: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        
    def get_cached_summary(self, tenant_id: str, fsa_id: str, 
                          version: int, slice_pattern: str) -> Optional[str]:
        """Get cached summary if available."""
        cache_key = f"{tenant_id}:{fsa_id}:{version}:{slice_pattern}"
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            # Check if still valid (simple TTL check)
            return entry.get("summary")
            
        return None
        
    def cache_summary(self, tenant_id: str, fsa_id: str, version: int,
                     slice_pattern: str, summary: str):
        """Cache a summary."""
        cache_key = f"{tenant_id}:{fsa_id}:{version}:{slice_pattern}"
        self.cache[cache_key] = {
            "summary": summary,
            "cached_at": datetime.utcnow()
        }
        
        # Simple cache eviction - keep last 1000 entries
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]["cached_at"])
            del self.cache[oldest_key]