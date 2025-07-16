"""
ADK Supabase Client implementation
"""

from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
import asyncio
from functools import wraps

from supabase import create_client, Client
from realtime.channel import Channel

from .types import (
    FSAState, FSADelta, Memory, Task, Agent, Project,
    TaskStatus, AgentStatus, MemoryType, ToolExecution,
    FSASliceResult, MemorySearchResult, TaskProgress,
    HealthCheck, ADKError
)


class ADKClient:
    """Main client for interacting with ADK Supabase backend"""
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        project_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.project_id = project_id
        self.tenant_id = tenant_id or "default"
        self._realtime_channels: Dict[str, Channel] = {}
    
    def _ensure_project_id(self) -> str:
        """Ensure project ID is set"""
        if not self.project_id:
            raise ADKError("Project ID not set. Call set_project() or create_project() first.")
        return self.project_id
    
    # Project Management
    
    async def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        budget: Optional[float] = None,
        agents: Optional[List[str]] = None
    ) -> str:
        """Create a new project"""
        response = await self.supabase.functions.invoke(
            "orchestrator/create-project",
            invoke_options={
                "body": {
                    "name": name,
                    "description": description,
                    "tenant_id": self.tenant_id,
                    "budget_total": budget,
                    "agents": agents
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to create project: {response.error}")
        
        self.project_id = response.data["project"]["id"]
        return self.project_id
    
    def set_project(self, project_id: str) -> None:
        """Set the active project ID"""
        self.project_id = project_id
    
    # FSA State Management
    
    async def get_state(
        self,
        fsa_id: str,
        version: Optional[int] = None,
        include_delta_history: bool = False
    ) -> FSAState:
        """Get FSA state"""
        response = await self.supabase.functions.invoke(
            "fsa-state/get",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "fsa_id": fsa_id,
                    "version": version,
                    "include_delta_history": include_delta_history
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to get state: {response.error}")
        
        return FSAState(**response.data)
    
    async def update_state(
        self,
        fsa_id: str,
        state: Dict[str, Any],
        actor: str,
        lineage_id: Optional[str] = None
    ) -> int:
        """Update FSA state completely"""
        response = await self.supabase.functions.invoke(
            "fsa-state/update",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "fsa_id": fsa_id,
                    "state": state,
                    "actor": actor,
                    "lineage_id": lineage_id or f"update-{datetime.now().timestamp()}"
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to update state: {response.error}")
        
        return response.data["version"]
    
    async def apply_delta(
        self,
        fsa_id: str,
        delta: List[FSADelta],
        actor: str,
        lineage_id: Optional[str] = None
    ) -> int:
        """Apply delta operations to FSA state"""
        response = await self.supabase.functions.invoke(
            "fsa-state/update",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "fsa_id": fsa_id,
                    "delta": [d.dict() if hasattr(d, 'dict') else d for d in delta],
                    "actor": actor,
                    "lineage_id": lineage_id or f"delta-{datetime.now().timestamp()}"
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to apply delta: {response.error}")
        
        return response.data["version"]
    
    async def query_slice(
        self,
        fsa_id: str,
        pattern: str,
        k: Optional[int] = None,
        use_cache: bool = True
    ) -> FSASliceResult:
        """Query a slice of FSA state"""
        response = await self.supabase.functions.invoke(
            "fsa-query/slice",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "fsa_id": fsa_id,
                    "pattern": pattern,
                    "k": k,
                    "use_cache": use_cache
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to query slice: {response.error}")
        
        return FSASliceResult(**response.data)
    
    async def query_multi_slice(
        self,
        fsa_id: str,
        slices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Query multiple slices at once"""
        response = await self.supabase.functions.invoke(
            "fsa-query/multi-slice",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "fsa_id": fsa_id,
                    "slices": slices
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to query multi-slice: {response.error}")
        
        return response.data
    
    # Memory Management (MemCube)
    
    async def create_memory(
        self,
        label: str,
        content: str,
        memory_type: MemoryType = MemoryType.PLAINTEXT,
        metadata: Optional[Dict[str, Any]] = None,
        pack_id: Optional[str] = None
    ) -> Memory:
        """Create a new memory"""
        response = await self.supabase.functions.invoke(
            "memories-crud/create",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "label": label,
                    "content": content,
                    "type": memory_type.value,
                    "metadata": metadata,
                    "pack_id": pack_id
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to create memory: {response.error}")
        
        return Memory(**response.data["memory"])
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemorySearchResult]:
        """Search memories semantically"""
        response = await self.supabase.functions.invoke(
            "memories-search/semantic",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "query": query,
                    "limit": limit,
                    "threshold": threshold,
                    "type": memory_type.value if memory_type else None
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to search memories: {response.error}")
        
        return [MemorySearchResult(**r) for r in response.data["results"]]
    
    async def get_memory(self, memory_id: str) -> Memory:
        """Get a specific memory"""
        response = await self.supabase.functions.invoke(
            "memories-crud/get",
            invoke_options={
                "body": {
                    "memory_id": memory_id
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to get memory: {response.error}")
        
        return Memory(**response.data["memory"])
    
    async def update_memory(
        self,
        memory_id: str,
        **updates
    ) -> Memory:
        """Update a memory"""
        response = await self.supabase.functions.invoke(
            "memories-crud/update",
            invoke_options={
                "body": {
                    "memory_id": memory_id,
                    **updates
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to update memory: {response.error}")
        
        return Memory(**response.data["memory"])
    
    async def delete_memory(self, memory_id: str) -> None:
        """Delete a memory"""
        response = await self.supabase.functions.invoke(
            "memories-crud/delete",
            invoke_options={
                "body": {
                    "memory_id": memory_id
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to delete memory: {response.error}")
    
    # Task Management
    
    async def create_task(
        self,
        task_id: str,
        task_type: str,
        title: str,
        description: Optional[str] = None,
        priority: int = 0,
        depends_on: Optional[List[str]] = None,
        estimated_hours: Optional[float] = None
    ) -> Task:
        """Create a new task"""
        response = await self.supabase.functions.invoke(
            "orchestrator/create-task",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "task_id": task_id,
                    "type": task_type,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "depends_on": depends_on,
                    "estimated_hours": estimated_hours
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to create task: {response.error}")
        
        return Task(**response.data["task"])
    
    async def assign_task(self, task_id: str, agent_id: str) -> None:
        """Assign a task to an agent"""
        response = await self.supabase.functions.invoke(
            "orchestrator/assign-task",
            invoke_options={
                "body": {
                    "task_id": task_id,
                    "agent_id": agent_id
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to assign task: {response.error}")
    
    async def get_next_task(self, agent_id: str) -> Optional[Task]:
        """Get next available task for an agent"""
        response = await self.supabase.functions.invoke(
            "orchestrator/get-next-task",
            invoke_options={
                "body": {
                    "agent_id": agent_id
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to get next task: {response.error}")
        
        task_data = response.data.get("task")
        return Task(**task_data) if task_data else None
    
    async def complete_task(
        self,
        task_id: str,
        agent_id: str,
        result: Optional[Any] = None,
        actual_hours: Optional[float] = None
    ) -> None:
        """Mark a task as completed"""
        response = await self.supabase.functions.invoke(
            "orchestrator/complete-task",
            invoke_options={
                "body": {
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "result": result,
                    "actual_hours": actual_hours
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to complete task: {response.error}")
    
    # Agent Management
    
    async def execute_task(
        self,
        agent_id: str,
        task_id: str,
        action: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        progress: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute task action as an agent"""
        response = await self.supabase.functions.invoke(
            "agent-execute/execute-task",
            invoke_options={
                "body": {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "project_id": self._ensure_project_id(),
                    "action": action,
                    "result": result,
                    "error": error,
                    "progress": progress
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to execute task action: {response.error}")
        
        return response.data
    
    async def update_progress(
        self,
        agent_id: str,
        task_id: str,
        progress: int,
        status_message: Optional[str] = None,
        intermediate_results: Optional[Any] = None
    ) -> None:
        """Update task progress"""
        response = await self.supabase.functions.invoke(
            "agent-execute/update-progress",
            invoke_options={
                "body": {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "progress": progress,
                    "status_message": status_message,
                    "intermediate_results": intermediate_results
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to update progress: {response.error}")
    
    async def request_tool(
        self,
        agent_id: str,
        task_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        wait_for_result: bool = False
    ) -> Any:
        """Request tool execution"""
        response = await self.supabase.functions.invoke(
            "agent-execute/request-tool",
            invoke_options={
                "body": {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "wait_for_result": wait_for_result
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to request tool: {response.error}")
        
        return response.data
    
    async def heartbeat(
        self,
        agent_id: str,
        status: AgentStatus = AgentStatus.ONLINE
    ) -> None:
        """Send agent heartbeat"""
        response = await self.supabase.functions.invoke(
            "orchestrator/agent-heartbeat",
            invoke_options={
                "body": {
                    "agent_id": agent_id,
                    "project_id": self._ensure_project_id(),
                    "status": status.value
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to send heartbeat: {response.error}")
    
    # Tool Execution
    
    async def execute_tool(
        self,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        task_id: Optional[str] = None,
        requires_approval: bool = False
    ) -> Any:
        """Execute a tool"""
        response = await self.supabase.functions.invoke(
            "orchestrator/execute-tool",
            invoke_options={
                "body": {
                    "agent_id": agent_id,
                    "project_id": self._ensure_project_id(),
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "task_id": task_id,
                    "requires_approval": requires_approval
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to execute tool: {response.error}")
        
        return response.data
    
    # Real-time Subscriptions
    
    def subscribe_to_state(
        self,
        fsa_id: str,
        callback: Callable[[FSAState], None]
    ) -> Callable[[], None]:
        """Subscribe to FSA state changes"""
        channel_name = f"fsa-{self.project_id}-{fsa_id}"
        
        # Unsubscribe existing channel if any
        if channel_name in self._realtime_channels:
            self._realtime_channels[channel_name].unsubscribe()
        
        async def on_state_change(payload):
            # Fetch latest state
            state = await self.get_state(fsa_id)
            callback(state)
        
        channel = (
            self.supabase.channel(channel_name)
            .on(
                "postgres_changes",
                {
                    "event": "INSERT",
                    "schema": "public",
                    "table": "events",
                    "filter": f"type=eq.fsa.state.updated&data->>project_id=eq.{self.project_id}&data->>fsa_id=eq.{fsa_id}"
                },
                on_state_change
            )
            .subscribe()
        )
        
        self._realtime_channels[channel_name] = channel
        
        def unsubscribe():
            channel.unsubscribe()
            self._realtime_channels.pop(channel_name, None)
        
        return unsubscribe
    
    def subscribe_to_tasks(
        self,
        callback: Callable[[Task], None]
    ) -> Callable[[], None]:
        """Subscribe to task changes"""
        channel_name = f"tasks-{self.project_id}"
        
        if channel_name in self._realtime_channels:
            self._realtime_channels[channel_name].unsubscribe()
        
        channel = (
            self.supabase.channel(channel_name)
            .on(
                "postgres_changes",
                {
                    "event": "*",
                    "schema": "public",
                    "table": "tasks",
                    "filter": f"project_id=eq.{self.project_id}"
                },
                lambda payload: callback(Task(**payload["new"]))
            )
            .subscribe()
        )
        
        self._realtime_channels[channel_name] = channel
        
        def unsubscribe():
            channel.unsubscribe()
            self._realtime_channels.pop(channel_name, None)
        
        return unsubscribe
    
    # Lifecycle Management
    
    async def cleanup(
        self,
        cleanup_type: str,
        older_than_hours: int = 24
    ) -> Dict[str, Any]:
        """Perform cleanup operations"""
        response = await self.supabase.functions.invoke(
            "lifecycle/cleanup",
            invoke_options={
                "body": {
                    "type": cleanup_type,
                    "project_id": self.project_id if cleanup_type == "states" else None,
                    "older_than_hours": older_than_hours
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to perform cleanup: {response.error}")
        
        return response.data["results"]
    
    async def archive_project(
        self,
        include_memories: bool = False,
        compress: bool = True
    ) -> str:
        """Archive the current project"""
        response = await self.supabase.functions.invoke(
            "lifecycle/archive-project",
            invoke_options={
                "body": {
                    "project_id": self._ensure_project_id(),
                    "include_memories": include_memories,
                    "compress": compress
                }
            }
        )
        
        if response.error:
            raise ADKError(f"Failed to archive project: {response.error}")
        
        return response.data["archive_id"]
    
    async def health_check(self) -> HealthCheck:
        """Perform system health check"""
        response = await self.supabase.functions.invoke(
            "lifecycle/health-check",
            invoke_options={"body": {}}
        )
        
        if response.error:
            raise ADKError(f"Failed to perform health check: {response.error}")
        
        return HealthCheck(**response.data)
    
    # Cleanup
    
    def disconnect(self) -> None:
        """Disconnect and cleanup resources"""
        for channel in self._realtime_channels.values():
            channel.unsubscribe()
        self._realtime_channels.clear()


# Factory function
def create_adk_client(
    supabase_url: str,
    supabase_key: str,
    project_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> ADKClient:
    """Create a new ADK client instance"""
    return ADKClient(supabase_url, supabase_key, project_id, tenant_id)